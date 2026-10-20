"""Split candidates into calibration/evaluation sets (spec 4.1). Run BEFORE any scoring.

    python scripts/split_data.py

What it does (also written to results/split_report.md):
  * Assigns whole BOOKS to one set, so all passages of a book share a set.
  * Picks 150 unmarked passages per set, at least 30 from each length
    group (aims for 50/50/50), spreading picks round-robin across books.
  * Picks watermark passages from the medium group (100-199 words):
    5 for calibration, 10 for evaluation, from different books where possible.
  * Randomly selects 5 of the 10 evaluation watermark passages for the
    Milestone 2 query-access forgery attack, using the seed in settings.json.
    No scores are computed here, so the selection cannot depend on scores.

Everything is driven by the seed in config/settings.json, so it is
reproducible. Refuses to re-split an already split manifest without --force.
"""
import _bootstrap  # noqa: F401

import argparse
import random
from collections import defaultdict

from wmark.config import RESULTS_DIR, load_settings
from wmark.manifest import read_manifest, write_manifest

SETS = ("calibration", "evaluation")
UNMARKED_PER_SET = 150
MIN_PER_GROUP = 30
WATERMARK_PER_SET = {"calibration": 5, "evaluation": 10}
FORGERY_COUNT = 5
GROUPS = ("short", "medium", "long")


def round_robin(cands: list[dict], k: int, rng: random.Random) -> list[dict]:
    """Pick k passages cycling through books, so sources are spread out."""
    by_book = defaultdict(list)
    for c in cands:
        by_book[c["book_id"]].append(c)
    books = list(by_book)
    rng.shuffle(books)
    for b in books:
        rng.shuffle(by_book[b])
    picked = []
    while len(picked) < k and any(by_book[b] for b in books):
        for b in books:
            if by_book[b] and len(picked) < k:
                picked.append(by_book[b].pop())
    return picked


def try_split(rows, rng):
    books = sorted({r["book_id"] for r in rows})
    rng.shuffle(books)
    size = defaultdict(int)
    for r in rows:
        size[r["book_id"]] += 1
    assign, load = {}, {s: 0 for s in SETS}
    for b in books:  # greedy: give each book to the lighter set
        s = min(SETS, key=lambda x: (load[x], rng.random()))
        assign[b] = s
        load[s] += size[b]

    chosen = {}
    for s in SETS:
        pool = [r for r in rows if assign[r["book_id"]] == s]
        medium = [r for r in pool if r["length_group"] == "medium"]
        wm = round_robin(medium, WATERMARK_PER_SET[s], rng)
        if len(wm) < WATERMARK_PER_SET[s]:
            return None, f"{s}: not enough medium passages for watermarking"
        wm_ids = {r["id"] for r in wm}
        rest = [r for r in pool if r["id"] not in wm_ids]

        unmarked = []
        for g in GROUPS:  # first pass: aim for an even 50 per group
            cand = [r for r in rest if r["length_group"] == g]
            unmarked += round_robin(cand, UNMARKED_PER_SET // 3, rng)
        counts = {g: sum(r["length_group"] == g for r in unmarked) for g in GROUPS}
        if any(counts[g] < MIN_PER_GROUP for g in GROUPS):
            return None, f"{s}: a length group has fewer than {MIN_PER_GROUP} passages: {counts}"
        if len(unmarked) < UNMARKED_PER_SET:  # top up from any group
            used = {r["id"] for r in unmarked}
            extra = [r for r in rest if r["id"] not in used]
            unmarked += round_robin(extra, UNMARKED_PER_SET - len(unmarked), rng)
        if len(unmarked) < UNMARKED_PER_SET:
            return None, f"{s}: only {len(unmarked)} unmarked passages available"
        chosen[s] = (wm, unmarked)
    return (assign, chosen), None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="re-split even though assignments exist (only before any scoring!)")
    args = ap.parse_args()

    settings = load_settings()
    rows = read_manifest()
    if any(r["set"] for r in rows) and not args.force:
        raise SystemExit("Manifest is already split. Re-splitting after scoring biases results. Use --force only if nothing has been scored.")

    base_seed = settings["seed"]
    result, last_err = None, None
    for attempt in range(200):
        rng = random.Random(base_seed + attempt)
        result, err = try_split(rows, rng)
        if result:
            used_seed = base_seed + attempt
            break
        last_err = err
    if not result:
        raise SystemExit(f"Could not satisfy the split constraints: {last_err}\nCollect more passages or more books.")

    assign, chosen = result
    for r in rows:
        r["collection"], r["set"], r["forgery_selected"] = "unused", "", ""
    by_id = {r["id"]: r for r in rows}
    for s, (wm, unmarked) in chosen.items():
        for r in wm:
            by_id[r["id"]].update(collection="watermark", set=s)
        for r in unmarked:
            by_id[r["id"]].update(collection="unmarked", set=s)

    eval_wm = sorted(r["id"] for r in chosen["evaluation"][0])
    forgery = sorted(random.Random(used_seed).sample(eval_wm, FORGERY_COUNT))
    for pid in forgery:
        by_id[pid]["forgery_selected"] = "yes"

    write_manifest(rows)

    # ---- report
    lines = ["# Data split report", "",
             f"Seed used: {used_seed} (base seed {base_seed} from config/settings.json, attempt {used_seed - base_seed}).", "",
             "Method: whole books assigned to one set (greedy balancing after a seeded shuffle); "
             "passages picked round-robin across books; watermark passages drawn from the 100-199 word group.", "",
             "| Set | Unmarked short | medium | long | Unmarked total | Watermark | Source documents |",
             "|---|---|---|---|---|---|---|"]
    for s in SETS:
        wm, unmarked = chosen[s]
        c = {g: sum(r["length_group"] == g for r in unmarked) for g in GROUPS}
        nbooks = len({r["book_id"] for r in wm + unmarked})
        lines.append(f"| {s} | {c['short']} | {c['medium']} | {c['long']} | {len(unmarked)} | {len(wm)} | {nbooks} |")
    lines += ["", "## Books per set", ""]
    for s in SETS:
        lines.append(f"- **{s}**: " + ", ".join(sorted(b for b, x in assign.items() if x == s)))
    lines += ["", "## Watermark passages", ""]
    for s in SETS:
        lines.append(f"- **{s}**: " + ", ".join(sorted(r["id"] for r in chosen[s][0])))
    lines += ["", "## Query-access forgery passages (Milestone 2)", "",
              f"Selected {FORGERY_COUNT} of the 10 evaluation watermark passages with "
              f"`random.Random({used_seed}).sample(sorted_ids, {FORGERY_COUNT})`, before any detector scores existed:", ""]
    lines += [f"- {pid}" for pid in forgery]
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "split_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines))
    print("\nManifest updated. Commit it now (before scoring anything).")


if __name__ == "__main__":
    main()
