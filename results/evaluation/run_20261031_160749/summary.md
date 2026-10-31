# Evaluation run

Threshold 0.63 (flag if green fraction > threshold), target 0.66, time limit 15 min, key fingerprint e2d33beeda7d2c39.

## Headline measurements

| Measurement | Count | Rate |
|---|---|---|
| Unmarked false-positive rate | 11/150 | 7.3% |
| Detection rate on watermarking outputs | 9/10 | 90.0% |
| Usable watermarking success rate | 9/10 | 90.0% |
| Attempts that reached the target | 5/10 | |

## Uncertainty

- 3/n rule (valid only for 0 errors): 3/150 = 2.0%.
- Exact one-sided 95% upper bound for 11 errors in 150: 11.8%.
- These bounds assume independent passages. The 150 passages come from 7 source documents, so passages from the same book are correlated and the real uncertainty is larger.

## Annual false flags (for the policy memo)

- Assumed volume: 10,000 unmarked submissions per year (change with --annual-volume and justify it).
- Point estimate: 10,000 x 7.3% = 733 false flags.
- Using the 95% upper bound: 10,000 x 11.8% = up to about 1,185.
- Discuss how closely public-domain book passages resemble the operator's real submissions.

## By length group (unmarked evaluation passages)

| Group | Flagged | Tested | Mean words | Mean distinct/total |
|---|---|---|---|---|
| short | 6 | 50 | 69 | 0.76 |
| medium | 4 | 50 | 166 | 0.64 |
| long | 1 | 50 | 306 | 0.57 |

## Watermarking attempts (all 10, including failures)

| Passage | Original score | Final score | Reached target | Flagged | Changed words | Minutes | Stop reason | Quality | Forgery-selected |
|---|---|---|---|---|---|---|---|---|---|
| douglass_narrative_0009 | 0.572222 | 0.662921 | True | True | 18 | 14.2 | target reached | usable |  |
| douglass_narrative_0026 | 0.5 | 0.630435 | False | True | 62 | 24.8 | time limit reached | usable | yes |
| doyle_sherlock_0009 | 0.543478 | 0.664835 | True | True | 24 | 14.1 | target reached | usable |  |
| doyle_sherlock_0015 | 0.491713 | 0.620879 | False | False | 67 | 25.6 | time limit reached | usable |  |
| dubois_souls_black_folk_0021 | 0.587879 | 0.636364 | False | True | 9 | 15.6 | time limit reached | usable | yes |
| london_call_wild_0032 | 0.593023 | 0.637427 | False | True | 10 | 15.4 | time limit reached | usable | yes |
| london_call_wild_0037 | 0.555556 | 0.684211 | True | True | 51 | 12.6 | target reached | usable |  |
| stevenson_treasure_0028 | 0.566845 | 0.639785 | False | True | 16 | 15.5 | time limit reached | usable | yes |
| thoreau_walden_0027 | 0.685897 | 0.685897 | True | True | 0 | 0.6 | target reached | usable |  |
| wells_time_machine_0022 | 0.592 | 0.669231 | True | True | 33 | 11.1 | target reached | usable | yes |

Note: originals already flagged before watermarking (false positives; matters for Milestone 2 forgery eligibility): thoreau_walden_0027
