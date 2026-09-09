"""Run final inference and judge evaluation after genuine human annotation."""

import subprocess
import sys
from pathlib import Path
from hiver_support.annotations import validate_annotation
from hiver_support.io import load_env, read_jsonl
from hiver_support.provider import Provider

root = Path(__file__).resolve().parents[1]
load_env(root / ".env")
examples = read_jsonl(root / "data/processed/candidates.jsonl")
eligible = [
    e
    for e in examples
    if not validate_annotation(e.get("annotation")) and e["annotation"]["eligible"]
]
if not 150 <= len(eligible) <= 250:
    raise SystemExit(
        "Complete 150–250 eligible human annotations in the dashboard before final evaluation."
    )
Provider()  # Validate configuration before changing result artifacts.
commands = [
    ["run", "--systems", "trivial", "simple", "agent"],
    ["review-packet", "--count", "40"],
    ["review-packet", "--name", "judge", "--pool", "heldout", "--count", "150"],
    ["judge", "--packet", "artifacts/judge_packet.jsonl"],
    ["evaluate"],
    ["stress", "--systems", "agent", "--partition", "development"],
]
for command in commands:
    subprocess.run(
        [sys.executable, "-m", "hiver_support.cli", *command], cwd=root, check=True
    )
print(
    "Next: complete the blinded human reply ratings, then run agreement and readiness."
)
