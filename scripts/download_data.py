"""Download the public source dataset; raw files stay ignored by Git."""

import shutil
import urllib.request
import zipfile
from pathlib import Path

destination = Path(__file__).resolve().parents[1] / "data" / "raw"
destination.mkdir(parents=True, exist_ok=True)
archive = destination / "twcs.zip"
url = "https://www.kaggle.com/api/v1/datasets/download/thoughtvector/customer-support-on-twitter"
if not archive.exists():
    temporary = archive.with_suffix(".part")
    with (
        urllib.request.urlopen(url, timeout=60) as response,
        temporary.open("wb") as target,
    ):
        shutil.copyfileobj(response, target)
    temporary.replace(archive)
with zipfile.ZipFile(archive) as zipped:
    member = next(n for n in zipped.namelist() if n.endswith("twcs.csv"))
    with zipped.open(member) as source, (destination / "twcs.csv").open("wb") as target:
        shutil.copyfileobj(source, target)
print("Raw dataset ready. Source attribution: docs/data_card.md")
