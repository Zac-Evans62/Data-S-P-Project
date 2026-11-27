"""Attack 1: remove a watermark using detector queries (spec 5.2).

QUERY ACCESS ONLY. This module may use nothing but the `client` and `wait`
objects handed to it by the experiment driver (experiments/attack1.py). It
does not import the detector, the service or the driver, and never sees the
key (checked by tests/test_boundary.py).

Contents:
  Budget / submit()      send text, wait out rate limits, enforce the request budget
  probe_color()          learn one word's color from a repeated-word query
  case_change(), zero_width_insert(), hyphen_split()   the character-change edits
  run_character_tests()  the three automated character tests, one shared budget
"""

from __future__ import annotations

import re

ZERO_WIDTH_SPACE = "​"
WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")   # rough word finder; the attacker's own, not the service's


class BudgetExhausted(Exception):
    pass


class Budget:
    """Counts every request sent (including rejected ones) against a fixed allowance."""

    def __init__(self, max_requests: int):
        self.max_requests = max_requests
        self.used = 0
        self.waited_seconds = 0.0

    @property
    def left(self) -> int:
        return self.max_requests - self.used


def submit(client, wait, text: str, budget: Budget) -> dict:
    """Send `text`; on a rate limit, wait (simulated) and retry. Every attempt costs budget."""
    while True:
        if budget.left <= 0:
            raise BudgetExhausted
        response = client.detect(text)
        budget.used += 1
        if response.get("error") == "rate_limited":
            seconds = float(response.get("retry_after_seconds", 1))
            wait(seconds)
            budget.waited_seconds += seconds
            continue
        return response


def probe_color(client, wait, word: str, budget: Budget, repeats: int = 100) -> str:
    """Repeat one word: in score mode the score is 1.000 (green) or 0.000 (red);
    in binary mode, flagged means green. Returns "green", "red" or "unknown"."""
    r = submit(client, wait, " ".join([word] * repeats), budget)
    if not r.get("ok"):
        return "unknown"
    if "score" in r:
        return "green" if float(r["score"]) >= 0.5 else "red"
    return "green" if r["flagged"] else "red"


# ------------------------------------------------------------ character edits

def word_spans(text: str) -> list[tuple[int, int]]:
    return [m.span() for m in WORD.finditer(text)]


def case_change(text: str) -> str:
    """Alternate letter case inside every word (e.g. 'water' -> 'WaTeR')."""
    def flip(m):
        w = m.group(0)
        return "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(w))
    return WORD.sub(flip, text)


def zero_width_insert(text: str, char: str = ZERO_WIDTH_SPACE) -> str:
    """Insert an invisible character after the first letter of every word of 2+ letters."""
    return WORD.sub(lambda m: m.group(0)[0] + char + m.group(0)[1:] if len(m.group(0)) > 1 else m.group(0), text)


def hyphen_split(text: str, span: tuple[int, int]) -> str:
    """Insert a hyphen in the middle of the word at `span` (word-internal punctuation)."""
    start, end = span
    mid = start + (end - start) // 2
    return text[:mid] + "-" + text[mid:]


def _flagged(r: dict):
    return r.get("flagged") if r.get("ok") else None


def run_character_tests(client, wait, watermarked: str, budget: Budget) -> dict:
    """Run the three character tests, each from a fresh copy, sharing one budget.

    case        : one submission with alternating case                 (prediction: ignored by case folding)
    zero_width  : one submission with U+200B inside every word         (prediction: deleted by normalization)
    punctuation : (a) one submission with extra punctuation between words (prediction: ignored)
                  (b) query-guided: hyphenate one word at a time, keep it only if the
                      score drops, until unflagged or out of budget    (prediction: splits words, can work)
    """
    results = {}

    def single(name, text, prediction):
        before = budget.used
        try:
            r = submit(client, wait, text, budget)
        except BudgetExhausted:
            results[name] = {"output": watermarked, "response": None, "queries": budget.used - before,
                             "success_candidate": False, "prediction": prediction, "note": "budget exhausted before test"}
            return
        # queries includes any requests the rate limit rejected before this one succeeded
        results[name] = {"output": text, "response": r, "queries": budget.used - before, "prediction": prediction,
                         "success_candidate": _flagged(r) is False}

    used_before = budget.used
    single("case", case_change(watermarked), "ignored: case folding makes the words identical")
    single("zero_width", zero_width_insert(watermarked),
           "ignored: U+200B is deleted before tokenizing, so every word is unchanged")

    # Punctuation (a): extra punctuation between words.
    start_used = budget.used
    spaced = re.sub(r"(?<=\w) (?=\w)", lambda m: ", " if (m.start() % 7 == 0) else " ", watermarked)
    log = []
    try:
        r = submit(client, wait, spaced, budget)
        log.append({"step": "between-word punctuation", "flagged": _flagged(r), "score": r.get("score")})
    except BudgetExhausted:
        r = None
    current, current_r = watermarked, None
    # Punctuation (b): word-internal hyphens, greedy, guided by scores.
    try:
        current_r = submit(client, wait, current, budget)            # baseline score of the fresh copy
        log.append({"step": "baseline", "flagged": _flagged(current_r), "score": current_r.get("score")})
        spans = sorted(word_spans(watermarked), key=lambda s: s[1] - s[0], reverse=True)
        offset_shift = []                                            # positions where hyphens were inserted
        for start, end in spans:
            if _flagged(current_r) is False:
                break
            if end - start < 4:
                continue
            shift = sum(1 for p in offset_shift if p <= start)
            candidate = hyphen_split(current, (start + shift, end + shift))
            cr = submit(client, wait, candidate, budget)
            better = (cr.get("ok") and "score" in cr and "score" in current_r
                      and float(cr["score"]) < float(current_r["score"])) or _flagged(cr) is False
            log.append({"step": f"hyphenate {watermarked[start:end]!r}", "kept": bool(better),
                        "flagged": _flagged(cr), "score": cr.get("score")})
            if better:
                current, current_r = candidate, cr
                offset_shift.append(start + (end - start) // 2)
    except BudgetExhausted:
        log.append({"step": "budget exhausted"})
    results["punctuation"] = {
        "output": current if _flagged(current_r) is False else (spaced if r and _flagged(r) is False else current),
        "response": current_r, "queries": budget.used - start_used, "steps": log,
        "prediction": "punctuation between words is ignored; a hyphen inside a word splits it into two new words "
                      "with fresh colors, which can lower the score but hurts readability",
        "success_candidate": (_flagged(current_r) is False) or (r is not None and _flagged(r) is False),
    }
    results["_total_queries"] = budget.used - used_before
    return results