"""Tokenization and normalization rules (project spec, Section 2).

THESE RULES ARE SHARED BY WATERMARKING AND DETECTION. Do not change them
after calibration starts. If the team changes them, re-run everything and
say so in the report.

Rules, applied in this order:

1. Unicode NFKC normalization. Compatibility characters become their plain
   forms (ligature "ﬁ" -> "fi", full-width "Ａ" -> "A", "é" stays one
   composed character).
2. Zero-width and invisible characters are DELETED (not turned into
   spaces): U+200B, U+200C, U+200D, U+2060, U+FEFF and soft hyphen U+00AD.
   So "water​mark" -> "watermark". (Team decision; this matters for
   the Milestone 2 character-change attack. The alternative is to treat
   them as word breaks.) Caveat: U+200C/U+200D are meaningful in some
   scripts and emoji; our corpus is English prose.
3. Curly and other apostrophe variants become a straight apostrophe "'".
4. Case folding (str.casefold), a stronger lowercase: "Book" -> "book",
   "Straße" -> "strasse".
5. A word is a run of Unicode letters or digits, optionally joined by
   single internal apostrophes: "don't", "o'clock" are one word each.
   Everything else is a separator: spaces, punctuation, hyphens
   ("well-known" -> "well", "known"), underscores (Gutenberg uses _italics_),
   and leading/trailing apostrophes ("'tis" -> "tis").
   Digits count as words ("1984" is a word).
"""

from __future__ import annotations

import re
import unicodedata

ZERO_WIDTH_CHARS = ("​", "‌", "‍", "⁠", "﻿", "­")
APOSTROPHE_VARIANTS = ("’", "‘", "ʼ", "′")

_DELETE_TABLE = {ord(c): None for c in ZERO_WIDTH_CHARS}
_APOSTROPHE_TABLE = {ord(c): "'" for c in APOSTROPHE_VARIANTS}

# [^\W_] = any Unicode letter or digit (\w minus underscore).
WORD_RE = re.compile(r"[^\W_]+(?:'[^\W_]+)*")


def normalize_text(text: str) -> str:
    """Apply rules 1-4 to a whole string."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DELETE_TABLE)
    text = text.translate(_APOSTROPHE_TABLE)
    return text.casefold()


def tokenize(text: str) -> list[str]:
    """Return the normalized words of ``text`` in order (rules 1-5)."""
    return WORD_RE.findall(normalize_text(text))


def normalize_word(word: str) -> str:
    """Normalize a single word, e.g. a synonym typed by a teammate.

    Raises ValueError if the input is not exactly one word under our rules.
    """
    toks = tokenize(word)
    if len(toks) != 1:
        raise ValueError(f"{word!r} is {len(toks)} words under our rules, expected 1")
    return toks[0]
