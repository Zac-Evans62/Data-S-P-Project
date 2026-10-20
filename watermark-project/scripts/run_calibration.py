"""Calibration run (spec 4.2 steps 1-3). Uses CALIBRATION passages only.

    python scripts/run_calibration.py
    python scripts/run_calibration.py --thresholds 0.55 0.58 0.60 0.62 0.65

Scores the 150 unmarked calibration passages and the 5 calibration
watermarking outputs (whatever is finished), then, for each candidate
threshold, counts:
  * unmarked passages that would be FLAGGED   (false positives)
  * watermarking outputs that would be UNFLAGGED (misses)

Writes results/calibration/run_<timestamp>/ with CSVs and summary.md.
Use the table to choose the threshold and the watermark target (strictly
above the threshold), put them in config/settings.json, then run
scripts/freeze_settings.py.
"""
import _bootstrap  # noqa: F401

import argparse
from fractions import Fraction

from wmark.config import load_key, load_settings
from wmark.experiment import new_run_dir, public, score_unmarked, snapshot_settings, watermark_records, write_csv
from wmark.manifest import read_manifest, select


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--thresholds", nargs="+", help="candidate thresholds (default: settings.json)")
    args = ap.parse_args()

    settings = load_settings()
    key = load_key(settings)
    thresholds = args.thresholds or settings["candidate_thresholds"]
    rows = read_manifest()
    unmarked_rows = select(rows, collection="unmarked", set_="calibration")
    wm_rows = select(rows, collection="watermark", set_="calibration")
    if not unmarked_rows:
        raise SystemExit("No calibration passages. Run scripts/split_data.py first.")

    run = new_run_dir("calibration")
    snapshot_settings(run, settings, key)
    unmarked = score_unmarked(unmarked_rows, key)
    wm = watermark_records(wm_rows, key)
    write_csv(run / "unmarked_scores.csv", public(unmarked))
    write_csv(run / "watermark_outputs.csv", public(wm))

    finished = [w for w in wm if w["_final_fraction"] is not None]
    sweep = []
    for t in thresholds:
        tf = Fraction(str(t))
        fp = sum(u["_fraction"] > tf for u in unmarked)
        miss = sum(w["_final_fraction"] <= tf for w in finished)
        sweep.append({"threshold": t, "unmarked_flagged": fp, "unmarked_tested": len(unmarked),
                      "fp_rate": round(fp / len(unmarked), 4),
                      "watermark_unflagged": miss, "watermark_tested": len(finished)})
    write_csv(run / "threshold_sweep.csv", sweep)

    scores = sorted(float(u["_fraction"]) for u in unmarked)
    lines = ["# Calibration run", "",
             f"Unmarked calibration passages: {len(unmarked)}; watermark outputs finished: {len(finished)}/{len(wm)}.", "",
             f"Unmarked green fraction: min {scores[0]:.3f}, median {scores[len(scores)//2]:.3f}, max {scores[-1]:.3f}.", "",
             "## Threshold sweep", "",
             "| Threshold | Unmarked flagged | Watermark outputs unflagged |", "|---|---|---|"]
    for s in sweep:
        lines.append(f"| {s['threshold']} | {s['unmarked_flagged']}/{s['unmarked_tested']} | {s['watermark_unflagged']}/{s['watermark_tested']} |")
    lines += ["", "## Watermarking practice", "",
              "| Passage | Original | Final | Target | Reached | Changed words | Minutes | Stop reason | Quality |",
              "|---|---|---|---|---|---|---|---|---|"]
    for w in wm:
        lines.append(f"| {w['id']} | {w['original_green_fraction']} | {w['final_green_fraction']} | {w.get('target', '')} | "
                     f"{w['reached_target']} | {w['changed_words']} | {w['minutes_used']} | {w['stop_reason']} | {w['quality']} |")
    (run / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved to {run}")


if __name__ == "__main__":
    main()
