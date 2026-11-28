"""Build attacks/query/thesaurus.tsv from Princeton WordNet 3.0 (one-time, key-independent).

The query-access attacker needs candidate replacement words. It must NOT use
data/synonyms.tsv: that list was built during keyed watermarking, so it carries
color information. This thesaurus comes from a public dictionary and has no
connection to the key.

    python scripts/build_thesaurus.py PATH/TO/wordnet-3.0 [--out attacks/query/thesaurus.tsv]

Rules (to keep replacements plausible):
  * single alphabetic words only, at least 3 letters
  * only words with a main part of speech (at least 60% of their tagged uses)
  * only the main senses of a word (at least 20% of its tagged uses)
  * the replacement must have tagged uses in that same sense, with the same main part of speech
  * at most 6 replacements per word, most frequent first
WordNet 3.0 license: https://wordnet.princeton.edu/license-and-commercial-use (permissive; cite Princeton University).
"""
import argparse
import re
from collections import defaultdict
from pathlib import Path

POS_FILES = {"n": "data.noun", "v": "data.verb", "a": "data.adj", "r": "data.adv"}
SS_DIGIT = {"1": "n", "2": "v", "3": "a", "4": "r", "5": "a"}
ALPHA = re.compile(r"^[a-z]{3,}$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wordnet_dir")
    ap.add_argument("--out", default="attacks/query/thesaurus.tsv")
    args = ap.parse_args()
    d = Path(args.wordnet_dir)

    tags = defaultdict(int)             # (lemma, pos, offset) -> tagged uses
    for line in (d / "index.sense").read_text(encoding="utf-8").splitlines():
        key, offset, _num, cnt = line.split()
        lemma, rest = key.split("%")
        pos = SS_DIGIT[rest.split(":")[0]]
        tags[(lemma.lower(), pos, offset)] += int(cnt)

    synsets = {}                         # (pos, offset) -> lemmas
    for pos, fname in POS_FILES.items():
        for line in (d / fname).read_text(encoding="utf-8").splitlines():
            if line.startswith(" "):
                continue
            f = line.split("|")[0].split()
            offset, n = f[0], int(f[3], 16)
            lemmas = [re.sub(r"\(.*\)$", "", f[4 + 2 * i]).lower() for i in range(n)]
            synsets[(pos, offset)] = lemmas

    total = defaultdict(int)             # lemma -> uses over all senses
    by_pos = defaultdict(lambda: defaultdict(int))
    for (lemma, pos, _), c in tags.items():
        total[lemma] += c
        by_pos[lemma][pos] += c

    def one_pos(w):
        """Main part of speech: at least 60% of the word's tagged uses (else None)."""
        if not by_pos[w]:
            return None
        pos, c = max(by_pos[w].items(), key=lambda kv: kv[1])
        return pos if c >= 0.6 * total[w] else None

    cands = defaultdict(list)            # w -> [(uses of w in sense, uses of s, s)]
    for (pos, offset), lemmas in synsets.items():
        for w in lemmas:
            if not ALPHA.match(w) or one_pos(w) != pos:
                continue
            uses = tags.get((w, pos, offset), 0)
            if uses < 1 or uses < 0.2 * total[w]:
                continue
            for s in lemmas:
                if (s != w and ALPHA.match(s) and one_pos(s) == pos
                        and tags.get((s, pos, offset), 0) >= 1):
                    cands[w].append((uses, tags[(s, pos, offset)], s))

    rows = []
    for w in sorted(cands):
        seen, out = set(), []
        for _, _, s in sorted(cands[w], reverse=True):
            if s not in seen:
                seen.add(s)
                out.append(s)
        rows.append(f"{w}\t{','.join(out[:6])}")
    Path(args.out).write_text("# word<TAB>replacements; built from WordNet 3.0 by scripts/build_thesaurus.py\n"
                              + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"{len(rows)} words written to {args.out}")


if __name__ == "__main__":
    main()
