"""Tests for the detection service controls (spec 5.1).  Run:  python -m unittest -v

Every request goes through client.Client, i.e. a separate `python -m service`
process, exactly as attack code will use it.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from client import Client  # noqa: E402
from service.admin import init_state, reset_state  # noqa: E402
from service.core import read_json, write_json  # noqa: E402

SENTINEL = "Zebrafinch quoth the unmistakable sentinel phrase"


class ServiceTestCase(unittest.TestCase):
    config = {"mode": "score", "clock": "simulated", "rate_limit": {"enabled": True, "requests": 5, "window_seconds": 60}}

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.state = self.tmp / "state"
        self.tokens = init_state(self.state, self.tmp / "credentials",
                                 {"sub": "submitter", "sub2": "submitter", "aud": "auditor"}, self.config)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def client(self, account="sub"):
        return Client(self.tokens[account], self.state)

    def log_text(self):
        return (self.state / "requests.jsonl").read_text(encoding="utf-8")

    def advance(self, seconds):
        now = read_json(self.state / "clock.json", {"now": 0})["now"]
        write_json(self.state / "clock.json", {"now": now + seconds})


class TestAuthentication(ServiceTestCase):
    def test_invalid_token_rejected(self):
        for bad in ["", "not-a-real-token", self.tokens["sub"] + "x"]:
            r = Client(bad, self.state).detect("Some ordinary text here.")
            self.assertEqual(r["error"], "invalid_credential")
            self.assertNotIn("flagged", r)

    def test_valid_token_accepted(self):
        r = self.client().detect("Some ordinary text here.")
        self.assertTrue(r["ok"])

    def test_tokens_stored_only_as_hashes(self):
        accounts = (self.state / "accounts.json").read_text(encoding="utf-8")
        for token in self.tokens.values():
            self.assertNotIn(token, accounts)


class TestAuthorization(ServiceTestCase):
    def test_submitter_cannot_read_logs(self):
        r = self.client("sub").read_logs()
        self.assertEqual(r["error"], "forbidden")

    def test_auditor_can_read_logs_and_detect(self):
        self.client("sub").detect("Some ordinary text here.")
        r = self.client("aud").read_logs()
        self.assertTrue(r["ok"])
        self.assertGreaterEqual(len(r["entries"]), 1)
        self.assertTrue(self.client("aud").detect("More text.")["ok"])

    def test_unknown_action_forbidden(self):
        r = self.client("aud")._call({"token": self.tokens["aud"], "action": "delete_logs"})
        self.assertEqual(r["error"], "forbidden")


class TestLogging(ServiceTestCase):
    def test_log_has_required_fields_and_no_text(self):
        self.client().detect(SENTINEL)
        Client("wrong", self.state).detect(SENTINEL)
        entries = [json.loads(x) for x in self.log_text().splitlines()]
        self.assertEqual(len(entries), 2)
        for e in entries:
            for field in ("account", "time", "outcome", "rate_limit", "action"):
                self.assertIn(field, e)
        self.assertEqual(entries[1]["outcome"], "invalid_credential")
        self.assertNotIn("zebrafinch", self.log_text().lower())
        self.assertNotIn("sentinel", self.log_text().lower())

    def test_log_never_contains_scores(self):
        self.client().detect(SENTINEL)
        self.assertNotIn("score", json.loads(self.log_text().splitlines()[0]))


class TestRateLimit(ServiceTestCase):
    def test_limit_enforced_and_survives_client_restart(self):
        for _ in range(5):
            self.assertTrue(self.client().detect("Some text.")["ok"])
        # A brand-new client object (and new process) is still limited.
        r = Client(self.tokens["sub"], self.state).detect("Some text.")
        self.assertEqual(r["error"], "rate_limited")
        self.assertGreater(r["retry_after_seconds"], 0)

    def test_window_expires(self):
        for _ in range(5):
            self.client().detect("Some text.")
        self.advance(61)
        self.assertTrue(self.client().detect("Some text.")["ok"])

    def test_limit_is_per_account(self):
        for _ in range(5):
            self.client("sub").detect("Some text.")
        self.assertEqual(self.client("sub").detect("x y z")["error"], "rate_limited")
        self.assertTrue(self.client("sub2").detect("x y z")["ok"])

    def test_rate_limited_requests_are_logged(self):
        for _ in range(6):
            self.client().detect("Some text.")
        last = json.loads(self.log_text().splitlines()[-1])
        self.assertEqual(last["outcome"], "rate_limited")
        self.assertFalse(last["rate_limit"]["allowed"])

    def test_reset_clears_counters(self):
        for _ in range(5):
            self.client().detect("Some text.")
        reset_state(self.state)
        self.assertTrue(self.client().detect("Some text.")["ok"])
        self.assertEqual(len(self.log_text().splitlines()), 1)


class TestRateLimitDisabled(ServiceTestCase):
    config = {"mode": "score", "clock": "simulated", "rate_limit": {"enabled": False}}

    def test_no_limit(self):
        for _ in range(8):
            self.assertTrue(self.client().detect("Some text.")["ok"])


class TestResponseModes(ServiceTestCase):
    def test_score_mode_returns_score_with_three_digits(self):
        r = self.client().detect("The cat sat on the mat. The cat sat again.")
        self.assertIn("score", r)
        self.assertRegex(r["score"], r"^\d\.\d{3}$")
        self.assertIsInstance(r["flagged"], bool)

    def test_repeated_word_reveals_color(self):
        r = self.client().detect("the " * 100)
        self.assertIn(r["score"], ("0.000", "1.000"))

    def test_empty_input_is_an_error(self):
        r = self.client().detect("!!! ...")
        self.assertEqual(r["error"], "empty_input")


class TestBinaryMode(ServiceTestCase):
    config = {"mode": "binary", "clock": "simulated", "rate_limit": {"enabled": True, "requests": 5, "window_seconds": 60}}

    def test_binary_hides_score_in_response_and_logs(self):
        r = self.client().detect("The cat sat on the mat. The cat sat again.")
        self.assertIn("flagged", r)
        self.assertNotIn("score", r)
        logs = self.client("aud").read_logs()
        self.assertNotIn("score", json.dumps(logs))
        self.assertNotIn("score", self.log_text())


class TestClock(ServiceTestCase):
    def test_each_request_costs_one_simulated_second(self):
        for _ in range(3):
            self.client().detect("Some text.")
        Client("bad", self.state).detect("x")
        self.assertEqual(read_json(self.state / "clock.json", {})["now"], 4.0)


if __name__ == "__main__":
    unittest.main()
