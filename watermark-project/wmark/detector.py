"""Word colors, scoring and the flag decision (project spec, Section 2).

Scores are kept as exact fractions so the threshold comparison is exact:
65/100 against threshold "0.65" is EQUAL, therefore NOT flagged. With
floats, 0.65 can round either way. Always pass thresholds as strings
("0.60") or Fractions, never as float literals you computed.
"""

from __future__ import annotations

import hmac
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from .textproc import tokenize

GREEN = 1
RED = 0


class EmptyInputError(ValueError):
    """Raised when a text contains no words under our rules."""


def word_color(word: str, key: bytes) -> int:
    """Color of an already-normalized word: 1 = green, 0 = red.

    This is exactly the function given in the project description.
    """
    return hmac.digest(key, word.encode("utf-8"), "sha256")[-1] & 1


@dataclass(frozen=True)
class ScoreResult:
    total: int            # word occurrences (repeats counted)
    green: int            # green word occurrences
    distinct: int         # distinct normalized words
    distinct_green: int   # distinct normalized words that are green

    @property
    def fraction(self) -> Fraction:
        """Exact green fraction. Use this for threshold comparisons."""
        return Fraction(self.green, self.total)

    @property
    def score(self) -> float:
        """Green fraction as a float, for display and CSV output only."""
        return self.green / self.total


def score_tokens(tokens: Iterable[str], key: bytes) -> ScoreResult:
    counts = Counter(tokens)
    if not counts:
        raise EmptyInputError("input contains no words under the project's word rules")
    green = 0
    distinct_green = 0
    for word, n in counts.items():
        if word_color(word, key) == GREEN:
            green += n
            distinct_green += 1
    return ScoreResult(
        total=sum(counts.values()),
        green=green,
        distinct=len(counts),
        distinct_green=distinct_green,
    )


def score_text(text: str, key: bytes) -> ScoreResult:
    return score_tokens(tokenize(text), key)


def parse_threshold(threshold) -> Fraction:
    """Turn "0.60", 0.6, or Fraction(3, 5) into an exact Fraction in [0, 1]."""
    t = threshold if isinstance(threshold, Fraction) else Fraction(str(threshold))
    if not (0 <= t <= 1):
        raise ValueError(f"threshold must be between 0 and 1, got {threshold}")
    return t


def is_flagged(result: ScoreResult, threshold) -> bool:
    """Flag only when green fraction is STRICTLY greater than the threshold."""
    return result.fraction > parse_threshold(threshold)


def detect(text: str, key: bytes, threshold) -> dict:
    """Score a text and return a plain dict (handy for CSV/JSON output)."""
    r = score_text(text, key)
    return {
        "total_words": r.total,
        "distinct_words": r.distinct,
        "green_words": r.green,
        "green_fraction": r.score,
        "flagged": is_flagged(r, threshold),
    }
