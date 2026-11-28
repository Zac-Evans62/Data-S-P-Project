# Attack 1 quality check: london_call_wild_0037 (word substitution)

Editor: Zac. **You must not be the editor.** Do not look at scores or results before recording your answers in `results/milestone2/attack1_query_removal/reviews.csv`.

Removal only counts if the edited version passes against **both** texts below. Answer yes only if both hold:

1. **Meaning preserved?** Does the edited version keep the main meaning of the watermarked version AND of the original?
2. **Readable?** Is the edited version readable prose?

---

## Edited version (read this first, on its own)

But near the end Buck’s pertinacity got rewarded; for the wolf, deducing no harm was intended, finally sniffed his nose. Then they turned friendly, and played about using the nervous, half-coy way which fierce beasts belie their fierceness. Some time later,the wolf left,using a light pace and an light deameaner which told Buck he was leaving. He made his intention clear, Buck needed to follow along, and they ran, side by side through the sad twilight, straight up the creek bed, into the valley where the river originated, and across the canyon where the creek took her rise.

---

## Watermarked version

But near the end Buck’s pertinacity got rewarded; for the wolf, deducing no harm was intended, finally smelled his nose. Then they turned companionable, and played about using the nervous, half-coy way which fierce beasts belie their fierceness. After a bit of movement of the sun, of this the wolf started off, a easy walk using a manner which conveyed that he intended on going somewhere. He made his instention clear, Buck needed to follow along, and they ran their sides close by eachother through the sombre twilight, straight up the creek bed, into the gorge from where the start came from, and across the bleak divide where the creek took her rise.

---

## Original version

But in the end Buck’s pertinacity was rewarded; for the wolf, finding that no harm was intended, finally sniffed noses with him. Then they became friendly, and played about in the nervous, half-coy way with which fierce beasts belie their fierceness. After some time of this the wolf started off at an easy lope in a manner that plainly showed he was going somewhere. He made it clear to Buck that he was to come, and they ran side by side through the sombre twilight, straight up the creek bed, into the gorge from which it issued, and across the bleak divide where it took its rise.

---

## Word diff, watermarked to edited

but near the end buck's pertinacity got rewarded for the wolf deducing no harm was intended finally [-smelled-] {+sniffed+} his nose then they turned [-companionable-] {+friendly+} and played about using the nervous half coy way which fierce beasts belie their fierceness [-after a bit of movement of the sun of this-] {+some time later+} the wolf [-started off a easy walk-] {+left+} using a [-manner-] {+light pace and an light deameaner+} which [-conveyed that-] {+told buck+} he [-intended on going somewhere-] {+was leaving+} he made his [-instention-] {+intention+} clear buck needed to follow along and they ran [-their sides close-] {+side+} by [-eachother-] {+side+} through the [-sombre-] {+sad+} twilight straight up the creek bed into the [-gorge from-] {+valley+} where the [-start came from-] {+river originated+} and across the [-bleak divide-] {+canyon+} where the creek took her rise
