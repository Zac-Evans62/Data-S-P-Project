# Detection service (Milestone 2, spec 5.1)

A local service that wraps the frozen Milestone 1 detector (threshold 0.63,
same key and word rules). Clients send one JSON request and get one JSON response.

## Quick start

```bash
python -m service.admin init                 # creates service_state/ and credentials/ (real clock)
python scripts/client.py detect passage.txt --account submitter1
python scripts/client.py logs --account auditor1
python scripts/demo_controls.py              # demonstrates every control; saves a transcript
```

## Requests and responses

| Request | Response |
|---|---|
| `{"token": T, "action": "detect", "text": "..."}` | score mode: `{"ok": true, "flagged": true, "score": "0.700"}`; binary mode: `{"ok": true, "flagged": true}` |
| `{"token": T, "action": "read_logs", "limit": 50}` | `{"ok": true, "entries": [...]}` (auditors only) |
| any failure | `{"ok": false, "error": E}` with E one of `invalid_credential`, `forbidden`, `rate_limited` (plus `retry_after_seconds`), `empty_input`, `too_long`, `bad_request` |

Every response also carries a random `request_id`.

## Controls

| Control | How it works | Where |
|---|---|---|
| **Authentication** | Each account has a random 192-bit token (`secrets.token_urlsafe(24)`). The service stores only its SHA-256 hash and compares hashes in constant time. | `service/core.py` `_authenticate`, `service/admin.py` |
| **Authorization** | Roles: `submitter` may `detect`; `auditor` may `detect` and `read_logs`. Anything else is `forbidden`. | `ROLES` in `service/core.py` |
| **Logging** | One JSON line per request: request id, time, account, role, action, outcome, rate-limit status, mode. Failed logins are logged with account `null`. **Document text and scores are never logged**, in either mode. | `requests.jsonl` in the state directory |
| **Rate limiting** | Per account, sliding window: 20 accepted requests per 60 seconds. Rejected requests are logged but do not count. Counters are stored in `ratelimit.json`, so they survive client restarts. Invalid-credential and forbidden requests are checked before the limit and do not use the allowance. | `_rate_limit` in `service/core.py` |
| **Response modes** | `score`: green fraction to 3 decimal places plus the decision. `binary`: decision only; no score in the response or the log. | `config.json` `mode`, `score_digits` |
| **Simulated clock** | In experiments, time is a number in `clock.json`. Each request advances it by 1 simulated second; only the experiment driver can advance it further (`wait`). | `service/core.py`, `experiments/driver.py` |
| **Input limits** | Text must be a string of at most 20,000 characters; input with no words returns `empty_input`. | `config.json` `max_chars` |

**Score precision.** Scores are rounded to 3 decimal places for display, but the
decision uses the exact fraction. A displayed `0.630` can therefore be flagged
(for example 87/138 = 0.63043).

**Additional accounts.** Limits are per account, so an attacker with k accounts
gets k × 20 requests per minute. The demo shows `submitter2` still being served
while `submitter1` is limited. Limiting by person or network address, or
requiring identity checks to open accounts, would close this gap.

## The security boundary

```
attack code (attacks/query/)  ──uses──▶  client.Client  ──new process──▶  python -m service  ──▶  key, counters, log
        ▲                                                                                     ▲
        └──── receives only (client, wait) from ────  experiments/driver.py  ── may read ─────┘
```

- **Service** (`service/`): the only code that loads the key on a client's behalf.
  It runs as a separate process per request, so attack code never shares memory with the key.
- **Client** (`client/`): imports nothing from `wmark` or `service`; it only starts
  the service process and passes JSON.
- **Query-access attack code** (`attacks/query/`): may use only the `Client` and
  `wait` handed to it by the driver. It may not import `wmark`, `service`,
  `experiments` or `hmac`, or mention the key or state files.
  `tests/test_boundary.py` checks this automatically.
- **Key-access attack code** (`attacks/key/`): may also load the key.
- **Experiment driver** (`experiments/driver.py`): sets up and resets runs, advances
  the clock, and may compute hidden scores for analysis. It never passes them to
  query-access code.

The boundary is simulated: everything runs as the same user on one machine, so
it is enforced by code separation and the boundary test, not by the operating system.

## State directory

| File | Contents |
|---|---|
| `config.json` | mode, score digits, rate limit, clock, request cost, max characters |
| `accounts.json` | account → role and token hash |
| `ratelimit.json` | account → timestamps of accepted requests in the current window |
| `clock.json` | simulated time in seconds |
| `requests.jsonl` | the request log |

`python -m service.admin reset --state DIR` (or `ExperimentRun.reset()`) clears
counters, clock and log, keeping accounts and config.
