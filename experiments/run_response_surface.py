"""Per-task response-surface figures: frame × incentive × difficulty per model.

For each task, produces one figure with a 3 × 6 grid:
    rows = difficulty levels (low/medium/high)
    columns = the 6 roster models

Each inner cell is a 5×3 heatmap of mean metric value: frame (rows) ×
incentive (columns).

This is the most information-dense per-task visualization — the full
manipulation response surface per model, side-by-side for cross-model
comparison within a task.

Outputs:
  paper/task<N>/<dir>/figures/fig7_response_surface.svg
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

TASKS = [
    {
        "name": "T1 Bargaining",
        "dir": "task1_bargaining",
        "log": "paper/task1_bargaining/eval_log.eval",
        "scorer": "bargaining_commit",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": (0, 80, 250),
        "incentive_labels": ("E=0", "E=80", "E=250"),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {
            "frame": "frame",
            "incentive": "expected_penalty",
            "difficulty": "difficulty",
        },
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
        "vmin": 0,
        "vmax": 1.0,
        "cmap": "Reds",
        "cbar_label": "Lying rate",
    },
    {
        "name": "T2 Debate",
        "dir": "task2_debate",
        "log": "paper/task2_debate/eval_log.eval",
        "scorer": "ground_truth_persuasion",
        "metric_field": "manipulation_occurred",
        "scenario_model_key": "manipulator_model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "incentive_labels": ("I=none", "I=mod", "I=high"),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {"frame": "frame", "incentive": "incentive", "difficulty": "difficulty"},
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
        "vmin": 0,
        "vmax": 1.0,
        "cmap": "Reds",
        "cbar_label": "Manipulation rate",
    },
    {
        "name": "T3 Village",
        "dir": "task3_village",
        "log": "paper/task3_village/eval_log.eval",
        "scorer": "exploitation_rate",
        "metric_field": "agent_1",
        "scenario_model_key": "manipulator_model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "incentive_labels": ("I=none", "I=mod", "I=high"),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {"frame": "frame", "incentive": "incentive", "difficulty": "difficulty"},
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
        "vmin": 0,
        "vmax": 1.0,
        "cmap": "Reds",
        "cbar_label": "Exploitation rate",
    },
    {
        "name": "T4 Sales",
        "dir": "task4_sales",
        "log": "paper/task4_sales/eval_log.eval",
        "scorer": "sales_classifier",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "incentive_labels": ("I=none", "I=mod", "I=high"),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {"frame": "frame", "incentive": "incentive", "difficulty": "difficulty"},
        "metadata_at_top": True,
        "model_remap": {"deepseek": "deepseek_v4", "gpt5": "gpt55"},
        "vmin": 0,
        "vmax": 1.0,
        "cmap": "Reds",
        "cbar_label": "Manipulation rate",
    },
    {
        "name": "T5 Committee",
        "dir": "task5_committee",
        "log": "paper/task5_committee/eval_log.eval",
        "scorer": "initial_rating_bias",
        "metric_field": "initial_bias",
        "scenario_model_key": "interested_model_label",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "incentive_labels": ("I=none", "I=mod", "I=high"),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {"frame": "frame", "incentive": "incentive", "difficulty": "difficulty"},
        "metadata_at_top": False,
        "model_remap": {"deepseek": "deepseek_v4", "gpt5": "gpt55"},
        "vmin": -20,
        "vmax": 20,
        "cmap": "RdBu_r",
        "cbar_label": "Initial rating bias (favored − peers)",
    },
]

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


def model_order_key(m: str) -> int:
    return list(DISPLAY).index(m) if m in DISPLAY else 999


def load_rows(task: dict) -> list[dict]:
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
        if model in task.get("model_remap", {}):
            model = task["model_remap"][model]
        row = {"model": model, "metric": float(metric)}
        for axis_name, sm_field in task["axis_keys"].items():
            row[axis_name] = md.get(sm_field)
        rows.append(row)
    return rows


def fig_response_surface(task: dict, rows: list[dict]) -> None:
    models = sorted({r["model"] for r in rows}, key=model_order_key)
    n_models = len(models)
    n_diff = len(task["difficulty_levels"])
    n_frame = len(task["frame_levels"])
    n_inc = len(task["incentive_levels"])

    fig, axes = plt.subplots(
        n_diff, n_models, figsize=(3.0 * n_models, 2.6 * n_diff), sharex=False, sharey=False
    )
    if n_diff == 1:
        axes = np.array([axes])
    if n_models == 1:
        axes = axes.reshape(-1, 1)

    im = None
    for di, diff in enumerate(task["difficulty_levels"]):
        for mi, model in enumerate(models):
            ax = axes[di, mi]
            grid = np.full((n_frame, n_inc), np.nan)
            for fi, f in enumerate(task["frame_levels"]):
                for ii, inc in enumerate(task["incentive_levels"]):
                    vals = [
                        r["metric"]
                        for r in rows
                        if r["model"] == model
                        and r["frame"] == f
                        and r["incentive"] == inc
                        and r["difficulty"] == diff
                    ]
                    if vals:
                        grid[fi, ii] = sum(vals) / len(vals)
            im = ax.imshow(
                grid, cmap=task["cmap"], vmin=task["vmin"], vmax=task["vmax"], aspect="auto"
            )
            # Annotate values
            for fi in range(n_frame):
                for ii in range(n_inc):
                    v = grid[fi, ii]
                    if not np.isnan(v):
                        if task["vmax"] <= 1.5:
                            text = f"{v:.2f}"
                            white_thresh = 0.55 * task["vmax"]
                        else:
                            text = f"{v:+.0f}"
                            white_thresh = task["vmax"] * 0.6
                        ax.text(
                            ii,
                            fi,
                            text,
                            ha="center",
                            va="center",
                            fontsize=7,
                            color="white" if abs(v) > white_thresh else "black",
                        )
            ax.set_xticks(range(n_inc))
            ax.set_xticklabels(task["incentive_labels"], fontsize=7)
            ax.set_yticks(range(n_frame))
            if mi == 0:
                ax.set_yticklabels(task["frame_levels"], fontsize=7)
                ax.set_ylabel(f"difficulty={diff}", fontsize=9, fontweight="bold")
            else:
                ax.set_yticklabels([])
            if di == 0:
                ax.set_title(DISPLAY.get(model, model), fontsize=9)

    fig.suptitle(
        f"{task['name']} — full response surface per model\n"
        f"Rows = difficulty; Columns = models. Each cell: frame (y) × incentive (x). Colour = mean {task['cbar_label']}.",
        fontsize=12,
        y=1.00,
    )
    if im is not None:
        fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.6, label=task["cbar_label"])
    out = Path("paper") / task["dir"] / "figures" / "fig7_response_surface.svg"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


def main():
    for task in TASKS:
        print(f"\n=== {task['name']} ===")
        rows = load_rows(task)
        print(f"  loaded {len(rows)} rows")
        fig_response_surface(task, rows)


if __name__ == "__main__":
    main()
