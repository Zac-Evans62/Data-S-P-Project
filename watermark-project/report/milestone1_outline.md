# Milestone 1 report outline (max 6 pages; references and contribution statement excluded)

Point values from the grading table are in brackets. Every number should
point to a file in `results/`.

## 1. The scheme and our detector  [10]
- How the key + HMAC assigns colors; how substitution embeds the watermark; how the score works. (Objective 1.)
- **Word rules** (from wmark/textproc.py): case, punctuation, apostrophes, hyphens, Unicode NFKC, zero-width characters, digits. One short table of examples.
- Scoring: repeated words counted; distinct words recorded; exact fraction comparison; equal-to-threshold is not flagged; empty input raises an error.
- Point to `tests/test_detector.py` as evidence.

## 2. Data  [part of 15]
- Sources: number of books, authors, periods (table in appendix or README).
- Passage cutting method and length groups.
- Split: whole books per set, counts per set and group (from `results/split_report.md`).
- How the 5 query-forgery passages were selected (seeded random, before scoring).

## 3. Calibration  [5]
- Unmarked calibration score distribution.
- Watermarking practice: target, stopping rule, what you adjusted and why, using calibration only.
- Threshold sweep table (from `results/calibration/run_*/summary.md`) and the reasoning for the chosen threshold.
- Frozen settings: key fingerprint, threshold, target, time limit, git tag `settings-frozen`.

## 4. Evaluation results  [5]
- Headline table: false-positive rate, detection rate, usable success rate.
- All 10 attempts, including failures: scores before/after, reached target, changed words (and counting method), minutes, stop reason, quality result.
- Quality-check process and how reviewer knowledge could bias it.

## 5. Interpretation  [5]
- Per length group: flagged/tested.
- Repetition: the most repetitive passage (from `scripts/repetition_analysis.py`), and the 1,000-repeats demo.
- Small samples: 3/n bound (or exact bound if errors > 0), and why shared books make it optimistic.
- Annual false flags: assumed volume, estimate, upper estimate, how book passages differ from real submissions.
- Any post-evaluation changes, reported separately.

## 6. Threat model  [20]
- The 2 x 3 table (from `report/threat_model.md`), predictions labelled.
- Key distribution, context dependence, digital signatures.

## 7. Reading
- One paragraph comparing Kirchenbauer et al.'s generation-time watermark with our word substitution.

## References

## Contribution statement
- Each member: what they did, with links to commits.
