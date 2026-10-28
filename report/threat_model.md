# Threat model (spec 4.3)

Draft filled in for review. Every claim is a **[Prediction]** until Milestone 2 measures it; the three cells Milestone 2 tests are marked ★.

**Assumptions behind the numbers (update after calibration):** threshold T = 0.60, watermark target 0.70, passage length N ≈ 150 normalized words. An unmarked passage is modeled as N independent fair coin flips (green with p = 0.5). Real prose repeats common words, so real scores vary more than this model says. The measured false-positive rate on the evaluation set overrides the model.

## Goals

- **Removal:** make an initially flagged, usable watermarked passage stop being flagged, keeping meaning and readability.
- **Forgery:** make unmarked prose become flagged without the legitimate watermarking service, keeping meaning and readability.

## Access levels

- **None:** knows the algorithm and our word rules; no key, no detector access.
- **Query:** can submit chosen text to the detector and see the permitted response (score or decision); cannot read the key or internal state.
- **Key:** query access plus the key, so can compute every word's color locally; no admin privileges.

## The 2 x 3 table

| | None | Query | Key |
|---|---|---|---|
| **Removal** | **Attack:** (a) swap letters for look-alike characters from another alphabet (Cyrillic "а" for Latin "a") or insert invisible characters our rules don't delete, so words become new tokens with fresh random colors while looking identical; or (b) rewrite most of the passage blind (by hand or with a paraphraser). No feedback, so the attacker cannot tell when the score has dropped.<br>**Queries:** 0.<br>**Editing effort:** each changed word becomes a fresh coin flip, so the expected score after changing a fraction f of words is 0.70(1−f) + 0.50f. Reaching 0.60 takes f ≈ 0.5, about 75 of 150 words, plus a safety margin because the result can't be checked. High for paraphrasing. Low for look-alike characters: a short script can alter every word, which pulls the expected score to about 0.50, below T.<br>**Text quality:** paraphrasing is likely poor at f ≥ 0.5. Look-alike characters look identical on screen, so a human reviewer sees no change, though copy/paste, search and screen readers break.<br>**Defense / condition:** a word-level scheme is not robust to paraphrase. The character attacks can be blocked by hardening normalization: strip all format (Cf) characters, map confusable characters to a common form, and reject words that mix alphabets. Policy must never treat "unflagged" as proof of no watermark. | ★ **Attack:** greedy synonym substitution guided by the score: swap one word, resubmit, keep the swap if the score falls. Also test case changes, punctuation changes and zero-width characters.<br>**Queries:** about 15 net green-to-red swaps are needed from 0.70 at N = 150. A random swap lowers the score with probability about 0.35, so roughly 3 queries per kept swap, ≈ 45 queries (range 30–100). Character tricks: 3 queries. Decision-only mode gives no feedback until the threshold is crossed, so the attacker first learns candidate word colors with repeated-word probes (1 query per word, ≈ 40–80).<br>**Editing effort:** about 15–25 substitutions by hand. Moderate.<br>**Text quality:** moderate; ~10–17% of words change and some red synonyms read badly.<br>**Defense / condition:** decision-only responses, rate limits (add time, not queries), per-account caps, and monitoring for near-duplicate resubmissions. Case changes, punctuation around words and the six deleted zero-width characters should fail because `wmark/textproc.py` ignores or deletes them. Punctuation or an unlisted invisible character inside a word splits it into two words, so those can lower the score (table below). | **Attack:** compute colors locally, replace green words with red synonyms until the score is at or below T, optionally verify with one query.<br>**Queries:** 0–1.<br>**Editing effort:** minimum swaps = green count − floor(T·N). From a 0.70 start that is 10 (N=100), 15 (N=150), 20 (N=200), about 10% of words. Low.<br>**Text quality:** best of the six cells; the same edit load as the watermarking itself, limited only by synonym availability.<br>**Defense / condition:** only keeping the key secret. Nothing in the detector helps once the key is known. Mitigations: key rotation, no local detection, short key lifetime. |
| **Forgery** | **Attack:** blind synonym swaps on unmarked prose, hoping to raise the green fraction.<br>**Queries:** 0.<br>**Editing effort:** any amount, with no way to confirm the result.<br>**Text quality:** whatever the edits cost.<br>**Defense / condition:** blind edits push the score toward 0.50, not up. Success is about as likely as an unmarked passage being falsely flagged: ≈ 0.6% at N = 150 under the coin-flip model (table below), and the attacker cannot see whether it worked. The key being secret is what prevents this. | ★ **Attack:** learn colors with repeated-word probes (one word repeated 100 times scores exactly 0 or 1; flagged means green for any threshold in [0, 1)), then swap red words for green synonyms.<br>**Queries:** about 2–3 per accepted swap (original word's color plus synonym's color; fewer when common words were learned earlier). From a 0.50 base, at least 16 net swaps are needed at N = 150 to pass 0.60 (30 to reach 0.70), so ≈ 40–100 queries per passage plus preparation. Color reuse across passages lowers this. With a 20 requests/minute limit, 100 queries is ≈ 5 minutes of simulated time; extra accounts multiply the allowance.<br>**Editing effort:** 16–30 substitutions. Moderate.<br>**Text quality:** moderate; 10–20% of words change.<br>**Defense / condition:** hiding scores does not stop it, since the binary decision leaks the color. A minimum total word count does not stop it either, because the probe can be repeated up to any length. A minimum distinct-word count would stop single-word probes but not probes with many distinct words, where a score response reveals how many are green. Other mitigations: rate limits plus monitoring of repeated-word queries, context-dependent colors. | ★ **Attack:** compute colors locally and swap red words for green synonyms until the score is above T. This is the legitimate watermarking procedure.<br>**Queries:** 0 (1 optional verification).<br>**Editing effort:** swaps needed = floor(T·N) + 1 − (original's green count). From a 0.50 base that is about 11 (N=100), 16 (N=150), 21 (N=200); about 20–40 to reach a 0.70 target. Low to moderate.<br>**Text quality:** same as the legitimate watermark.<br>**Defense / condition:** none from the detector. A forgery is indistinguishable from real output. Limit who holds the key, and use signatures where origin matters. |

### Supporting arithmetic

All numbers below were computed from the model above and checked with a short script.

False-positive chance for an unmarked passage at T = 0.60, under the coin-flip model:

| Words N | 30 | 50 | 100 | 150 | 300 |
|---|---|---|---|---|---|
| P(flagged) | 10.0% | 6.0% | 1.8% | 0.56% | 0.02% |

Real text repeats common words, which makes the effective N smaller. Expect measured rates above these, especially for the 30–99 word group.

Swaps needed (T = 0.60):

| N | Forgery from 0.50 base (just above T) | Forgery to 0.70 | Removal from 0.70 (to ≤ T) |
|---|---|---|---|
| 100 | 11 | 20 | 10 |
| 150 | 16 | 30 | 15 |
| 200 | 21 | 40 | 20 |

Blind edits: expected score after changing a fraction f of words is 0.70(1−f) + 0.50f, giving 0.64 at f = 0.3, 0.60 at f = 0.5 and 0.58 at f = 0.6.

### Predicted results of the character-change tests

Checked by running `wmark/textproc.py` on each input. The prediction is for the Milestone 2 removal tests, which start from a flagged output.

| Change | What the tokenizer does | Prediction |
|---|---|---|
| Letter case (`LaRgE`) | casefolded to `large` | No effect; removal fails |
| Punctuation around a word (`Large,`) | punctuation is a separator | No effect; removal fails |
| Punctuation inside a word (`lar-ge`, `lar.ge`) | splits into `lar`, `ge` | New tokens with fresh colors; can lower the score, but the text looks broken |
| Listed zero-width characters (U+200B, U+200C, U+200D, U+2060, U+FEFF, U+00AD) | deleted, so `lar​ge` becomes `large` | No effect; removal fails |
| Unlisted invisible characters inside a word (U+200E, U+2061, U+034F, U+FE0F) | not deleted, and they act as separators: splits the word | Can lower the score while looking unchanged |
| Look-alike letters (Cyrillic "а", Greek "ο") | not mapped back by NFKC, so a different token | Can lower the score while looking unchanged |
| Non-breaking space between words | NFKC turns it into a normal space | No effect |

The required zero-width test will probably fail if it uses U+200B. Report the unlisted-character and look-alike variants as a separate extra, since they test a different gap in the word rules. Hardening the rules is the matching optional experiment, reported separately.

## Design questions (8 points)

### Key distribution

- **Who can do what [Prediction/design choice]:** the operator holds the key. The service is the only component that watermarks and detects. Submitters send text to the service and receive a response; auditors can additionally inspect query metadata. No one else gets the key.
- **Consequence of local detection:** anyone who can detect locally holds the key, so they can also forge and remove with the minimal-effort attacks in the Key column. Local detection hands out a forging tool, so avoid it.
- **What the operator sees:** the full text of every submitted passage, because the service must score it. The service should score in memory and log only the account, timestamp, outcome and rate-limit status, not the text.
- **Independent review of a disputed result:** (1) a trusted third party holds an escrowed copy of the key and re-scores the disputed text; (2) the operator reveals the colors of only the words in the disputed text, which leaks part of the key, so it should be paired with rotating the key afterward; (3) the operator publishes a hash commitment to the key in advance, so a reviewer can confirm that a revealed key is the one used. Review also needs the saved text, the settings and the threshold.

### Context dependence

- **Repeated-word probe:** if a word's color depended on the previous word, repeating one word would only reveal the color of the pair (w, w), not of w in other contexts. The shortcut stops working.
- **Color-learning cost:** the attacker would need colors of word pairs, roughly the square of the vocabulary instead of the vocabulary. Colors learned on one passage are much less reusable on another.
- **Forgery with queries:** harder. A swap changes two pairs (the new word with its left neighbor and with its right neighbor), so a green synonym must be green in both contexts.
- **Removal:** easier for a blind attacker. Each edit re-randomizes about two positions. If edits are spread out, the fraction of positions touched is 1 − (1 − e)², so reaching f ≈ 0.5 takes only e ≈ 0.29 of words edited (versus 0.50 now).
- **Key holders:** unaffected, since they compute every context's color locally. **[Prediction]**

### Digital signatures

- **What they are:** a signature on the exact text, made with a private key and checked with a public key. It proves that the text is unmodified since signing and that it was signed with that key.
- **Key compromise:** a stolen signing key lets an attacker sign anything as the owner, until the key is revoked and republished. A stolen watermark key lets an attacker forge and remove marks, and because the same key detects, it cannot be split into a public verifier and a private signer. A signature scheme can publish the verification key safely; ours cannot.
- **Editing:** changing a single character breaks a signature. The watermark tolerates edits (removal needs about 10% of words changed at N = 150 with the key), but it is only a statistical signal, and it fails entirely under a thorough paraphrase.
- **What verification establishes:** a valid signature establishes that someone holding that key signed those exact bytes. A watermark flag establishes that the text is unusually green under our key. Neither proves a particular person wrote the text. Authorship needs separate evidence, such as drafts, logs and an interview.
- **Trade-off:** signatures give strong origin evidence but break when text is edited or retyped. Watermarks survive light edits but offer weak, statistical evidence with a nonzero false-positive rate.

## Before moving this into the report

- The character-trick predictions were checked against `wmark/textproc.py`. Re-check them if the team changes the word rules.
- Replace the T = 0.60, target = 0.70 and N ≈ 150 assumptions with the frozen settings once calibration is done.
- The report limit is 6 pages. The table plus design questions should fit in about 2 pages if the cells are tightened.