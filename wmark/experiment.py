"""Shared helpers for the calibration and evaluation runs."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from fractions import Fraction
from pathlib import Path

from .config import REPO_ROOT, RESULTS_DIR, WATERMARKED_DIR, key_fingerprint
from .detector import is_flagged, score_tokens
from .metrics import changed_words
from .reviews import read_reviews, review_status
from .textproc import tokenize


def new_run_dir(kind: str) -> Path:
    """results/<kind>/run_<timestamp>/ - never overwrite an earlier run."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    d = RESULTS_DIR / kind / f"run_{stamp}"
    d.mkdir(parents=True, exist_ok=False)
    return d


def snapshot_settings(run_dir: Path, settings: dict, key: bytes) -> None:
    snap = dict(settings, key_fingerprint=key_fingerprint(key), run_at=datetime.now().isoformat())
    (run_dir / "settings_used.json").write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def score_unmarked(rows: list[dict], key: bytes, threshold=None) -> list[dict]:
    out = []
    for r in rows:
        toks = tokenize((REPO_ROOT / r["file"]).read_text(encoding="utf-8"))
        s = score_tokens(toks, key)
        rec = {
            "id": r["id"], "book_id": r["book_id"], "length_group": r["length_group"],
            "total_words": s.total, "distinct_words": s.distinct,
            "distinct_ratio": round(s.distinct / s.total, 4),
            "green_words": s.green, "green_fraction": round(s.score, 6),
            "_fraction": s.fraction,
        }
        if threshold is not None:
            rec["flagged"] = is_flagged(s, threshold)
        out.append(rec)
    return out


def watermark_records(rows: list[dict], key: bytes, threshold=None) -> list[dict]:
    reviews = {(r["passage_id"], r["stage"]): r for r in read_reviews()}
    out = []
    for r in rows:
        pid = r["id"]
        orig_toks = tokenize((REPO_ROOT / r["file"]).read_text(encoding="utf-8"))
        orig = score_tokens(orig_toks, key)
        rec = {
            "id": pid, "book_id": r["book_id"], "forgery_selected": r["forgery_selected"],
            "original_total_words": orig.total, "original_green_fraction": round(orig.score, 6),
        }
        final = WATERMARKED_DIR / pid / "final.txt"
        log_path = WATERMARKED_DIR / pid / "log.json"
        if not final.exists():
            rec.update(status="not finished", final_green_fraction="", reached_target="",
                       changed_words="", minutes_used="", stop_reason="", editor="",
                       quality="not reviewed", quality_problems="", _final_fraction=None)
            out.append(rec)
            continue
        log = json.loads(log_path.read_text(encoding="utf-8"))
        fin_toks = tokenize(final.read_text(encoding="utf-8"))
        fin = score_tokens(fin_toks, key)
        quality, problems = review_status(reviews.get((pid, "watermark")))
        rec.update(
            status="finished", target=log["target"],
            final_total_words=fin.total, final_green_fraction=round(fin.score, 6),
            reached_target=fin.fraction >= Fraction(log["target"]),
            changed_words=changed_words(orig_toks, fin_toks),
            minutes_used=log.get("minutes_used", ""), stop_reason=log["stop_reason"],
            versions_saved=len(log["versions"]), editor=log["editor"],
            quality=quality, quality_problems="; ".join(problems),
            _final_fraction=fin.fraction,
        )
        if threshold is not None:
            rec["original_flagged"] = is_flagged(orig, threshold)
            rec["final_flagged"] = is_flagged(fin, threshold)
        out.append(rec)
    return out


def public(rows: list[dict]) -> list[dict]:
    """Drop internal fields (starting with _) before writing CSVs."""
    return [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
