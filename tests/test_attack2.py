"""Tests for Attack 2 helper logic.  Run:  python -m unittest -v"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from attacks.key.forge import best_in_time, swaps_to_flag, swaps_to_target  # noqa: E402


class TestSwaps(unittest.TestCase):
    def test_swaps_to_flag_uses_strict_greater(self):
        t = Fraction("0.63")
        # 63/100 equals the threshold: not flagged, so one more swap is needed.
        self.assertEqual(swaps_to_flag(63, 100, t), 1)
        self.assertEqual(swaps_to_flag(64, 100, t), 0)
        # wells_time_machine_0022: 74 of 125 green; needs 79 (79/125 = 0.632 > 0.63).
        self.assertEqual(swaps_to_flag(74, 125, t), 5)

    def test_swaps_to_target_allows_equality(self):
        target = Fraction("0.66")
        self.assertEqual(swaps_to_target(66, 100, target), 0)
        self.assertEqual(swaps_to_target(74, 125, target), 9)   # ceil(82.5) = 83
        self.assertEqual(swaps_to_target(90, 100, target), 0)


class TestBestInTime(unittest.TestCase):
    def setUp(self):
        self.start = datetime(2026, 11, 25, 12, 0, tzinfo=timezone.utc)

    def v(self, name, minutes, green, total=100):
        return {"version": name, "at": (self.start + timedelta(minutes=minutes)).isoformat(),
                "green": green, "total": total}

    def test_late_versions_ignored(self):
        versions = [self.v("v000", 0, 55), self.v("v001", 10, 62), self.v("v002", 16, 70)]
        self.assertEqual(best_in_time(versions, self.start.isoformat(), 15)["version"], "v001")

    def test_tie_keeps_earliest(self):
        versions = [self.v("v000", 0, 55), self.v("v001", 5, 64), self.v("v002", 9, 64)]
        self.assertEqual(best_in_time(versions, self.start.isoformat(), 15)["version"], "v001")


if __name__ == "__main__":
    unittest.main()