# Milestone 1 Report Outline

Nov 1, 2026 · @Billy @ Zac

The report has seven sections in rubric order, capped at 6 pages, and Section 6 below is the threat model updated for the frozen threshold 0.63 and target 0.66.

## How to use this outline

Each section below says what to write, which spec requirement it covers, and where in the repo the evidence lives. References and the contribution statement don't count toward the 6 pages.

| Section | Rubric points | Page budget |
| --- | --- | --- |
| 1. Scheme and detector | Detector: 10 | 0.75 |
| 2. Data and split | Evaluation (part of 5) | 0.5 |
| 3. Calibration and frozen settings | Evaluation: 5 | 0.75 |
| 4. Evaluation results | Evaluation: 5 | 1 |
| 5. Interpretation | Evaluation: 5 | 1 |
| 6. Threat model | Threat model: 20 | 1.75 |
| 7. Reading comparison | (required reading) | 0.25 |

**Rules for every section**

- Every number cites a file. Write it as "(results/evaluation/run\_20261031\_160749/summary.md)" or a footnote. Spec section 6 says: "For each conclusion, identify the supporting results and the conditions under which it applies."
- Use the official runs. Evaluation: `results/evaluation/run_20261031_160749/`. Calibration sweep with all thresholds: `results/calibration/run_20261029_173414/`. The earlier calibration runs are kept as a record; mention them in one line, don't report them.
- Paths below are relative to the repo root.

## 1. The scheme and the detector (10 points, about 0.75 page)

This section explains how the watermark works and shows the detector follows the spec. The 10 points split into correct scoring and threshold comparison (5), and documented word processing, counts and empty-input handling (5).

**What to write**

1. How it works: the key and HMAC give each normalized word a fixed color; watermarking swaps red words for green synonyms; the detector computes green occurrences ÷ total occurrences and flags strictly above the threshold.
2. Word rules: the five rules in order, with a small table of examples (input → tokens). Cover case, punctuation, apostrophes, hyphens, Unicode (NFKC), zero-width characters and digits.
3. Scoring details: repeated words counted each time; distinct words recorded; exact fractions so a score equal to the threshold is never flagged; empty input raises an error.
4. Evidence: name the unit tests that prove each behavior.
5. Key: one 32-byte key, generated once; cite its fingerprint, never the key itself.

| What you need | Where to find it |
| --- | --- |
| The five word rules, in words | Docstring at the top of `wmark/textproc.py` |
| Example inputs and outputs for the rules table | `tests/test_detector.py`, class `TestWordRules` (each test is one example) |
| `word_color`, scoring, strict-greater flag, empty-input error | `wmark/detector.py` (`word_color`, `score_tokens`, `is_flagged`, `EmptyInputError`) |
| Proof that equal-to-threshold is unflagged | `test_equal_to_threshold_is_not_flagged` and `test_exact_comparison_avoids_float_error` in `tests/test_detector.py` |
| Proof of empty-input handling | `test_empty_input_rejected` |
| Key fingerprint | `key_fingerprint` in `config/settings.json` |
| A live example to show the colors | Run `python scripts/score.py - --colors` on a short sentence |

## 2. Data and the split (about 0.5 page)

This section shows the data meets spec 4.1 and that calibration and evaluation were kept apart. It supports the "separate calibration and evaluation" points.

**What to write**

1. Sources: how many books, the mix of authors, periods and genres, all public domain from Project Gutenberg.
2. How passages were cut: headers stripped, paragraphs joined to a target length, headings skipped; how many candidates that produced; how many were removed as junk and why.
3. The split: a table of passages per set and length group, and source documents per set. State that each book sits entirely in one set.
4. Watermark and forgery passages: which passages were chosen for watermarking, and how the 5 query-forgery passages were picked (seeded random, before any scoring).
5. One honest limitation: the two sets differ in genre, and evaluation has few source documents. Section 5 uses this.

