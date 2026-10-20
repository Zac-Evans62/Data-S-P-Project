"""Unit tests for word rules and scoring.  Run:  python -m unittest -v"""
import hmac
import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wmark.detector import (GREEN, RED, EmptyInputError, detect, is_flagged,  # noqa: E402
                            parse_threshold, score_text, score_tokens, word_color)
from wmark.metrics import binomial_upper_bound, changed_words  # noqa: E402
from wmark.textproc import normalize_word, tokenize  # noqa: E402

TEST_KEY = bytes(range(32))  # fixed key for tests only; NOT the experiment key


def words_of_color(color, n):
    out, i = [], 0
    while len(out) < n:
        w = f"w{i}"
        if word_color(w, TEST_KEY) == color:
            out.append(w)
        i += 1
    return out


class TestWordRules(unittest.TestCase):
    def test_case_and_punctuation(self):
        self.assertEqual(tokenize("The Book! the book?"), ["the", "book", "the", "book"])

    def test_apostrophes(self):
        self.assertEqual(tokenize("Don’t stop; it's o'clock"), ["don't", "stop", "it's", "o'clock"])
        self.assertEqual(tokenize("'tis the season'"), ["tis", "the", "season"])

    def test_hyphen_and_underscore_split(self):
        self.assertEqual(tokenize("well-known _italic_ text"), ["well", "known", "italic", "text"])

    def test_zero_width_removed(self):
        self.assertEqual(tokenize("water​mark wa‍ter﻿"), ["watermark", "water"])

    def test_unicode_nfkc_and_casefold(self):
        self.assertEqual(tokenize("ﬁsh ＡBC Straße"), ["fish", "abc", "strasse"])
        self.assertEqual(tokenize("café"), tokenize("café"))

    def test_digits_are_words(self):
        self.assertEqual(tokenize("In 1984, 3 men"), ["in", "1984", "3", "men"])

    def test_normalize_word(self):
        self.assertEqual(normalize_word("Book"), "book")
        with self.assertRaises(ValueError):
            normalize_word("two words")


class TestScoring(unittest.TestCase):
    def test_word_color_matches_spec(self):
        for w in ["the", "book", "watermark"]:
            expected = hmac.digest(TEST_KEY, w.encode("utf-8"), "sha256")[-1] & 1
            self.assertEqual(word_color(w, TEST_KEY), expected)

    def test_example_from_spec(self):
        text = " ".join(words_of_color(GREEN, 65) + words_of_color(RED, 35))
        r = score_text(text, TEST_KEY)
        self.assertEqual((r.green, r.total), (65, 100))
        self.assertTrue(is_flagged(r, "0.60"))

    def test_equal_to_threshold_is_not_flagged(self):
        text = " ".join(words_of_color(GREEN, 6) + words_of_color(RED, 4))
        r = score_text(text, TEST_KEY)
        self.assertEqual(r.fraction, Fraction(3, 5))
        self.assertFalse(is_flagged(r, "0.60"))
        self.assertFalse(is_flagged(r, 0.6))
        self.assertTrue(is_flagged(r, "0.59"))

    def test_exact_comparison_avoids_float_error(self):
        # 65/100 vs 0.65: equal, so not flagged (floats could get this wrong)
        text = " ".join(words_of_color(GREEN, 65) + words_of_color(RED, 35))
        self.assertFalse(is_flagged(score_text(text, TEST_KEY), "0.65"))

    def test_repeats_counted_and_distinct_recorded(self):
        g = words_of_color(GREEN, 1)[0]
        rd = words_of_color(RED, 1)[0]
        r = score_tokens([g, g, g, rd], TEST_KEY)
        self.assertEqual((r.green, r.total, r.distinct), (3, 4, 2))

    def test_repetition_gives_zero_or_one(self):
        for w in ["the", "and", "cat"]:
            self.assertIn(score_tokens([w] * 1000, TEST_KEY).fraction, (0, 1))

    def test_empty_input_rejected(self):
        for text in ["", "   ", "!!! --- ...", "​​"]:
            with self.assertRaises(EmptyInputError):
                score_text(text, TEST_KEY)

    def test_detect_dict(self):
        d = detect("The cat sat", TEST_KEY, "0.5")
        self.assertEqual(d["total_words"], 3)
        self.assertIn("flagged", d)

    def test_threshold_range(self):
        with self.assertRaises(ValueError):
            parse_threshold("1.5")


class TestMetrics(unittest.TestCase):
    def test_changed_words(self):
        a = tokenize("the big dog ran fast")
        self.assertEqual(changed_words(a, tokenize("the large dog ran fast")), 1)
        self.assertEqual(changed_words(a, tokenize("the very large dog ran fast")), 2)
        self.assertEqual(changed_words(a, tokenize("The BIG dog, ran fast!")), 0)

    def test_bounds(self):
        self.assertAlmostEqual(binomial_upper_bound(0, 150), 1 - 0.05 ** (1 / 150), places=4)
        self.assertLess(abs(binomial_upper_bound(0, 150) - 3 / 150), 0.001)
        self.assertGreater(binomial_upper_bound(2, 150), 2 / 150)


if __name__ == "__main__":
    unittest.main()
