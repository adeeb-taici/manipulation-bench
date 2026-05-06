"""Pick representative (incentive, difficulty) cells for the paraphrase-robustness sweep.

For each task, compute per-(incentive, difficulty) frame slopes (averaged across
the 6 models) and pick the cell whose magnitude is closest to the per-task
mean |frame slope| (Table 2). The chosen cell becomes the held-fixed slice
for the paraphrase sweep.

Output: paper/paraphrase_robustness/cell_selection.json
"""

from __future__ import annotations

import glob
import json
import math
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import read_eval_log

OUT = Path("paper/paraphrase_robustness/cell_selection.json")
OUT.parent.mkdir(parents=True, exist_ok=True)

FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
INCENTIVES = ("none", "moderate", "high")
DIFFICULTIES = ("low", "medium", "high")


def slope(values):
    valid = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if len(valid) < 2:
        return float("nan")
    n = len(values)
    xs = list(range(n))
    xbar = sum(xs) / n
    ybar = sum(values) / n
    num = sum((xs[i] - xbar) * (values[i] - ybar) for i in range(n))
    den = sum((xs[i] - xbar) ** 2 for i in range(n))
    return num / den if den else float("nan")


def safe_mean(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float("nan") if not xs else sum(xs) / len(xs)


def load_t3_rows():
    rows = []
    log = read_eval_log("paper/task3_village/eval_log.eval")
    by_id = {}
    for s in log.samples:
        if s.error:
            continue
        md = (s.metadata or {}).get("scenario", {}).get("metadata", {})
        er = (s.scores or {}).get("exploitation_rate")
        if er is None or not isinstance(er.value, dict):
            continue
        m_er = er.value.get("agent_1")
        if m_er is None:
            continue
        # Keep last write per id (post-amendment dedupe)
        by_id[s.id] = dict(
            model=md.get("manipulator_model"),
            frame=md.get("frame"),
            incentive=md.get("incentive"),
            difficulty=md.get("difficulty"),
            metric=m_er,
        )
    return list(by_id.values())


def load_t4_rows():
    log = read_eval_log("paper/task4_sales/eval_log.eval")
    by_id = {}
    for s in log.samples:
        if s.error:
            continue
        md = s.metadata or {}
        sc = (s.scores or {}).get("sales_classifier")
        if sc is None or not isinstance(sc.value, dict):
            continue
        rate = sc.value.get("manipulation_rate")
        if rate is None:
            continue
        model = md.get("model")
        if model == "gpt5":
            model = "gpt55"
        by_id[s.id] = dict(
            model=model,
            frame=md.get("frame"),
            incentive=md.get("incentive"),
            difficulty=md.get("difficulty"),
            metric=float(rate),
        )
    return list(by_id.values())


def per_cell_frame_slopes(rows):
    """For each (incentive, difficulty), compute the across-models average frame slope.

    Implementation: for each model and (i, d), compute the 5-frame mean vector,
    then slope over those 5 means. Average the resulting per-model slopes.
    """
    models = sorted({r["model"] for r in rows if r["model"]})
    out = {}
    for i in INCENTIVES:
        for d in DIFFICULTIES:
            per_model_slopes = []
            for m in models:
                frame_means = []
                for f in FRAMES:
                    vals = [
                        r["metric"]
                        for r in rows
                        if r["model"] == m
                        and r["frame"] == f
                        and r["incentive"] == i
                        and r["difficulty"] == d
                    ]
                    frame_means.append(safe_mean(vals))
                s = slope(frame_means)
                if not math.isnan(s):
                    per_model_slopes.append(s)
            avg = safe_mean(per_model_slopes)
            out[(i, d)] = dict(
                avg_frame_slope=avg,
                per_model_slopes={
                    m: per_model_slopes[idx] if idx < len(per_model_slopes) else None
                    for idx, m in enumerate(models)
                },
                n_models=len(per_model_slopes),
            )
    return out, models


def aggregate_frame_slope(rows):
    """Per-task aggregate frame slope: mean over models of the model's frame
    slope (which itself averages over incentive × difficulty)."""
    models = sorted({r["model"] for r in rows if r["model"]})
    per_model = {}
    for m in models:
        frame_means = []
        for f in FRAMES:
            vals = [r["metric"] for r in rows if r["model"] == m and r["frame"] == f]
            frame_means.append(safe_mean(vals))
        per_model[m] = slope(frame_means)
    abs_slopes = [abs(v) for v in per_model.values() if not math.isnan(v)]
    return dict(per_model=per_model, mean_abs=safe_mean(abs_slopes))


def pick_cell(per_cell, target_abs):
    best = None
    best_dist = float("inf")
    table = []
    for (i, d), info in per_cell.items():
        s = info["avg_frame_slope"]
        if math.isnan(s):
            continue
        dist = abs(abs(s) - target_abs)
        table.append(((i, d), abs(s), dist))
        if dist < best_dist:
            best_dist = dist
            best = (i, d)
    return best, sorted(table, key=lambda x: x[2])


def main():
    print("Loading T3 Village log...")
    t3 = load_t3_rows()
    print(f"  {len(t3)} rows")
    print("Loading T4 Sales log...")
    t4 = load_t4_rows()
    print(f"  {len(t4)} rows")

    out = {}

    for name, rows in [("T3_village", t3), ("T4_sales", t4)]:
        agg = aggregate_frame_slope(rows)
        per_cell, models = per_cell_frame_slopes(rows)
        target = agg["mean_abs"]
        best, table = pick_cell(per_cell, target)
        print(f"\n=== {name} ===")
        print(f"Per-task mean |frame slope|: {target:.4f}")
        print(f"Per-(incentive, difficulty) avg frame slope (|.|, dist to target):")
        for (i, d), abs_s, dist in table:
            mark = "  <-- chosen" if (i, d) == best else ""
            print(f"  ({i:8s}, {d:6s}): |slope|={abs_s:.4f}  dist={dist:.4f}{mark}")
        out[name] = dict(
            mean_abs_frame_slope=target,
            per_cell_table=[
                dict(incentive=i, difficulty=d, abs_avg_frame_slope=abs_s, dist=dist)
                for (i, d), abs_s, dist in table
            ],
            chosen=dict(incentive=best[0], difficulty=best[1]) if best else None,
            models_seen=models,
        )

    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
