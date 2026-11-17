"""The detection service: authentication, authorization, logging, rate limiting,
response modes and a simulated clock (spec 5.1).

All state lives in one *state directory*:

    config.json       service settings for this run (mode, rate limit, ...)
    accounts.json     account name -> role and SHA-256 hash of its token
    ratelimit.json    per-account timestamps of accepted requests
    clock.json        simulated time in seconds (only when clock = "simulated")
    requests.jsonl    request log, one JSON object per line

Because every request is a separate process that reads and writes these
files, counters and logs survive client restarts by construction.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path

from wmark.config import load_key, load_settings, threshold_of
from wmark.detector import EmptyInputError, is_flagged, score_text

# Which actions each role may perform (authorization).
ROLES = {
    "submitter": {"detect"},
    "auditor": {"detect", "read_logs"},
}

DEFAULT_CONFIG = {
    "mode": "score",              # "score" = green fraction + decision, "binary" = decision only
    "score_digits": 3,            # digits after the decimal point in score mode
    "rate_limit": {"enabled": True, "requests": 20, "window_seconds": 60},
    "clock": "simulated",         # "simulated" (experiments) or "real"
    "request_cost_seconds": 1.0,  # simulated seconds each request takes
    "max_chars": 20000,           # longer input is rejected
}

STATE_FILES = ("config.json", "accounts.json", "ratelimit.json", "clock.json", "requests.jsonl")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def read_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data) -> None:
    """Write atomically, so a crash never leaves a half-written state file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def load_config(state_dir: Path) -> dict:
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    user = read_json(state_dir / "config.json", {})
    rl = user.pop("rate_limit", None)
    cfg.update(user)
    if rl:
        cfg["rate_limit"].update(rl)
    if cfg["mode"] not in ("score", "binary"):
        raise ValueError(f"unknown mode {cfg['mode']!r}")
    return cfg


class DetectionService:
    def __init__(self, state_dir):
        self.dir = Path(state_dir)
        if not (self.dir / "accounts.json").exists():
            raise FileNotFoundError(
                f"No service state in {self.dir}. Create it with: python -m service.admin init --state {self.dir}")
        self.config = load_config(self.dir)
        self.accounts = read_json(self.dir / "accounts.json", {})
        settings = load_settings()
        if not settings.get("frozen"):
            raise RuntimeError("Detector settings are not frozen; Milestone 2 must use the frozen Milestone 1 settings.")
        self.threshold = threshold_of(settings)
        self._key = load_key(settings)

    # ------------------------------------------------------------- clock
    def now(self) -> float:
        if self.config["clock"] == "simulated":
            return float(read_json(self.dir / "clock.json", {"now": 0.0})["now"])
        return time.time()

    def _advance_clock(self) -> None:
        if self.config["clock"] == "simulated":
            write_json(self.dir / "clock.json", {"now": self.now() + float(self.config["request_cost_seconds"])})

    # ---------------------------------------------------- authentication
    def _authenticate(self, token) -> str | None:
        if not isinstance(token, str) or not token:
            return None
        h = hash_token(token)
        for name, acct in self.accounts.items():
            if hmac.compare_digest(h, acct["token_sha256"]):
                return name
        return None

    # ------------------------------------------------------ rate limiting
    def _rate_limit(self, account: str, now: float) -> dict:
        rl = self.config["rate_limit"]
        if not rl["enabled"]:
            return {"allowed": True, "used": None, "limit": None}
        state = read_json(self.dir / "ratelimit.json", {})
        window = float(rl["window_seconds"])
        recent = [t for t in state.get(account, []) if t > now - window]
        if len(recent) >= rl["requests"]:
            retry = round(min(recent) + window - now, 3)
            state[account] = recent
            write_json(self.dir / "ratelimit.json", state)
            return {"allowed": False, "used": len(recent), "limit": rl["requests"], "retry_after_seconds": retry}
        recent.append(now)
        state[account] = recent
        write_json(self.dir / "ratelimit.json", state)
        return {"allowed": True, "used": len(recent), "limit": rl["requests"]}

    # ------------------------------------------------------------ logging
    def _log(self, entry: dict) -> None:
        # Never log document text or scores (binary mode must hide scores everywhere).
        with open(self.dir / "requests.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def read_log(self, limit: int = 50) -> list[dict]:
        path = self.dir / "requests.jsonl"
        if not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return [json.loads(x) for x in lines[-limit:] if x.strip()]

    # ------------------------------------------------------------ request
    def handle(self, request) -> dict:
        now = self.now()
        rid = uuid.uuid4().hex[:12]
        entry = {"request_id": rid, "time": now, "clock": self.config["clock"],
                 "account": None, "role": None, "action": None, "outcome": None,
                 "rate_limit": None, "mode": self.config["mode"]}
        try:
            response = self._handle(request if isinstance(request, dict) else {}, entry)
        finally:
            self._log(entry)
            self._advance_clock()
        response["request_id"] = rid
        return response

    def _handle(self, request: dict, entry: dict) -> dict:
        action = request.get("action")
        entry["action"] = action if isinstance(action, str) else None

        account = self._authenticate(request.get("token"))
        if account is None:
            entry["outcome"] = "invalid_credential"
            return {"ok": False, "error": "invalid_credential"}
        role = self.accounts[account]["role"]
        entry.update(account=account, role=role)

        if action not in ROLES.get(role, set()):
            entry["outcome"] = "forbidden"
            return {"ok": False, "error": "forbidden", "detail": f"role {role!r} may not perform {action!r}"}

        rl = self._rate_limit(account, self.now())
        entry["rate_limit"] = {k: rl[k] for k in ("allowed", "used", "limit")}
        if not rl["allowed"]:
            entry["outcome"] = "rate_limited"
            return {"ok": False, "error": "rate_limited", "retry_after_seconds": rl["retry_after_seconds"]}

        if action == "read_logs":
            limit = request.get("limit", 50)
            limit = limit if isinstance(limit, int) and 0 < limit <= 1000 else 50
            entry["outcome"] = "ok"
            return {"ok": True, "entries": self.read_log(limit)}

        # action == "detect"
        text = request.get("text")
        if not isinstance(text, str):
            entry["outcome"] = "error:bad_request"
            return {"ok": False, "error": "bad_request", "detail": "text must be a string"}
        if len(text) > self.config["max_chars"]:
            entry["outcome"] = "error:too_long"
            return {"ok": False, "error": "too_long", "detail": f"max {self.config['max_chars']} characters"}
        try:
            result = score_text(text, self._key)
        except EmptyInputError:
            entry["outcome"] = "error:empty_input"
            return {"ok": False, "error": "empty_input"}
        flagged = is_flagged(result, self.threshold)
        entry["outcome"] = "flagged" if flagged else "not_flagged"
        response = {"ok": True, "flagged": flagged}
        if self.config["mode"] == "score":
            response["score"] = f"{result.score:.{self.config['score_digits']}f}"
        return response
