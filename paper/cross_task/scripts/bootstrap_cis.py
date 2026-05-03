"""Compute bootstrap CIs for per-model per-axis slopes across all 5 tasks.

Reads the consolidated results CSV via load_corpus(), computes bootstrap CIs
at N=1000 resamples (per-task PREREG seeds), writes JSON per task, and
generates per-task slope+CI bar figures.

Outputs:
  paper/task<N>/<dir>/analysis/bootstrap_cis.json
  paper/task<N>/<dir>/figures/fig5_slopes_with_ci.pdf
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np
from bootstrap_slopes import bootstrap_aggregate_cis, bootstrap_slope_cis
from load import load_corpus


# Per-task config: analysis parameters only (data loading handled by load_corpus)
TASKS = [
    {
        "name": "T1 Bargaining",
        "short_name": "bargaining",
        "dir": "task1_bargaining",
        "axis_keys": {
            "frame": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
            "incentive": ("none", "moderate", "high"),
            "difficulty": ("low", "medium", "high"),
        },
        "seed": 20260422,
    },
    {
        "name": "T2 Debate",
        "short_name": "debate",
        "dir": "task2_debate",
        "axis_keys": {
            "frame": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
            "incentive": ("none", "moderate", "high"),
            "difficulty": ("low", "medium", "high"),
        },
        "seed": 20260423,
    },
    {
        "name": "T3 Village",
        "short_name": "village",
        "dir": "task3_village",
        "axis_keys": {
            "frame": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
            "incentive": ("none", "moderate", "high"),
            "difficulty": ("low", "medium", "high"),
        },
        "seed": 20260424,
    },
    {
        "name": "T4 Sales",
        "short_name": "sales",
        "dir": "task4_sales",
        "axis_keys": {
            "frame": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
            "incentive": ("none", "moderate", "high"),
            "difficulty": ("low", "medium", "high"),
        },
        "seed": 20260425,
    },
    {
        "name": "T5 Committee",
        "short_name": "committee",
        "dir": "task5_committee",
        "axis_keys": {
            "frame": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
            "incentive": ("none", "moderate", "high"),
            "difficulty": ("low", "medium", "high"),
        },
        "seed": 20260422,
    },
]

DISPLAY = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5": "GPT-5.5",
    "Gemini-3.1-Pro": "Gemini 3.1 Pro",
    "Grok-4": "Grok 4",
    "Llama-3.3-70B": "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
    # T4/T5 lowercase keys
    "claude": "Claude Opus 4.7",
    "gpt55": "GPT-5.5",
    "gemini": "Gemini 3.1 Pro",
    "grok": "Grok 4",
    "llama": "Llama 3.3 70B",
    "deepseek_v4": "DeepSeek V4 Pro",
}


def fig_slopes_with_ci(task: dict, ci_data: dict, out_path: Path) -> None:
    """3-panel bar chart: each axis with per-model slope + 95% CI error bars."""
    axis_names = list(task["axis_keys"].keys())
    models = sorted(ci_data.keys(), key=lambda m: list(DISPLAY).index(m) if m in DISPLAY else 999)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    colors = plt.cm.tab10(np.linspace(0, 1, len(models)))

    for ax, axis_name in zip(axes, axis_names):
        x = np.arange(len(models))
        points = []
        los = []
        his = []
        for m in models:
            d = ci_data.get(m, {}).get(axis_name, {})
            p = d.get("point", float("nan"))
            lo = d.get("lo", p)
            hi = d.get("hi", p)
            points.append(0 if math.isnan(p) else p)
            los.append(0 if math.isnan(lo) else lo)
            his.append(0 if math.isnan(hi) else hi)
        # Asymmetric error bars
        err_lo = [max(0, p - lo) for p, lo in zip(points, los)]
        err_hi = [max(0, hi - p) for p, hi in zip(points, his)]
        ax.bar(x, points, yerr=[err_lo, err_hi], color=colors, capsize=3, alpha=0.85)
        ax.axhline(0, color="black", linewidth=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels([DISPLAY.get(m, m) for m in models], rotation=30, ha="right", fontsize=8)
        ax.set_title(f"{axis_name} slope ± 95% bootstrap CI", fontsize=11)
        ax.set_ylabel("Slope")
        ax.grid(axis="y", alpha=0.3)

    fig.suptitle(f"{task['name']} — per-model axis slopes with bootstrap CIs (N=1000)", fontsize=13)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out_path}")


def main():
    full_df = load_corpus(verbose=False)
    for task in TASKS:
        print(f"\n=== {task['name']} ===")
        df_task = full_df[full_df["task"] == task["short_name"]].copy()
        rows = df_task.to_dict(orient="records")
        print(f"  loaded {len(rows)} rows")

        ci_data = bootstrap_slope_cis(
            rows=rows,
            metric_key="metric",
            model_key="model",
            axes_spec=task["axis_keys"],
            seed=task["seed"],
            n=1000,
        )
        agg_ci = bootstrap_aggregate_cis(
            rows=rows,
            metric_key="metric",
            axes_spec=task["axis_keys"],
            seed=task["seed"],
            n=1000,
        )

        out_dir = Path("paper") / task["dir"] / "analysis"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_json = out_dir / "bootstrap_cis.json"

        # JSON-safe
        def sanitize(x):
            if isinstance(x, dict):
                return {k: sanitize(v) for k, v in x.items()}
            if isinstance(x, (list, tuple)):
                return [sanitize(v) for v in x]
            if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
                return None
            return x

        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(
                sanitize({"per_model": ci_data, "aggregate": agg_ci, "task": task["name"]}),
                f,
                indent=2,
                default=str,
            )
        print(f"  wrote {out_json}")

        fig_path = Path("paper") / task["dir"] / "figures" / "fig5_slopes_with_ci.pdf"
        fig_path.parent.mkdir(parents=True, exist_ok=True)
        fig_slopes_with_ci(task, ci_data, fig_path)


if __name__ == "__main__":
    main()
