# Threat model (spec 4.3) — 20 of the 45 Milestone 1 points

Working draft. Fill every cell, then move it into the report.

## Goals

- **Removal:** make an initially flagged, usable watermarked passage stop being flagged, keeping meaning and readability.
- **Forgery:** make unmarked prose become flagged without the legitimate watermarking service, keeping meaning and readability.

## Access levels

- **None:** knows the algorithm and our word rules; no key, no detector access.
- **Query:** can submit chosen text to the detector and see the permitted response (score or decision); cannot read the key or internal state.
- **Key:** query access plus the key, so can compute every word's color locally; no admin privileges.

## The 2 x 3 table (12 points: all six cells need strategy AND costs)

Each cell must contain these five things. Label each claim **[Prediction]**
or **[Measured: <result file>]**. Milestone 2 measures the three cells marked ★.

| | None | Query | Key |
|---|---|---|---|
| **Removal** | Attack: <br>Queries: <br>Editing effort: <br>Text quality: <br>Defense: | ★ Attack: <br>Queries: <br>Editing effort: <br>Text quality: <br>Defense: | Attack: <br>Queries: <br>Editing effort: <br>Text quality: <br>Defense: |
| **Forgery** | Attack: <br>Queries: <br>Editing effort: <br>Text quality: <br>Defense: | ★ Attack: <br>Queries: <br>Editing effort: <br>Text quality: <br>Defense: | ★ Attack: <br>Queries: <br>Editing effort: <br>Text quality: <br>Defense: |

### Questions to think through per cell

- **None / Removal:** without colors, what blind edits lower the green fraction? (Paraphrasing many words; each changed word is a fresh coin flip. How many changes to drop from ~0.70 to below the threshold, on average? Do the arithmetic.)
- **None / Forgery:** can you raise the green fraction without knowing colors? (Blind edits push toward 0.5, not up. What does that predict?)
- **Query / Removal:** how do score responses guide which words to swap? What changes with decision-only responses? Do character tricks (case, punctuation, zero-width) survive our normalization? (See wmark/textproc.py.)
- **Query / Forgery:** the repeated-word query reveals one word's color per query. How many queries to learn the colors you need? How do rate limits and decision-only mode change cost (queries vs. time)?
- **Key / Removal:** with every color known, what is the minimum number of edits? (Compute: green words to remove = how many?)
- **Key / Forgery:** same, in the other direction. Why is key access the strongest case, and what does that imply for who holds the key?
- **Defenses to consider:** keeping the key secret, rate limits, decision-only responses, minimum distinct-word counts, monitoring repeated-word queries, per-account limits (and why multiple accounts weaken them), context-dependent colors.

## Design questions (8 points)

### Key distribution
- Who can watermark, detect locally, and submit queries?
- Anyone who can detect locally holds the key and can therefore forge. Consequence?
- What document content does the operator see during detection?
- How could an independent reviewer check a disputed result (escrowed key, re-scoring by a trusted third party, publishing the color of disputed words after the fact)?

### Context dependence
- If a word's color depended on the previous word (like Kirchenbauer et al.), what happens to the repeated-word trick?
- How many queries would color-learning then need (pairs instead of single words)?
- Does removal get easier or harder (editing one word changes the colors of its neighbours)?

### Digital signatures
- Compare: a signature on the exact text vs. a statistical watermark.
- Key compromise: what can an attacker do with a stolen signing key vs. a stolen watermark key?
- Editing: a one-character edit breaks a signature; how many edits break the watermark?
- What does verification establish about origin? About authorship? (Neither proves a particular person wrote the text.)
