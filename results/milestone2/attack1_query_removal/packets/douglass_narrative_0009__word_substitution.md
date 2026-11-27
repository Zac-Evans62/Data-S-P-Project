# Attack 1 quality check: douglass_narrative_0009 (word substitution)

Editor: Zac. **You must not be the editor.** Do not look at scores or results before recording your answers in `results/milestone2/attack1_query_removal/reviews.csv`.

Removal only counts if the edited version passes against **both** texts below. Answer yes only if both hold:

1. **Meaning preserved?** Does the edited version keep the main meaning of the watermarked version AND of the original?
2. **Readable?** Is the edited version readable prose?

---

## Edited version (read this first, on its own)

My father was a white man. He was told to be such by everyone I ever heard talk of him. The opinion was also spoken that my master was my father; but I'm not sure this is true; the means of knowing was denied me. My mother and I were separated when I was but an infant—before I knew her as my mother. It is a general custom, in the part of Maryland from which I ran away, to part children from their mothers at a very early age. Frequently, before the child has reached a year old, its mother is taken from it, and given to a farm a considerable distance off, and the child is placed under the keeping of an old woman, too old for field work. For what this separation is done, I know not, unless it be to slow the development of the child’s likeness of its mother, and to blunt and destroy the natural fondness of the mother for the child. This is the inevitable result.

---

## Watermarked version

My father was a white man. He was admitted to be such by everyone I ever heard talk of my parentage. The opinion was also murmured that my owner was my father; but of the truth of this opinion, I know nothing; the means of knowing was denied me. My mother and I were separated when I was but an infant—before I knew her as my mother. It is a general custom, in the part of Maryland from which I ran away, to part children from their mothers at a very early age. Frequently, before the child has reached its twelfth month, its mother is taken from it, and let out upon a farm a considerable distance off, and the child is placed under the keeping of an old woman, too old for field work. For what this separation is done, I know not, unless it be to hinder the development of the child’s fondness for its mother, and to blunt and destroy the natural fondness of the mother for the child. This is the inevitable result.

---

## Original version

My father was a white man. He was admitted to be such by all I ever heard speak of my parentage. The opinion was also whispered that my master was my father; but of the correctness of this opinion, I know nothing; the means of knowing was withheld from me. My mother and I were separated when I was but an infant—before I knew her as my mother. It is a common custom, in the part of Maryland from which I ran away, to part children from their mothers at a very early age. Frequently, before the child has reached its twelfth month, its mother is taken from it, and hired out on some farm a considerable distance off, and the child is placed under the care of an old woman, too old for field labor. For what this separation is done, I do not know, unless it be to hinder the development of the child’s affection toward its mother, and to blunt and destroy the natural affection of the mother for the child. This is the inevitable result.

---

## Word diff, watermarked to edited

my father was a white man he was [-admitted-] {+told+} to be such by everyone i ever heard talk of [-my parentage-] {+him+} the opinion was also [-murmured-] {+spoken+} that my [-owner-] {+master+} was my father but [-of the truth of-] {+i'm not sure+} this [-opinion i know nothing-] {+is true+} the means of knowing was denied me my mother and i were separated when i was but an infant before i knew her as my mother it is a general custom in the part of maryland from which i ran away to part children from their mothers at a very early age frequently before the child has reached [-its twelfth month-] {+a year old+} its mother is taken from it and [-let out upon-] {+given to+} a farm a considerable distance off and the child is placed under the keeping of an old woman too old for field work for what this separation is done i know not unless it be to [-hinder-] {+slow+} the development of the child's [-fondness for-] {+likeness of+} its mother and to blunt and destroy the natural fondness of the mother for the child this is the inevitable result
