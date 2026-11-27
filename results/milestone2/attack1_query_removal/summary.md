# Attack 1: removal with detector queries

Service: score mode (3 digits), rate limit 20 requests per minute. Budgets: word substitution 15 minutes and 100 requests per passage; the three character tests share one 100-request budget per passage.

Eligible watermarked outputs: 9. Excluded: doyle_sherlock_0015 (output not flagged)

| Variant | Unflagged | Successes (unflagged and usable) | Requests (total) |
|---|---|---|---|
| word substitution | 9/9 | 9/9 (100%) | 170 |
| case | 0/9 | 0/9 (0%) | 9 |
| zero width | 0/9 | 0/9 (0%) | 9 |
| punctuation | 9/9 | 9/9 (100%) | 107 |
| **character changes overall** (any of the three) | | 9/9 (100%) | 125 |

Time: word substitution used 48.6 editing minutes in total (plus 320 simulated seconds waiting out rate limits); the automated character tests took 367 simulated seconds in total (1 second per request plus rate-limit waits). Request counts include requests rejected by the rate limit.

| Passage | Variant | Start | Margin (green words) | Final | Unflagged | Changed words | Requests | Minutes | Quality | Success |
|---|---|---|---|---|---|---|---|---|---|---|
| douglass_narrative_0009 | word substitution | 0.663 | 6 | 0.624 | True | 22 | 4 | 5.5 | usable | True |
| douglass_narrative_0009 | case | 0.663 | 6 | 0.663 | False | 0 | 1 |  | n/a (still flagged) | False |
| douglass_narrative_0009 | zero width | 0.663 | 6 | 0.663 | False | 0 | 1 |  | n/a (still flagged) | False |
| douglass_narrative_0009 | punctuation | 0.663 | 6 | 0.627 | True | 14 | 11 |  | usable | True |
| douglass_narrative_0026 | word substitution | 0.630 | 1 | 0.619 | True | 13 | 1 | 1.7 | usable | True |
| douglass_narrative_0026 | case | 0.630 | 1 | 0.630 | False | 0 | 1 |  | n/a (still flagged) | False |
| douglass_narrative_0026 | zero width | 0.630 | 1 | 0.630 | False | 0 | 1 |  | n/a (still flagged) | False |
| douglass_narrative_0026 | punctuation | 0.630 | 1 | 0.626 | True | 2 | 4 |  | usable | True |
| doyle_sherlock_0009 | word substitution | 0.665 | 7 | 0.626 | True | 31 | 52 | 9.1 | usable | True |
| doyle_sherlock_0009 | case | 0.665 | 7 | 0.665 | False | 0 | 1 |  | n/a (still flagged) | False |
| doyle_sherlock_0009 | zero width | 0.665 | 7 | 0.665 | False | 0 | 1 |  | n/a (still flagged) | False |
| doyle_sherlock_0009 | punctuation | 0.665 | 7 | 0.627 | True | 22 | 19 |  | usable | True |
| dubois_souls_black_folk_0021 | word substitution | 0.636 | 2 | 0.627 | True | 8 | 1 | 1.0 | usable | True |
| dubois_souls_black_folk_0021 | case | 0.636 | 2 | 0.636 | False | 0 | 1 |  | n/a (still flagged) | False |
| dubois_souls_black_folk_0021 | zero width | 0.636 | 2 | 0.636 | False | 0 | 1 |  | n/a (still flagged) | False |
| dubois_souls_black_folk_0021 | punctuation | 0.636 | 2 | 0.629 | True | 4 | 4 |  | usable | True |
| london_call_wild_0032 | word substitution | 0.637 | 2 | 0.615 | True | 12 | 1 | 2.0 | usable | True |
| london_call_wild_0032 | case | 0.637 | 2 | 0.637 | False | 0 | 1 |  | n/a (still flagged) | False |
| london_call_wild_0032 | zero width | 0.637 | 2 | 0.637 | False | 0 | 1 |  | n/a (still flagged) | False |
| london_call_wild_0032 | punctuation | 0.637 | 2 | 0.628 | True | 2 | 10 |  | usable | True |
| london_call_wild_0037 | word substitution | 0.684 | 7 | 0.614 | True | 42 | 28 | 6.3 | usable | True |
| london_call_wild_0037 | case | 0.684 | 7 | 0.684 | False | 0 | 1 |  | n/a (still flagged) | False |
| london_call_wild_0037 | zero width | 0.684 | 7 | 0.684 | False | 0 | 1 |  | n/a (still flagged) | False |
| london_call_wild_0037 | punctuation | 0.684 | 7 | 0.622 | True | 10 | 10 |  | usable | True |
| stevenson_treasure_0028 | word substitution | 0.640 | 2 | 0.616 | True | 14 | 1 | 2.3 | usable | True |
| stevenson_treasure_0028 | case | 0.640 | 2 | 0.640 | False | 0 | 1 |  | n/a (still flagged) | False |
| stevenson_treasure_0028 | zero width | 0.640 | 2 | 0.640 | False | 0 | 1 |  | n/a (still flagged) | False |
| stevenson_treasure_0028 | punctuation | 0.640 | 2 | 0.628 | True | 4 | 6 |  | usable | True |
| thoreau_walden_0027 | word substitution | 0.686 | 9 | 0.623 | True | 39 | 40 | 12.0 | usable | True |
| thoreau_walden_0027 | case | 0.686 | 9 | 0.686 | False | 0 | 1 |  | n/a (still flagged) | False |
| thoreau_walden_0027 | zero width | 0.686 | 9 | 0.686 | False | 0 | 1 |  | n/a (still flagged) | False |
| thoreau_walden_0027 | punctuation | 0.686 | 9 | 0.627 | True | 20 | 20 |  | usable | True |
| wells_time_machine_0022 | word substitution | 0.669 | 6 | 0.585 | True | 38 | 42 | 8.7 | usable | True |
| wells_time_machine_0022 | case | 0.669 | 6 | 0.669 | False | 0 | 1 |  | n/a (still flagged) | False |
| wells_time_machine_0022 | zero width | 0.669 | 6 | 0.669 | False | 0 | 1 |  | n/a (still flagged) | False |
| wells_time_machine_0022 | punctuation | 0.669 | 6 | 0.628 | True | 14 | 23 |  | usable | True |
