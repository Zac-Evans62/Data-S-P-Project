"""Cut public-domain books into candidate passages and write the manifest.

Input
-----
data/sources/<book_id>.txt     plain-text books (e.g. Project Gutenberg "Plain Text UTF-8")
data/sources/sources.csv       one row per book: book_id,title,author,url,license

Output
------
data/passages/<id>.txt         one file per candidate passage
data/manifest.csv              one row per candidate (collection/set left blank)

    python scripts/collect_passages.py
    python scripts/collect_passages.py --max-per-book 30

Collect MORE candidates than you need (aim for 500+ from 15+ books).
split_data.py then picks exactly 300 unmarked + 15 watermark passages.
Using many books matters: passages from one book are correlated, and all of
a book's passages must go to the same set.

How passages are cut: Gutenberg header/footer is stripped, the text is
split into paragraphs at blank lines, and consecutive paragraphs are joined
until the word count reaches a random target inside the current length
group. Groups rotate short -> medium -> long so every book yields a mix.
Paragraphs that look like headings (few words, mostly capitals, "CHAPTER")
are skipped. Read a sample of the output: poetry, tables of contents and
footnotes can slip through; delete bad passage rows by hand if needed.
"""
import _bootstrap  # noqa: F401

import argparse
import csv
import hashlib
import random
import re

from wmark.config import MANIFEST_PATH, PASSAGES_DIR, REPO_ROOT, SOURCES_DIR, load_settings
from wmark.manifest import LENGTH_GROUPS, length_group, write_manifest
from wmark.textproc import tokenize

GROUP_ORDER = ["short", "medium", "long"]
START_RE = re.compile(r"^\*\*\*\s*START OF.*$", re.MULTILINE | re.IGNORECASE)
END_RE = re.compile(r"^\*\*\*\s*END OF.*$", re.MULTILINE | re.IGNORECASE)


def strip_gutenberg(text: str) -> str:
    m = START_RE.search(text)
    if m:
        text = text[m.end():]
    m = END_RE.search(text)
    if m:
        text = text[: m.start()]
    return text


def paragraphs(text: str) -> list[str]:
    text = text.replace("\r\n", "\n")
    paras = []
    for block in re.split(r"\n\s*\n", text):
        p = " ".join(line.strip() for line in block.splitlines()).strip()
        if p:
            paras.append(p)
    return paras


def looks_like_heading(p: str) -> bool:
    letters = [c for c in p if c.isalpha()]
    if not letters:
        return True
    upper = sum(c.isupper() for c in letters) / len(letters)
    return (
        len(tokenize(p)) < 5
        or upper > 0.5
        or p.upper().startswith(("CHAPTER", "BOOK ", "PART ", "[ILLUSTRATION", "CONTENTS"))
    )


def cut_book(paras: list[str], rng: random.Random) -> list[str]:
    out = []
    gi = rng.randrange(3)

    def new_target():
        lo, hi = LENGTH_GROUPS[GROUP_ORDER[gi]]
        return lo, hi, rng.randint(lo, hi)

    lo, hi, target = new_target()
    cur, count = [], 0
    for p in paras:
        if looks_like_heading(p):
            cur, count = [], 0  # don't join across a heading
            continue
        n = len(tokenize(p))
        if count + n > hi:
            if count >= lo:
                out.append("\n\n".join(cur))
                gi = (gi + 1) % 3
                lo, hi, target = new_target()
            cur, count = [], 0
            if n > hi:
                continue
        cur.append(p)
        count += n
        if count >= target:
            out.append("\n\n".join(cur))
            gi = (gi + 1) % 3
            lo, hi, target = new_target()
            cur, count = [], 0
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-per-book", type=int, default=40,
                    help="cap candidates per book so no single book dominates (default 40)")
    ap.add_argument("--force", action="store_true", help="overwrite a manifest that already has set assignments")
    args = ap.parse_args()

    settings = load_settings()
    rng = random.Random(settings["seed"])

    if MANIFEST_PATH.exists() and not args.force:
        with open(MANIFEST_PATH, newline="", encoding="utf-8") as f:
            if any(r.get("set") for r in csv.DictReader(f)):
                raise SystemExit("Manifest already has set assignments. Re-collecting would invalidate the split. Use --force only if you mean it.")

    meta_path = SOURCES_DIR / "sources.csv"
    if not meta_path.exists():
        raise SystemExit(f"Missing {meta_path}. See data/sources/README.md.")
    # utf-8-sig: tolerate the invisible BOM Excel adds; skip blank rows like ",,,,,"
    with open(meta_path, newline="", encoding="utf-8-sig") as f:
        meta = {r["book_id"].strip(): r for r in csv.DictReader(f) if (r.get("book_id") or "").strip()}

    books = sorted(SOURCES_DIR.glob("*.txt"))
    if not books:
        raise SystemExit(f"No .txt books in {SOURCES_DIR}.")

    PASSAGES_DIR.mkdir(parents=True, exist_ok=True)
    for old in PASSAGES_DIR.glob("*.txt"):
        old.unlink()

    rows, seen = [], set()
    for path in books:
        book_id = path.stem
        if book_id not in meta:
            print(f"warning: {book_id} has no row in sources.csv; skipping")
            continue
        text = strip_gutenberg(path.read_text(encoding="utf-8", errors="replace"))
        cands = cut_book(paragraphs(text), rng)
        if len(cands) > args.max_per_book:
            keep = sorted(rng.sample(range(len(cands)), args.max_per_book))
            cands = [cands[i] for i in keep]
        n_book = 0
        for passage in cands:
            toks = tokenize(passage)
            group = length_group(len(toks))
            digest = hashlib.sha256(" ".join(toks).encode()).hexdigest()
            if group is None or digest in seen:
                continue
            seen.add(digest)
            n_book += 1
            pid = f"{book_id}_{n_book:04d}"
            out = PASSAGES_DIR / f"{pid}.txt"
            out.write_text(passage + "\n", encoding="utf-8")
            rows.append({
                "id": pid,
                "book_id": book_id,
                "source_title": meta[book_id].get("title", ""),
                "source_url": meta[book_id].get("url", ""),
                "file": str(out.relative_to(REPO_ROOT)),
                "word_count": len(toks),
                "distinct_words": len(set(toks)),
                "length_group": group,
                "collection": "",
                "set": "",
                "forgery_selected": "",
                "notes": "",
            })
        print(f"{book_id:30s} {n_book:4d} passages")

    write_manifest(rows)
    by_group = {g: sum(r["length_group"] == g for r in rows) for g in GROUP_ORDER}
    print(f"\n{len(rows)} candidate passages from {len(books)} books: {by_group}")
    print(f"Manifest written to {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print("Need at least: 300 unmarked (>= 60 per group across both sets) + 15 medium for watermarking.")


if __name__ == "__main__":
    main()
