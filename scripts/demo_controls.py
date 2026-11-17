"""Demonstrate every service control (spec 5.1) and save a transcript for the report.

    python scripts/demo_controls.py

Creates results/milestone2/controls_demo/ (fresh each time) and writes
controls_demo.md there. Each request runs as a separate client process,
so "client restart" is real: no state lives in the client.
"""
import _bootstrap  # noqa: F401

import json

from client import Client
from experiments.driver import ExperimentRun

SAMPLE = "The cat sat on the mat. The cat sat again."
SECRET_PHRASE = "Confidential essay text that must never appear in the log"

lines: list[str] = []


def say(text=""):
    print(text)
    lines.append(text)


def show(label, response):
    shown = {k: v for k, v in response.items() if k != "request_id"}
    say(f"- **{label}:** `{json.dumps(shown)}`")
    return response


def main():
    run = ExperimentRun.create("controls_demo", overwrite=True, mode="score", rate_limit_enabled=True)
    sub = run.client("submitter1")
    aud = run.client("auditor1")
    limit = 20

    say("# Service controls demonstration")
    say()
    say("Settings: score mode (3 digits), rate limit 20 requests per 60 simulated seconds, "
        "accounts submitter1 and submitter2 (role submitter) and auditor1 (role auditor). "
        "Every request ran as a separate client process.")
    say()
    say("## 1. Authentication: invalid credentials are rejected")
    show("valid submitter token", sub.detect(SAMPLE))
    show("wrong token", Client("not-a-real-token", run.state_dir).detect(SAMPLE))
    show("empty token", Client("", run.state_dir).detect(SAMPLE))
    say()
    say("## 2. Authorization: roles are enforced")
    show("submitter1 asks to read logs", sub.read_logs(limit=3))
    r = aud.read_logs(limit=3)
    say(f"- **auditor1 reads logs:** ok={r['ok']}, {len(r['entries'])} entries returned")
    show("auditor1 also allowed to detect", aud.detect(SAMPLE))
    say()
    say("## 3. Logging: account, time, outcome and rate-limit status; no document text")
    sub.detect(SECRET_PHRASE)
    entry = run.service_log()[-1]
    say(f"- Last log entry: `{json.dumps(entry)}`")
    log_text = (run.state_dir / "requests.jsonl").read_text(encoding="utf-8")
    say(f"- Secret phrase present in the log file: **{SECRET_PHRASE.lower() in log_text.lower()}**")
    say(f"- Any log entry containing a score value: **{any('score' in e for e in run.service_log())}**")
    say()
    say("## 4. Rate limiting persists across client restarts")
    run.reset()
    say("Counters reset by the driver. submitter1 now sends 20 requests, each from a new Client object and process:")
    for i in range(limit):
        Client(run.token("submitter1"), run.state_dir).detect(SAMPLE)
    show(f"request {limit + 1}, from a brand-new client", Client(run.token("submitter1"), run.state_dir).detect(SAMPLE))
    show("submitter2 at the same moment (separate allowance)", run.client("submitter2").detect(SAMPLE))
    run.wait(61)
    show("submitter1 after the driver advances the clock 61 s", Client(run.token("submitter1"), run.state_dir).detect(SAMPLE))
    say()
    say("## 5. Response modes")
    show("score mode, ordinary text", sub.detect(SAMPLE))
    binary = ExperimentRun.create("controls_demo_binary", overwrite=True, mode="binary", rate_limit_enabled=True)
    show("binary mode, same text", binary.client("submitter1").detect(SAMPLE))
    say(f"- Any binary-mode log entry containing a score value: **{any('score' in e for e in binary.service_log())}**")
    show("binary mode, 'the' repeated 100 times", binary.client("submitter1").detect("the " * 100))
    show("binary mode, 'watermark' repeated 100 times", binary.client("submitter1").detect("watermark " * 100))
    say("- Even without scores, a repeated single word is flagged exactly when that word is green, "
        "so the binary response still discloses word colors (Attack 3).")
    say()
    say("## 6. Additional accounts")
    say(f"- Each account has its own allowance of {limit} requests per minute, so an attacker holding k accounts "
        f"gets k x {limit} requests per minute. Section 4 shows submitter2 still served while submitter1 is limited.")

    out = run.dir / "controls_demo.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nSaved transcript to {out}")


if __name__ == "__main__":
    main()
