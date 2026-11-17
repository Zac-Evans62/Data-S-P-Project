# Service controls demonstration

Settings: score mode (3 digits), rate limit 20 requests per 60 simulated seconds, accounts submitter1 and submitter2 (role submitter) and auditor1 (role auditor). Every request ran as a separate client process.

## 1. Authentication: invalid credentials are rejected
- **valid submitter token:** `{"ok": true, "flagged": true, "score": "0.700"}`
- **wrong token:** `{"ok": false, "error": "invalid_credential"}`
- **empty token:** `{"ok": false, "error": "invalid_credential"}`

## 2. Authorization: roles are enforced
- **submitter1 asks to read logs:** `{"ok": false, "error": "forbidden", "detail": "role 'submitter' may not perform 'read_logs'"}`
- **auditor1 reads logs:** ok=True, 3 entries returned
- **auditor1 also allowed to detect:** `{"ok": true, "flagged": true, "score": "0.700"}`

## 3. Logging: account, time, outcome and rate-limit status; no document text
- Last log entry: `{"request_id": "237242fe6dc9", "time": 6.0, "clock": "simulated", "account": "submitter1", "role": "submitter", "action": "detect", "outcome": "not_flagged", "rate_limit": {"allowed": true, "used": 2, "limit": 20}, "mode": "score"}`
- Secret phrase present in the log file: **False**
- Any log entry containing a score value: **False**

## 4. Rate limiting persists across client restarts
Counters reset by the driver. submitter1 now sends 20 requests, each from a new Client object and process:
- **request 21, from a brand-new client:** `{"ok": false, "error": "rate_limited", "retry_after_seconds": 40.0}`
- **submitter2 at the same moment (separate allowance):** `{"ok": true, "flagged": true, "score": "0.700"}`
- **submitter1 after the driver advances the clock 61 s:** `{"ok": true, "flagged": true, "score": "0.700"}`

## 5. Response modes
- **score mode, ordinary text:** `{"ok": true, "flagged": true, "score": "0.700"}`
- **binary mode, same text:** `{"ok": true, "flagged": true}`
- Any binary-mode log entry containing a score value: **False**
- **binary mode, 'the' repeated 100 times:** `{"ok": true, "flagged": true}`
- **binary mode, 'watermark' repeated 100 times:** `{"ok": true, "flagged": false}`
- Even without scores, a repeated single word is flagged exactly when that word is green, so the binary response still discloses word colors (Attack 3).

## 6. Additional accounts
- Each account has its own allowance of 20 requests per minute, so an attacker holding k accounts gets k x 20 requests per minute. Section 4 shows submitter2 still served while submitter1 is limited.
