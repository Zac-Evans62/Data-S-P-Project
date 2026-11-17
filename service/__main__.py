"""Transport: one JSON request on stdin -> one JSON response on stdout.

    echo {"token": "...", "action": "detect", "text": "..."} | python -m service

The state directory comes from the WMARK_SERVICE_STATE environment variable
(default: service_state/ in the repo). Clients should use client.Client
rather than calling this directly.
"""

import json
import os
import sys
from pathlib import Path

from .core import DetectionService

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    state = os.environ.get("WMARK_SERVICE_STATE") or str(REPO_ROOT / "service_state")
    try:
        request = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        request = {}
    try:
        response = DetectionService(state).handle(request)
    except (FileNotFoundError, RuntimeError) as e:
        response = {"ok": False, "error": "service_unavailable", "detail": str(e)}
    sys.stdout.buffer.write(json.dumps(response).encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
