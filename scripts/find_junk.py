"""Find (and optionally remove) candidate passages that are probably not prose.

    python scripts/find_junk.py                      # list suspects with reasons
    python scripts/find_junk.py --remove ID1 ID2 ... # delete those passages + manifest rows

Run AFTER your final collect_passages.py and BEFORE split_data.py.
(Re-running collect_passages.py recreates everything, so removals would be lost.)

A suspect is not automatically junk: open each one and decide. Remove only
passages that are not ordinary prose (tables of contents, chapter lists,
footnotes, letter headers, indexes, transcriber's notes, poetry, lists).
Note in the report how many were removed and why.
"""
import _bootstrap  # noqa: F401

import argparse
import re

from wmark.config import REPO_ROOT
from wmark.manifest import read_manifest, write_manifest

KEYWORDS = re.compile(
    r"\b(contents|chapter|illustration|footnote|transcriber|gutenberg|appendix|index|"
    r"preface|copyright|ebook|vol\.|page)\b", re.IGNORECASE)
ROMAN_RUN = re.compile(r"(\b[IVXLC]+\.\s*){3,}")


def reasons_for(text: str) -> list[str]:
    reasons = []
    found = sorted({m.group(0).lower() for m in KEYWORDS.finditer(text)})
    if found:
        reasons.append("keywords: " + ", ".join(found))
    if ROMAN_RUN.search(text):
        reasons.append("run of roman numerals (chapter list?)")
    letters = [c for c in text if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.15:
        reasons.append("lots of CAPITALS")
    digits = sum(c.isdigit() for c in text)
    if digits > 15:
        reasons.append(f"{digits} digits")
    if text.count("[") + text.count("*") > 3:
        reasons.append("brackets/asterisks (notes?)")
    sentences = max(1, len(re.findall(r"[.!?]", text)))
    words = len(text.split())
    if words / sentences > 60:
        reasons.append("very long or missing sentences (list/poetry?)")
    return reasons


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--remove", nargs="+", metavar="ID", help="passage ids to delete")
    args = ap.parse_args()
    rows = read_manifest()
    if any(r["set"] for r in rows):
        raise SystemExit("Manifest is already split; removing passages now would break the split.")

    if args.remove:
        ids = set(args.remove)
        unknown = ids - {r["id"] for r in rows}
        if unknown:
            raise SystemExit(f"Unknown ids: {', '.join(sorted(unknown))}")
        for r in rows:
            if r["id"] in ids:
                (REPO_ROOT / r["file"]).unlink(missing_ok=True)
        rows = [r for r in rows if r["id"] not in ids]
        write_manifest(rows)
        print(f"Removed {len(ids)} passages. {len(rows)} candidates remain.")
        return

    n = 0
    for r in rows:
        text = (REPO_ROOT / r["file"]).read_text(encoding="utf-8")
        why = reasons_for(text)
        if why:
            n += 1
            print(f"{r['id']:35s} {r['file']}\n    " + "; ".join(why))
    print(f"\n{n} suspects out of {len(rows)} candidates. Open each, then remove the real junk with --remove.")


if __name__ == "__main__":
    main()