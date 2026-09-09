"""Inspectable unigram TF-IDF retrieval with normalized cosine similarity."""

import math
import re
from collections import Counter, defaultdict

STOP = set(
    "a an the to of and is it i you my me for on in at with this that your user link we our be have has".split()
)


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


class Retriever:
    def __init__(self, corpus):
        self.corpus = corpus
        counts = [Counter(tokens(e["text"])) for e in corpus]
        df = Counter(t for c in counts for t in c)
        self.idf = {t: math.log((1 + len(corpus)) / (1 + n)) + 1 for t, n in df.items()}
        self.postings = defaultdict(list)
        for index, count in enumerate(counts):
            for token, weight in self.vector(count).items():
                self.postings[token].append((index, weight))

    def vector(self, count):
        vector = {
            t: (1 + math.log(n)) * self.idf[t]
            for t, n in count.items()
            if t in self.idf
        }
        norm = math.sqrt(sum(w * w for w in vector.values())) or 1
        return {t: w / norm for t, w in vector.items()}

    def search(self, text, k=3, excluded_group=None):
        scores = defaultdict(float)
        for token, weight in self.vector(Counter(tokens(text))).items():
            for index, other in self.postings[token]:
                if self.corpus[index]["group_id"] != excluded_group:
                    scores[index] += weight * other
        ranked = sorted(scores, key=lambda i: (-scores[i], self.corpus[i]["id"]))[:k]
        return [{**self.corpus[i], "score": round(scores[i], 6)} for i in ranked]
