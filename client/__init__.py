"""Client for the detection service: the ONLY interface attack code may use.

Each call starts `python -m service` as a separate process, sends one JSON
request and reads one JSON response. This module deliberately imports
nothing from `wmark` or `service`, so code that uses it cannot read the key,
call the color function, or touch the service's counters, logs or clock.

    from client import Client
    c = Client.from_token_file("credentials/submitter1.token", state_dir="service_state")
    c.detect("Some text")        # {'ok': True, 'flagged': False, 'score': '0.512', 'request_id': ...}
    c.requests_sent              # how many requests this client has sent (including rejected ones)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class ServiceError(RuntimeError):
    """The service process itself failed (not a normal error response)."""


class Client:
    def __init__(self, token: str, state_dir=None, timeout: float = 60):
        self.token = token
        self._state_dir = str(Path(state_dir).resolve()) if state_dir else None
        self.timeout = timeout
        self.requests_sent = 0

    @classmethod
    def from_token_file(cls, path, state_dir=None, **kw) -> "Client":
        return cls(Path(path).read_text(encoding="utf-8").strip(), state_dir, **kw)

    def _call(self, payload: dict) -> dict:
        env = dict(os.environ)
        if self._state_dir:
            env["WMARK_SERVICE_STATE"] = self._state_dir
        proc = subprocess.run(
            [sys.executable, "-m", "service"],
            input=json.dumps(payload).encode("utf-8"),
            capture_output=True, cwd=REPO_ROOT, env=env, timeout=self.timeout,
        )
        self.requests_sent += 1
        if proc.returncode != 0:
            raise ServiceError(proc.stderr.decode("utf-8", "replace")[-2000:])
        return json.loads(proc.stdout.decode("utf-8"))

    def detect(self, text: str) -> dict:
        return self._call({"token": self.token, "action": "detect", "text": text})

    def read_logs(self, limit: int = 50) -> dict:
        return self._call({"token": self.token, "action": "read_logs", "limit": limit})
