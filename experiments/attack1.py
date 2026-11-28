"""Attack 1 driver: remove the watermark using detector queries (spec 5.2).

The attacker has QUERY ACCESS only: no key, no local scores. Every score they
see comes from a service query, which costs one request from the budget.
This driver sets up the run, decides eligibility, keeps the records, and
hands attack code (attacks/query/removal.py) only a client and wait().

Run every command from the repo root:

    python -m experiments.attack1 setup                     # once: run + eligibility of the 10 outputs

  Variant 1, word substitution (by hand, 15 minutes and 100 requests per passage):
    python -m experiments.attack1 start <id> --editor Zac   # copy of the watermarked output to edit
    python -m experiments.attack1 query <id>                # send your current edit (1 request)
    python -m experiments.attack1 probe <id> word word ...  # learn colors by repeated-word queries (1 request each)
    python -m experiments.attack1 finish <id>               # keep the best queried version

  Variant 2, the three character tests (automated, one shared 100-request budget per passage):
    python -m experiments.attack1 chartests                 # all eligible passages

    python -m experiments.attack1 packets                   # blind review sheets (unflagged outputs only)
    python -m experiments.attack1 report                    # summary.md, attempts.csv, totals.json
    python -m experiments.attack1 status

Results are saved in results/milestone2/attack1_query_removal/.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from attacks.query.removal import Budget, BudgetExhausted, probe_color, run_character_tests, submit
from experiments.driver import RUNS_DIR, ExperimentRun
from wmark.config import REPO_ROOT, WATERMARKED_DIR, load_settings, threshold_of
from wmark.manifest import read_manifest
from wmark.metrics import changed_words, word_diff
from wmark.reviews import read_reviews, review_status
from wmark.textproc import tokenize

RUN_NAME = "attack1_query_removal"
RUN_DIR = RUNS_DIR / RUN_NAME
WORD_DIR = RUN_DIR / "word_substitution"
CHAR_DIR = RUN_DIR / "character_tests"
ELIGIBILITY = RUN_DIR / "eligibility.csv"
REVIEWS = RUN_DIR / "reviews.csv"
PACKETS = RUN_DIR / "packets"
REVIEW_FIELDS = ["passage_id", "variant", "editor", "reviewer", "meaning_preserved", "readable", "notes", "reviewed_at"]
CHAR_TESTS = ("case", "zero_width", "punctuation")
ACCOUNT_WORD, ACCOUNT_CHAR = "submitter1", "submitter2"   # separate accounts so the variants don't share a rate limit


# ------------------------------------------------------------------ helpers

def now() -> datetime:
    return datetime.now(timezone.utc)


def minutes_since(iso: str, at: datetime | None = None) -> float:
    return ((at or now()) - datetime.fromisoformat(iso)).total_seconds() / 60


def budgets() -> dict:
    return json.loads((REPO_ROOT / "config" / "attack_budgets.json").read_text(encoding="utf-8"))


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


def passages() -> dict[str, dict]:
    rows = [r for r in read_manifest() if r["collection"] == "watermark" and r["set"] == "evaluation"]
    return {r["id"]: r for r in sorted(rows, key=lambda r: r["id"])}


def original_text(pid: str) -> str:
    return (REPO_ROOT / passages()[pid]["file"]).read_text(encoding="utf-8")


def watermarked_text(pid: str) -> str:
    return (WATERMARKED_DIR / pid / "final.txt").read_text(encoding="utf-8")


def load_run() -> ExperimentRun:
    if not (RUN_DIR / "state" / "accounts.json").exists():
        sys.exit("Attack 1 is not set up yet. Run: python -m experiments.attack1 setup")
    return ExperimentRun(RUN_DIR)


def eligibility() -> dict[str, dict]:
    rows = read_csv(ELIGIBILITY)
    if not rows:
        sys.exit("No eligibility.csv. Run: python -m experiments.attack1 setup")
    return {r["id"]: r for r in rows}


def require_eligible(pid: str) -> dict:
    elig = eligibility()
    if pid not in elig:
        sys.exit(f"{pid} is not one of the 10 watermarked outputs: {', '.join(elig)}")
    if elig[pid]["eligible"] != "yes":
        sys.exit(f"{pid} is not eligible: {elig[pid]['note']}")
    return elig[pid]


def margin_words(green: int, total: int, threshold: Fraction) -> int:
    """How many green words above the threshold: green - floor(threshold * total).

    A margin of 1 means changing one green word to red would unflag the text."""
    return green - math.floor(threshold * total)


# ------------------------------------------------------------------ setup

def cmd_setup(args):
    if RUN_DIR.exists() and not args.force:
        sys.exit(f"{RUN_DIR.relative_to(REPO_ROOT)} already exists. Use status to see progress.")
    run = ExperimentRun.create(RUN_NAME, mode="score", rate_limit_enabled=True, overwrite=args.force)
    settings = load_settings()
    t = threshold_of(settings)
    m1_reviews = {(r["passage_id"], r["stage"]): r for r in read_reviews()}
    client, wait = run.attacker_view(ACCOUNT_WORD)
    budget = Budget(10 ** 6)
    rows = []
    print("Checking the 10 watermarked outputs (eligible = flagged by the service AND usable in Milestone 1):\n")
    for pid in passages():
        text = watermarked_text(pid)
        resp = submit(client, wait, text, budget)
        quality, _ = review_status(m1_reviews.get((pid, "watermark")))
        hidden = run.hidden_score(text)
        eligible = resp.get("flagged") is True and quality == "usable"
        note = "" if eligible else ("output not flagged" if resp.get("flagged") is not True else f"Milestone 1 quality: {quality}")
        rows.append({"id": pid, "m1_editor": m1_reviews.get((pid, "watermark"), {}).get("editor", ""),
                     "service_score": resp.get("score", ""), "service_flagged": resp.get("flagged", ""),
                     "m1_quality": quality, "exact_green": hidden["green"], "exact_total": hidden["total"],
                     "margin_words": margin_words(hidden["green"], hidden["total"], t),
                     "eligible": "yes" if eligible else "no", "note": note})
        print(f"  {pid:32s} {resp.get('score', '?'):>6s}  "
              + (f"eligible (margin {rows[-1]['margin_words']} green words)" if eligible else f"EXCLUDED: {note}"))
    write_csv(ELIGIBILITY, rows, list(rows[0]))
    write_csv(REVIEWS, [], REVIEW_FIELDS)
    WORD_DIR.mkdir(parents=True, exist_ok=True)
    CHAR_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n{sum(r['eligible'] == 'yes' for r in rows)} of 10 eligible. Saved {ELIGIBILITY.relative_to(REPO_ROOT)}.")
    print("Tip: attack passages you did NOT watermark in Milestone 1 (the m1_editor column), "
          "so you are not reusing your own editing records.")


# ------------------------------------------------------------------ word substitution

def word_paths(pid: str):
    d = WORD_DIR / pid
    return d, d / "working.txt", d / "versions", d / "log.json", d / "final.txt"


def load_wlog(pid: str) -> dict:
    p = word_paths(pid)[3]
    if not p.exists():
        sys.exit(f"No word-substitution session for {pid}. Run: python -m experiments.attack1 start {pid} --editor NAME")
    return json.loads(p.read_text(encoding="utf-8"))


def save_wlog(pid: str, log: dict) -> None:
    word_paths(pid)[3].write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _budget_from(log: dict) -> Budget:
    b = Budget(log["max_requests"])
    b.used, b.waited_seconds = log["requests_used"], log["simulated_wait_seconds"]
    return b


def cmd_start(args):
    e = require_eligible(args.passage_id)
    pid = args.passage_id
    d, working, versions, log_path, _ = word_paths(pid)
    if log_path.exists():
        sys.exit(f"{pid} already has a word-substitution session. One attempt per passage.")
    if e["m1_editor"] and e["m1_editor"].strip().lower() == args.editor.strip().lower():
        print(f"Warning: you watermarked {pid} in Milestone 1. The spec forbids reusing editing records "
              "from keyed watermarking; if possible let a teammate attack this one. (Continuing.)")
    versions.mkdir(parents=True)
    text = watermarked_text(pid)
    working.write_text(text, encoding="utf-8")
    shutil.copy(working, versions / "v000.txt")
    b = budgets()
    log = {"passage_id": pid, "editor": args.editor, "max_minutes": b["per_passage_minutes"],
           "max_requests": b["per_passage_requests"], "started_at": now().isoformat(),
           "versions": [{"version": "v000", "at": now().isoformat(), "queried": False}],
           "probes": [], "requests_used": 0, "simulated_wait_seconds": 0.0,
           "finished_at": None, "final_version": None, "stop_reason": None}
    save_wlog(pid, log)
    print(f"Started {pid}. You are a query-access attacker: no key, no local scores.")
    print(f"The service flags this text now. Make it unflagged while keeping meaning and readability.")
    print(f"Budget: {b['per_passage_minutes']} minutes and {b['per_passage_requests']} requests. Clock started.")
    print(f"Edit {working.relative_to(REPO_ROOT)}, then: python -m experiments.attack1 query {pid}")


def _save_version_if_changed(pid: str, log: dict) -> dict:
    _, working, versions, _, _ = word_paths(pid)
    last = log["versions"][-1]
    if working.read_text(encoding="utf-8") != (versions / f"{last['version']}.txt").read_text(encoding="utf-8"):
        v = {"version": f"v{len(log['versions']):03d}", "at": now().isoformat(), "queried": False}
        shutil.copy(working, versions / f"{v['version']}.txt")
        log["versions"].append(v)
        return v
    return last


def cmd_query(args):
    pid = args.passage_id
    log = load_wlog(pid)
    if log["finished_at"]:
        sys.exit("Session already finished.")
    elapsed = minutes_since(log["started_at"])
    if elapsed > log["max_minutes"]:
        sys.exit(f"Time limit reached ({elapsed:.1f} min). Run: python -m experiments.attack1 finish {pid}")
    v = _save_version_if_changed(pid, log)
    run = load_run()
    client, wait = run.attacker_view(ACCOUNT_WORD)
    budget = _budget_from(log)
    _, _, versions, _, _ = word_paths(pid)
    try:
        r = submit(client, wait, (versions / f"{v['version']}.txt").read_text(encoding="utf-8"), budget)
    except BudgetExhausted:
        save_wlog(pid, log)
        sys.exit(f"Request budget used up ({log['max_requests']}). Run: python -m experiments.attack1 finish {pid}")
    v.update(queried=True, response={k: r.get(k) for k in ("ok", "flagged", "score", "error")}, queried_at=now().isoformat())
    log.update(requests_used=budget.used, simulated_wait_seconds=budget.waited_seconds)
    save_wlog(pid, log)
    print(f"{v['version']}: flagged={r.get('flagged')}  score={r.get('score')}   "
          f"elapsed {elapsed:.1f}/{log['max_minutes']} min   requests {budget.used}/{log['max_requests']}")
    if r.get("flagged") is False:
        print(f">> Unflagged. Run: python -m experiments.attack1 finish {pid}")


def cmd_probe(args):
    pid = args.passage_id
    log = load_wlog(pid)
    if log["finished_at"]:
        sys.exit("Session already finished.")
    if minutes_since(log["started_at"]) > log["max_minutes"]:
        sys.exit("Time limit reached.")
    run = load_run()
    client, wait = run.attacker_view(ACCOUNT_WORD)
    budget = _budget_from(log)
    for w in args.words:
        try:
            color = probe_color(client, wait, w, budget)
        except BudgetExhausted:
            print("Request budget used up.")
            break
        log["probes"].append({"word": w, "color": color, "at": now().isoformat()})
        print(f"  {w:20s} {color}")
    log.update(requests_used=budget.used, simulated_wait_seconds=budget.waited_seconds)
    save_wlog(pid, log)
    print(f"requests {budget.used}/{log['max_requests']}")


def best_queried(versions: list[dict], started_at: str, max_minutes: float) -> dict | None:
    """The attacker only knows the scores of versions they queried within the time limit.
    Prefer the earliest unflagged one; otherwise the lowest score (earliest on a tie)."""
    ok = [v for v in versions if v.get("queried") and (v.get("response") or {}).get("ok")
          and minutes_since(started_at, datetime.fromisoformat(v["queried_at"])) <= max_minutes]
    if not ok:
        return None
    unflagged = [v for v in ok if v["response"]["flagged"] is False]
    if unflagged:
        return unflagged[0]
    return min(ok, key=lambda v: (float(v["response"]["score"]), int(v["version"][1:])))


def cmd_finish(args):
    pid = args.passage_id
    log = load_wlog(pid)
    if log["finished_at"]:
        sys.exit("Session already finished.")
    _save_version_if_changed(pid, log)
    elapsed = minutes_since(log["started_at"])
    best = best_queried(log["versions"], log["started_at"], log["max_minutes"])
    if best and best["response"]["flagged"] is False:
        reason = "unflagged"
    elif elapsed >= log["max_minutes"]:
        reason = "time limit reached"
    elif log["requests_used"] >= log["max_requests"]:
        reason = "request budget used up"
    elif args.reason:
        reason = args.reason
    else:
        sys.exit("Still flagged and time remains. Keep going, or stop early with --reason \"...\" (it is reported).")
    _, _, versions, _, final = word_paths(pid)
    chosen = best["version"] if best else "v000"
    shutil.copy(versions / f"{chosen}.txt", final)
    unqueried = sum(1 for v in log["versions"] if not v.get("queried") and v["version"] != "v000")
    log.update(finished_at=now().isoformat(), final_version=chosen, stop_reason=reason,
               minutes_used=round(min(elapsed, log["max_minutes"]), 1), unqueried_versions=unqueried,
               final_response=best["response"] if best else None)
    save_wlog(pid, log)
    print(f"Finished {pid}: kept {chosen} "
          f"({'flagged=' + str(best['response']['flagged']) + ', score ' + str(best['response']['score']) if best else 'no queried version: still the watermarked text'}). "
          f"Stop reason: {reason}. Requests used {log['requests_used']}/{log['max_requests']}.")
    if unqueried:
        print(f"{unqueried} version(s) were never queried, so the attacker could not know their result; they are not used.")


# ------------------------------------------------------------------ character tests

def cmd_chartests(args):
    elig = eligibility()
    run = load_run()
    b = budgets()
    todo = [args.passage_id] if args.passage_id else [p for p, e in elig.items() if e["eligible"] == "yes"]
    for pid in todo:
        require_eligible(pid)
        out_dir = CHAR_DIR / pid
        if (out_dir / "log.json").exists():
            print(f"  {pid:32s} already done")
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        client, wait = run.attacker_view(ACCOUNT_CHAR)
        budget = Budget(b["per_passage_requests"])
        sim_start = run.now()
        results = run_character_tests(client, wait, watermarked_text(pid), budget)
        record = {"passage_id": pid, "requests_used": budget.used, "simulated_wait_seconds": budget.waited_seconds,
                  "simulated_seconds": run.now() - sim_start, "tests": {}}
        wm_tokens = tokenize(watermarked_text(pid))
        for name in CHAR_TESTS:
            res = results[name]
            (out_dir / f"{name}.txt").write_text(res["output"], encoding="utf-8")
            hidden = run.hidden_score(res["output"])
            record["tests"][name] = {
                "prediction": res["prediction"], "queries": res["queries"],
                "response": res["response"], "unflagged": res["success_candidate"],
                "changed_words_vs_watermarked": changed_words(wm_tokens, tokenize(res["output"])),
                "exact": hidden, "steps": res.get("steps", []),
            }
        (out_dir / "log.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        summary = ", ".join(f"{n}: {'UNFLAGGED' if record['tests'][n]['unflagged'] else 'still flagged'}" for n in CHAR_TESTS)
        print(f"  {pid:32s} {summary}   ({budget.used} requests)")
    print("Outputs are in", CHAR_DIR.relative_to(REPO_ROOT))


# ------------------------------------------------------------------ reviews and report

def outputs_needing_review() -> list[tuple[str, str, str, Path]]:
    """(passage, variant, editor, output file) for every UNFLAGGED output.
    Still-flagged outputs already failed, so they need no review."""
    out = []
    for pid, e in eligibility().items():
        if e["eligible"] != "yes":
            continue
        wp = word_paths(pid)
        if wp[4].exists():
            log = json.loads(wp[3].read_text(encoding="utf-8"))
            if (log.get("final_response") or {}).get("flagged") is False:
                out.append((pid, "word_substitution", log["editor"], wp[4]))
        cl = CHAR_DIR / pid / "log.json"
        if cl.exists():
            rec = json.loads(cl.read_text(encoding="utf-8"))
            for name in CHAR_TESTS:
                if rec["tests"][name]["unflagged"]:
                    out.append((pid, name, "automated", CHAR_DIR / pid / f"{name}.txt"))
    return out


def cmd_packets(args):
    reviews = read_csv(REVIEWS)
    have = {(r["passage_id"], r["variant"]) for r in reviews}
    PACKETS.mkdir(parents=True, exist_ok=True)
    items = outputs_needing_review()
    for pid, variant, editor, path in items:
        orig, wm, edited = original_text(pid).strip(), watermarked_text(pid).strip(), path.read_text(encoding="utf-8").strip()
        (PACKETS / f"{pid}__{variant}.md").write_text(
            f"# Attack 1 quality check: {pid} ({variant.replace('_', ' ')})\n\n"
            f"Editor: {editor}. **You must not be the editor.** Do not look at scores or results before recording "
            f"your answers in `{REVIEWS.relative_to(REPO_ROOT).as_posix()}`.\n\n"
            "Removal only counts if the edited version passes against **both** texts below. Answer yes only if both hold:\n\n"
            "1. **Meaning preserved?** Does the edited version keep the main meaning of the watermarked version AND of the original?\n"
            "2. **Readable?** Is the edited version readable prose?\n\n---\n\n"
            f"## Edited version (read this first, on its own)\n\n{edited}\n\n---\n\n## Watermarked version\n\n{wm}\n\n---\n\n"
            f"## Original version\n\n{orig}\n\n---\n\n## Word diff, watermarked to edited\n\n{word_diff(tokenize(wm), tokenize(edited))}\n",
            encoding="utf-8")
        if (pid, variant) not in have:
            reviews.append({"passage_id": pid, "variant": variant, "editor": editor})
    write_csv(REVIEWS, reviews, REVIEW_FIELDS)
    print(f"Wrote {len(items)} packets to {PACKETS.relative_to(REPO_ROOT)} (unflagged outputs only; flagged ones already failed).")
    print(f"Reviewer fills {REVIEWS.relative_to(REPO_ROOT)}: reviewer, meaning_preserved, readable (yes/no), notes, reviewed_at.")
    print("For automated character tests (editor 'automated'), any teammate may review.")


def _quality(reviews: dict, pid: str, variant: str) -> str:
    r = reviews.get((pid, variant))
    if r is None:
        return "not reviewed"
    status, _ = review_status(dict(r))
    return status


def cmd_report(args):
    elig = eligibility()
    reviews = {(r["passage_id"], r["variant"]): r for r in read_csv(REVIEWS)}
    rows, problems = [], []
    eligible_ids = [p for p, e in elig.items() if e["eligible"] == "yes"]
    for pid in eligible_ids:
        e = elig[pid]
        base = {"id": pid, "start_score": e["service_score"], "margin_words": e["margin_words"]}
        wp = word_paths(pid)
        if wp[4].exists():
            log = json.loads(wp[3].read_text(encoding="utf-8"))
            fr = log.get("final_response") or {}
            unflagged = fr.get("flagged") is False
            q = _quality(reviews, pid, "word_substitution") if unflagged else "n/a (still flagged)"
            rows.append(dict(base, variant="word_substitution", editor=log["editor"], final_score=fr.get("score", ""),
                             unflagged=unflagged, requests=log["requests_used"], minutes=log.get("minutes_used"),
                             simulated_wait_s=log["simulated_wait_seconds"],
                             changed_words=changed_words(tokenize(watermarked_text(pid)), tokenize(wp[4].read_text(encoding="utf-8"))),
                             quality=q, success=unflagged and q == "usable", stop_reason=log["stop_reason"]))
            if unflagged and q in ("not reviewed", "invalid review"):
                problems.append(f"{pid} word substitution: {q}")
        else:
            rows.append(dict(base, variant="word_substitution", success=False,
                             stop_reason="not finished" if wp[3].exists() else "not attempted"))
            problems.append(f"{pid} word substitution: {'not finished' if wp[3].exists() else 'not attempted'}")
        cl = CHAR_DIR / pid / "log.json"
        if cl.exists():
            rec = json.loads(cl.read_text(encoding="utf-8"))
            for name in CHAR_TESTS:
                t = rec["tests"][name]
                q = _quality(reviews, pid, name) if t["unflagged"] else "n/a (still flagged)"
                rows.append(dict(base, variant=name, editor="automated", final_score=(t["response"] or {}).get("score", ""),
                                 unflagged=t["unflagged"], requests=t["queries"], changed_words=t["changed_words_vs_watermarked"],
                                 quality=q, success=t["unflagged"] and q == "usable"))
                if t["unflagged"] and q in ("not reviewed", "invalid review"):
                    problems.append(f"{pid} {name}: {q}")
        else:
            problems.append(f"{pid} character tests: not run")

    fields = ["id", "variant", "editor", "start_score", "margin_words", "final_score", "unflagged", "changed_words",
              "requests", "minutes", "simulated_wait_s", "quality", "success", "stop_reason"]
    write_csv(RUN_DIR / "attempts.csv", rows, fields)

    n = len(eligible_ids)
    def rate(k):
        return f"{k}/{n} ({100 * k / n:.0f}%)" if n else "not applicable"
    variant_rows = []
    for v in ("word_substitution",) + CHAR_TESTS:
        vs = [r for r in rows if r["variant"] == v]
        variant_rows.append((v, sum(bool(r.get("unflagged")) for r in vs), sum(bool(r.get("success")) for r in vs),
                             sum(int(r.get("requests") or 0) for r in vs)))
    any_char = sum(any(r.get("success") for r in rows if r["id"] == p and r["variant"] in CHAR_TESTS) for p in eligible_ids)
    char_requests = sum(int(r.get("requests") or 0) for r in rows if r["variant"] in CHAR_TESTS)
    char_sim = sum(json.loads((CHAR_DIR / p / "log.json").read_text(encoding="utf-8"))["simulated_seconds"]
                   for p in eligible_ids if (CHAR_DIR / p / "log.json").exists())
    word_rows = [r for r in rows if r["variant"] == "word_substitution" and r.get("minutes") is not None]
    word_minutes = sum(float(r["minutes"]) for r in word_rows)
    word_wait = sum(float(r.get("simulated_wait_s") or 0) for r in word_rows)
    totals = {"eligible": n, "excluded": {p: e["note"] for p, e in elig.items() if e["eligible"] != "yes"},
              "variants": {v: {"unflagged": u, "successes": s, "requests": q} for v, u, s, q in variant_rows},
              "character_overall": {"successes": any_char, "requests": char_requests, "simulated_seconds": char_sim},
              "word_substitution_time": {"editing_minutes": round(word_minutes, 1), "rate_limit_wait_seconds": word_wait}}
    (RUN_DIR / "totals.json").write_text(json.dumps(totals, indent=2) + "\n", encoding="utf-8")

    L = ["# Attack 1: removal with detector queries", "",
         f"Service: score mode (3 digits), rate limit 20 requests per minute. Budgets: word substitution 15 minutes and "
         f"100 requests per passage; the three character tests share one 100-request budget per passage.", "",
         f"Eligible watermarked outputs: {n}. Excluded: "
         + (", ".join(f"{p} ({why})" for p, why in totals["excluded"].items()) or "none"), "",
         "| Variant | Unflagged | Successes (unflagged and usable) | Requests (total) |", "|---|---|---|---|"]
    for v, u, s, q in variant_rows:
        L.append(f"| {v.replace('_', ' ')} | {u}/{n} | {rate(s)} | {q} |")
    L.append(f"| **character changes overall** (any of the three) | | {rate(any_char)} | {char_requests} |")
    L += ["", f"Time: word substitution used {word_minutes:.1f} editing minutes in total "
              f"(plus {word_wait:.0f} simulated seconds waiting out rate limits); the automated character tests took "
              f"{char_sim:.0f} simulated seconds in total (1 second per request plus rate-limit waits). "
              "Request counts include requests rejected by the rate limit."]
    L += ["", "| Passage | Variant | Start | Margin (green words) | Final | Unflagged | Changed words | Requests | Minutes | Quality | Success |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['id']} | {r['variant'].replace('_', ' ')} | {r['start_score']} | {r['margin_words']} | {r.get('final_score', '')} | "
                 f"{r.get('unflagged', '')} | {r.get('changed_words', '')} | {r.get('requests', '')} | {r.get('minutes', '') or ''} | "
                 f"{r.get('quality', '')} | {r.get('success', '')} |")
    if problems:
        L += ["", "## Problems to fix before reporting", ""] + [f"- {p}" for p in problems]
    text = "\n".join(L) + "\n"
    (RUN_DIR / "summary.md").write_text(text, encoding="utf-8")
    print(text)
    print(f"Saved {(RUN_DIR / 'summary.md').relative_to(REPO_ROOT)}, attempts.csv and totals.json")


def cmd_status(args):
    for pid, e in eligibility().items():
        if e["eligible"] != "yes":
            print(f"  {pid:32s} excluded ({e['note']})")
            continue
        wp = word_paths(pid)
        word = "done" if wp[4].exists() else ("in progress" if wp[3].exists() else "not started")
        char = "done" if (CHAR_DIR / pid / "log.json").exists() else "not run"
        print(f"  {pid:32s} word substitution: {word:12s} character tests: {char:8s} (M1 editor: {e['m1_editor']})")


def main():
    ap = argparse.ArgumentParser(prog="python -m experiments.attack1", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup"); s.add_argument("--force", action="store_true", help=argparse.SUPPRESS)
    s = sub.add_parser("start"); s.add_argument("passage_id"); s.add_argument("--editor", required=True)
    s = sub.add_parser("query"); s.add_argument("passage_id")
    s = sub.add_parser("probe"); s.add_argument("passage_id"); s.add_argument("words", nargs="+")
    s = sub.add_parser("finish"); s.add_argument("passage_id"); s.add_argument("--reason")
    s = sub.add_parser("chartests"); s.add_argument("passage_id", nargs="?")
    sub.add_parser("packets"); sub.add_parser("report"); sub.add_parser("status")
    args = ap.parse_args()
    {"setup": cmd_setup, "start": cmd_start, "query": cmd_query, "probe": cmd_probe, "finish": cmd_finish,
     "chartests": cmd_chartests, "packets": cmd_packets, "report": cmd_report, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    main()