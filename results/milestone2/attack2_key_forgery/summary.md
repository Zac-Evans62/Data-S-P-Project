# Attack 2: forgery with the key

Settings: threshold 0.63, target 0.66, budget per passage 15 minutes and 100 requests (`config/attack_budgets.json`). Local color checks with the key are free; only service queries count.

| Group | Eligible | Attempted | Flagged by service | Successes (flagged and usable) |
|---|---|---|---|---|
| All 10 originals | 9 | 9 | 9 | 9/9 (100%) |
| The 5 forgery-selected originals | 5 | 5 | 5 | 5/5 (100%) |

Excluded as false positives (original already flagged): thoreau_walden_0027

| Passage | Selected | Original | Final | Flagged | Changed words | Minutes | Requests | Stop reason | Quality | Success |
|---|---|---|---|---|---|---|---|---|---|---|
| douglass_narrative_0009 |  | 0.572 | 0.667 | True | 21 | 11.1 | 1 | target reached | usable | True |
| douglass_narrative_0026 | yes | 0.500 | 0.662 | True | 43 | 11.7 | 1 | target reached | usable | True |
| doyle_sherlock_0009 |  | 0.543 | 0.665 | True | 25 | 9.3 | 1 | target reached | usable | True |
| doyle_sherlock_0015 |  | 0.492 | 0.645 | True | 43 | 14.4 | 1 | time limit reached | usable | True |
| dubois_souls_black_folk_0021 | yes | 0.588 | 0.660 | True | 25 | 7.0 | 1 | target reached | usable | True |
| london_call_wild_0032 | yes | 0.593 | 0.663 | True | 21 | 8.9 | 1 | target reached | usable | True |
| london_call_wild_0037 |  | 0.556 | 0.667 | True | 24 | 8.2 | 1 | target reached | usable | True |
| stevenson_treasure_0028 | yes | 0.567 | 0.670 | True | 31 | 11.5 | 1 | target reached | usable | True |
| thoreau_walden_0027 |  | 0.686 | excluded | | | | | | | |
| wells_time_machine_0022 | yes | 0.592 | 0.661 | True | 13 | 5.3 | 1 | target reached | usable | True |
