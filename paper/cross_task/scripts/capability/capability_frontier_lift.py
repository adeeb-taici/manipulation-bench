"""Generation lift: paired within-family deltas (current minus prev), bootstrapped.

For each (family, prev_model -> current_model) pair on the same axis cell,
compute the manipulation-rate delta. Bootstrap a 95% CI on the per-task mean
delta over cells.

Outputs:
  paper/cross_task/analysis/capability_frontier_lift.json
  paper/cross_task/figures/capability/capability_frontier_lift.png
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from _capability_io import ANALYSIS_DIR, FIG_DIR, TASKS, ensure_dirs, load_joined


GEN_PAIRS = [
    ("haiku35", "haiku45"),
    ("sonnet37", "sonnet46"),
    ("gpt41", "GPT-5.5"),
    ("gpt41mini", "gpt54mini"),
    ("gpt41nano", "gpt54nano"),
]
N_BOOT = 1000
RNG = np.random.default_rng(0)


def _cell_means(df, model):
    sub = df[df["model"] == model]
    if sub.empty:
        return None
    g = sub.groupby(["task", "frame", "incentive", "difficulty"], observed=True)["manipulation_metric"].mean()
    return g.reset_index()


def paired_deltas(df, prev_model, current_model):
    a = _cell_means(df, prev_model)
    b = _cell_means(df, current_model)
    if a is None or b is None:
        return None
    merged = a.merge(b, on=["task", "frame", "incentive", "difficulty"],
                     suffixes=("_prev", "_current"))
    merged["delta"] = merged["manipulation_metric_current"] - merged["manipulation_metric_prev"]
    return merged


def bootstrap_mean_delta(deltas: np.ndarray, n_boot: int = N_BOOT) -> tuple[float, float, float]:
    if len(deltas) == 0:
        return float("nan"), float("nan"), float("nan")
    mean = float(np.mean(deltas))
    boots = np.empty(n_boot)
    n = len(deltas)
    for i in range(n_boot):
        boots[i] = np.mean(RNG.choice(deltas, size=n, replace=True))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return mean, float(lo), float(hi)


def main() -> None:
    ensure_dirs()
    df = load_joined()

    summary = {"pairs": {}}
    for prev_model, current_model in GEN_PAIRS:
        merged = paired_deltas(df, prev_model, current_model)
        if merged is None or merged.empty:
            summary["pairs"][f"{prev_model}->{current_model}"] = {"skipped": True}
            continue
        per_task = {}
        for task in TASKS:
            sub = merged[merged["task"] == task]
            if sub.empty:
                continue
            mean_d, lo, hi = bootstrap_mean_delta(sub["delta"].to_numpy())
            per_task[task] = {
                "n_cells": int(len(sub)),
                "mean_delta": mean_d,
                "ci95": [lo, hi],
                "prev_mean": float(sub["manipulation_metric_prev"].mean()),
                "current_mean": float(sub["manipulation_metric_current"].mean()),
            }
        summary["pairs"][f"{prev_model}->{current_model}"] = per_task

    with open(ANALYSIS_DIR / "capability_frontier_lift.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    pairs = [k for k, v in summary["pairs"].items() if isinstance(v, dict) and "skipped" not in v]
    if pairs:
        fig, ax = plt.subplots(figsize=(13, 5.5), constrained_layout=True)
        width = 0.13
        x = np.arange(len(pairs))
        for i, task in enumerate(TASKS):
            means, los, his = [], [], []
            for p in pairs:
                d = summary["pairs"][p].get(task)
                if d is None:
                    means.append(np.nan); los.append(np.nan); his.append(np.nan)
                else:
                    means.append(d["mean_delta"])
                    los.append(d["ci95"][0])
                    his.append(d["ci95"][1])
            offset = (i - 2.5) * width
            ax.bar(x + offset, means, width, label=task)
            yerr_lo = [m - lo if not np.isnan(m) else 0 for m, lo in zip(means, los)]
            yerr_hi = [hi - m if not np.isnan(m) else 0 for m, hi in zip(means, his)]
            ax.errorbar(x + offset, means, yerr=[yerr_lo, yerr_hi], fmt="none",
                        ecolor="black", elinewidth=0.6, capsize=2)
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(pairs, rotation=20, ha="right", fontsize=9)
        ax.set_ylabel("Mean cell-paired delta (current - prev)")
        ax.set_title("Within-family generation lift: change in manipulation rate, paired by axis cell")
        ax.legend(fontsize=8, ncol=3)
        ax.grid(True, alpha=0.3, axis="y")
        fig.savefig(FIG_DIR / "capability_frontier_lift.png", dpi=150)
        plt.close(fig)

    print(f"Wrote {ANALYSIS_DIR / 'capability_frontier_lift.json'}")
    print(f"Wrote {FIG_DIR / 'capability_frontier_lift.png'}")
    print()
    for pair, per_task in summary["pairs"].items():
        if not isinstance(per_task, dict) or "skipped" in per_task:
            print(f"  {pair}: skipped"); continue
        print(f"  {pair}:")
        for task, d in per_task.items():
            sig = " *" if (d["ci95"][0] > 0 or d["ci95"][1] < 0) else ""
            print(f"    {task:12s}  delta={d['mean_delta']:+.3f}  "
                  f"95% CI=[{d['ci95'][0]:+.3f}, {d['ci95'][1]:+.3f}]  n_cells={d['n_cells']}{sig}")


if __name__ == "__main__":
    main()
