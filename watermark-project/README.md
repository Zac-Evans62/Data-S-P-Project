# Keyed Text Watermarking — Team Project

Word-based keyed watermark: a secret key colors every word green or red,
watermarking swaps red words for green synonyms, and the detector flags text
whose green fraction is above a threshold.

**Milestone 1:** detector, calibration/evaluation, threat model.
See [CHECKLIST.md](CHECKLIST.md) for the full to-do list.

## Setup

Python 3.10+ only; no third-party packages.

```bash
git clone <repo-url> && cd <repo>
python -m unittest -v          # 18 tests should pass
```

## Repository layout

| Path | What it is |
|---|---|
| `wmark/textproc.py` | **Word rules** (tokenization + normalization). Shared by everything. |
| `wmark/detector.py` | HMAC word colors, exact scoring, flag decision, empty-input error |
| `wmark/metrics.py` | Changed-word counting, small-sample error bounds |
| `wmark/manifest.py` | The passage manifest (`data/manifest.csv`) |
| `config/settings.json` | Seed, key file, threshold, target, time limit, frozen flag |
| `config/key.hex` | The experiment key (demonstration key, committed for reproducibility) |
| `data/sources/` | Public-domain books + `sources.csv` |
| `data/passages/` | Every candidate passage (originals, never edited) |
| `data/watermarked/<id>/` | Watermarking sessions: every version, log, `final.txt` |
| `data/synonyms.tsv` | Team synonym list |
| `quality_checks/` | Blind review packets and `reviews.csv` |
| `results/` | Split report and every calibration/evaluation run |
| `report/` | Report outline and threat model draft |
| `tests/` | Unit tests |

## Run order (Milestone 1)

```bash
# 0. once, by one person; commit the result
python scripts/generate_key.py

# 1. data: put books in data/sources/ and fill sources.csv, then
python scripts/collect_passages.py
python scripts/split_data.py            # BEFORE any scoring; commit manifest + results/split_report.md

# 2. calibration (calibration passages only)
python scripts/wm_session.py start <calib_id> --editor NAME --target 0.70
python scripts/wm_session.py check <calib_id>    # repeat while editing working.txt
python scripts/wm_session.py finish <calib_id>
python scripts/make_review_packets.py --set calibration   # reviewers fill quality_checks/reviews.csv
python scripts/run_calibration.py
#    -> choose threshold + target, write them into config/settings.json (as strings)

# 3. freeze
python scripts/freeze_settings.py
git commit -am "Freeze settings" && git tag settings-frozen && git push --tags

# 4. evaluation
python scripts/wm_session.py start <eval_id> --editor NAME   # x10, then check/finish
python scripts/make_review_packets.py --set evaluation
python scripts/run_evaluation.py --annual-volume 10000
python scripts/repetition_analysis.py --set evaluation
```

Score anything ad hoc: `python scripts/score.py file.txt` (add `--colors` to see word colors).

## Word rules (summary; full version in `wmark/textproc.py`)

1. Unicode NFKC normalization
2. Zero-width characters (U+200B/C/D, U+2060, U+FEFF) and soft hyphens deleted
3. Curly apostrophes → `'`
4. Case folding (`Book` → `book`)
5. A word is a run of letters/digits with optional internal apostrophes (`don't`); hyphens, underscores and all other punctuation separate words

## Data sources

See `data/sources/sources.csv` (title, author, URL, license for every book).
Number of source documents per set: `results/split_report.md`.

## Key handling

One random 32-byte key, generated once with `scripts/generate_key.py`. It is
a demonstration key committed so results can be reproduced. Reports cite its
fingerprint (first 16 hex digits of SHA-256), not the key itself.

## Contribution statement

<!-- Fill in before submission. Link specific commits: https://github.com/<org>/<repo>/commit/<sha> -->

| Member | Contributions | Key commits |
|---|---|---|
| Name 1 | | |
| Name 2 | | |
| Name 3 | | |
| Name 4 | | |
