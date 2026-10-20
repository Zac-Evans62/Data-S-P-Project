"""Watermark one passage by hand, with timing, versions and a log.

Workflow for an editor:

    python scripts/wm_session.py start  <passage_id> --editor "Alex"
    # edit data/watermarked/<passage_id>/working.txt in any text editor
    python scripts/wm_session.py check  <passage_id>     # repeat as you edit
    python scripts/wm_session.py finish <passage_id>

`start` copies the original into working.txt and starts the clock.
`check` saves a new version if working.txt changed, prints the score,
        time used, the red words (most frequent first) and any GREEN
        synonyms for them from data/synonyms.tsv.
`finish` applies the stopping rule, keeps the BEST-scoring version as
        final.txt (spec: keep the best output even if it misses the target)
        and records why you stopped.

Stopping rule: stop when the green fraction reaches the target, or when
`stopping_rule_max_minutes` have passed, whichever comes first.

Calibration passages: you may pass --target while experimenting (settings
not frozen yet). Evaluation passages: settings must be frozen; the frozen
target and time limit are used and cannot be overridden.

Never show the reviewer the output of this script.
"""
import _bootstrap  # noqa: F401

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction

from wmark.config import REPO_ROOT, SYNONYMS_PATH, WATERMARKED_DIR, load_key, load_settings
from wmark.detector import GREEN, score_tokens, word_color
from wmark.manifest import read_manifest
from wmark.metrics import changed_words
from wmark.textproc import normalize_word, tokenize


def now():
    return datetime.now(timezone.utc)


def load_synonyms() -> dict[str, list[str]]:
    """data/synonyms.tsv: word<TAB>syn1, syn2, ...  (# comments allowed)."""
    syn = {}
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


def passage_row(pid):
    for r in read_manifest():
        if r["id"] == pid:
            if r["collection"] != "watermark":
                sys.exit(f"{pid} is not a watermark passage (collection={r['collection']!r}).")
            return r
    sys.exit(f"No passage {pid} in the manifest.")


def paths(pid):
    d = WATERMARKED_DIR / pid
    return d, d / "working.txt", d / "versions", d / "log.json", d / "final.txt"


def load_log(pid):
    _, _, _, log_path, _ = paths(pid)
    if not log_path.exists():
        sys.exit(f"No session for {pid}. Run: python scripts/wm_session.py start {pid} --editor NAME")
    return json.loads(log_path.read_text(encoding="utf-8"))


def save_log(pid, log):
    _, _, _, log_path, _ = paths(pid)
    log_path.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")


def cmd_start(args):
    settings = load_settings()
    row = passage_row(args.passage_id)
    d, working, versions, log_path, _ = paths(args.passage_id)
    if log_path.exists() and not args.restart:
        sys.exit(f"Session for {args.passage_id} already exists. Use --restart to archive it and start over (calibration only).")

    if row["set"] == "evaluation":
        if not settings.get("frozen"):
            sys.exit("Evaluation passages can only be watermarked after settings are frozen.")
        if args.target or args.restart:
            sys.exit("Evaluation passages use the frozen target and cannot be restarted.")
        target = settings["watermark_target"]
    else:
        target = args.target or settings.get("watermark_target")
        if target is None:
            sys.exit("No watermark_target in settings yet; pass --target 0.70 for practice runs.")

    if d.exists():  # keep earlier practice attempts (spec: save each version and its settings)
        n = 1
        while (WATERMARKED_DIR / "_previous_attempts" / f"{args.passage_id}_attempt{n}").exists():
            n += 1
        dest = WATERMARKED_DIR / "_previous_attempts" / f"{args.passage_id}_attempt{n}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(d), str(dest))
        print(f"Previous attempt archived to {dest.relative_to(REPO_ROOT)}")
    versions.mkdir(parents=True)
    original = (REPO_ROOT / row["file"]).read_text(encoding="utf-8")
    working.write_text(original, encoding="utf-8")
    shutil.copy(working, versions / "v000.txt")

    key = load_key(settings)
    r = score_tokens(tokenize(original), key)
    log = {
        "passage_id": args.passage_id,
        "set": row["set"],
        "editor": args.editor,
        "target": str(target),
        "max_minutes": settings["stopping_rule_max_minutes"],
        "settings_frozen": bool(settings.get("frozen")),
        "started_at": now().isoformat(),
        "versions": [{"version": "v000", "at": now().isoformat(), "green": r.green, "total": r.total, "score": r.score}],
        "finished_at": None,
        "stop_reason": None,
        "final_version": None,
    }
    save_log(args.passage_id, log)
    print(f"Started {args.passage_id}. Original score {r.score:.4f}, target {target}.")
    print(f"Edit: {working.relative_to(REPO_ROOT)}   then run: python scripts/wm_session.py check {args.passage_id}")


