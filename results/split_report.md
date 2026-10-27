# Data split report

Seed used: 2026 (base seed 2026 from config/settings.json, attempt 0).

Method: whole books assigned to one set (greedy balancing after a seeded shuffle); passages picked round-robin across books; watermark passages drawn from the 100-199 word group.

| Set | Unmarked short | medium | long | Unmarked total | Watermark | Source documents |
|---|---|---|---|---|---|---|
| calibration | 50 | 50 | 50 | 150 | 5 | 8 |
| evaluation | 50 | 50 | 50 | 150 | 10 | 7 |

## Books per set

- **calibration**: austen_emma, austen_pride, bronte_jane_eyre, dickens_expectations, franklin_autobiography, jerome_three_men, shelley_frankenstein, washington_up_from_slavery
- **evaluation**: douglass_narrative, doyle_sherlock, dubois_souls_black_folk, london_call_wild, stevenson_treasure, thoreau_walden, wells_time_machine

## Watermark passages

- **calibration**: austen_emma_0025, bronte_jane_eyre_0028, jerome_three_men_0021, shelley_frankenstein_0039, washington_up_from_slavery_0038
- **evaluation**: douglass_narrative_0009, douglass_narrative_0026, doyle_sherlock_0009, doyle_sherlock_0015, dubois_souls_black_folk_0021, london_call_wild_0032, london_call_wild_0037, stevenson_treasure_0028, thoreau_walden_0027, wells_time_machine_0022

## Query-access forgery passages (Milestone 2)

Selected 5 of the 10 evaluation watermark passages with `random.Random(2026).sample(sorted_ids, 5)`, before any detector scores existed:

- douglass_narrative_0026
- dubois_souls_black_folk_0021
- london_call_wild_0032
- stevenson_treasure_0028
- wells_time_machine_0022