| What you need | Where to find it |
| --- | --- |
| Book titles, authors, URLs, license | `data/sources/sources.csv` |
| Passage-cutting method | Docstring of `scripts/collect_passages.py` |
| Number of candidates and which ones were used | `data/manifest.csv` (`collection` column: unmarked, watermark, unused) |
| Junk removed | Your own note (count and reason); the method is in `scripts/find_junk.py` |
| Split table, books per set, seed | `results/split_report.md` |
| Forgery-selection method | Last section of `results/split_report.md` |
| Word count and distinct words per passage | `data/manifest.csv` (`word_count`, `distinct_words`) |

## 3. Calibration and frozen settings (5 points, about 0.75 page)

This section justifies the threshold, target and stopping rule using calibration data only, then shows they were frozen before evaluation. It earns the "separate calibration and evaluation with fixed settings" points (spec 4.2, steps 1–4).

**What to write**

1. Unmarked calibration scores: the range and median of the 150 scores.
2. Practice watermarking: the practice target and stopping rule, each passage's score before and after, minutes, changed words and quality result. Describe what made editing hard and which editing moves worked. Mention retried or abandoned attempts.
3. Threshold sweep: the table of thresholds against unmarked passages flagged and practice outputs missed.
4. The choice: why this threshold and target, argued from the sweep counts and the practice results. The target must be strictly above the threshold.
5. Frozen settings: threshold, target, time limit, key fingerprint, word rules, and the git tag that proves the freeze happened before evaluation.
6. Stopping-rule exceptions: any practice version kept after the time limit, stated plainly.

| What you need | Where to find it |
| --- | --- |
| Unmarked score range and median | `results/calibration/run_20261029_173414/summary.md`, first lines |
| Full threshold sweep (0.55 to 0.65) | `results/calibration/run_20261029_173414/threshold_sweep.csv` |
| Practice results table | Same run, `watermark_outputs.csv` (or the table in `summary.md`) |
| Per-version scores and timestamps for each practice passage | `data/watermarked/<passage_id>/log.json` |
| Every saved version | `data/watermarked/<passage_id>/versions/` |
| Quality results for practice | `quality_checks/reviews.csv`, rows where `set` is calibration |
| Frozen settings and freeze time | `config/settings.json` (`frozen_at`, `key_fingerprint`) |
| Proof of freeze | Git tag `settings-frozen` on GitHub (link it) |
| What you learned while editing | Your own calibration notes |

## 4. Evaluation results (5 points, about 1 page)

This section reports the three required rates and every attempt, failures included. It earns the "complete detection and quality results, including failures" points (spec 4.2, step 5 and the quality check).

**What to write**

1. Headline table: the three measurements exactly as the spec defines them, as counts and rates: unmarked false-positive rate (flagged ÷ 150), detection rate (flagged outputs ÷ 10), usable success rate (flagged and passed review ÷ 10).
2. All 10 attempts: a table with score before and after, reached target, flagged, changed words, stop reason and quality. Keep the failures in.
3. Special cases: any original already flagged before editing, and what that means for the detection rate. Any unflagged output.
4. Changed-word counting method: one or two sentences.
5. Quality check: who reviewed what, how scores were hidden, and how a teammate's knowledge could bias the review (the spec asks for this explicitly).

| What you need | Where to find it |
| --- | --- |
| Headline measurements | `results/evaluation/run_20261031_160749/summary.md`, "Headline measurements" |
| All 10 attempts | Same `summary.md`, "Watermarking attempts" table (or `watermark_outputs.csv`) |
| Already-flagged originals | The "Note" line at the end of that `summary.md` |
| Per-passage false-positive details | `results/evaluation/run_20261031_160749/unmarked_scores.csv` (`flagged` column) |
| Changed-word counting method | Docstring of `changed_words` in `wmark/metrics.py` |
| Reviewer for each passage | `quality_checks/reviews.csv`, rows where `set` is evaluation |
| What reviewers saw (proof scores were hidden) | Any file in `quality_checks/packets/evaluation/` |
| Review process | `quality_checks/README.md` |
| Editing time per passage | `data/watermarked/<passage_id>/log.json` (version timestamps) |

## 5. Interpretation: length, repetition, uncertainty, annual false flags (5 points, about 1 page)

This section explains what the numbers mean and where they stop being trustworthy. It earns the "length, repetition, uncertainty, and false-flag interpretation" points. Use four short subsections.

