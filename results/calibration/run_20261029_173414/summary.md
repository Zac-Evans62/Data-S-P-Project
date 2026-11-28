# Calibration run

Unmarked calibration passages: 150; watermark outputs finished: 5/5.

Unmarked green fraction: min 0.391, median 0.532, max 0.707.

## Threshold sweep

| Threshold | Unmarked flagged | Watermark outputs unflagged |
|---|---|---|
| 0.55 | 47/150 | 0/5 |
| 0.60 | 14/150 | 0/5 |
| 0.61 | 12/150 | 0/5 |
| 0.62 | 8/150 | 1/5 |
| 0.63 | 6/150 | 1/5 |
| 0.64 | 3/150 | 1/5 |
| 0.65 | 2/150 | 3/5 |

## Watermarking practice

| Passage | Original | Final | Target | Reached | Changed words | Minutes | Stop reason | Quality |
|---|---|---|---|---|---|---|---|---|
| austen_emma_0025 | 0.486111 | 0.641509 | 0.70 | False | 65 | 19.2 | time limit reached | usable |
| bronte_jane_eyre_0028 | 0.544776 | 0.644809 | 0.70 | False | 76 | 15.8 | time limit reached | usable |
| jerome_three_men_0021 | 0.645833 | 0.717949 | 0.70 | True | 33 | 9.3 | target reached | usable |
| shelley_frankenstein_0039 | 0.658031 | 0.70297 | 0.70 | True | 28 | 8.0 | target reached | usable |
| washington_up_from_slavery_0038 | 0.483444 | 0.6125 | 0.70 | False | 85 | 18.0 | time limit reached | usable |
