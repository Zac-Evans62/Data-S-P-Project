"""Attack 3 driver: forge a watermark using detector queries (spec 5.2).

The attacker has QUERY ACCESS only. This driver creates the three service
configurations, decides eligibility, resets state, keeps the records and
computes hidden scores for analysis. Attack code (attacks/query/forgery.py)
gets only a client, wait() and a thesaurus the driver loads for it.

    A: score + decision, rate limit off      B: score + decision, rate limit on      C: decision only, rate limit on

Run every command from the repo root:

    python -m experiments.attack3 setup               # once: 3 runs + eligibility of the 5 forgery-selected originals
    python -m experiments.attack3 run A               # then B, then C (each resets state and learned colors first)
    python -m experiments.attack3 packets             # blind review sheets for outputs the service flagged
    python -m experiments.attack3 report              # summary.md, attempts.csv, totals.json
    python -m experiments.attack3 status

Results: results/milestone2/attack3/ (summary) and results/milestone2/attack3_config_<A|B|C>/ (each run).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from attacks.query.forgery import Spender, forge, prepare
from attacks.query.removal import Budget
from experiments.driver import CONFIGURATIONS, RUNS_DIR, ExperimentRun
from wmark.config import REPO_ROOT
from wmark.manifest import read_manifest
from wmark.metrics import changed_words, word_diff
from wmark.reviews import review_status
from wmark.textproc import tokenize

SUMMARY_DIR = RUNS_DIR / "attack3"
ELIGIBILITY = SUMMARY_DIR / "eligibility.csv"
REVIEWS = SUMMARY_DIR / "reviews.csv"
PACKETS = SUMMARY_DIR / "packets"
THESAURUS = REPO_ROOT / "attacks" / "query" / "thesaurus.tsv"
REVIEW_FIELDS = ["passage_id", "config", "editor", "reviewer", "meaning_preserved", "readable", "notes", "reviewed_at"]
ACCOUNT = "submitter1"
CONFIGS = ("A", "B", "C")


# ------------------------------------------------------------------ helpers

def run_dir(config: str) -> Path:
    return RUNS_DIR / f"attack3_config_{config}"


def budgets() -> dict:
    b = json.loads((REPO_ROOT / "config" / "attack_budgets.json").read_text(encoding="utf-8"))
    for key in ("preparation_requests", "prep_requests", "preparation", "color_learning_requests"):
        if key in b:
            b["_prep"] = int(b[key])
            break
    else:
        print("Note: no preparation budget key found in config/attack_budgets.json; using 100 requests.")
        b["_prep"] = 100
    return b


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if any((v or "").strip() for v in r.values())]


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def forgery_passages() -> dict[str, dict]:
    rows = [r for r in read_manifest()
            if r["collection"] == "watermark" and r["set"] == "evaluation" and r["forgery_selected"] == "yes"]
    return {r["id"]: r for r in sorted(rows, key=lambda r: r["id"])}


def original_text(pid: str) -> str:
    return (REPO_ROOT / forgery_passages()[pid]["file"]).read_text(encoding="utf-8")


def load_thesaurus() -> dict[str, list[str]]:
    th: dict[str, list[str]] = {}
    for line in THESAURUS.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#") and "\t" in line:
            w, rest = line.split("\t", 1)
            th[w] = [s for s in rest.split(",") if s]
    return th


def eligibility() -> dict[str, dict]:
    rows = read_csv(ELIGIBILITY)
    if not rows:
        sys.exit("No eligibility.csv. Run: python -m experiments.attack3 setup")
    return {r["id"]: r for r in rows}


# ------------------------------------------------------------------ setup

def cmd_setup(args):
    if SUMMARY_DIR.exists() and not args.force:
        sys.exit(f"{SUMMARY_DIR.relative_to(REPO_ROOT)} already exists. Use status to see progress.")
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    runs = {c: ExperimentRun.create(f"attack3_config_{c}", overwrite=args.force, **CONFIGURATIONS[c]) for c in CONFIGS}
    rows = []
    print("Checking the 5 forgery-selected originals (driver-side exact scores; eligible = NOT flagged):\n")
    for pid, row in forgery_passages().items():
        hidden = runs["A"].hidden_score(original_text(pid))
        eligible = not hidden["flagged"]
        rows.append({"id": pid, "book_id": row["book_id"], "exact_green": hidden["green"], "exact_total": hidden["total"],
                     "exact_score": f"{hidden['score']:.4f}", "eligible": "yes" if eligible else "no",
                     "note": "" if eligible else "original already flagged: false positive, excluded"})
        print(f"  {pid:32s} {hidden['score']:.4f}  " + ("eligible" if eligible else "EXCLUDED (false positive)"))
    write_csv(ELIGIBILITY, rows, list(rows[0]))
    write_csv(REVIEWS, [], REVIEW_FIELDS)
    print(f"\n{sum(r['eligible'] == 'yes' for r in rows)} of {len(rows)} eligible. Saved {ELIGIBILITY.relative_to(REPO_ROOT)}.")
    print("Next: python -m experiments.attack3 run A   (then B, then C)")


# ------------------------------------------------------------------ run one configuration

def cmd_run(args):
    config = args.config.upper()
    d = run_dir(config)
    if not (d / "state" / "accounts.json").exists():
        sys.exit("Not set up. Run: python -m experiments.attack3 setup")
    if (d / "result.json").exists() and not args.force:
        sys.exit(f"Configuration {config} already has results. One run per configuration.")
    elig = {p: e for p, e in eligibility().items() if e["eligible"] == "yes"}
    b = budgets()
    thesaurus = load_thesaurus()

    run = ExperimentRun(d)
    run.reset()                                           # counters, clock and log cleared by the driver
    client, wait = run.attacker_view(ACCOUNT)
    colors: dict[str, str] = {}                           # the attacker's learned colors: empty at the start
    spender = Spender(client, wait, Budget(b["_prep"]), Budget(b["per_passage_requests"]))
    texts = {pid: original_text(pid) for pid in elig}

    t0 = run.now()
    prep = prepare(spender, colors, thesaurus, list(texts.values()))
    prep_seconds = run.now() - t0
    print(f"Config {config}: preparation used {prep['requests']}/{b['_prep']} requests, learned {prep['colors_learned']} colors "
          f"({spender.mode} responses), {prep_seconds:.0f} simulated seconds.")

    out_dir = d / "outputs"
    out_dir.mkdir(exist_ok=True)
    attempts = []
    for pid, text in texts.items():
        spender.edit = Budget(b["per_passage_requests"])
        t1 = run.now()
        res = forge(spender, colors, thesaurus, text, max_seconds=b["per_passage_minutes"] * 60)
        seconds = run.now() - t1
        (out_dir / f"{pid}.txt").write_text(res["output"], encoding="utf-8")
        hidden = run.hidden_score(res["output"])
        attempts.append({
            "id": pid, "config": config, "service_flagged": res["flagged"], "hidden_flagged": hidden.get("flagged"),
            "hidden_score": f"{hidden['score']:.4f}" if "score" in hidden else "",
            "changed_words": changed_words(tokenize(text), tokenize(res["output"])),
            "swaps": res["swaps"], "edit_requests": res["edit_requests"], "edit_seconds": round(seconds, 1),
            "stop_reason": res["stop_reason"], "colors_known": res["colors_known"], "history": res["history"]})
        print(f"  {pid:32s} flagged={res['flagged']}  swaps {len(res['swaps'])}  edit requests {res['edit_requests']}  "
              f"{seconds:.0f} s  ({res['stop_reason']})")

    # Driver-only check of the attacker's knowledge (never shown to attack code).
    right = sum((run.hidden_score(w)["flagged"] is True) == (c == "green") for w, c in colors.items())
    result = {"config": config, "mode": spender.mode, "preparation": {**prep, "seconds": prep_seconds, "budget": b["_prep"]},
              "colors_correct": right, "colors_total": len(colors), "attempts": attempts,
              "request_counts_logged": run.request_counts(ACCOUNT)}
    run.write_json("result.json", result)
    print(f"Learned colors correct (driver check): {right}/{len(colors)}. Saved {(d / 'result.json').relative_to(REPO_ROOT)}")


# ------------------------------------------------------------------ reviews

def flagged_outputs() -> list[tuple[str, str, Path]]:
    out = []
    for c in CONFIGS:
        rp = run_dir(c) / "result.json"
        if rp.exists():
            for a in json.loads(rp.read_text(encoding="utf-8"))["attempts"]:
                if a["service_flagged"]:
                    out.append((a["id"], c, run_dir(c) / "outputs" / f"{a['id']}.txt"))
    return out


def cmd_packets(args):
    reviews = read_csv(REVIEWS)
    have = {(r["passage_id"], r["config"]) for r in reviews}
    PACKETS.mkdir(parents=True, exist_ok=True)
    items = flagged_outputs()
    for pid, c, path in items:
        orig, edited = original_text(pid).strip(), path.read_text(encoding="utf-8").strip()
        (PACKETS / f"{pid}__{c}.md").write_text(
            f"# Attack 3 quality check: {pid} (configuration {c})\n\n"
            "The edit was made by an automated attack, so any teammate may review. Do not look at scores or results "
            f"before recording your answers in `{REVIEWS.relative_to(REPO_ROOT).as_posix()}`.\n\n"
            "Answer yes or no:\n\n1. **Meaning preserved?** Does the edited version keep the main meaning of the original?\n"
            "2. **Readable?** Is the edited version readable prose?\n\n---\n\n"
            f"## Edited version (read this first, on its own)\n\n{edited}\n\n---\n\n## Original version\n\n{orig}\n\n---\n\n"
            f"## Word diff ([-removed-] {{+added+}})\n\n{word_diff(tokenize(orig), tokenize(edited))}\n", encoding="utf-8")
        if (pid, c) not in have:
            reviews.append({"passage_id": pid, "config": c, "editor": "automated"})
    write_csv(REVIEWS, reviews, REVIEW_FIELDS)
    print(f"Wrote {len(items)} packets to {PACKETS.relative_to(REPO_ROOT)} (outputs the service flagged; unflagged ones already failed).")
    print(f"Reviewer fills {REVIEWS.relative_to(REPO_ROOT)}: reviewer, meaning_preserved, readable (yes/no), notes, reviewed_at.")


def _quality(reviews: dict, pid: str, c: str) -> str:
    r = reviews.get((pid, c))
    if r is None:
        return "not reviewed"
    return review_status(dict(r))[0]


# ------------------------------------------------------------------ report

def cmd_report(args):
    elig = eligibility()
    eligible_ids = [p for p, e in elig.items() if e["eligible"] == "yes"]
    n = len(eligible_ids)
    reviews = {(r["passage_id"], r["config"]): r for r in read_csv(REVIEWS)}
    rows, per_config, problems = [], {}, []
    for c in CONFIGS:
        rp = run_dir(c) / "result.json"
        if not rp.exists():
            problems.append(f"configuration {c}: not run")
            continue
        res = json.loads(rp.read_text(encoding="utf-8"))
        per_config[c] = res
        for a in res["attempts"]:
            q = _quality(reviews, a["id"], c) if a["service_flagged"] else "n/a (not flagged)"
            rows.append({"config": c, "id": a["id"], "flagged": a["service_flagged"], "hidden_score": a["hidden_score"],
                         "changed_words": a["changed_words"], "edit_requests": a["edit_requests"],
                         "edit_seconds": a["edit_seconds"], "stop_reason": a["stop_reason"], "quality": q,
                         "success": a["service_flagged"] and q == "usable"})
            if a["service_flagged"] and q in ("not reviewed", "invalid review"):
                problems.append(f"{a['id']} configuration {c}: {q}")
            if a["service_flagged"] != a["hidden_flagged"]:
                problems.append(f"{a['id']} configuration {c}: service decision and driver score disagree")
    write_csv(SUMMARY_DIR / "attempts.csv", rows, ["config", "id", "flagged", "hidden_score", "changed_words", "edit_requests",
                                                   "edit_seconds", "stop_reason", "quality", "success"])

    def rate(k):
        return f"{k}/{n} ({100 * k / n:.0f}%)" if n else "not applicable"

    excluded = [p for p, e in elig.items() if e["eligible"] != "yes"]
    L = ["# Attack 3: forgery with detector queries", "",
         "Eligible originals (the forgery-selected 5, not already flagged): " + str(n)
         + (f". Excluded as false positives: {', '.join(excluded)}" if excluded else ""), "",
         "| Configuration | Response | Rate limit | Prep requests | Prep time (s) | Colors learned (correct) | "
         "Edit requests (total) | Edit time (s, total) | Flagged within budget | Successes (flagged and usable) |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    desc = {"A": ("score + decision", "off"), "B": ("score + decision", "on"), "C": ("decision only", "on")}
    for c, res in per_config.items():
        rs = [r for r in rows if r["config"] == c]
        L.append(f"| {c} | {desc[c][0]} | {desc[c][1]} | {res['preparation']['requests']}/{res['preparation']['budget']} | "
                 f"{res['preparation']['seconds']:.0f} | {res['colors_total']} ({res['colors_correct']}) | "
                 f"{sum(r['edit_requests'] for r in rs)} | {sum(r['edit_seconds'] for r in rs):.0f} | "
                 f"{rate(sum(bool(r['flagged']) for r in rs))} | {rate(sum(bool(r['success']) for r in rs))} |")
    L += ["", "Request counts include requests rejected by the rate limit. Time is simulated seconds from the driver's clock.", "",
          "| Config | Passage | Flagged | Changed words | Edit requests | Edit time (s) | Stop reason | Quality | Success |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['config']} | {r['id']} | {r['flagged']} | {r['changed_words']} | {r['edit_requests']} | "
                 f"{r['edit_seconds']} | {r['stop_reason']} | {r['quality']} | {r['success']} |")

    a2 = read_csv(RUNS_DIR / "attack2_key_forgery" / "attempts.csv")
    if a2:
        L += ["", "## Key access (Attack 2) on the same originals", "",
              "| Passage | Flagged | Changed words | Requests used | Minutes | Quality | Success |", "|---|---|---|---|---|---|---|"]
        for r in a2:
            if r["id"] in elig:
                L.append(f"| {r['id']} | {r.get('flagged', '')} | {r.get('changed_words', '')} | {r.get('requests_used', '')} | "
                         f"{r.get('minutes_to_final', '')} | {r.get('quality', '')} | {r.get('success', '')} |")
    if problems:
        L += ["", "## Problems to fix before reporting", ""] + [f"- {p}" for p in problems]
    text = "\n".join(L) + "\n"
    (SUMMARY_DIR / "summary.md").write_text(text, encoding="utf-8")
    (SUMMARY_DIR / "totals.json").write_text(json.dumps(
        {"eligible": n, "excluded": excluded,
         "configs": {c: {"flagged": sum(bool(r["flagged"]) for r in rows if r["config"] == c),
                         "successes": sum(bool(r["success"]) for r in rows if r["config"] == c),
                         "prep_requests": res["preparation"]["requests"], "colors_learned": res["colors_total"]}
                     for c, res in per_config.items()}}, indent=2) + "\n", encoding="utf-8")
    print(text)
    print(f"Saved {(SUMMARY_DIR / 'summary.md').relative_to(REPO_ROOT)}, attempts.csv and totals.json")


def cmd_status(args):
    for pid, e in eligibility().items():
        if e["eligible"] != "yes":
            print(f"  {pid:32s} excluded ({e['note']})")
    for c in CONFIGS:
        print(f"  configuration {c}: " + ("done" if (run_dir(c) / "result.json").exists() else "not run"))
    print(f"  reviews recorded: {sum(bool(r.get('reviewer')) for r in read_csv(REVIEWS))}/{len(read_csv(REVIEWS))}")


def main():
    ap = argparse.ArgumentParser(prog="python -m experiments.attack3", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup"); s.add_argument("--force", action="store_true", help=argparse.SUPPRESS)
    s = sub.add_parser("run"); s.add_argument("config", choices=CONFIGS + tuple(c.lower() for c in CONFIGS))
    s.add_argument("--force", action="store_true", help=argparse.SUPPRESS)
    sub.add_parser("packets"); sub.add_parser("report"); sub.add_parser("status")
    args = ap.parse_args()
    {"setup": cmd_setup, "run": cmd_run, "packets": cmd_packets, "report": cmd_report, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    main()
