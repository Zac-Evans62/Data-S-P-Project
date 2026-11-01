# Keyed Text Watermarking: Detector, Evaluation and Threat Model

A word based keyed watermark for English composition, with a detector, a calibration/evaluation experiment and a threat model.

**Functionality** A secret key colors every normalized word green or red. Watermarking replaces red words with green synonyms. The detector computes the fraction of green word occurrences and flags text when that fraction is strictly above a threshold.

## Results at a glance

Official evaluation run: `results/evaluation/run_20261031_160749/` (full tables in its `summary.md`). Threshold 0.63, target 0.66.

| Measurement | Count | Rate |
|---|---|---|
| Unmarked false-positive rate (150 evaluation passages) | 11/150 | 7.3% |
| Detection rate on watermarking outputs | 9/10 | 90.0% |
| Usable watermarking success rate (flagged and passed blind review) | 9/10 | 90.0% |
| Attempts that reached the 0.66 target | 5/10 | |

- One of the 10 watermarking originals (`thoreau_walden_0027`) was already flagged before any editing, so it needed 0 edits. Excluding it, detection is 8/9.
- False flags by length group: short 6/50, medium 4/50, long 1/50.
- Exact one-sided 95% upper bound on the false-positive rate: 11.8%. The 150 passages come from only 7 books, so the real uncertainty is larger.

The threat model is in `report/threat_model.md`. The report outline is in `report/milestone1_outline.md`.

## Setup

Requires Python 3.10+ and nothing else (standard library only).

```bash
git clone <repo-url>
cd <repo>
python -m unittest -v          # 18 tests should pass
```

Score any text file, and see each word's color:

```bash
python scripts/score.py file.txt --threshold 0.63 --colors
```

Check a saved watermarking output:

```bash
python scripts/score.py data/watermarked/<passage_id>/final.txt --threshold 0.63
```

