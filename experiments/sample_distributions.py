"""Per-task sample distribution figures.

For each task, produce a faceted figure: rows = models, cols = frames,
each panel a swarm/violin of the per-sample metric. This reveals whether
the headline mean hides bimodality (e.g., model "almost always honest"
vs "always lies on this scenario type") that a flat heatmap would miss.

Outputs:
  paper/task<N>/<dir>/figures/fig10_sample_distributions.png
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

DISPLAY = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5": "GPT-5.5",
    "Gemini-3.1-Pro": "Gemini 3.1 Pro",
    "Grok-4": "Grok 4",
    "Llama-3.3-70B": "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
    "claude": "Claude Opus 4.7",
    "gpt55": "GPT-5.5",
    "gemini": "Gemini 3.1 Pro",
    "grok": "Grok 4",
    "llama": "Llama 3.3 70B",
    "deepseek_v4": "DeepSeek V4 Pro",
}

TASKS = [
    {
        "name": "T1 Bargaining",
        "dir": "task1_bargaining",
        "log": "paper/task1_bargaining/eval_log.eval",
        "scorer": "bargaining_commit",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "axis_keys": {"frame": "frame"},
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
        "metric_label": "Lying rate",
        "ylim": (-0.05, 1.05),
    },
    {
        "name": "T2 Debate",
        "dir": "task2_debate",
        "log": "paper/task2_debate/eval_log.eval",
        "scorer": "ground_truth_persuasion",
        "metric_field": "manipulation_occurred",
        "scenario_model_key": "manipulator_model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "axis_keys": {"frame": "frame"},
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
        "metric_label": "Manipulation occurred (0/1)",
        "ylim": (-0.05, 1.05),
        "binary": True,
    },
    {
        "name": "T3 Village",
        "dir": "task3_village",
        "log": "paper/task3_village/eval_log.eval",
        "scorer": "exploitation_rate",
        "metric_field": "agent_1",
        "scenario_model_key": "manipulator_model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "axis_keys": {"frame": "frame"},
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
        "metric_label": "Exploitation rate",
        "ylim": (-0.05, 1.05),
    },
    {
        "name": "T4 Sales",
        "dir": "task4_sales",
        "log": "paper/task4_sales/eval_log.eval",
        "scorer": "sales_classifier",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "axis_keys": {"frame": "frame"},
        "metadata_at_top": True,
        "model_remap": {"deepseek": "deepseek_v4", "gpt5": "gpt55"},
        "metric_label": "Manipulation rate (per-scenario, 5 questions)",
        "ylim": (-0.05, 1.05),
    },
    {
        "name": "T5 Committee",
        "dir": "task5_committee",
        "log": "paper/task5_committee/eval_log.eval",
        "scorer": "initial_rating_bias",
        "metric_field": "initial_bias",
        "scenario_model_key": "interested_model_label",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "axis_keys": {"frame": "frame"},
        "metadata_at_top": False,
        "model_remap": {"deepseek": "deepseek_v4", "gpt5": "gpt55"},
        "metric_label": "Initial rating bias (favored − peers)",
        "ylim": (-25, 25),
    },
]


def model_order_key(m):
    return list(DISPLAY).index(m) if m in DISPLAY else 999


def load_rows(task):
    log = read_eval_log(task["log"])
    rows = []
    for s in log.samples or []:
        if s.error:
            continue
        if task.get("metadata_at_top"):
            md = s.metadata or {}
        else:
            md = (s.metadata or {}).get("scenario", {}).get("metadata", {})
        sc = (s.scores or {}).get(task["scorer"])
        if sc is None or not isinstance(sc.value, dict):
            continue
        v = sc.value
        if v.get("sample_failed"):
            continue
        metric = v.get(task["metric_field"])
        if metric is None:
            continue
        model = md.get(task["scenario_model_key"])
        model = task.get("model_remap", {}).get(model, model)
        if model is None:
            continue
        row = {"model": model, "metric": float(metric), "frame": md.get("frame")}
        rows.append(row)
    return rows


def violin(task):
    rows = load_rows(task)
    models = sorted({r["model"] for r in rows}, key=model_order_key)

    fig, axes = plt.subplots(1, len(models), figsize=(2.6 * len(models), 4.5), sharey=True)
    if len(models) == 1:
        axes = [axes]
    for mi, model in enumerate(models):
        ax = axes[mi]
        data_per_frame = []
        for f in task["frame_levels"]:
            vals = [r["metric"] for r in rows if r["model"] == model and r["frame"] == f]
            data_per_frame.append(vals)
        if any(data_per_frame):
            # Filter empty before violin (matplotlib chokes)
            positions = [i + 1 for i, d in enumerate(data_per_frame) if d]
            non_empty = [d for d in data_per_frame if d]
            if task.get("binary"):
                # For 0/1 binary, use jittered scatter + mean line
                for i, d in enumerate(data_per_frame):
                    if not d:
                        continue
                    xj = np.random.uniform(i + 0.85, i + 1.15, size=len(d))
                    ax.scatter(xj, d, alpha=0.05, s=3, color="C0")
                    ax.scatter(
                        [i + 1],
                        [np.mean(d)],
                        color="red",
                        s=40,
                        zorder=5,
                        edgecolor="black",
                        linewidth=0.7,
                    )
            else:
                vp = ax.violinplot(
                    non_empty,
                    positions=positions,
                    showmeans=True,
                    showmedians=False,
                    showextrema=False,
                    widths=0.85,
                )
                for body in vp["bodies"]:
                    body.set_alpha(0.5)
                    body.set_edgecolor("black")
                    body.set_linewidth(0.5)
        ax.set_xticks(range(1, len(task["frame_levels"]) + 1))
        ax.set_xticklabels(task["frame_levels"], rotation=40, ha="right", fontsize=7)
        ax.set_title(DISPLAY.get(model, model), fontsize=9)
        ax.set_ylim(*task["ylim"])
        ax.grid(axis="y", alpha=0.3)
        if mi == 0:
            ax.set_ylabel(task["metric_label"], fontsize=9)

    fig.suptitle(
        f"{task['name']} — per-sample metric distribution by frame, per model\n"
        f"(red dot = mean; for binary T2: jittered 0/1 dots + red mean)",
        fontsize=11,
        y=1.02,
    )
    fig.tight_layout()
    out = Path("paper") / task["dir"] / "figures" / "fig10_sample_distributions.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


def main():
    np.random.seed(42)
    for task in TASKS:
        print(f"\n=== {task['name']} ===")
        violin(task)


if __name__ == "__main__":
    main()
