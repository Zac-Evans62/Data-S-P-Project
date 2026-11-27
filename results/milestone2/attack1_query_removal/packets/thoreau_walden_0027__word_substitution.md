# Attack 1 quality check: thoreau_walden_0027 (word substitution)

Editor: Zac. **You must not be the editor.** Do not look at scores or results before recording your answers in `results/milestone2/attack1_query_removal/reviews.csv`.

Removal only counts if the edited version passes against **both** texts below. Answer yes only if both hold:

1. **Meaning preserved?** Does the edited version keep the main meaning of the watermarked version AND of the original?
2. **Readable?** Is the edited version readable prose?

---

## Edited version (read this first, on its own)

closer to town, you come to Breed’s location, on the oposite side of the path, just on the edge of the woods; ground famous for the pranks of a demon not distinctly named in old mythology, who has acted a large and impressive part in our New England life, and deserves, as much as any mythological character, to have his biography written one day; who first comes in disguise as a friend or worker, and then robs and kills the whole family,—New-England Rum. But history must not tell the tragedies that happened here; allow time to interfere in some way to assuage and lend an blue tint to them. On these grounds the most hidden and vile event states that once a bar stood; the well the same, which tempered the traveller’s drink and refreshed his horse. Here then men saluted eachother, heard and told gossip, and left again.

---

## Watermarked version

Nearer yet to town, you come to Breed’s location, on the other side of the way, just on the edge of the wood; ground famous for the pranks of a demon not distinctly named in old mythology, who has acted a prominent and astounding part in our New England life, and deserves, as much as any mythological character, to have his biography written one day; who first comes in the guise of a friend or hired man, and then robs and murders the whole family,—New-England Rum. But history must not yet tell the tragedies enacted here; let time intervene in some measure to assuage and lend an azure tint to them. Here the most indistinct and dubious tradition says that once a tavern stood; the well the same, which tempered the traveller’s beverage and refreshed his steed. Here then men saluted one another, and heard and told the news, and went their ways again.

---

## Original version

Nearer yet to town, you come to Breed’s location, on the other side of the way, just on the edge of the wood; ground famous for the pranks of a demon not distinctly named in old mythology, who has acted a prominent and astounding part in our New England life, and deserves, as much as any mythological character, to have his biography written one day; who first comes in the guise of a friend or hired man, and then robs and murders the whole family,—New-England Rum. But history must not yet tell the tragedies enacted here; let time intervene in some measure to assuage and lend an azure tint to them. Here the most indistinct and dubious tradition says that once a tavern stood; the well the same, which tempered the traveller’s beverage and refreshed his steed. Here then men saluted one another, and heard and told the news, and went their ways again.

---

## Word diff, watermarked to edited

[-nearer yet-] {+closer+} to town you come to breed's location on the [-other-] {+oposite+} side of the [-way-] {+path+} just on the edge of the [-wood-] {+woods+} ground famous for the pranks of a demon not distinctly named in old mythology who has acted a [-prominent-] {+large+} and [-astounding-] {+impressive+} part in our new england life and deserves as much as any mythological character to have his biography written one day who first comes in [-the guise of-] {+disguise as+} a friend or [-hired man-] {+worker+} and then robs and [-murders-] {+kills+} the whole family new england rum but history must not [-yet-] tell the tragedies [-enacted-] {+that happened+} here [-let-] {+allow+} time [-intervene-] {+to interfere+} in some [-measure-] {+way+} to assuage and lend an [-azure-] {+blue+} tint to them [-here-] {+on these grounds+} the most [-indistinct-] {+hidden+} and [-dubious tradition says-] {+vile event states+} that once a [-tavern-] {+bar+} stood the well the same which tempered the traveller's [-beverage-] {+drink+} and refreshed his [-steed-] {+horse+} here then men saluted [-one another and-] {+eachother+} heard and told [-the news-] {+gossip+} and [-went their ways-] {+left+} again
