"""Stream Twitter CSV; reconstruct observed reply paths without future leakage."""
import csv
import html
import hashlib
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from email.utils import parsedate_to_datetime

from .io import fingerprint, write_json, write_jsonl


def sanitize(text):
    text = html.unescape(text)
    text = re.sub(r"https?://\S+", "[link]", text)
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[email]", text)
    text = re.sub(r"@[\w]+", "@user", text)
    text = re.sub(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)", "[number]", text)
    return " ".join(text.split())


def normalized(text):
    return " ".join(re.findall(r"[a-z]+", sanitize(text).lower().replace("@user", "")))


def rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def audit(path):
    brands = Counter()
    count = 0
    for row in rows(path):
        count += 1
        if row["inbound"].lower() == "false":
            brands[row["author_id"]] += 1
    return {"total_tweets": count, "brand_outbound_counts": brands.most_common()}


def prepare(path, brand, output, seed=42, max_corpus=5000):
    # First pass collects the brand and direct parent IDs. Second pass collects
    # inbound tweets only. Raw text is never copied into the public artifacts.
    brand_rows = {}
    customer_ids = set()
    for row in rows(path):
        if row["author_id"].lower() == brand.lower() and row["inbound"].lower() == "false":
            brand_rows[row["tweet_id"]] = row
            if row["in_response_to_tweet_id"]:
                customer_ids.add(row["in_response_to_tweet_id"])
    if not brand_rows:
        raise ValueError(f"Brand not found: {brand}")
    nodes = dict(brand_rows)
    for row in rows(path):
        if row["inbound"].lower() == "true":
            # Include inbound replies to brand turns as well as direct requests.
            if row["tweet_id"] in customer_ids or row["in_response_to_tweet_id"] in brand_rows:
                nodes[row["tweet_id"]] = row
    parents = {key: key for key in nodes}

    def root(key):
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    def union(a, b):
        a, b = root(a), root(b)
        parents[max(a, b)] = min(a, b)

    for key, row in nodes.items():
        parent = row["in_response_to_tweet_id"]
        if parent in nodes:
            union(key, parent)
    # Near duplicates: discard punctuation/handles/URLs and group token signatures.
    signatures = {}
    for key in sorted(customer_ids):
        if key not in nodes:
            continue
        signature = normalized(nodes[key]["text"])
        if signature in signatures:
            union(key, signatures[signature])
        signatures[signature] = key
    replies = defaultdict(list)
    for key, row in brand_rows.items():
        replies[row["in_response_to_tweet_id"]].append(row)
    examples = []
    missing_parent = 0
    for key in sorted(customer_ids):
        if key not in nodes:
            continue
        row = nodes[key]
        context, visited = [], {key}
        parent = row["in_response_to_tweet_id"]
        incomplete = False
        while parent:
            if parent not in nodes or parent in visited:
                incomplete = True
                break
            visited.add(parent)
            ancestor = nodes[parent]
            context.append({"tweet_id": parent, "role": "customer" if ancestor["inbound"].lower() == "true" else "brand", "text": sanitize(ancestor["text"])})
            parent = ancestor["in_response_to_tweet_id"]
        missing_parent += incomplete
        response = min(replies[key], key=lambda r: (parsedate_to_datetime(r["created_at"]), r["tweet_id"]))
        examples.append({
            "id": "tw_" + key, "tweet_id": key, "group_id": root(key), "brand": brand,
            "text": sanitize(row["text"]), "context": list(reversed(context[:8])),
            "context_incomplete": incomplete, "created_at": row["created_at"],
            "historical_reply": sanitize(response["text"]), "reply_id": response["tweet_id"],
            "evidence_type": "observed_response", "source": "thoughtvector/customer-support-on-twitter",
        })
    # Stable group-level assignment, independent of CSV ordering.
    pools = defaultdict(list)
    for example in examples:
        bucket = int(hashlib.sha256(f"{seed}:{example['group_id']}".encode()).hexdigest()[:8], 16) % 100
        pools["retrieval" if bucket < 70 else "development" if bucket < 80 else "test"].append(example)
    rng = random.Random(seed)
    for pool in pools.values():
        rng.shuffle(pool)

    def unique_groups(pool):
        seen = set()
        selected = []
        for example in pool:
            if example["group_id"] not in seen:
                selected.append(example)
                seen.add(example["group_id"])
        return selected

    development = unique_groups(pools["development"])[:50]
    test_pool = unique_groups(pools["test"])
    representative = test_pool[:120]
    remainder = test_pool[120:]
    # Heuristic challenge selection is disclosed, not a human risk label.
    challenge = sorted(remainder, key=lambda e: (
        -(3 * e["context_incomplete"] + (len(e["text"].split()) < 7) + bool(re.search(r"refund|charge|password|hacked|again|still|not", e["text"], re.I))), e["id"]
    ))[:30]
    corpus = pools["retrieval"][:max_corpus]
    candidates = []
    for partition, selected in [("development", development), ("representative", representative), ("challenge", challenge)]:
        for example in selected:
            candidates.append({**example, "partition": partition, "annotation": None})
    if len(candidates) < 200:
        raise ValueError("Not enough independent conversation groups for 200 examples; choose a larger brand.")
    output = Path(output)
    write_jsonl(output / "corpus.jsonl", corpus)
    write_jsonl(output / "candidates.jsonl", candidates)
    report = {
        "brand": brand, "seed": seed, "brand_tweets": len(brand_rows), "usable_customer_turns": len(examples),
        "incomplete_context_examples": missing_parent, "corpus_size": len(corpus),
        "partitions": dict(Counter(e["partition"] for e in candidates)),
        "corpus_hash": fingerprint(corpus), "candidates_hash": fingerprint(candidates),
        "deduplication": "normalized exact text; semantic paraphrases may remain",
        "scope": "linked brand/customer paths only; no language filtering, English eligibility requires human review",
        "challenge_sampling": "ranked for missing context, short messages, and risk/ambiguity keywords",
    }
    write_json(output / "audit.json", report)
    return report


def validate_splits(corpus, candidates):
    errors = []
    corp_groups = {e["group_id"] for e in corpus}
    corp_ids = {e["id"] for e in corpus}
    corp_text = {normalized(e["text"]) for e in corpus}
    partitions = {}
    ids = set()
    for example in candidates:
        if example["id"] in ids:
            errors.append(f"duplicate candidate ID: {example['id']}")
        ids.add(example["id"])
        if example["group_id"] in corp_groups or example["id"] in corp_ids or normalized(example["text"]) in corp_text:
            errors.append(f"retrieval leakage: {example['id']}")
        previous = partitions.setdefault(example["group_id"], example["partition"])
        if previous != example["partition"]:
            errors.append(f"cross-partition group: {example['group_id']}")
        context_ids = {turn["tweet_id"] for turn in example["context"]}
        if example["tweet_id"] in context_ids or example["reply_id"] in context_ids:
            errors.append(f"future/input leakage: {example['id']}")
    return errors
