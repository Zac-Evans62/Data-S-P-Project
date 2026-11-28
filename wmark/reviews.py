"""Quality-check records: quality_checks/reviews.csv.

One row per reviewed output. The reviewer fills meaning_preserved and
readable with yes/no BEFORE seeing any score or detector decision.
"""

from __future__ import annotations

import csv

from .config import REVIEWS_PATH

FIELDS = ["passage_id", "set", "stage", "editor", "reviewer",
          "meaning_preserved", "readable", "notes", "reviewed_at"]


def read_reviews() -> list[dict]:
    if not REVIEWS_PATH.exists():
        return []
    with open(REVIEWS_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_reviews(rows: list[dict]) -> None:
    REVIEWS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REVIEWS_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def review_status(row: dict | None) -> tuple[str, list[str]]:
    """Return ("usable" | "not usable" | "not reviewed" | "invalid review", problems).

    Only "usable" counts toward the usable success rate.
    """
    if row is None:
        return "not reviewed", ["no row in quality_checks/reviews.csv"]
    m = row.get("meaning_preserved", "").strip().lower()
    r = row.get("readable", "").strip().lower()
    if m not in ("yes", "no") or r not in ("yes", "no"):
        return "not reviewed", ["meaning_preserved and readable must both be yes or no"]
    reviewer = row.get("reviewer", "").strip().lower()
    if not reviewer:
        return "invalid review", ["reviewer name missing"]
    if reviewer == row.get("editor", "").strip().lower():
        return "invalid review", ["reviewer is the editor; a different teammate must review"]
    return ("usable" if m == r == "yes" else "not usable"), []
