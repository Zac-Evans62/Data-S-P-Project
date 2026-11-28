"""Attack 3: forge a watermark using detector queries (spec 5.2).

QUERY ACCESS ONLY. This module may use nothing but the `client` and `wait`
objects handed to it by the experiment driver (experiments/attack3.py). It
imports no detector, service or driver code and never sees the key (checked by
tests/test_boundary.py). It also does NOT use data/synonyms.tsv, which was built
with the key during watermarking; replacements come from attacks/query/thesaurus.tsv
(built from WordNet by scripts/build_thesaurus.py) and are passed in by the driver.

How it works
  1. Color disclosure. Submitting one word repeated many times gives a score of
     exactly 0 or 1 (or, with a decision-only response, flagged / not flagged), so the
     color of that word is revealed whatever the threshold is (0 <= threshold < 1).
  2. Learning colors. Binary mode reveals 1 color per request. Score mode reveals
     several per request: words are repeated 4, 8, 16, 32, 64 times in one text and
     the green share of the score, read as a binary number, says which are green.
  3. Editing. Replace a word the attacker knows is red by a synonym it knows is green,
     a few swaps at a time, and ask the service after each batch until it flags the text.

Costs are split into preparation (learning colors, shared across passages) and
editing (everything sent while working on one passage).
"""

from __future__ import annotations

import re
from collections import Counter

from attacks.query.removal import Budget, BudgetExhausted, submit

WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")   # the attacker's own word finder
BATCH_WEIGHTS = (4, 8, 16, 32, 64)               # 5 colors per score-mode request (124 words)
VOWELS = "aeiou"


class Spender:
    """Sends queries on behalf of the attacker and charges them to the right budget."""

    def __init__(self, client, wait, prep: Budget, edit: Budget, seconds_per_request: float = 1.0):
        self.client, self.wait, self.prep, self.edit = client, wait, prep, edit
        self.phase = "prep"
        self.mode = None                         # "score" or "binary", learned from the first response
        self.seconds_per_request = seconds_per_request

    @property
    def budget(self) -> Budget:
        return self.prep if self.phase == "prep" else self.edit

    @property
    def left(self) -> int:
        return self.budget.left

    def seconds_used(self, budget: Budget) -> float:
        return budget.used * self.seconds_per_request + budget.waited_seconds

    def send(self, text: str) -> dict:
        r = submit(self.client, self.wait, text, self.budget)
        if r.get("ok") and self.mode is None:
            self.mode = "score" if "score" in r else "binary"
        return r


# ------------------------------------------------------------------ color disclosure

def probe_single(spender: Spender, word: str, repeats: int = 100) -> str:
    """One word repeated `repeats` times: score is 1 or 0 (score mode); flagged means green (binary)."""
    r = spender.send(" ".join([word] * repeats))
    if not r.get("ok"):
        return "unknown"
    if "score" in r:
        return "green" if float(r["score"]) >= 0.5 else "red"
    return "green" if r["flagged"] else "red"


def probe_batch(spender: Spender, words: list[str]) -> dict[str, str] | None:
    """Score mode only: learn up to 5 colors from one request. None if the score is too coarse to decode."""
    weights = BATCH_WEIGHTS[: len(words)]
    total = sum(weights)
    r = spender.send(" ".join(w for w, k in zip(words, weights) for _ in range(k)))
    if not r.get("ok") or "score" not in r:
        return None
    green = float(r["score"]) * total
    n = round(green)
    if abs(green - n) > 0.25:
        return None
    return {w: ("green" if n & k else "red") for w, k in zip(words, weights)}


def demonstrate_disclosure(spender: Spender, words: list[str], colors: dict[str, str]) -> list[dict]:
    """The required demonstration: repeated-word queries, whose response is 0/1 or flagged/unflagged."""
    out = []
    for w in words:
        if w in colors or spender.left <= 0:
            continue
        r = spender.send(" ".join([w] * 100))
        color = ("green" if float(r["score"]) >= 0.5 else "red") if r.get("ok") and "score" in r else \
                ("green" if r.get("flagged") else "red") if r.get("ok") else "unknown"
        out.append({"word": w, "repeats": 100, "response": {k: r.get(k) for k in ("ok", "flagged", "score")}, "color": color})
        if color != "unknown":
            colors[w] = color
    return out


