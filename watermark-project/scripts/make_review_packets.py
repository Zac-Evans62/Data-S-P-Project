"""Make blind quality-check packets for finished watermarking outputs.

    python scripts/make_review_packets.py --set calibration
    python scripts/make_review_packets.py --set evaluation

For every watermark passage in the set with a final.txt, writes
quality_checks/packets/<set>/<id>.md containing the EDITED text, the
ORIGINAL text and a word diff, but NO scores, NO detector decision and NO
indication of whether the target was reached.

It also adds a blank row per passage to quality_checks/reviews.csv with the
editor filled in. The reviewer (anyone but the editor) reads the packet and
fills in reviewer, meaning_preserved (yes/no), readable (yes/no), notes and
reviewed_at. Commit reviews.csv BEFORE looking at the scores.
"""
import _bootstrap  # noqa: F401

import argparse
import json

from wmark.config import QUALITY_DIR, REPO_ROOT, WATERMARKED_DIR
from wmark.manifest import read_manifest, select
from wmark.metrics import word_diff
from wmark.reviews import read_reviews, write_reviews
from wmark.textproc import tokenize

TEMPLATE = """# Quality check: {pid}

Editor: {editor}. **You must not be the editor.** Do not run any scoring
script on this text before your answers are recorded in
`quality_checks/reviews.csv`.

Answer two questions, yes or no:

1. **Meaning preserved?** Does the edited version keep the main meaning of the original?
2. **Readable?** Is the edited version readable prose?

Both must be yes for the output to count as usable.

---

## Edited version (read this first, on its own, for readability)

{edited}

---

## Original version

{original}

---

## Word diff (normalized words; [-removed-] {{+added+}})

{diff}
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", required=True, choices=["calibration", "evaluation"])
    args = ap.parse_args()

    rows = select(read_manifest(), collection="watermark", set_=args.set)
    reviews = read_reviews()
    have = {(r["passage_id"], r["stage"]) for r in reviews}
    out_dir = QUALITY_DIR / "packets" / args.set
    out_dir.mkdir(parents=True, exist_ok=True)

    made, missing = 0, []
    for row in rows:
        pid = row["id"]
        final = WATERMARKED_DIR / pid / "final.txt"
        if not final.exists():
            missing.append(pid)
            continue
        log = json.loads((WATERMARKED_DIR / pid / "log.json").read_text(encoding="utf-8"))
        original = (REPO_ROOT / row["file"]).read_text(encoding="utf-8").strip()
        edited = final.read_text(encoding="utf-8").strip()
        (out_dir / f"{pid}.md").write_text(TEMPLATE.format(
            pid=pid, editor=log["editor"], edited=edited, original=original,
            diff=word_diff(tokenize(original), tokenize(edited))), encoding="utf-8")
        made += 1
        if (pid, "watermark") not in have:
            reviews.append({"passage_id": pid, "set": args.set, "stage": "watermark", "editor": log["editor"]})

    write_reviews(reviews)
    print(f"Wrote {made} packets to {out_dir.relative_to(REPO_ROOT)}")
    if missing:
        print(f"Not finished yet (no final.txt): {', '.join(missing)}")
    print("Reviewers: fill in quality_checks/reviews.csv, then commit it before anyone looks at scores.")


if __name__ == "__main__":
    main()
