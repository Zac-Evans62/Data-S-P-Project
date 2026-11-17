"""Create or reset service state (operator tool; never used by attack code).

    python -m service.admin init --state service_state --credentials credentials \\
        --account submitter1=submitter --account auditor1=auditor --mode score
    python -m service.admin reset --state service_state

`init` writes a fresh state directory and one token file per account into
the credentials directory (demonstration credentials only). `reset` clears
rate-limit counters, the clock and the log, keeping accounts and config.
"""

from __future__ import annotations

import argparse
import json
import secrets
import shutil
from pathlib import Path

from .core import DEFAULT_CONFIG, ROLES, hash_token, write_json

DEFAULT_ACCOUNTS = {"submitter1": "submitter", "submitter2": "submitter", "auditor1": "auditor"}


def init_state(state_dir, credentials_dir, accounts=None, config=None, overwrite=False) -> dict[str, str]:
    """Create a fresh state directory. Returns {account: token}."""
    state_dir, credentials_dir = Path(state_dir), Path(credentials_dir)
    accounts = accounts or DEFAULT_ACCOUNTS
    for name, role in accounts.items():
        if role not in ROLES:
            raise ValueError(f"unknown role {role!r} for {name!r}; roles: {sorted(ROLES)}")
    if state_dir.exists():
        if not overwrite:
            raise FileExistsError(f"{state_dir} already exists (use overwrite=True / --overwrite)")
        shutil.rmtree(state_dir)
    state_dir.mkdir(parents=True)
    credentials_dir.mkdir(parents=True, exist_ok=True)

    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    for k, v in (config or {}).items():
        if k == "rate_limit":
            cfg["rate_limit"].update(v)
        else:
            cfg[k] = v
    write_json(state_dir / "config.json", cfg)

    tokens, records = {}, {}
    for name, role in accounts.items():
        token = secrets.token_urlsafe(24)
        tokens[name] = token
        records[name] = {"role": role, "token_sha256": hash_token(token)}
        (credentials_dir / f"{name}.token").write_text(token + "\n", encoding="utf-8")
    write_json(state_dir / "accounts.json", records)
    reset_state(state_dir)
    return tokens


def reset_state(state_dir) -> None:
    """Clear counters, clock and log; keep accounts and config."""
    state_dir = Path(state_dir)
    write_json(state_dir / "ratelimit.json", {})
    write_json(state_dir / "clock.json", {"now": 0.0})
    (state_dir / "requests.jsonl").write_text("", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--state", default="service_state")
    i.add_argument("--credentials", default="credentials")
    i.add_argument("--account", action="append", metavar="NAME=ROLE",
                   help="repeatable; default: submitter1, submitter2, auditor1")
    i.add_argument("--mode", choices=["score", "binary"], default="score")
    i.add_argument("--no-rate-limit", action="store_true")
    i.add_argument("--clock", choices=["simulated", "real"], default="real",
                   help="real for interactive use; experiments use simulated (default here: real)")
    i.add_argument("--overwrite", action="store_true")
    r = sub.add_parser("reset")
    r.add_argument("--state", default="service_state")
    args = ap.parse_args()

    if args.cmd == "reset":
        reset_state(args.state)
        print(f"Reset counters, clock and log in {args.state}")
        return
    accounts = dict(a.split("=", 1) for a in args.account) if args.account else None
    config = {"mode": args.mode, "clock": args.clock, "rate_limit": {"enabled": not args.no_rate_limit}}
    tokens = init_state(args.state, args.credentials, accounts, config, args.overwrite)
    print(f"Created {args.state} ({args.mode} mode, clock {args.clock}). Tokens written to {args.credentials}/:")
    for name in tokens:
        print(f"  {name}.token")


if __name__ == "__main__":
    main()
