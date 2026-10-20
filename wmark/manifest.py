"""The passage manifest: data/manifest.csv, one row per candidate passage.

Columns
-------
id                passage id, e.g. "austen_pride_0012"
book_id           source document id (file stem in data/sources/)
source_title      from data/sources/sources.csv
source_url        from data/sources/sources.csv
file              passage text file, relative to repo root
word_count        total normalized words
distinct_words    distinct normalized words
length_group      short (30-99) | medium (100-199) | long (200-400)
collection        unmarked | watermark | unused   (set by split_data.py)
set               calibration | evaluation | ""    (set by split_data.py)
forgery_selected  "yes" for the 5 query-forgery passages, else ""
notes             free text
"""

from __future__ import annotations

import csv
from pathlib import Path

from .config import MANIFEST_PATH

FIELDS = [
    "id", "book_id", "source_title", "source_url", "file",
    "word_count", "distinct_words", "length_group",
    "collection", "set", "forgery_selected", "notes",
]

# Inclusive word-count ranges for the three length groups (spec 4.1).
LENGTH_GROUPS = {
    "short": (30, 99),
    "medium": (100, 199),
    "long": (200, 400),
}


def length_group(n_words: int) -> str | None:
    for name, (lo, hi) in LENGTH_GROUPS.items():
        if lo <= n_words <= hi:
            return name
    return None


def read_manifest(path: Path = MANIFEST_PATH) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"No manifest at {path}. Run scripts/collect_passages.py first.")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_manifest(rows: list[dict], path: Path = MANIFEST_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def select(rows: list[dict], *, collection: str | None = None, set_: str | None = None) -> list[dict]:
    out = rows
    if collection is not None:
        out = [r for r in out if r["collection"] == collection]
    if set_ is not None:
        out = [r for r in out if r["set"] == set_]
    return out
