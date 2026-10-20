"""Score any text file (or stdin) with the detector.

    python scripts/score.py some_passage.txt
    echo "The cat sat on the mat" | python scripts/score.py -
    python scripts/score.py file.txt --threshold 0.60 --colors

Uses the threshold from config/settings.json unless --threshold is given.
--colors prints each distinct word with its color (debugging only; do not
show this to the quality-check reviewer).
"""
import _bootstrap  # noqa: F401

import argparse
import sys
from collections import Counter

from wmark.config import load_key, load_settings
from wmark.detector import EmptyInputError, GREEN, is_flagged, score_tokens, word_color
from wmark.textproc import tokenize


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="text file, or - for stdin")
    ap.add_argument("--threshold", help='e.g. "0.60" (default: settings.json)')
    ap.add_argument("--colors", action="store_true", help="list each word's color")
    args = ap.parse_args()

    settings = load_settings()
    key = load_key(settings)
    text = sys.stdin.read() if args.path == "-" else open(args.path, encoding="utf-8").read()
    tokens = tokenize(text)
    try:
        r = score_tokens(tokens, key)
    except EmptyInputError as e:
        sys.exit(f"error: {e}")

    print(f"total words     {r.total}")
    print(f"distinct words  {r.distinct}")
    print(f"green words     {r.green}")
    print(f"green fraction  {r.score:.4f}  ({r.green}/{r.total})")
    threshold = args.threshold or settings.get("threshold")
    if threshold is not None:
        print(f"threshold       {threshold}  ->  {'FLAGGED' if is_flagged(r, threshold) else 'not flagged'}")
    else:
        print("threshold       (not chosen yet)")

    if args.colors:
        print()
        for word, n in Counter(tokens).most_common():
            c = "green" if word_color(word, key) == GREEN else "red"
            print(f"{n:5d}  {c:5s}  {word}")


if __name__ == "__main__":
    main()
