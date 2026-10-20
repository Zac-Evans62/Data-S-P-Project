"""Repetition analysis for the report (spec 4.2, "Length and repetition").

    python scripts/repetition_analysis.py --set evaluation
    python scripts/repetition_analysis.py --file some_text.txt

Shows:
  1. A synthetic demo: one word repeated 1,000 times scores exactly 0 or 1.
  2. The most repetitive unmarked passage in the set (lowest distinct/total
     ratio), with the words that contribute most to its score.
  3. Correlation between repetitiveness and score across the set.

Using --set evaluation requires frozen settings.
"""
import _bootstrap  # noqa: F401

import argparse
from collections import Counter

from wmark.config import REPO_ROOT, load_key, load_settings, require_frozen
from wmark.detector import GREEN, score_tokens, word_color
from wmark.manifest import read_manifest, select
from wmark.textproc import tokenize


def contributions(tokens, key, top=12):
    total = len(tokens)
    print(f"{'count':>5}  {'share':>6}  color  word")
    for w, n in Counter(tokens).most_common(top):
        c = "green" if word_color(w, key) == GREEN else "red"
        print(f"{n:5d}  {n / total:6.1%}  {c:5s}  {w}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--set", choices=["calibration", "evaluation"])
    g.add_argument("--file")
    args = ap.parse_args()

    settings = load_settings()
    key = load_key(settings)

    print("1) Synthetic repetition demo")
    for word in ["the", "and", "of", "watermark"]:
        r = score_tokens([word] * 1000, key)
        print(f"   '{word}' x 1000 -> green fraction {r.score:.0f}  (distinct words: {r.distinct})")
    print("   1,000 occurrences, but only ONE color assignment: the score is all-or-nothing.\n")

    if args.file:
        toks = tokenize(open(args.file, encoding="utf-8").read())
        r = score_tokens(toks, key)
        print(f"2) {args.file}: {r.total} words, {r.distinct} distinct, score {r.score:.4f}")
        contributions(toks, key)
        return

    if args.set == "evaluation":
        require_frozen(settings)
    rows = select(read_manifest(), collection="unmarked", set_=args.set)
    # Repetitiveness = share of all word occurrences taken by the 5 most
    # frequent words. (distinct/total is also reported, but it falls with
    # length for any text, so it mostly measures length.)
    data = []
    for row in rows:
        toks = tokenize((REPO_ROOT / row["file"]).read_text(encoding="utf-8"))
        r = score_tokens(toks, key)
        top5 = sum(n for _, n in Counter(toks).most_common(5)) / r.total
        data.append({"id": row["id"], "group": row["length_group"], "top5": top5, "score": r.score, "toks": toks, "r": r})
    worst = max(data, key=lambda d: d["top5"])
    r = worst["r"]
    print(f"2) Most repetitive {args.set} passage: {worst['id']} ({worst['group']})")
    print(f"   {r.total} words, {r.distinct} distinct (ratio {r.distinct / r.total:.2f}), green fraction {r.score:.4f}")
    print(f"   The 5 most frequent words make up {worst['top5']:.0%} of all word occurrences.")
    contributions(worst["toks"], key)
    print("   Each row is ONE color decision; its share is how much that single coin flip moves the score.\n")

    # Within each length group (so length is held roughly fixed), compare how
    # far scores stray from 0.5 for more vs less repetitive passages.
    print("3) Mean distance of score from 0.5, within each length group")
    print(f"   {'group':7s} {'more repetitive half':>22s} {'less repetitive half':>22s}")
    for g in ("short", "medium", "long"):
        xs = sorted((d for d in data if d["group"] == g), key=lambda d: -d["top5"])
        if len(xs) < 2:
            continue
        half = len(xs) // 2
        spread = lambda ys: sum(abs(y["score"] - 0.5) for y in ys) / len(ys)  # noqa: E731
        print(f"   {g:7s} {spread(xs[:half]):22.4f} {spread(xs[half:]):22.4f}")
    print("   Expect larger spread for more repetitive text: fewer independent color decisions.")


if __name__ == "__main__":
    main()
