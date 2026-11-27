"""Tests for Attack 1: the character edits behave as predicted under our word rules,
and the attacker-side helpers count budget correctly.  Run:  python -m unittest -v"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attacks.query.removal import Budget, BudgetExhausted, case_change, hyphen_split, submit, word_spans, zero_width_insert  # noqa: E402
from experiments.attack1 import best_queried, margin_words  # noqa: E402
from fractions import Fraction  # noqa: E402
from wmark.textproc import tokenize  # noqa: E402

TEXT = "The traveller's lantern hung above the doorway, flickering softly."


class TestCharacterEdits(unittest.TestCase):
    def test_case_change_is_invisible_to_the_detector(self):
        changed = case_change(TEXT)
        self.assertNotEqual(changed, TEXT)
        self.assertEqual(tokenize(changed), tokenize(TEXT))

    def test_zero_width_is_invisible_to_the_detector(self):
        changed = zero_width_insert(TEXT)
        self.assertIn("​", changed)
        self.assertEqual(tokenize(changed), tokenize(TEXT))

    def test_hyphen_splits_a_word_into_two(self):
        span = [s for s in word_spans(TEXT) if TEXT[s[0]:s[1]] == "lantern"][0]
        changed = hyphen_split(TEXT, span)
        self.assertIn("lan-tern", changed)
        self.assertEqual(len(tokenize(changed)), len(tokenize(TEXT)) + 1)


class FakeClient:
    """Rate-limits every other request, to test retry and budget counting."""
    def __init__(self):
        self.calls = 0

    def detect(self, text):
        self.calls += 1
        if self.calls % 2 == 1:
            return {"ok": False, "error": "rate_limited", "retry_after_seconds": 5}
        return {"ok": True, "flagged": True, "score": "0.700"}


class TestBudget(unittest.TestCase):
    def test_rejected_requests_count_and_waits_recorded(self):
        waits = []
        b = Budget(10)
        r = submit(FakeClient(), waits.append, "text", b)
        self.assertTrue(r["ok"])
        self.assertEqual(b.used, 2)
        self.assertEqual(waits, [5.0])

    def test_budget_exhausted(self):
        b = Budget(1)
        with self.assertRaises(BudgetExhausted):
            submit(FakeClient(), lambda s: None, "text", b)


class TestDriverHelpers(unittest.TestCase):
    def test_margin_words(self):
        t = Fraction("0.63")
        self.assertEqual(margin_words(87, 138, t), 1)    # douglass_narrative_0026: one green word above
        self.assertEqual(margin_words(113, 182, t), -1)  # doyle_sherlock_0015: below the threshold

    def test_best_queried_prefers_first_unflagged_in_time(self):
        start = datetime(2026, 11, 27, 12, tzinfo=timezone.utc)
        def v(name, minute, flagged, score, queried=True):
            return {"version": name, "queried": queried, "queried_at": (start + timedelta(minutes=minute)).isoformat(),
                    "response": {"ok": True, "flagged": flagged, "score": score}}
        versions = [v("v000", 0, True, "0.640"), v("v001", 5, True, "0.632"), v("v002", 8, False, "0.628"),
                    v("v003", 9, False, "0.600"), v("v004", 16, False, "0.500")]
        self.assertEqual(best_queried(versions, start.isoformat(), 15)["version"], "v002")
        self.assertEqual(best_queried(versions[:2], start.isoformat(), 15)["version"], "v001")
        self.assertIsNone(best_queried([], start.isoformat(), 15))


if __name__ == "__main__":
    unittest.main()