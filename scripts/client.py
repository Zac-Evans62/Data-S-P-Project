"""Command-line client for the detection service (for people; attack code uses client.Client).

    python -m service.admin init                       # once: creates service_state/ and credentials/
    python scripts/client.py detect passage.txt --account submitter1
    echo "Some text" | python scripts/client.py detect - --account submitter1
    python scripts/client.py logs --account auditor1 --limit 10

Uses service_state/ and credentials/ by default; pass --state and
--credentials to talk to an experiment run, e.g.
    --state results/milestone2/controls_demo/state --credentials results/milestone2/controls_demo/credentials
"""
import _bootstrap  # noqa: F401

import argparse
import json
import sys
from pathlib import Path

from client import Client

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["detect", "logs"])
    ap.add_argument("path", nargs="?", help="text file, or - for stdin (detect only)")
    ap.add_argument("--account", default="submitter1")
    ap.add_argument("--state", default=str(ROOT / "service_state"))
    ap.add_argument("--credentials", default=str(ROOT / "credentials"))
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    token_file = Path(args.credentials) / f"{args.account}.token"
    if not token_file.exists():
        sys.exit(f"No token at {token_file}. Create accounts with: python -m service.admin init")
    c = Client.from_token_file(token_file, args.state)
    if args.action == "logs":
        r = c.read_logs(args.limit)
    else:
        if not args.path:
            sys.exit("detect needs a file path or -")
        text = sys.stdin.read() if args.path == "-" else open(args.path, encoding="utf-8").read()
        r = c.detect(text)
    print(json.dumps(r, indent=2))


if __name__ == "__main__":
    main()
