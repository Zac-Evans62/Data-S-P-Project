"""Changed-word counts and small-sample error bounds."""

from __future__ import annotations

import difflib
from math import comb


def changed_words(original_tokens: list[str], edited_tokens: list[str]) -> int:
    """Count changed words between two token lists.

    Method (state this in the report): align the two normalized word
    sequences with difflib.SequenceMatcher. For every non-matching block,
    count max(words removed, words inserted). So a one-for-one synonym swap
    counts 1, replacing one word with two counts 2, a pure deletion of one
    word counts 1. Case/punctuation-only edits count 0 because both sides
    are normalized first.
    """
    sm = difflib.SequenceMatcher(a=original_tokens, b=edited_tokens, autojunk=False)
    changed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            changed += max(i2 - i1, j2 - j1)
    return changed


def word_diff(original_tokens: list[str], edited_tokens: list[str]) -> str:
    """Readable word diff: [-old-]{+new+}."""
    sm = difflib.SequenceMatcher(a=original_tokens, b=edited_tokens, autojunk=False)
    parts = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            parts.append(" ".join(original_tokens[i1:i2]))
        else:
            if i2 > i1:
                parts.append("[-" + " ".join(original_tokens[i1:i2]) + "-]")
            if j2 > j1:
                parts.append("{+" + " ".join(edited_tokens[j1:j2]) + "+}")
    return " ".join(p for p in parts if p)


def rule_of_three(n: int) -> float:
    """Approximate 95% upper bound on the error rate after 0 errors in n."""
    return 3 / n


def binomial_upper_bound(k: int, n: int, confidence: float = 0.95) -> float:
    """One-sided exact (Clopper-Pearson) upper bound on an error rate.

    Use this when k > 0 errors were observed. For k = 0 it is
    1 - (1 - confidence)**(1/n), which is close to 3/n.
    Assumes independent passages: passages from the same book are not
    fully independent, so the true uncertainty is larger (say so).
    """
    if not 0 <= k <= n or n == 0:
        raise ValueError("need 0 <= k <= n and n > 0")
    if k == n:
        return 1.0
    alpha = 1 - confidence

    def cdf(p: float) -> float:  # P(X <= k) for X ~ Binomial(n, p)
        return sum(comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))

    lo, hi = k / n, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if cdf(mid) > alpha:
            lo = mid
        else:
            hi = mid
    return hi
