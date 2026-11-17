# Quality checks

Spec 4.2: for every watermarking output (and later every attack output), a teammate who did not edit the passage compares the original and the edited version and answers two questions.

1. **Is the main meaning preserved?**
2. **Is the prose readable?**

An output is **usable** only if it is flagged by the detector and both answers are yes. All 15 watermarking outputs (5 calibration, 10 evaluation) were reviewed by someone other than their editor.

## Files

| Path | What it is |
|---|---|
| `packets/<set>/<passage_id>.md` | One review sheet per output: the edited text, the original, and a word diff. No scores, no detector decisions, no target status |
| `reviews.csv` | One row per output; the reviewer fills in the answers |

`reviews.csv` columns:

| Column | Meaning |
|---|---|
| `passage_id` | The passage, for example `douglass_narrative_0009` |
| `set` | `calibration` or `evaluation` |
| `stage` | `watermark` now; attack outputs are added in Milestone 2 |
| `editor` | Who edited the passage (filled in by the script) |
| `reviewer` | Who reviewed it. Must be a different person from the editor; the code rejects a review by the editor |
| `meaning_preserved` | `yes` or `no` |
| `readable` | `yes` or `no` |
| `notes` | Anything odd, such as a swap that reads badly; `none` if nothing |
| `reviewed_at` | Date of the review |

## Process

1. The editor finishes a passage with `python scripts/wm_session.py finish <id>`.
2. Someone runs `python scripts/make_review_packets.py --set <calibration|evaluation>`. This writes the packets and adds a blank row per output to `reviews.csv`.
3. The reviewer reads each packet and fills in their own row of `reviews.csv`, entering their own name as `reviewer`.
4. `reviews.csv` is committed before anyone runs the calibration or evaluation scripts, or tells the reviewer any scores.

## Guidance for reviewers

- **Meaning preserved** means the main claims, events and who did what are the same. Small shifts in tone or nuance are fine. Answer no if a reader of the edited text would come away with a different main point.
- **Readable** means a reader would not stumble: no ungrammatical sentences and no word choices that read as odd or out of place in the passage's style. Answer no if you would mark the sentence as awkward on a first read.
- When unsure, write the doubt in `notes` and pick the answer you would defend to a grader.

## Rules that keep the review blind

- Reviewers do not run `score.py` or `wm_session.py check`, and do not look in `results/`, for passages they have not reviewed yet.
- Editors do not tell reviewers whether the target was reached or whether the output was flagged.
- Reviewers rotate so each person reviews passages edited by others.
- Reviews are recorded under the name of the person who actually did them.

## How a teammate's knowledge could bias the review

Reviewers are teammates, not independent readers, so:

- They know the scheme swaps red words for green synonyms, so they may spot likely swaps and judge them harshly, or may overlook awkward ones they expect.
- They want the experiment to work, which can push them toward answering yes.
- They may recognize the editor's style or favorite synonyms from the shared list.
- They have read the original in the same packet, so differences are easier to see than for a real reader who only sees the edited text; this could make the review stricter than a normal reader's.
- All reviewers are the same few people, so one person's reading standards affect every result.

The review is two yes/no answers from one person, so treat the usable-success rate as indicative, not as a measurement of how an outside reader would judge.