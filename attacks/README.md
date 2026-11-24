# Attack code (Milestone 2, spec 5.2)

## Access rules

| Folder | Attacks | May use |
|---|---|---|
| `attacks/query/` | 1 (removal with queries), 3 (forgery with queries) | Only the `client` and `wait` objects passed in by the driver. No `wmark`, `service`, `experiments`, `hmac`, key file or service state files (checked by `tests/test_boundary.py`). Must not reuse word colors or editing records from keyed watermarking. |
| `attacks/key/` | 2 (forgery with the key) | The key and `wmark` functions, plus the client. |

## How an attack run is wired

```python
from experiments.driver import ExperimentRun, CONFIGURATIONS
from attacks.query.forgery import run_forgery          # your attack code

run = ExperimentRun.create("attack3_config_C", **CONFIGURATIONS["C"])
client, wait = run.attacker_view("submitter1")
result = run_forgery(client, wait, originals, budget)  # attack sees only client + wait
run.write_json("attempts.json", result)
# driver-side analysis, never shown to the attacker:
hidden = [run.hidden_score(r["output"]) for r in result]
```

When the client returns `{"error": "rate_limited", "retry_after_seconds": s}`,
attack code calls `wait(s)` and retries; the driver records the waiting time.
`client.requests_sent` counts every request, including rejected ones.

## Budgets

Fixed in `config/attack_budgets.json` before any attack: 100 requests and
15 minutes per passage per variant or configuration, a separate preparation
budget of 100 requests for learning colors (Attack 3), and one shared budget
for the three character-change tests. Commit it and tag the commit
`budgets-set` before the first attack.

## Eligible passages (from the Milestone 1 evaluation run)

| Attack | Eligible | Excluded |
|---|---|---|
| 1. Removal with queries | 9 watermarked outputs (flagged and usable) | doyle_sherlock_0015 (output not flagged) |
| 2. Forgery with the key | 9 unmarked originals | thoreau_walden_0027 (original already flagged; record as a false positive) |
| 3. Forgery with queries | 5 forgery-selected originals: douglass_narrative_0026, dubois_souls_black_folk_0021, london_call_wild_0032, stevenson_treasure_0028, wells_time_machine_0022 | none (all 5 originals are unflagged) |

## Attack 2: forgery with the key (`attacks/key/forge.py`)

```bash
python -m attacks.key.forge setup                     # once: scores all 10 originals, marks eligibility
python -m attacks.key.forge start <id> --editor NAME  # 15-minute session on one eligible original
python -m attacks.key.forge check <id>                # local score, swaps still needed, red words (free)
python -m attacks.key.forge color WORD WORD ...       # colors of candidate replacements (free)
python -m attacks.key.forge finish <id>               # keep best in-time version, verify with the service
python -m attacks.key.forge packets                   # blind review sheets
python -m attacks.key.forge report                    # summary.md, attempts.csv, totals.json
```

The key gives local, free color checks; only service queries count toward the
100-request budget (each `finish` uses 1). Results go to
`results/milestone2/attack2_key_forgery/`. Colors learned here must **not** be
reused in Attack 3.

Removal succeeds only if the output is unflagged **and** passes a blind quality
check against both the watermarked input and the original. Forgery succeeds only
if the output is flagged and passes a quality check against the original.
Errors and rejected requests never count as success. Record every attempt,
including failures.