**5a. Length groups.** Flagged and tested counts for short, medium and long unmarked evaluation passages, and why shorter text is flagged more often (fewer independent color decisions).

**5b. Repetition.** The 1,000-repeats demo (score is exactly 0 or 1), then one highly repetitive real passage and how its most frequent words drive its score. Add the common-word finding: which very common words are green under your key, and how that shifts the median above 0.50.

**5c. Small samples.** The 95% upper bound on the false-positive rate (the exact bound, since you have more than 0 errors; the 3/n rule only applies to 0). Then why shared sources make the real uncertainty larger, and why the rate changed between calibration and evaluation.

**5d. Annual false flags.** A named hypothetical operator and yearly volume, the point estimate and the upper-bound estimate, and how book passages differ from real submissions (genre, length, era, modern vocabulary).

| What you need | Where to find it |
| --- | --- |
| Flagged and tested per length group | `results/evaluation/run_20261031_160749/summary.md`, "By length group" |
| Total and distinct words per passage | `results/evaluation/run_20261031_160749/unmarked_scores.csv` |
| Repetition demo and most repetitive passage | `results/repetition_analysis.txt` |
| Colors of common words | `results/common_word_colors.txt` |
| Exact 95% upper bound and source-document count | `summary.md`, "Uncertainty" |
| Calibration false-positive count at the frozen threshold, for comparison | `results/calibration/run_20261029_173414/threshold_sweep.csv`, row 0.63 |
| Annual false-flag figures | `summary.md`, "Annual false flags" (rerun with `--annual-volume N` for another volume) |
| Coin-flip prediction to compare against | "Supporting arithmetic" in Section 6 below |

## 6. Threat model

This is the largest section by points: 12 for the six cells with strategies and costs, 8 for the three design questions (spec 4.3). The text below is updated for the frozen threshold 0.63 and target 0.66 and is ready to move into the report.

**Before moving it into the report**

- [ ] Fill in the two `[FILL IN]` placeholders below (measured false-positive rate and unmarked median score) from `results/evaluation/run_20261031_160749/`
- [ ] Where a measured result now exists, label it measured and cite the file
- [ ] Cut the cell text so the table fits about one page
- [ ] Re-arrange the table into the spec's grid (goals as rows, access levels as columns) by pasting each row's items into its cell

### Settings and definitions

Threshold T = 0.63 and target 0.66 (`config/settings.json`, frozen). Numbers use N = 150 words (the watermarking passages are 100–199 words) unless stated, and treat words as independent fair coin flips (green with probability 0.5). Real prose repeats common words, so the measured rates in Sections 4–5 take precedence: unmarked false-positive rate **11/150 = 7.3% (measured: results/evaluation/run\_20261031\_160749/summary.md)**, unmarked median score **\[FILL IN: from unmarked\_scores.csv\]**. Every claim is a **\[Prediction\]**. Milestone 2 measures the three cells marked ★.

**Model versus measurement.** The coin-flip numbers below underestimate real unmarked text: the model predicts a 0.07% chance of a false flag at 150 words, and the measured rate is 7.3% (11/150; 6/50 short, 4/50 medium, 1/50 long passages). Common words push unmarked text above 0.50 under this key: the nine unflagged watermarking originals averaged 0.556 (range 0.49–0.59, results/evaluation/run\_20261031\_160749/summary.md). So blind removal needs somewhat more edits than the 30–40% quoted, and forgery needs fewer swaps than the 20–24 quoted. Treat the model as a rough guide only.

- **Removal:** make a flagged, usable watermarked passage unflagged, keeping meaning and readability.
- **Forgery:** make unmarked prose flagged without the watermarking service, keeping meaning and readability.
- **None:** knows the algorithm and word rules only. **Query:** can submit text to the detector and see its permitted response. **Key:** query access plus the key, so it can compute every color locally.

### The six cells