On Windows PowerShell use backslashes in paths and run commands one per line (older PowerShell doesn't support `&&`).

## Reproducing the results

The editing was done by hand and every version is saved, so reproducing the numbers means re-scoring the saved files, not redoing the editing.

```bash
python -m unittest -v
python scripts/run_evaluation.py --annual-volume 10000
python scripts/repetition_analysis.py --set evaluation
```

`run_evaluation.py` only runs once settings are frozen (`config/settings.json`, `frozen: true`) and writes a new timestamped folder under `results/evaluation/`, so re-running never overwrites the official run listed above. The official calibration run (all thresholds 0.55 to 0.65) is `results/calibration/run_20261029_173414/`; earlier calibration runs are kept as a record only.

### Run order of the experiment

Do not repeat steps 0 and 1: the key and the split are generated once, and `split_data.py` refuses to run twice.

```bash
# 0. once, by one person; the result is committed
python scripts/generate_key.py

# 1. data: put books in data/sources/ and fill sources.csv, then
python scripts/collect_passages.py
python scripts/find_junk.py              # flags junk passages (tables of contents, poetry, footnotes)
python scripts/split_data.py             # BEFORE any scoring; writes results/split_report.md

# 2. calibration (calibration passages only)
python scripts/wm_session.py start <calib_id> --editor NAME --target <practice_target>
python scripts/wm_session.py check <calib_id>    # repeat while editing working.txt
python scripts/wm_session.py finish <calib_id>
python scripts/make_review_packets.py --set calibration
python scripts/run_calibration.py
#    -> choose threshold + target, write them into config/settings.json

# 3. freeze
python scripts/freeze_settings.py
git commit -am "Freeze settings"
git tag settings-frozen
git push --tags

# 4. evaluation (one attempt per passage, settings frozen)
python scripts/wm_session.py start <eval_id> --editor NAME      # x10, then check / finish
python scripts/make_review_packets.py --set evaluation
python scripts/run_evaluation.py --annual-volume 10000
python scripts/repetition_analysis.py --set evaluation
```

## Repository layout

| Path | What it is |
|---|---|
| `wmark/textproc.py` | Word rules (tokenization and normalization), shared by everything |
| `wmark/detector.py` | HMAC word colors, exact scoring, strict-greater flag decision, empty-input error |
| `wmark/metrics.py` | Changed-word counting and small-sample error bounds |
| `wmark/manifest.py` | Reads and writes the passage manifest (`data/manifest.csv`) |
| `wmark/reviews.py` | Quality-review records; rejects a review by the passage's own editor |
| `wmark/experiment.py` | Shared helpers for the calibration and evaluation scripts |
| `scripts/` | The commands listed in the run order above, plus `score.py` and `repetition_analysis.py` |
| `config/settings.json` | Seed, key file, threshold, target, time limit, frozen flag, key fingerprint |
| `config/key.hex` | The experiment key (demonstration key, committed on purpose) |
| `data/sources/` | Public-domain books and `sources.csv` |
| `data/passages/` | Every candidate passage; originals, never edited |
| `data/manifest.csv` | One row per passage: source, length group, word counts, set, role |
| `data/watermarked/<id>/` | One folder per watermarking session: every version, `log.json`, `final.txt` |
| `data/synonyms.tsv` | The team's red-to-green synonym list |
| `quality_checks/` | Blind review packets and `reviews.csv` |
| `results/` | Split report, every calibration and evaluation run, repetition analysis, common-word colors |
| `report/` | Report outline and threat model |
| `tests/` | 18 unit tests for the word rules, scoring, threshold tie, empty input, repetition |

## Frozen settings

Chosen from the calibration data only, then frozen before evaluation (git tag `settings-frozen`).

| Setting | Value |
|---|---|
| Detection threshold | 0.63 (flag if green fraction is strictly greater) |
| Watermarking target | 0.66 |
| Stopping rule | Stop at the target or after 15 minutes, keep the best version |
| Random seed | 2026 |
| Key fingerprint | `e2d33beeda7d2c39` |

A score exactly equal to the threshold is not flagged. Fractions are compared exactly, not as floats.

## Word rules

Full version in the docstring of `wmark/textproc.py`. The same rules are used for watermarking and detection.

1. Unicode NFKC normalization.
2. The invisible characters U+200B, U+200C, U+200D, U+2060, U+FEFF and the soft hyphen U+00AD are deleted (not turned into spaces).
3. Curly apostrophes become `'`.
4. Case folding (`Book` becomes `book`).
5. A word is a run of Unicode letters or digits, with optional single internal apostrophes (`don't`). Hyphens, underscores and all other punctuation separate words. Digits count as words.

Empty input (no words) raises an explicit error. Each score also records total and distinct word counts, and repeated words count every time.

## Data

- **Sources:** 15 public-domain books from Project Gutenberg, listed with title, author, URL and license in `data/sources/sources.csv`.
- **Passages:** 300 unmarked passages in three length groups (30–99, 100–199, 200–400 words) plus 15 additional passages of 100–200 words for watermarking, all distinct, 315 in total. Cutting method: docstring of `scripts/collect_passages.py`.
- **Split** (`results/split_report.md`, seed 2026; every book sits entirely in one set):

| Set | Unmarked (short / medium / long) | Watermark passages | Books |
|---|---|---|---|
| Calibration | 50 / 50 / 50 | 5 | austen_emma, austen_pride, bronte_jane_eyre, dickens_expectations, franklin_autobiography, jerome_three_men, shelley_frankenstein, washington_up_from_slavery |
| Evaluation | 50 / 50 / 50 | 10 | douglass_narrative, doyle_sherlock, dubois_souls_black_folk, london_call_wild, stevenson_treasure, thoreau_walden, wells_time_machine |

- **Forgery passages for Milestone 2:** 5 of the 10 evaluation watermarking passages were selected before any scoring with `random.Random(2026).sample(sorted_ids, 5)`: `douglass_narrative_0026`, `dubois_souls_black_folk_0021`, `london_call_wild_0032`, `stevenson_treasure_0028`, `wells_time_machine_0022`.

## Quality checks

Every watermarking output (15 in all) was reviewed by a teammate who did not edit it. The reviewer sees the original, the edited text and a word diff, and does not see scores or detector decisions. They answer two yes/no questions: is the main meaning preserved, and is the prose readable. An output is usable only if it is flagged and both answers are yes. Packets are in `quality_checks/packets/` and answers in `quality_checks/reviews.csv`. Process details: `quality_checks/README.md`.

## Key handling

One random 32-byte key, generated once with `scripts/generate_key.py` and never regenerated. It is a demonstration key committed so results can be reproduced. Reports cite its fingerprint (first 16 hex digits of SHA-256), not the key itself.

## Known limitations

- Detection is statistical. Measured false-positive rate is 7.3% on book passages, much higher than a coin-flip model predicts (about 0.07% at 150 words), because common words push unmarked text above 0.50 under this key.
- Word-level watermarks do not survive paraphrase, and the word rules leave look-alike letters and some invisible characters untouched (see the threat model).

## Contribution statement

<!-- Draft from the commit history; confirm each line with its owner and add real commit links: https://github.com/<org>/<repo>/commit/<sha> -->

| Member | Contributions | Key commits |
|---|---|---|
| Billy Vincini | Compiled the 15-book source list (`sources.csv`); blind reviews of the calibration outputs; edited 5 of the 10 evaluation passages; wrote the threat model (`report/threat_model.md`) and report Section 6 |  [`cff45df`](https://github.com/Zac-Evans62/Data-S-P-Project/commit/cff45df), [`e8fff16`](https://github.com/Zac-Evans62/Data-S-P-Project/commit/e8fff16), [`d136d4e`](https://github.com/Zac-Evans62/Data-S-P-Project/commit/d136d4e), [`2d3032c`](https://github.com/Zac-Evans62/Data-S-P-Project/commit/2d3032c) |
| Zachary Evans | Repository scaffold and detector; passage collection, junk removal and split; calibration practice watermarking and threshold choice; froze settings; edited 5 of the 10 evaluation passages; blind reviews of evaluation outputs; ran the evaluation | [`34ab017`](https://github.com/Zac-Evans62/Data-S-P-Project/commit/34ab017), [`110e6db`](https://github.com/Zac-Evans62/Data-S-P-Project/commit/110e6db), [`0ba15ab`](https://github.com/Zac-Evans62/Data-S-P-Project/commit/0ba15ab), [`673e138`](https://github.com/Zac-Evans62/Data-S-P-Project/commit/673e138), [`8612100`](https://github.com/Zac-Evans62/Data-S-P-Project/commit/8612100), [`0400b0f`](https://github.com/Zac-Evans62/Data-S-P-Project/commit/0400b0f), [`cc09f02`](https://github.com/Zac-Evans62/Data-S-P-Project/commit/cc09f02) |