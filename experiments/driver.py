"""Set up runs, reset state, advance simulated time and record measurements.

    from experiments.driver import ExperimentRun, CONFIGURATIONS

    run = ExperimentRun.create("attack3_config_B", **CONFIGURATIONS["B"])
    client, wait = run.attacker_view("submitter1")   # the ONLY things attack code receives
    ...attack code uses client.detect(...) and wait(seconds)...
    run.hidden_score(text)        # driver-only: exact score for analysis, never shown to the attacker
    run.write_json("results.json", {...})

Each run lives in results/milestone2/<name>/:
    state/          service state (config, hashed accounts, counters, clock, log)
    credentials/    demonstration tokens for the run's accounts
    driver_log.jsonl  every wait() the driver performed
    (your result files)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from client import Client
from service.admin import DEFAULT_ACCOUNTS, init_state, reset_state
from service.core import load_config, read_json, write_json

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO_ROOT / "results" / "milestone2"

# Spec 5.2, Attack 3: the three service configurations.
CONFIGURATIONS = {
    "A": {"mode": "score", "rate_limit_enabled": False},
    "B": {"mode": "score", "rate_limit_enabled": True},
    "C": {"mode": "binary", "rate_limit_enabled": True},
}


class ExperimentRun:
    def __init__(self, run_dir):
        self.dir = Path(run_dir)
        self.state_dir = self.dir / "state"
        self.credentials_dir = self.dir / "credentials"
        if not (self.state_dir / "accounts.json").exists():
            raise FileNotFoundError(f"{self.dir} is not an experiment run (no state/accounts.json)")

    # ------------------------------------------------------------ setup
    @classmethod
    def create(cls, name: str, *, mode: str = "score", rate_limit_enabled: bool = True,
               accounts: dict | None = None, overwrite: bool = False, **config) -> "ExperimentRun":
        """Create results/milestone2/<name>/ with fresh service state (simulated clock)."""
        run_dir = RUNS_DIR / name
        cfg = {"mode": mode, "clock": "simulated", "rate_limit": {"enabled": rate_limit_enabled}}
        cfg.update(config)
        init_state(run_dir / "state", run_dir / "credentials", accounts or DEFAULT_ACCOUNTS, cfg, overwrite)
        (run_dir / "driver_log.jsonl").write_text("", encoding="utf-8")
        return cls(run_dir)

    def reset(self) -> None:
        """Clear rate-limit counters, the clock and the service log (spec: reset between configurations)."""
        reset_state(self.state_dir)
        self._driver_log({"event": "reset"})

    # ------------------------------------------------------------ attacker side
    def token(self, account: str) -> str:
        return (self.credentials_dir / f"{account}.token").read_text(encoding="utf-8").strip()

    def client(self, account: str = "submitter1") -> Client:
        return Client(self.token(account), self.state_dir)

    def attacker_view(self, account: str = "submitter1"):
        """Return (client, wait): everything query-access attack code is allowed to have."""
        return self.client(account), self.wait

    # ------------------------------------------------------------ simulated time
    def now(self) -> float:
        return float(read_json(self.state_dir / "clock.json", {"now": 0.0})["now"])

    def wait(self, seconds: float) -> None:
        """Advance simulated time (the attacker waiting out a rate limit). Recorded by the driver."""
        if seconds <= 0:
            return
        if load_config(self.state_dir)["clock"] != "simulated":
            raise RuntimeError("wait() only works with a simulated clock")
        before = self.now()
        write_json(self.state_dir / "clock.json", {"now": before + float(seconds)})
        self._driver_log({"event": "wait", "seconds": float(seconds), "from": before, "to": before + float(seconds)})

    # ------------------------------------------------------------ driver-only analysis
    def hidden_score(self, text: str) -> dict:
        """Exact score and decision, computed with the key. Never pass this to attack code."""
        from wmark.config import load_key, load_settings, threshold_of
        from wmark.detector import EmptyInputError, is_flagged, score_text
        settings = load_settings()
        try:
            r = score_text(text, load_key(settings))
        except EmptyInputError:
            return {"error": "empty_input"}
        return {"green": r.green, "total": r.total, "distinct": r.distinct,
                "score": r.score, "flagged": is_flagged(r, threshold_of(settings))}

    def service_log(self) -> list[dict]:
        path = self.state_dir / "requests.jsonl"
        return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

    def request_counts(self, account: str | None = None) -> dict:
        """Count logged requests by outcome (all requests, including rejected ones)."""
        counts: dict[str, int] = {}
        for e in self.service_log():
            if account is None or e.get("account") == account:
                counts[e["outcome"]] = counts.get(e["outcome"], 0) + 1
        counts["total"] = sum(counts.values())
        return counts

    # ------------------------------------------------------------ recording
    def write_json(self, filename: str, data) -> Path:
        path = self.dir / filename
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return path

    def write_csv(self, filename: str, rows: list[dict]) -> Path:
        path = self.dir / filename
        with open(path, "w", newline="", encoding="utf-8") as f:
            if rows:
                w = csv.DictWriter(f, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
        return path

    def _driver_log(self, entry: dict) -> None:
        entry = dict(entry, at=self.now())
        with open(self.dir / "driver_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