| Goal · access | Attack | Queries | Editing effort | Text quality | Defense |
| --- | --- | --- | --- | --- | --- |
| Removal · None | Blind paraphrase, or swap letters for look-alike characters or insert invisible characters the rules don't delete | 0 | Blind edits can't be verified: changing 30% of words (45 of 150) works about 74% of the time, 40% about 86%. A script can alter every word with look-alikes | Paraphrase risks meaning drift. Look-alikes look identical on screen but break search and copy | None against paraphrase at word level. Harden normalization: strip all format characters, map confusables, reject mixed-alphabet words |
| ★ Removal · Query | Score-guided synonym swaps (keep a swap only if the score drops), plus case, punctuation and zero-width tests | About 5 net drops needed; each trial drops the score with probability about 0.33, so ≈ 15–30 with scores. Decision-only responses give no feedback until the threshold is crossed, so color learning comes first: ≈ 30–60 | 5–10 substitutions | Good (about 3–7% of words) | Decision-only mode, rate limits, per-account caps, flagging near-duplicate resubmissions |
| Removal · Key | Compute colors, swap green words for red synonyms | 0–1 | 5 swaps at 150 words (3 at 100, 6 at 200), about 3% of words | Best of the six cells | Only key secrecy; rotate the key; avoid local detection |
| Forgery · None | Blind synonym swaps on unmarked text | 0 | Any amount, with no way to confirm the result | Whatever the edits cost | Blind edits push the score toward the unmarked baseline, so the chance of being flagged is the false-positive chance: 7.3% measured (11/150) against 0.07% predicted by the coin-flip model.&#32; |
| ★ Forgery · Query | Learn colors with the repeated-word probe (one word repeated 100 times scores 0 or 1, so flagged means green for any threshold in \[0, 1)), then swap red words for green synonyms | About 2–3 per accepted swap; at least 20 net swaps from a 0.50 base (24 to reach 0.66), so ≈ 50–80 plus preparation; fewer if unmarked text starts above 0.50. At 20 requests/minute that is minutes of simulated time; extra accounts multiply the allowance | 20–30 substitutions | Moderate (about 15% of words) | Hiding scores or requiring a minimum word count doesn't stop it, since repetition reaches any length. Use rate limits, monitoring of repeated-word queries, per-account caps |
| ★ Forgery · Key | Compute colors, swap red words for green synonyms until flagged | 0 | 20 swaps to flag (14 at 100, 27 at 200), 24 to reach the target | Same as legitimate watermarking | None from the detector; a forgery is indistinguishable from real output. Limit who holds the key |
|  |  |  |  |  |  |

### Supporting arithmetic

Coin-flip model, T = 0.63. An unmarked passage is flagged by chance 10.0% of the time at 30 words, 3.3% at 50, 0.33% at 100 and 0.07% at 150.

| Words N | Green needed to flag | Removal swaps from target | Forgery swaps from 0.50 (to flag / to target) |
| --- | --- | --- | --- |
| 100 | 64 | 3 | 14 / 16 |
| 150 | 95 | 5 | 20 / 24 |
| 200 | 127 | 6 | 27 / 32 |

### Character-change predictions

Checked by running `wmark/textproc.py` on each input. Removal starts from a flagged output.

| Change | Tokenizer behavior | Prediction |
| --- | --- | --- |
| Case, punctuation around a word, non-breaking space | Casefolded or treated as a separator | No effect |
| Listed zero-width characters (U+200B/C/D, U+2060, U+FEFF, U+00AD) | Deleted | No effect |
| Punctuation inside a word (`lar-ge`) | Splits into two words | Can lower the score; text looks broken |
| Unlisted invisible characters (U+200E, U+2061, U+034F, U+FE0F) | Not deleted; split the word | Can lower the score invisibly |
| Look-alike letters (Cyrillic "а") | A different token | Can lower the score invisibly |

### Design questions

**Key distribution.** The operator holds the key and is the only party that watermarks and detects. Submitters send text and get a response; auditors can also inspect query metadata. Anyone who can detect locally holds the key and so can forge or remove with the Key-column attacks, so local detection should not be offered. The operator sees the full text of every submission; it should score in memory and log only account, time, outcome and rate-limit status. An independent reviewer could re-score the disputed text with an escrowed key, or the operator could reveal the colors of just the disputed words (which leaks part of the key, so rotate it afterward), checked against a hash commitment to the key published in advance.