# ------------------------------------------------------------------ inflected forms

_CVC = re.compile(r"[^aeiou][aeiou][^aeiouwxy]$")     # stop -> stopped: doubling, so we skip these


def _inflect(base: str, kind: str) -> str | None:
    if kind == "s":
        if re.search(r"(s|x|z|ch|sh)$", base):
            return base + "es"
        return base[:-1] + "ies" if re.search(r"[^aeiou]y$", base) else base + "s"
    if kind == "ed":
        if base.endswith("e"):
            return base + "d"
        if re.search(r"[^aeiou]y$", base):
            return base[:-1] + "ied"
        return None if _CVC.search(base) else base + "ed"
    if kind == "ing":
        if base.endswith("ie"):
            return base[:-2] + "ying"
        if base.endswith("e") and not base.endswith("ee"):
            return base[:-1] + "ing"
        return None if _CVC.search(base) else base + "ing"
    return None


def _stems(w: str):
    """(possible base word, suffix kind) pairs for a regularly inflected word."""
    if w.endswith("ies") and len(w) > 4:
        yield w[:-3] + "y", "s"
    if w.endswith("es") and len(w) > 4:
        yield w[:-2], "s"
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        yield w[:-1], "s"
    if w.endswith("ied") and len(w) > 4:
        yield w[:-3] + "y", "ed"
    if w.endswith("ed") and len(w) > 4:
        yield w[:-2], "ed"
        yield w[:-1], "ed"
        if w[-3] == w[-4]:
            yield w[:-3], "ed"
    if w.endswith("ing") and len(w) > 5:
        yield w[:-3], "ing"
        yield w[:-3] + "e", "ing"
        if w[-4] == w[-5]:
            yield w[:-4], "ing"


def expand(thesaurus: dict[str, list[str]], text: str) -> dict[str, list[str]]:
    """Add replacements for regularly inflected forms found in `text` (plurals, -ed, -ing) by
    inflecting the base word's replacements the same way. Irregular forms are not handled."""
    out = dict(thesaurus)
    for m in WORD.finditer(text):
        w = m.group().lower()
        if w in out:
            continue
        for base, kind in _stems(w):
            if base in thesaurus:
                syns = [x for x in (_inflect(s, kind) for s in thesaurus[base]) if x]
                if syns:
                    out[w] = syns
                break
    return out


# ------------------------------------------------------------------ candidates and learning

def candidates(text: str, thesaurus: dict[str, list[str]]) -> list[tuple[int, int, str]]:
    """(start, end, lowercase word) for every word in the text that has replacements."""
    return [(m.start(), m.end(), m.group().lower()) for m in WORD.finditer(text) if m.group().lower() in thesaurus]


def _clean(w: str) -> bool:
    return w.isalpha() and w.islower()


def next_unknown(colors: dict, thesaurus: dict, focus: Counter, limit: int) -> list[str]:
    """Pick the next words worth learning: candidate words first (most frequent first), then
    replacements of known-red candidates that still have no known green replacement."""
    words = [w for w, _ in focus.most_common() if w not in colors and _clean(w)]
    if words:
        return words[:limit]
    out = []
    for w, _ in focus.most_common():
        if colors.get(w) != "red" or any(colors.get(s) == "green" for s in thesaurus[w]):
            continue
        for s in thesaurus[w]:
            if s not in colors and s not in out and _clean(s):
                out.append(s)
                if len(out) == limit:
                    return out
    return out


def learn_step(spender: Spender, colors: dict, thesaurus: dict, focus: Counter) -> bool:
    """Spend one request learning colors. False if the budget is gone or nothing is left to learn."""
    if spender.left <= 0:
        return False
    batch = len(BATCH_WEIGHTS) if spender.mode == "score" else 1
    words = next_unknown(colors, thesaurus, focus, batch)
    if not words:
        return False
    try:
        learned = probe_batch(spender, words) if batch > 1 else None
        if learned is None:
            learned = {words[0]: probe_single(spender, words[0])}
    except BudgetExhausted:
        return False
    for w, c in learned.items():
        if c != "unknown":
            colors[w] = c
    return True


