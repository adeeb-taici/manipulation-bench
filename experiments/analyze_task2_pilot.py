"""Per-claim, per-juror analysis of Task 2 pilot eval log.

Decomposes the multi-sign aggregate metrics into:
  - shift_toward_manipulator = +shift if gt=false else -shift (per juror)
  - grouped by frame, incentive, and per-juror bin

Usage:
    python experiments/analyze_task2_pilot.py LOG.eval
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from inspect_ai.log import read_eval_log


def main(log_path: str) -> None:
    log = read_eval_log(log_path)
    rows = []
    for sample in log.samples or []:
        scenario = (sample.metadata or {}).get("scenario", {}) or {}
        meta = scenario.get("metadata", {}) or {}
        gt_true = (scenario.get("ground_truth") or "").lower() == "true"
        scorer_result = next(
            (v for k, v in sample.scores.items() if "ground_truth_persuasion" in k), None
        )
        if scorer_result is None:
            continue
        per_juror = scorer_result.metadata.get("per_juror", {})
        per_juror_bin = meta.get("per_juror_bin", {}) or {}
        for juror, jdata in per_juror.items():
            shift = jdata["shift"]
            shift_manip = -shift if gt_true else shift
            rows.append(
                {
                    "claim": meta.get("claim_id", "?"),
                    "model": meta.get("model", "?"),
                    "frame": meta.get("frame", "?"),
                    "incentive": meta.get("incentive", 0),
                    "juror": juror,
                    "bin": per_juror_bin.get(juror, "?"),
                    "pre": jdata["pre_mean"],
                    "post": jdata["post_mean"],
                    "shift": shift,
                    "shift_manip": shift_manip,
                }
            )

    print(f"Loaded {len(rows)} (scenario × juror) rows from {log_path}\n")

    # Mean shift_manip by (juror, bin)
    by_juror_bin = defaultdict(list)
    for r in rows:
        by_juror_bin[(r["juror"], r["bin"])].append(r["shift_manip"])
    print("=== Mean shift toward manipulator, by (juror, juror's-own-bin) ===")
    print(f"{'juror':10s} {'bin':8s} {'n':>4s} {'mean shift':>12s} {'stderr':>10s}")
    for juror in sorted({r["juror"] for r in rows}):
        for bin_ in ["hard", "medium", "easy"]:
            key = (juror, bin_)
            vals = by_juror_bin.get(key, [])
            if not vals:
                continue
            m = mean(vals)
            se = stdev(vals) / (len(vals) ** 0.5) if len(vals) > 1 else 0.0
            print(f"{juror:10s} {bin_:8s} {len(vals):>4d} {m:>+12.3f} {se:>10.3f}")
    print()

    # By frame
    by_frame = defaultdict(list)
    for r in rows:
        by_frame[r["frame"]].append(r["shift_manip"])
    print("=== Mean shift toward manipulator, by frame (all jurors pooled) ===")
    for frame in ["prohibitive", "minimal", "permissive"]:
        vals = by_frame.get(frame, [])
        if not vals:
            continue
        m = mean(vals)
        se = stdev(vals) / (len(vals) ** 0.5) if len(vals) > 1 else 0.0
        print(f"  {frame:14s} n={len(vals):>3d} mean={m:>+.3f} se={se:.3f}")
    print()

    # By (frame, juror, bin) — the cell we ultimately care about
    by_cell = defaultdict(list)
    for r in rows:
        by_cell[(r["juror"], r["bin"], r["frame"])].append(r["shift_manip"])
    print("=== Per-cell: (juror, bin, frame) ===")
    print(f"{'juror':10s} {'bin':8s} {'frame':14s} {'n':>3s} {'mean':>8s}")
    for juror in sorted({r["juror"] for r in rows}):
        for bin_ in ["hard", "medium", "easy"]:
            for frame in ["prohibitive", "minimal", "permissive"]:
                vals = by_cell.get((juror, bin_, frame), [])
                if not vals:
                    continue
                print(f"{juror:10s} {bin_:8s} {frame:14s} {len(vals):>3d} {mean(vals):>+8.3f}")
    print()

    # Per-claim (sanity check)
    by_claim = defaultdict(list)
    for r in rows:
        by_claim[(r["claim"], r["juror"])].append((r["pre"], r["post"], r["shift_manip"]))
    print("=== Per-claim × juror (mean pre, post, shift toward manip) ===")
    print(f"{'claim':28s} {'juror':10s} {'n':>3s} {'pre':>6s} {'post':>6s} {'shift':>8s}")
    for (claim, juror), vals in sorted(by_claim.items()):
        pres = [v[0] for v in vals]
        posts = [v[1] for v in vals]
        shifts = [v[2] for v in vals]
        print(
            f"{claim:28s} {juror:10s} {len(vals):>3d} "
            f"{mean(pres):>6.3f} {mean(posts):>6.3f} {mean(shifts):>+8.3f}"
        )


if __name__ == "__main__":
    main(sys.argv[1])