**Context dependence.** If a word's color depended on the previous word, the repeated-word probe would reveal only the color of the pair (w, w), and learned colors would transfer poorly between passages, so query forgery gets much harder: the attacker needs colors of word pairs, roughly the square of the vocabulary, and each swap must be green in two contexts. Blind removal gets easier, since each edit re-randomizes about two positions: to touch 30% of positions, only about 16% of words need editing. Key holders are unaffected.

**Digital signatures.** A signature on the exact text proves the bytes are unchanged since signing and were signed with that key; a stolen signing key lets an attacker sign anything until it is revoked, but the verification key can be public. A stolen watermark key lets an attacker forge and remove, and the same key detects, so it cannot be split into a public verifier and a private signer. A one-character edit breaks a signature, whereas the watermark survives light edits (about 3% of words must change to remove it) but is only statistical and fails under paraphrase. Neither proves a particular person wrote the text: a valid signature shows a key holder signed it, a flag shows the text is unusually green under our key. Authorship needs separate evidence such as drafts and logs.

**Evidence for this section**

| What you need | Where to find it |
| --- | --- |
| The drafted table, arithmetic and design questions | This section (and `report/threat_model.md` once updated) |
| Frozen threshold and target | `config/settings.json` |
| Measured false-positive rate to compare with the model | `results/evaluation/run_20261031_160749/summary.md` |
| Word rules behind the character-change predictions | `wmark/textproc.py` (`ZERO_WIDTH_CHARS` and the docstring) |
| Spec wording for goals, access levels and questions | Spec section 4.3 |

## 7. Reading comparison (about 0.25 page)

One paragraph comparing Kirchenbauer et al.'s generation-time watermark with this project's word substitution, as spec section 3 asks.

**Points to cover**

- **When the mark is added:** while a language model generates text, versus by editing finished prose.
- **How colors are chosen:** their green list depends on the previous token (context dependence); ours is fixed per word.
- **Detection:** they use a z-test on green-token counts; we use a green-fraction threshold. Both produce false positives on short text.
- **Cost of embedding:** nearly free for a model; slow and limited by synonyms for a human editor, as your practice runs showed.

Source: the paper's introduction and scheme sections, [arXiv:2301.10226](https://arxiv.org/abs/2301.10226). The optional readings may be cited too, but aren't required.

## References and contribution statement (outside the page limit)

**References:** the Kirchenbauer et al. paper, any optional readings you cite, and the 15 source books (title, author, Gutenberg URL). The book list can be copied from `data/sources/sources.csv`.

**Contribution statement:** each member, what they did, and links to the commits that show it. The spec requires the commit links, and it's graded in both milestones. Put the same table in the README (its "Contribution statement" section is still empty) and in the report.

| Member | Contributions | Key commits |
| --- | --- | --- |
|  |  |  |
|  |  |  |
|  |  |  |
|  |  |  |

To get a commit link: open the repo on GitHub, click Commits, click a commit, and copy the address bar. Pick commits that match each contribution (the split, the freeze, watermarking sessions, the threat model, the report).

## Final submission checklist

**Report**

- [ ] Six pages or fewer, excluding references and contributions
- [ ] Every number cites a results file
- [ ] Failed attempts and the already-flagged original are reported, not hidden
- [ ] Changed-word counting method stated
- [ ] Reviewer-bias paragraph included
- [ ] Threat model uses the frozen settings

**Repo cleanup**

- [ ] Fill in the README contribution table with commit links
- [ ] Re-save `results/repetition_analysis.txt` and `results/common_word_colors.txt` as UTF-8. PowerShell's `>` saved them as UTF-16, so they look garbled on GitHub. Rerun each with `| Out-File -Encoding utf8 results\<name>.txt` instead of `>`
- [ ] Fresh-clone test: clone into a new folder, run `python -m unittest -v` and `python scripts/run_evaluation.py`

**Already confirmed in the repo**

- Settings frozen (`config/settings.json`, `frozen: true`) and tagged
- NOT CONFIRMED: summary.md shows 5 attempts ending after 15 minutes (24.8 and 25.6 min for douglass\_narrative\_0026 and doyle\_sherlock\_0015); check when each final version was saved (from each `log.json`)
- All 15 outputs reviewed by someone other than their editor (`quality_checks/reviews.csv`)
- The full threshold sweep is saved (`results/calibration/run_20261029_173414/`)