def prepare(spender: Spender, colors: dict, thesaurus: dict, texts: list[str]) -> dict:
    """Preparation phase: learn colors with the shared preparation budget before any editing."""
    spender.phase = "prep"
    focus = Counter()
    for t in texts:
        thesaurus = expand(thesaurus, t)
        for _, _, w in candidates(t, thesaurus):
            focus[w] += 1
    demo = demonstrate_disclosure(spender, [w for w, _ in focus.most_common(2)] or ["the"], colors)
    steps = 0
    while learn_step(spender, colors, thesaurus, focus):
        steps += 1
    return {"demonstration": demo, "learning_requests": steps,
            "colors_learned": len(colors), "requests": spender.prep.used,
            "simulated_wait_seconds": spender.prep.waited_seconds}


# ------------------------------------------------------------------ editing

def _match_case(orig: str, new: str) -> str:
    if len(orig) > 1 and orig.isupper():
        return new.upper()
    return new.capitalize() if orig[:1].isupper() else new


def _article_ok(text: str, start: int, new: str) -> bool:
    """Avoid 'a apple' / 'an big' after the replacement."""
    m = re.search(r"\b(a|an)\s+$", text[:start], re.IGNORECASE)
    if not m:
        return True
    return (m.group(1).lower() == "an") == (new[:1].lower() in VOWELS)


def render(text: str, swaps: dict[int, tuple[int, str]]) -> str:
    """Apply {start: (end, new_word)} swaps to the original text."""
    out, pos = [], 0
    for start in sorted(swaps):
        end, new = swaps[start]
        out.append(text[pos:start])
        out.append(_match_case(text[start:end], new))
        pos = end
    out.append(text[pos:])
    return "".join(out)


def forge(spender: Spender, colors: dict, thesaurus: dict, original: str, *,
          step: int = 3, max_seconds: float = 900.0) -> dict:
    """Edit phase for one passage. Replace known-red words by known-green synonyms, `step` swaps
    at a time, asking the service after each batch, until it flags the text or the budget ends."""
    spender.phase = "edit"
    thesaurus = expand(thesaurus, original)
    cands = candidates(original, thesaurus)
    focus = Counter(w for _, _, w in cands)
    swaps: dict[int, tuple[int, str]] = {}         # start -> (end, replacement), insertion order = apply order
    order: list[int] = []
    history, last_text, last_resp = [], original, None
    stop = "no more swaps available"

    def grow_plan():
        for start, end, w in cands:
            if start in swaps or colors.get(w) != "red":
                continue
            s = next((s for s in thesaurus[w] if colors.get(s) == "green" and _article_ok(original, start, s)), None)
            if s:
                swaps[start] = (end, s)
                order.append(start)

    applied = 0
    while True:
        grow_plan()
        if applied < len(order):
            applied = min(len(order), applied + step)
            text = render(original, {s: swaps[s] for s in order[:applied]})
            if spender.seconds_used(spender.edit) >= max_seconds:
                stop = "time limit reached"
                break
            try:
                r = spender.send(text)
            except BudgetExhausted:
                stop = "edit request budget used up"
                break
            last_text, last_resp = text, r
            history.append({"swaps_applied": applied, "flagged": r.get("flagged"), "score": r.get("score"),
                            "error": r.get("error"), "edit_requests": spender.edit.used})
            if r.get("ok") and r.get("flagged") is True:
                stop = "flagged"
                break
            continue
        if spender.seconds_used(spender.edit) >= max_seconds:
            stop = "time limit reached"
            break
        if not learn_step(spender, colors, thesaurus, focus):
            stop = "edit request budget used up" if spender.left <= 0 else "nothing left to learn or swap"
            break

    return {"output": last_text, "response": last_resp, "flagged": bool(last_resp and last_resp.get("flagged") is True),
            "swaps": [{"from": original[s:swaps[s][0]], "to": _match_case(original[s:swaps[s][0]], swaps[s][1])}
                      for s in order[:applied]],
            "stop_reason": stop, "history": history,
            "edit_requests": spender.edit.used, "edit_wait_seconds": spender.edit.waited_seconds,
            "colors_known": len(colors)}
