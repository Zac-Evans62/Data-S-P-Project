"""Attack 2: forge a watermark using the key (spec 5.2).

The attacker has the key, so every word's color can be computed locally for
free. They edit an UNMARKED original, replacing red words with green ones,
until the detector flags it. Only queries to the detection service count
toward the request budget. Success = the service flags the output AND a
teammate's blind review says meaning is preserved and the prose is readable.

Run every command from the repo root:

    python -m attacks.key.forge setup                      # once: create the run, score all 10 originals
    python -m attacks.key.forge start <id> --editor Zac    # start a timed session on one original
    python -m attacks.key.forge check <id>                 # after each batch of edits (local, free)
    python -m attacks.key.forge color large huge vast      # check candidate words' colors (local, free)
    python -m attacks.key.forge query <id>                 # optional: ask the service (costs 1 request)
    python -m attacks.key.forge finish <id>                # stop: keep best version, verify with the service
    python -m attacks.key.forge packets                    # blind review sheets for the reviewer
    python -m attacks.key.forge report                     # results table and summary.md
    python -m attacks.key.forge status                     # what is done / left

Everything is saved in results/milestone2/attack2_key_forgery/.
Settings come from the frozen config: threshold 0.63, target 0.66, and the
per-passage budget in config/attack_budgets.json (15 minutes, 100 requests).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from experiments.driver import RUNS_DIR, ExperimentRun
from wmark.config import REPO_ROOT, SYNONYMS_PATH, load_key, load_settings, threshold_of
from wmark.detector import GREEN, score_tokens, word_color
from wmark.manifest import read_manifest
from wmark.metrics import changed_words, word_diff
from wmark.reviews import review_status
from wmark.textproc import normalize_word, tokenize

RUN_NAME = "attack2_key_forgery"
RUN_DIR = RUNS_DIR / RUN_NAME
SESSIONS = RUN_DIR / "sessions"
ELIGIBILITY = RUN_DIR / "eligibility.csv"
REVIEWS = RUN_DIR / "reviews.csv"
PACKETS = RUN_DIR / "packets"
REVIEW_FIELDS = ["passage_id", "editor", "reviewer", "meaning_preserved", "readable", "notes", "reviewed_at"]
ACCOUNT = "submitter1"


# ------------------------------------------------------------------ helpers

def now() -> datetime:
    return datetime.now(timezone.utc)


def budgets() -> dict:
    return json.loads((REPO_ROOT / "config" / "attack_budgets.json").read_text(encoding="utf-8"))


def originals() -> dict[str, dict]:
    """The 10 evaluation watermark passages; Attack 2 starts from their UNMARKED originals."""
    rows = [r for r in read_manifest() if r["collection"] == "watermark" and r["set"] == "evaluation"]
    return {r["id"]: r for r in sorted(rows, key=lambda r: r["id"])}


def original_text(row: dict) -> str:
    return (REPO_ROOT / row["file"]).read_text(encoding="utf-8")


def load_run() -> ExperimentRun:
    if not (RUN_DIR / "state" / "accounts.json").exists():
        sys.exit("Attack 2 is not set up yet. Run: python -m attacks.key.forge setup")
    return ExperimentRun(RUN_DIR)


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


def eligibility() -> dict[str, dict]:
    rows = read_csv(ELIGIBILITY)
    if not rows:
        sys.exit("No eligibility.csv. Run: python -m attacks.key.forge setup")
    return {r["id"]: r for r in rows}


def session_paths(pid: str):
    d = SESSIONS / pid
    return d, d / "working.txt", d / "versions", d / "log.json", d / "final.txt"


def load_log(pid: str) -> dict:
    _, _, _, log_path, _ = session_paths(pid)
    if not log_path.exists():
        sys.exit(f"No session for {pid}. Start one with: python -m attacks.key.forge start {pid} --editor NAME")
    return json.loads(log_path.read_text(encoding="utf-8"))


def save_log(pid: str, log: dict) -> None:
    _, _, _, log_path, _ = session_paths(pid)
    log_path.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")


def minutes_since(iso: str, at: datetime | None = None) -> float:
    return ((at or now()) - datetime.fromisoformat(iso)).total_seconds() / 60


def swaps_to_flag(green: int, total: int, threshold: Fraction) -> int:
    """One-for-one red->green swaps needed so green/total > threshold (green >= floor(t*total) + 1)."""
    return max(0, math.floor(threshold * total) + 1 - green)


def swaps_to_target(green: int, total: int, target: Fraction) -> int:
    """One-for-one red->green swaps needed so green/total >= target (green >= ceil(target*total))."""
    return max(0, math.ceil(target * total) - green)


def best_in_time(versions: list[dict], started_at: str, max_minutes: float) -> dict:
    """Highest-scoring version saved within the time limit (earliest wins a tie)."""
    eligible = [v for v in versions if minutes_since(started_at, datetime.fromisoformat(v["at"])) <= max_minutes]
    return max(eligible, key=lambda v: (Fraction(v["green"], v["total"]), -int(v["version"][1:])))


def load_synonyms() -> dict[str, list[str]]:
    syn: dict[str, list[str]] = {}
    if not SYNONYMS_PATH.exists():
        return syn
    for line in SYNONYMS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#") or "\t" not in line:
            continue
        word, rest = line.split("\t", 1)
        try:
            w = normalize_word(word)
        except ValueError:
            continue
        syn.setdefault(w, []).extend(s.strip() for s in rest.split(",") if s.strip())
    return syn


def is_green_phrase(phrase: str, key: bytes) -> bool:
    toks = tokenize(phrase)
    return bool(toks) and all(word_color(t, key) == GREEN for t in toks)


def ask_service(run: ExperimentRun, text: str) -> tuple[dict, int, float]:
    """Send text to the service as the attacker. Waits out rate limits (simulated time).

    Returns (response, requests sent, simulated seconds waited)."""
    client = run.client(ACCOUNT)
    waited = 0.0
    for _ in range(5):
        r = client.detect(text)
        if r.get("error") == "rate_limited":
            run.wait(r["retry_after_seconds"])
            waited += r["retry_after_seconds"]
            continue
        return r, client.requests_sent, waited
    return r, client.requests_sent, waited


# ------------------------------------------------------------------ commands

def cmd_setup(args):
    if RUN_DIR.exists() and not args.force:
        sys.exit(f"{RUN_DIR.relative_to(REPO_ROOT)} already exists. Attack 2 is set up once; use status to see progress.")
    run = ExperimentRun.create(RUN_NAME, mode="score", rate_limit_enabled=True, overwrite=args.force)
    SESSIONS.mkdir(parents=True, exist_ok=True)
    rows = []
    print("Scoring all 10 unmarked originals through the service (spec: 'Score all 10 unmarked originals'):\n")
    for pid, row in originals().items():
        text = original_text(row)
        resp, sent, _ = ask_service(run, text)
        hidden = run.hidden_score(text)
        eligible = resp.get("ok") and not resp["flagged"]
        rows.append({
            "id": pid, "book_id": row["book_id"], "forgery_selected": row["forgery_selected"],
            "service_score": resp.get("score", ""), "service_flagged": resp.get("flagged", ""),
            "exact_green": hidden["green"], "exact_total": hidden["total"],
            "eligible": "yes" if eligible else "no",
            "note": "" if eligible else "original already flagged: false positive, excluded",
            "requests": sent,
        })
        mark = "eligible" if eligible else "EXCLUDED (already flagged = false positive)"
        print(f"  {pid:32s} {resp.get('score', '?'):>6s}  {mark}")
    write_csv(ELIGIBILITY, rows, list(rows[0]))
    write_csv(REVIEWS, [], REVIEW_FIELDS)
    n = sum(r["eligible"] == "yes" for r in rows)
    print(f"\n{n} of 10 originals are eligible. Saved {ELIGIBILITY.relative_to(REPO_ROOT)}.")
    print("Next: python -m attacks.key.forge start <id> --editor YOURNAME")


def cmd_start(args):
    elig = eligibility()
    pid = args.passage_id
    if pid not in elig:
        sys.exit(f"{pid} is not one of the 10 Attack 2 originals: {', '.join(elig)}")
    if elig[pid]["eligible"] != "yes":
        sys.exit(f"{pid} is not eligible: {elig[pid]['note']}")
    d, working, versions, log_path, _ = session_paths(pid)
    if log_path.exists():
        sys.exit(f"{pid} already has a session. One attempt per passage; use check / finish.")
    versions.mkdir(parents=True)
    text = original_text(originals()[pid])
    working.write_text(text, encoding="utf-8")
    shutil.copy(working, versions / "v000.txt")

    settings, b = load_settings(), budgets()
    key = load_key(settings)
    r = score_tokens(tokenize(text), key)
    log = {
        "passage_id": pid, "editor": args.editor, "forgery_selected": elig[pid]["forgery_selected"],
        "threshold": settings["threshold"], "target": settings["watermark_target"],
        "max_minutes": b["per_passage_minutes"], "max_requests": b["per_passage_requests"],
        "started_at": now().isoformat(),
        "versions": [{"version": "v000", "at": now().isoformat(), "green": r.green, "total": r.total, "score": r.score}],
        "queries": [], "requests_used": 0, "simulated_wait_seconds": 0.0,
        "finished_at": None, "stop_reason": None, "final_version": None, "service_result": None,
    }
    save_log(pid, log)
    t, target = threshold_of(settings), Fraction(settings["watermark_target"])
    print(f"Started {pid}. Original: {r.green}/{r.total} green = {r.score:.4f}.")
    print(f"Swaps needed to be flagged (> {settings['threshold']}): {swaps_to_flag(r.green, r.total, t)};"
          f" to reach the target {settings['watermark_target']}: {swaps_to_target(r.green, r.total, target)}.")
    print(f"Clock started: {b['per_passage_minutes']} minutes. Edit {working.relative_to(REPO_ROOT)}")
    print(f"then run: python -m attacks.key.forge check {pid}")


def cmd_check(args):
    pid = args.passage_id
    log = load_log(pid)
    if log["finished_at"]:
        sys.exit("Session already finished.")
    settings = load_settings()
    key = load_key(settings)
    _, working, versions, _, _ = session_paths(pid)
    text = working.read_text(encoding="utf-8")
    tokens = tokenize(text)
    r = score_tokens(tokens, key)
    elapsed = minutes_since(log["started_at"])
    last = versions / f"{log['versions'][-1]['version']}.txt"
    if text != last.read_text(encoding="utf-8"):
        v = f"v{len(log['versions']):03d}"
        shutil.copy(working, versions / f"{v}.txt")
        log["versions"].append({"version": v, "at": now().isoformat(), "green": r.green, "total": r.total, "score": r.score})
        save_log(pid, log)
        saved = f"saved as {v}" + ("  (AFTER the time limit: will not count)" if elapsed > log["max_minutes"] else "")
    else:
        saved = "no change since last version"

    t, target = Fraction(log["threshold"]), Fraction(log["target"])
    orig_tokens = tokenize((versions / "v000.txt").read_text(encoding="utf-8"))
    print(f"local score {r.score:.4f} ({r.green}/{r.total})   flagged would be {r.fraction > t}   "
          f"elapsed {elapsed:.1f}/{log['max_minutes']} min   changed words {changed_words(orig_tokens, tokens)}   [{saved}]")
    print(f"swaps still needed: {swaps_to_flag(r.green, r.total, t)} to be flagged, "
          f"{swaps_to_target(r.green, r.total, target)} to reach the target {log['target']}")
    if r.fraction >= target:
        print(">> Target reached. Run: python -m attacks.key.forge finish " + pid)
    elif elapsed >= log["max_minutes"]:
        print(">> Time limit reached. Stop editing and run: python -m attacks.key.forge finish " + pid)

    syn = load_synonyms()
    red = [(w, n) for w, n in Counter(tokens).most_common() if word_color(w, key) != GREEN]
    print(f"\nRed words ({len(red)} distinct), most frequent first (green synonyms from data/synonyms.tsv):")
    for w, n in red[: args.top]:
        greens = [s for s in syn.get(w, []) if is_green_phrase(s, key)]
        print(f"  {n:3d}  {w}" + (f"   ->  {', '.join(greens)}" if greens else ""))
    if len(red) > args.top:
        print(f"  ... {len(red) - args.top} more")
    print("\nCheck your own candidates: python -m attacks.key.forge color WORD WORD ...")


def cmd_color(args):
    key = load_key(load_settings())
    for w in args.words:
        toks = tokenize(w)
        if not toks:
            print(f"{w!r}: no words")
            continue
        colors = ["green" if word_color(t, key) == GREEN else "red" for t in toks]
        print(f"{w:20s} " + ", ".join(f"{t}={c}" for t, c in zip(toks, colors)))


def cmd_query(args):
    pid = args.passage_id
    log = load_log(pid)
    if log["finished_at"]:
        sys.exit("Session already finished.")
    if log["requests_used"] >= log["max_requests"] - 1:
        sys.exit("Only the final verification request is left in this passage's budget.")
    run = load_run()
    _, working, _, _, _ = session_paths(pid)
    resp, sent, waited = ask_service(run, working.read_text(encoding="utf-8"))
    log["requests_used"] += sent
    log["simulated_wait_seconds"] += waited
    log["queries"].append({"at": now().isoformat(), "kind": "query", "response": resp, "requests": sent})
    save_log(pid, log)
    print(f"service: {json.dumps({k: v for k, v in resp.items() if k != 'request_id'})}   "
          f"requests used {log['requests_used']}/{log['max_requests']}")


def cmd_finish(args):
    pid = args.passage_id
    log = load_log(pid)
    if log["finished_at"]:
        sys.exit("Session already finished.")
    _, working, versions, _, final = session_paths(pid)
    last = versions / f"{log['versions'][-1]['version']}.txt"
    if working.read_text(encoding="utf-8") != last.read_text(encoding="utf-8"):
        elapsed = minutes_since(log["started_at"])
        if elapsed <= log["max_minutes"]:
            sys.exit("working.txt has unsaved edits. Run check first (you are still within the time limit).")
        print("Note: unsaved edits after the time limit are ignored.")

    best = best_in_time(log["versions"], log["started_at"], log["max_minutes"])
    late = len(log["versions"]) - sum(
        minutes_since(log["started_at"], datetime.fromisoformat(v["at"])) <= log["max_minutes"] for v in log["versions"])
    elapsed = minutes_since(log["started_at"])
    target = Fraction(log["target"])
    if Fraction(best["green"], best["total"]) >= target:
        reason = "target reached"
    elif elapsed >= log["max_minutes"]:
        reason = "time limit reached"
    elif args.reason:
        reason = args.reason
    else:
        sys.exit("Target not reached and time remains. Keep editing, or stop early with --reason \"...\" (it is reported).")

    shutil.copy(versions / f"{best['version']}.txt", final)
    run = load_run()
    resp, sent, waited = ask_service(run, final.read_text(encoding="utf-8"))
    log["requests_used"] += sent
    log["simulated_wait_seconds"] += waited
    log["queries"].append({"at": now().isoformat(), "kind": "final verification", "response": resp, "requests": sent})
    best_at = minutes_since(log["started_at"], datetime.fromisoformat(best["at"]))
    log.update(finished_at=now().isoformat(), stop_reason=reason, final_version=best["version"],
               minutes_to_final=round(best_at, 1), late_versions_ignored=late,
               service_result={"flagged": resp.get("flagged"), "score": resp.get("score"), "error": resp.get("error")})
    save_log(pid, log)
    print(f"Finished {pid}: kept {best['version']} ({best['score']:.4f}, saved at {best_at:.1f} min). Stop reason: {reason}.")
    if late:
        print(f"{late} version(s) saved after the time limit were ignored.")
    print(f"Service says: flagged={resp.get('flagged')}  score={resp.get('score')}   requests used {log['requests_used']}/{log['max_requests']}")
    print("Next: python -m attacks.key.forge packets   (then a teammate reviews it blind)")


def cmd_packets(args):
    reviews = read_csv(REVIEWS)
    have = {r["passage_id"] for r in reviews}
    PACKETS.mkdir(parents=True, exist_ok=True)
    made, missing = 0, []
    for pid, row in originals().items():
        _, _, _, log_path, final = session_paths(pid)
        if not final.exists():
            if log_path.exists():
                missing.append(pid)
            continue
        log = json.loads(log_path.read_text(encoding="utf-8"))
        orig, edited = original_text(row).strip(), final.read_text(encoding="utf-8").strip()
        (PACKETS / f"{pid}.md").write_text(
            f"# Attack 2 quality check: {pid}\n\nEditor: {log['editor']}. **You must not be the editor.** "
            "Do not look at any scores or results for this passage before recording your answers in "
            f"`{REVIEWS.relative_to(REPO_ROOT).as_posix()}`.\n\n"
            "Answer yes or no:\n\n1. **Meaning preserved?** Does the edited version keep the main meaning of the original?\n"
            "2. **Readable?** Is the edited version readable prose?\n\n---\n\n"
            f"## Edited version (read this first, on its own)\n\n{edited}\n\n---\n\n## Original version\n\n{orig}\n\n---\n\n"
            f"## Word diff ([-removed-] {{+added+}})\n\n{word_diff(tokenize(orig), tokenize(edited))}\n",
            encoding="utf-8")
        made += 1
        if pid not in have:
            reviews.append({"passage_id": pid, "editor": log["editor"]})
    write_csv(REVIEWS, reviews, REVIEW_FIELDS)
    print(f"Wrote {made} packets to {PACKETS.relative_to(REPO_ROOT)}")
    if missing:
        print(f"Not finished yet: {', '.join(missing)}")
    print(f"Reviewer fills {REVIEWS.relative_to(REPO_ROOT)}: reviewer, meaning_preserved (yes/no), readable (yes/no), notes, reviewed_at.")


def collect_results() -> tuple[list[dict], dict]:
    elig = eligibility()
    reviews = {r["passage_id"]: r for r in read_csv(REVIEWS)}
    rows = []
    for pid, e in elig.items():
        rec = {"id": pid, "forgery_selected": e["forgery_selected"], "eligible": e["eligible"],
               "original_score": e["service_score"]}
        _, _, _, log_path, final = session_paths(pid)
        if e["eligible"] != "yes":
            rec.update(status="excluded (original already flagged)")
            rows.append(rec)
            continue
        if not final.exists():
            rec.update(status="not attempted" if not log_path.exists() else "not finished", success=False)
            rows.append(rec)
            continue
        log = json.loads(log_path.read_text(encoding="utf-8"))
        orig_toks = tokenize(original_text(originals()[pid]))
        fin_toks = tokenize(final.read_text(encoding="utf-8"))
        rev = reviews.get(pid)
        if rev is not None:
            rev = dict(rev)
            rev.setdefault("editor", log["editor"])
        quality, problems = review_status(rev)
        sr = log["service_result"] or {}
        flagged = sr.get("flagged") is True
        rec.update(
            status="finished", editor=log["editor"], final_score=sr.get("score"), flagged=flagged,
            reached_target=log["stop_reason"] == "target reached", changed_words=changed_words(orig_toks, fin_toks),
            minutes_to_final=log.get("minutes_to_final"), requests_used=log["requests_used"],
            simulated_wait_seconds=log["simulated_wait_seconds"], stop_reason=log["stop_reason"],
            quality=quality, quality_problems="; ".join(problems), success=flagged and quality == "usable",
        )
        rows.append(rec)

    def tally(subset):
        eligible = [r for r in subset if r["eligible"] == "yes"]
        return {"eligible": len(eligible),
                "attempted": sum(r["status"] == "finished" for r in eligible),
                "flagged": sum(bool(r.get("flagged")) for r in eligible),
                "successes": sum(bool(r.get("success")) for r in eligible),
                "excluded_false_positives": [r["id"] for r in subset if r["eligible"] != "yes"]}
    return rows, {"all": tally(rows), "forgery_selected": tally([r for r in rows if r["forgery_selected"] == "yes"])}


def cmd_report(args):
    rows, totals = collect_results()
    fields = ["id", "forgery_selected", "eligible", "status", "editor", "original_score", "final_score", "flagged",
              "reached_target", "changed_words", "minutes_to_final", "requests_used", "simulated_wait_seconds",
              "stop_reason", "quality", "quality_problems", "success"]
    write_csv(RUN_DIR / "attempts.csv", rows, fields)
    (RUN_DIR / "totals.json").write_text(json.dumps(totals, indent=2) + "\n", encoding="utf-8")

    def rate(t):
        return f"{t['successes']}/{t['eligible']}" + (f" ({100 * t['successes'] / t['eligible']:.0f}%)" if t["eligible"] else " (not applicable)")

    L = ["# Attack 2: forgery with the key", "",
         "Settings: threshold 0.63, target 0.66, budget per passage 15 minutes and 100 requests "
         "(`config/attack_budgets.json`). Local color checks with the key are free; only service queries count.", "",
         "| Group | Eligible | Attempted | Flagged by service | Successes (flagged and usable) |",
         "|---|---|---|---|---|"]
    for name, label in (("all", "All 10 originals"), ("forgery_selected", "The 5 forgery-selected originals")):
        t = totals[name]
        L.append(f"| {label} | {t['eligible']} | {t['attempted']} | {t['flagged']} | {rate(t)} |")
    if totals["all"]["excluded_false_positives"]:
        L += ["", "Excluded as false positives (original already flagged): "
              + ", ".join(totals["all"]["excluded_false_positives"])]
    L += ["", "| Passage | Selected | Original | Final | Flagged | Changed words | Minutes | Requests | Stop reason | Quality | Success |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    problems = []
    for r in rows:
        if r["eligible"] != "yes":
            L.append(f"| {r['id']} | {r['forgery_selected']} | {r['original_score']} | excluded | | | | | | | |")
            continue
        L.append(f"| {r['id']} | {r['forgery_selected']} | {r['original_score']} | {r.get('final_score', '')} | "
                 f"{r.get('flagged', '')} | {r.get('changed_words', '')} | {r.get('minutes_to_final', '')} | "
                 f"{r.get('requests_used', '')} | {r.get('stop_reason', '')} | {r.get('quality', '')} | {r.get('success', '')} |")
        if r["status"] != "finished":
            problems.append(f"{r['id']}: {r['status']}")
        elif r.get("quality_problems"):
            problems.append(f"{r['id']}: {r['quality']}: {r['quality_problems']}")
    if problems:
        L += ["", "## Problems to fix before reporting", ""] + [f"- {p}" for p in problems]
    text = "\n".join(L) + "\n"
    (RUN_DIR / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"Saved {(RUN_DIR / 'summary.md').relative_to(REPO_ROOT)}, attempts.csv and totals.json")


def cmd_status(args):
    elig = eligibility()
    reviews = {r["passage_id"]: r for r in read_csv(REVIEWS)}
    for pid, e in elig.items():
        _, _, _, log_path, final = session_paths(pid)
        if e["eligible"] != "yes":
            state = "excluded (false positive)"
        elif final.exists():
            rv = reviews.get(pid, {})
            state = "finished, " + ("reviewed" if rv.get("meaning_preserved") else "awaiting review")
        elif log_path.exists():
            state = f"in progress ({minutes_since(load_log(pid)['started_at']):.0f} min since start)"
        else:
            state = "not started"
        sel = " [forgery-selected]" if e["forgery_selected"] == "yes" else ""
        print(f"  {pid:32s} {state}{sel}")


def main():
    ap = argparse.ArgumentParser(prog="python -m attacks.key.forge", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup"); s.add_argument("--force", action="store_true", help=argparse.SUPPRESS)
    s = sub.add_parser("start"); s.add_argument("passage_id"); s.add_argument("--editor", required=True)
    s = sub.add_parser("check"); s.add_argument("passage_id"); s.add_argument("--top", type=int, default=25)
    s = sub.add_parser("color"); s.add_argument("words", nargs="+")
    s = sub.add_parser("query"); s.add_argument("passage_id")
    s = sub.add_parser("finish"); s.add_argument("passage_id"); s.add_argument("--reason")
    sub.add_parser("packets"); sub.add_parser("report"); sub.add_parser("status")
    args = ap.parse_args()
    {"setup": cmd_setup, "start": cmd_start, "check": cmd_check, "color": cmd_color, "query": cmd_query,
     "finish": cmd_finish, "packets": cmd_packets, "report": cmd_report, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    main()