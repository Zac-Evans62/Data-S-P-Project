# Attack 1 quality check: doyle_sherlock_0009 (word substitution)

Editor: Zac. **You must not be the editor.** Do not look at scores or results before recording your answers in `results/milestone2/attack1_query_removal/reviews.csv`.

Removal only counts if the edited version passes against **both** texts below. Answer yes only if both hold:

1. **Meaning preserved?** Does the edited version keep the main meaning of the watermarked version AND of the original?
2. **Readable?** Is the edited version readable prose?

---

## Edited version (read this first, on its own)

“Oh, it won’t work—really it won’t,” remarked Holmes sharply. “I cant find a possibility you can get out of it, Mr. Windibank. It is obvious, and it was very a very bad compliment when you said that it was impossible for me to answer such a simple question. That’s correct! Sit down and let us talk it over.”

Our visitor collapsed into a chair, with a scared face and a drop of sweat on his forehead. “It—it’s not punishable,” he stammered.

“I fear that it is not. But between us, Windibank, it was as savage and selfish and callous a trick in a petty way as ever came to me. Now, let me just run over the sequence of events, and you may correct me if I am wrong.”

The man sat hunched in his chair, with his head sunk upon his chest, like one who is wholly beaten. Holmes stuck his feet up on the corner of the table and, leaning back with his hands in his pockets, began talking, rather to himself, as it seemed, than to us.

---

## Watermarked version

“Oh, it won’t work—really it won’t,” remarked Holmes smoothly. “There is no possible getting out of it, Mr. Windibank. It is quite too evident, and it was very bad flattery when you said that it was impossible for me to answer so simple a question. That’s correct! Sit down and let us talk it over.”

Our visitor collapsed into a chair, with a pallid face and a film of sweat upon his forehead. “It—it’s not punishable,” he stammered.

“I am very much afraid that it is not. But between ourselves, Windibank, it was as brutal and selfish and callous a trick in a petty way as ever came before me. Now, let me just run over the chain of events, and you may correct me if I am wrong.”

The man sat hunched in his chair, with his head sunk upon his breast, like one who is wholly beaten. Holmes stuck his feet up on the corner of the mantelpiece and, leaning back with his hands in his pockets, began talking, rather to himself, as it seemed, than to us.

---

## Original version

“Oh, it won’t do—really it won’t,” said Holmes suavely. “There is no possible getting out of it, Mr. Windibank. It is quite too transparent, and it was a very bad compliment when you said that it was impossible for me to solve so simple a question. That’s right! Sit down and let us talk it over.”

Our visitor collapsed into a chair, with a ghastly face and a glitter of moisture on his brow. “It—it’s not actionable,” he stammered.

“I am very much afraid that it is not. But between ourselves, Windibank, it was as cruel and selfish and heartless a trick in a petty way as ever came before me. Now, let me just run over the course of events, and you will contradict me if I go wrong.”

The man sat huddled up in his chair, with his head sunk upon his breast, like one who is utterly crushed. Holmes stuck his feet up on the corner of the mantelpiece and, leaning back with his hands in his pockets, began talking, rather to himself, as it seemed, than to us.

---

## Word diff, watermarked to edited

oh it won't work really it won't remarked holmes [-smoothly there is no possible getting-] {+sharply i cant find a possibility you can get+} out of it mr windibank it is [-quite too evident-] {+obvious+} and it was very {+a very+} bad [-flattery-] {+compliment+} when you said that it was impossible for me to answer [-so-] {+such a+} simple [-a-] question that's correct sit down and let us talk it over our visitor collapsed into a chair with a [-pallid-] {+scared+} face and a [-film-] {+drop+} of sweat [-upon-] {+on+} his forehead it it's not punishable he stammered i [-am very much afraid-] {+fear+} that it is not but between [-ourselves-] {+us+} windibank it was as [-brutal-] {+savage+} and selfish and callous a trick in a petty way as ever came [-before-] {+to+} me now let me just run over the [-chain-] {+sequence+} of events and you may correct me if i am wrong the man sat hunched in his chair with his head sunk upon his [-breast-] {+chest+} like one who is wholly beaten holmes stuck his feet up on the corner of the [-mantelpiece-] {+table+} and leaning back with his hands in his pockets began talking rather to himself as it seemed than to us
