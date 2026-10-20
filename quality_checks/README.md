# Quality checks

Spec 4.2: for every watermarking output (and later every attack output) a
teammate **who did not edit the passage** answers two questions:

1. Is the main meaning preserved?
2. Is the prose readable?

Both "yes" = usable.

## Process

1. Editor finishes a passage with `scripts/wm_session.py finish <id>`.
2. Someone runs `python scripts/make_review_packets.py --set <set>`.
   This writes `packets/<set>/<id>.md` (edited text, original, word diff;
   **no scores**) and adds a row to `reviews.csv`.
3. The reviewer reads the packet and fills in their row of `reviews.csv`:
   `reviewer`, `meaning_preserved` (yes/no), `readable` (yes/no), `notes`,
   `reviewed_at` (date).
4. Commit `reviews.csv` **before** anyone runs calibration/evaluation scripts
   or tells the reviewer the scores.

## Rules that keep the review blind

- Reviewers never run `score.py`, `wm_session.py check`, or look at
  `results/` for passages they have not reviewed yet.
- Editors do not tell reviewers whether the target was reached.
- Rotate reviewers so each person reviews passages edited by others.

The report must explain how a teammate's knowledge of the project could bias
the review (they know which words tend to be swapped, they want the
experiment to work, they may recognise awkward synonym patterns, etc.).
