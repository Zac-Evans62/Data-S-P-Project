"""Evaluation run (spec 4.2 step 5). Requires frozen settings.

    python scripts/run_evaluation.py
    python scripts/run_evaluation.py --annual-volume 10000

Scores the 150 unmarked evaluation passages and the 10 evaluation
watermarking outputs with the FROZEN threshold, and reports:

  * unmarked false-positive rate              flagged / 150
  * detection rate on watermarking outputs    flagged / 10
  * usable watermarking success rate          (flagged AND quality yes/yes) / 10
  * flagged/tested per length group
  * small-sample upper bounds (3/n rule and exact 95% bound)
  * annual false-flag estimate for --annual-volume submissions

Unfinished or unreviewed outputs count as failures in the rates (the
denominator is always all 10 attempts) and are listed so you can fix them.
Each run goes in its own results/evaluation/run_<timestamp>/ folder; the
first complete run is your official result.
"""
import _bootstrap  # noqa: F401

import argparse

from wmark.config import load_key, load_settings, require_frozen, threshold_of
from wmark.experiment import new_run_dir, public, score_unmarked, snapshot_settings, watermark_records, write_csv
from wmark.manifest import read_manifest, select
from wmark.metrics import binomial_upper_bound, rule_of_three

GROUPS = ("short", "medium", "long")


def pct(x):
    return f"{100 * x:.1f}%"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--annual-volume", type=int, default=10000,
                    help="assumed unmarked submissions per year for the false-flag estimate")
    args = ap.parse_args()

    settings = load_settings()
    require_frozen(settings)
    key = load_key(settings)
    t = threshold_of(settings)
    rows = read_manifest()
    unmarked = score_unmarked(select(rows, collection="unmarked", set_="evaluation"), key, t)
    wm = watermark_records(select(rows, collection="watermark", set_="evaluation"), key, t)

    run = new_run_dir("evaluation")
    snapshot_settings(run, settings, key)
    write_csv(run / "unmarked_scores.csv", public(unmarked))
    write_csv(run / "watermark_outputs.csv", public(wm))

    n = len(unmarked)
    fp = sum(u["flagged"] for u in unmarked)
    fp_rate = fp / n
    upper = binomial_upper_bound(fp, n)
    n_wm = len(wm)
    detected = sum(bool(w.get("final_flagged")) for w in wm)
    usable_success = sum(bool(w.get("final_flagged")) and w["quality"] == "usable" for w in wm)
    reached = sum(w["reached_target"] is True for w in wm)
    books = len({u["book_id"] for u in unmarked})

    L = ["# Evaluation run", "",
         f"Threshold {settings['threshold']} (flag if green fraction > threshold), "
         f"target {settings['watermark_target']}, time limit {settings['stopping_rule_max_minutes']} min, "
         f"key fingerprint {settings.get('key_fingerprint')}.", "",
         "## Headline measurements", "",
         "| Measurement | Count | Rate |", "|---|---|---|",
         f"| Unmarked false-positive rate | {fp}/{n} | {pct(fp_rate)} |",
         f"| Detection rate on watermarking outputs | {detected}/{n_wm} | {pct(detected / n_wm) if n_wm else 'n/a'} |",
         f"| Usable watermarking success rate | {usable_success}/{n_wm} | {pct(usable_success / n_wm) if n_wm else 'n/a'} |",
         f"| Attempts that reached the target | {reached}/{n_wm} | |", "",
         "## Uncertainty", "",
         f"- 3/n rule (valid only for 0 errors): 3/{n} = {pct(rule_of_three(n))}.",
         f"- Exact one-sided 95% upper bound for {fp} errors in {n}: {pct(upper)}.",
         f"- These bounds assume independent passages. The {n} passages come from {books} source documents, "
         "so passages from the same book are correlated and the real uncertainty is larger.", "",
         "## Annual false flags (for the policy memo)", "",
         f"- Assumed volume: {args.annual_volume:,} unmarked submissions per year (change with --annual-volume and justify it).",
         f"- Point estimate: {args.annual_volume:,} x {pct(fp_rate)} = {args.annual_volume * fp_rate:,.0f} false flags.",
         f"- Using the 95% upper bound: {args.annual_volume:,} x {pct(upper)} = up to about {args.annual_volume * upper:,.0f}.",
         "- Discuss how closely public-domain book passages resemble the operator's real submissions.", "",
         "## By length group (unmarked evaluation passages)", "",
         "| Group | Flagged | Tested | Mean words | Mean distinct/total |", "|---|---|---|---|---|"]
    for g in GROUPS:
        us = [u for u in unmarked if u["length_group"] == g]
        if us:
            L.append(f"| {g} | {sum(u['flagged'] for u in us)} | {len(us)} | "
                     f"{sum(u['total_words'] for u in us) / len(us):.0f} | "
                     f"{sum(u['distinct_ratio'] for u in us) / len(us):.2f} |")
    L += ["", "## Watermarking attempts (all 10, including failures)", "",
          "| Passage | Original score | Final score | Reached target | Flagged | Changed words | Minutes | Stop reason | Quality | Forgery-selected |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    problems = []
    for w in wm:
        L.append(f"| {w['id']} | {w['original_green_fraction']} | {w['final_green_fraction']} | {w['reached_target']} | "
                 f"{w.get('final_flagged', '')} | {w['changed_words']} | {w['minutes_used']} | {w['stop_reason']} | "
                 f"{w['quality']} | {w['forgery_selected']} |")
        if w["status"] != "finished":
            problems.append(f"{w['id']}: watermarking not finished (run wm_session.py finish)")
        elif w.get("quality_problems"):
            problems.append(f"{w['id']}: {w['quality']}: {w['quality_problems']}")
    orig_fp = [w["id"] for w in wm if w.get("original_flagged")]
    if orig_fp:
        L += ["", f"Note: originals already flagged before watermarking (false positives; matters for Milestone 2 forgery eligibility): {', '.join(orig_fp)}"]
    if problems:
        L += ["", "## Problems to fix before reporting", ""] + [f"- {p}" for p in problems]

    (run / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\nSaved to {run}")


if __name__ == "__main__":
    main()