def cmd_check(args):
    settings = load_settings()
    key = load_key(settings)
    log = load_log(args.passage_id)
    if log["finished_at"]:
        sys.exit("Session already finished.")
    _, working, versions, _, _ = paths(args.passage_id)
    text = working.read_text(encoding="utf-8")
    last = versions / f"{log['versions'][-1]['version']}.txt"
    tokens = tokenize(text)
    r = score_tokens(tokens, key)

    if text != last.read_text(encoding="utf-8"):
        v = f"v{len(log['versions']):03d}"
        shutil.copy(working, versions / f"{v}.txt")
        log["versions"].append({"version": v, "at": now().isoformat(), "green": r.green, "total": r.total, "score": r.score})
        save_log(args.passage_id, log)
        saved = f"saved as {v}"
    else:
        saved = "no change since last version"

    elapsed = (now() - datetime.fromisoformat(log["started_at"])).total_seconds() / 60
    target = Fraction(log["target"])
    original_tokens = tokenize((versions / "v000.txt").read_text(encoding="utf-8"))
    print(f"score {r.score:.4f} ({r.green}/{r.total})   target {log['target']}   "
          f"elapsed {elapsed:.1f}/{log['max_minutes']} min   changed words {changed_words(original_tokens, tokens)}   [{saved}]")
    if r.fraction >= target:
        print(">> Target reached. Stopping rule says: stop now and run `finish`.")
    if elapsed >= log["max_minutes"]:
        print(">> Time limit reached. Stopping rule says: stop now and run `finish`.")

    syn = load_synonyms()
    red = [(w, n) for w, n in Counter(tokens).most_common() if word_color(w, key) != GREEN]
    print(f"\nRed words ({len(red)} distinct), most frequent first:")
    for w, n in red[: args.top]:
        greens = []
        for s in syn.get(w, []):
            try:
                if word_color(normalize_word(s), key) == GREEN:
                    greens.append(s)
            except ValueError:  # multi-word synonym: check every word
                if all(word_color(t, key) == GREEN for t in tokenize(s)):
                    greens.append(s)
        hint = f"  green synonyms: {', '.join(greens)}" if greens else ""
        print(f"  {n:3d}  {w}{hint}")
    if len(red) > args.top:
        print(f"  ... {len(red) - args.top} more")
    print("\nTip: check a candidate replacement with: echo WORD | python scripts/score.py - --colors")


def cmd_finish(args):
    log = load_log(args.passage_id)
    if log["finished_at"]:
        sys.exit("Session already finished.")
    # make sure the latest edit is captured
    _, working, versions, _, final = paths(args.passage_id)
    if working.read_text(encoding="utf-8") != (versions / f"{log['versions'][-1]['version']}.txt").read_text(encoding="utf-8"):
        sys.exit("working.txt has unsaved edits. Run `check` first.")

    target = Fraction(log["target"])
    best = max(log["versions"], key=lambda v: (Fraction(v["green"], v["total"]), -int(v["version"][1:])))
    elapsed = (now() - datetime.fromisoformat(log["started_at"])).total_seconds() / 60
    if Fraction(best["green"], best["total"]) >= target:
        reason = "target reached"
    elif elapsed >= log["max_minutes"]:
        reason = "time limit reached"
    elif args.reason:
        reason = args.reason
    else:
        sys.exit("Target not reached and time remains. Keep editing, or pass --reason \"...\" to stop early (it will be reported).")

    shutil.copy(versions / f"{best['version']}.txt", final)
    log.update(finished_at=now().isoformat(), stop_reason=reason, final_version=best["version"],
               minutes_used=round(elapsed, 1))
    save_log(args.passage_id, log)
    print(f"Finished {args.passage_id}: kept {best['version']} (score {best['score']:.4f}). Stop reason: {reason}.")
    print("Now hand it to a teammate for the quality check (scripts/make_review_packets.py).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start");  s.add_argument("passage_id"); s.add_argument("--editor", required=True)
    s.add_argument("--target", help="practice target for calibration passages, e.g. 0.70")
    s.add_argument("--restart", action="store_true", help="archive an existing calibration session and start over")
    c = sub.add_parser("check");  c.add_argument("passage_id"); c.add_argument("--top", type=int, default=25)
    f = sub.add_parser("finish"); f.add_argument("passage_id"); f.add_argument("--reason")
    args = ap.parse_args()
    {"start": cmd_start, "check": cmd_check, "finish": cmd_finish}[args.cmd](args)


if __name__ == "__main__":
    main()
