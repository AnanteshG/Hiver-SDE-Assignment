"""Recompute metrics from frozen artifacts; no credentials or raw download needed."""

import subprocess
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parents[1]
start = time.perf_counter()
for command in ["validate", "evaluate", "readiness"]:
    subprocess.run(
        [sys.executable, "-m", "hiver_support.cli", command], cwd=root, check=True
    )
print(
    f"Cached reproduction completed in {time.perf_counter() - start:.2f}s. This did not run fresh model inference."
)
