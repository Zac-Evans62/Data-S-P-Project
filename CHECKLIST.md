# Milestone 1 checklist (45 points)

Deliverable: **detector code + report (max 6 pages)** in the shared repo, with a
README (run instructions, data sources, contribution statement with commit links).

Owners: **A** = detector & code, **B** = data, **C** = watermarking & quality checks,
**D** = threat model & report. Everyone reviews passages they didn't edit.
Replace the letters with names.

---

## Phase 0 — Setup (Days 1–2, Tue Oct 20 – Wed Oct 21)

- [ ] Create the shared GitHub repo and push this scaffold — *A*
- [ ] Everyone clones it and runs `python -m unittest -v` (18 tests pass) — *all*
- [ ] Read the word rules in `wmark/textproc.py`; agree or change them **now** (especially the zero-width choice) — *all*
- [ ] Generate the key once: `python scripts/generate_key.py`; commit `config/key.hex` — *A*
- [ ] Read Kirchenbauer et al. (intro + scheme) — *all*; D drafts the comparison paragraph
- [ ] Rule for the whole project: commit your own work under your own name (commit history is graded)

## Phase 1 — Detector (Days 2–4) — 10 pts

- [ ] Tokenization/normalization documented: case, punctuation, Unicode, apostrophes, hyphens, zero-width, digits — *A*
- [ ] Scoring = green occurrences / total occurrences; repeats counted — *A* (done in scaffold, review it)
- [ ] Flag only when score **>** threshold; equal is unflagged — *A* (done, tested)
- [ ] Empty input → explicit error — *A* (done, tested)
- [ ] Distinct word count recorded for every passage — *A* (done)
- [ ] Add any extra tests for rule changes you make — *A*

## Phase 2 — Data (Days 1–5) — start immediately — part of 15 pts

- [ ] Choose 15–25 public-domain prose books, different authors/periods (see `data/sources/README.md`) — *B*
- [ ] Download plain-text files into `data/sources/`; fill `sources.csv` (title, author, URL, license) — *B*
- [ ] `python scripts/collect_passages.py`; skim ~20 random passages for junk (TOCs, poetry, footnotes) and delete bad rows — *B*
- [ ] Confirm enough candidates: ≥ 300 unmarked across 3 groups + ≥ 15 medium (100–199 words) — *B*
- [ ] **Before any scoring:** `python scripts/split_data.py` — *B*
  - [ ] 150 unmarked calibration / 150 unmarked evaluation
  - [ ] ≥ 30 per length group in each set
  - [ ] 5 calibration / 10 evaluation watermark passages
  - [ ] All passages of a book in the same set
  - [ ] 5 of the 10 evaluation watermark passages labelled `forgery_selected` (method recorded in `results/split_report.md`)
- [ ] Commit `data/manifest.csv`, `data/passages/`, `results/split_report.md` — *B*

## Phase 3 — Calibration (Days 5–8) — 5 pts

- [ ] Extend `data/synonyms.tsv` as you go — *C*
- [ ] Watermark the **5 calibration** passages with `wm_session.py` (practice target, e.g. `--target 0.70`) — *C + others*
- [ ] Record per attempt: target, stopping rule, final score, editing time, changed words (the log does this) — *C*
- [ ] Adjust the procedure using **calibration only**; re-attempts are archived automatically — *C*
- [ ] Blind quality checks: `make_review_packets.py --set calibration`; reviewers fill `reviews.csv`; commit before seeing scores — *non-editors*
- [ ] `python scripts/run_calibration.py` — score 150 unmarked calibration passages + 5 outputs — *A*
- [ ] Threshold sweep (e.g. 0.55 / 0.60 / 0.65): count flagged unmarked and unflagged watermark outputs for each — *A*
- [ ] Choose threshold + target (target strictly above threshold) + time limit; write the justification using the counts — *A + D*
- [ ] `python scripts/freeze_settings.py`, commit, `git tag settings-frozen`, push tags — *A*

## Phase 4 — Evaluation (Days 8–11) — 5 pts

- [ ] Watermark all **10 evaluation** passages with frozen settings; follow the stopping rule even if a passage stays unflagged — *split across team*
- [ ] Blind quality checks for all 10 (`make_review_packets.py --set evaluation`) — *non-editors*
- [ ] `python scripts/run_evaluation.py --annual-volume <N>` — *A*
- [ ] Report, from the run's `summary.md`:
  - [ ] False-positive rate = flagged / 150
  - [ ] Detection rate = flagged outputs / 10
  - [ ] Usable success rate = (flagged AND quality yes/yes) / 10
  - [ ] How many attempts reached the target; scores before and after
  - [ ] Failed attempts and outputs that changed meaning / hurt readability (don't hide them)
  - [ ] Changed-word counts + the counting method (`wmark/metrics.py` docstring)
- [ ] Note any original already flagged before watermarking (matters for Milestone 2)

## Phase 5 — Interpretation (Days 10–12) — 5 pts

- [ ] Per length group: flagged / tested for unmarked evaluation passages — *D*
- [ ] Total + distinct word counts per passage are in `unmarked_scores.csv` — *D*
- [ ] Repetition: `python scripts/repetition_analysis.py --set evaluation`; analyze one highly repetitive example — *D*
- [ ] Small samples: 3/n bound (≈ 2% for 150) or exact bound if errors > 0; explain correlation from shared books — *D*
- [ ] Annual false flags: chosen volume × measured rate, with uncertainty and how book passages differ from real submissions — *D*
- [ ] If anything changed after evaluation: keep original results, report new runs separately, say what used evaluation info — *all*

## Phase 6 — Threat model (Days 3–12, in parallel) — 20 pts (the biggest chunk)

Work in `report/threat_model.md`.

- [ ] 2 × 3 table: Removal/Forgery × None/Query/Key — *D*
- [ ] Each of the 6 cells has: attack, expected queries, editing effort, text-quality effect, defense — *D*
- [ ] Every claim labelled Prediction or Measured — *D*
- [ ] Key distribution: who watermarks, detects locally, queries; what content the operator sees; how an independent reviewer checks a disputed result — *D*
- [ ] Context dependence: how preceding-token coloring changes each attack — *D*
- [ ] Digital signatures: key compromise, editing, what verification proves about origin and authorship — *D*
- [ ] Team review of the table (everyone reads it once) — *all*

## Phase 7 — Write-up and submission (Days 12–14, ~Mon Nov 2 – Tue Nov 3)

- [ ] Report in the order of `report/milestone1_outline.md`, **≤ 6 pages** (refs + contributions excluded) — *D lead, all write their parts*
- [ ] Every number in the report traceable to a file in `results/`
- [ ] Explain how reviewer knowledge could bias the quality check
- [ ] README: run instructions, data sources, contribution statement with **commit links** for each member — *all*
- [ ] Fresh-clone test: clone into a new folder, run tests and `run_evaluation.py`, confirm it works — *A*
- [ ] All outputs committed: passages, every watermark version, logs, reviews, results runs
- [ ] Submit

---

## Common ways to lose points

- Tuning anything after looking at evaluation passages
- Generating a new key because the scores looked bad
- Splitting one book across calibration and evaluation
- Reviewer seeing scores before answering, or reviewing their own edits
- Leaving out failed attempts
- Watermark target not strictly above the threshold
- Missing contribution statement or commit links
