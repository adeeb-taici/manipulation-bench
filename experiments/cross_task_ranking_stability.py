"""Cross-task model-ranking stability.

For each task, rank the 6 models by their permissive-frame manipulation
rate (the most-manipulable endpoint). Then compute pairwise Spearman ρ
across all 10 task pairs. Strong ρ = same model ordering across tasks
(stable trait); weak ρ = task-specific behaviour.

Outputs:
  paper/cross_task/figures/fig_ranking_stability.svg  (5×5 ρ matrix)
  paper/cross_task/ranking_stability.json
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log
from scipy.stats import spearmanr

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
        "log": "paper/task1_bargaining/eval_log.eval",
        "scorer": "bargaining_commit",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "axis_keys": {"frame": "frame"},
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
    },
    {
        "name": "T2 Debate",
        "log": "paper/task2_debate/eval_log.eval",
        "scorer": "ground_truth_persuasion",
        "metric_field": "manipulation_occurred",
        "scenario_model_key": "manipulator_model",
        "axis_keys": {"frame": "frame"},
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
    },
    {
        "name": "T3 Village",
        "log": "paper/task3_village/eval_log.eval",
        "scorer": "exploitation_rate",
        "metric_field": "agent_1",
        "scenario_model_key": "manipulator_model",
        "axis_keys": {"frame": "frame"},
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
    },
    {
        "name": "T4 Sales",
        "log": "paper/task4_sales/eval_log.eval",
        "scorer": "sales_classifier",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "axis_keys": {"frame": "frame"},
        "metadata_at_top": True,
        "model_remap": {"deepseek": "deepseek_v4", "gpt5": "gpt55"},
    },
    {
        "name": "T5 Committee",
        "log": "paper/task5_committee/eval_log.eval",
        "scorer": "initial_rating_bias",
        "metric_field": "initial_bias",
        "scenario_model_key": "interested_model_label",
        "axis_keys": {"frame": "frame"},
        "metadata_at_top": False,
        "model_remap": {"deepseek": "deepseek_v4", "gpt5": "gpt55"},
    },
]


def model_canonical(m, remap):
    if m in remap:
        return remap[m]
    return m


def display_canonical(m):
    return DISPLAY.get(m, m)


def load_permissive_rates(task):
    """Mean metric per model under frame=permissive (averaged over inc+diff)."""
    log = read_eval_log(task["log"])
    bucket = defaultdict(list)
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
        frame = md.get("frame")
        if frame != "permissive":
            continue
        model = md.get(task["scenario_model_key"])
        model = model_canonical(model, task.get("model_remap", {}))
        bucket[display_canonical(model)].append(float(metric))
    return {m: float(np.mean(v)) for m, v in bucket.items() if v}


def main():
    print("Loading permissive-frame rates per task ...")
    per_task = {}
    for task in TASKS:
        rates = load_permissive_rates(task)
        per_task[task["name"]] = rates
        print(f"  {task['name']}: {rates}")

    # Common models
    all_models = sorted(
        set.intersection(*(set(d.keys()) for d in per_task.values())),
        key=lambda m: list(DISPLAY.values()).index(m) if m in DISPLAY.values() else 999,
    )
    print(f"\nCommon models: {all_models}")

    task_names = list(per_task.keys())
    rho_mat = np.full((len(task_names), len(task_names)), np.nan)
    for i, ti in enumerate(task_names):
        for j, tj in enumerate(task_names):
            xs = [per_task[ti][m] for m in all_models]
            ys = [per_task[tj][m] for m in all_models]
            r, _ = spearmanr(xs, ys)
            rho_mat[i, j] = r

    # Heatmap
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(rho_mat, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(task_names)))
    ax.set_yticks(range(len(task_names)))
    ax.set_xticklabels(task_names, rotation=30, ha="right")
    ax.set_yticklabels(task_names)
    for i in range(len(task_names)):
        for j in range(len(task_names)):
            v = rho_mat[i, j]
            if not np.isnan(v):
                ax.text(
                    j,
                    i,
                    f"{v:.2f}",
                    ha="center",
                    va="center",
                    fontsize=10,
                    color="white" if abs(v) > 0.6 else "black",
                )
    fig.colorbar(im, ax=ax, label="Spearman ρ")
    ax.set_title(
        "Cross-task model-ranking stability (permissive-frame manipulation)\n"
        "ρ between per-task model orderings — same models top-ranked everywhere = high ρ",
        fontsize=11,
    )
    fig.tight_layout()
    out = Path("paper/cross_task/figures") / "fig_ranking_stability.svg"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nsaved {out}")

    # Save JSON
    rec = {
        "task_names": task_names,
        "models": all_models,
        "permissive_rates_per_task": {
            t: {m: round(per_task[t][m], 3) for m in all_models} for t in task_names
        },
        "rho_matrix": [
            [None if np.isnan(v) else round(float(v), 3) for v in row] for row in rho_mat
        ],
        "mean_offdiag_rho": round(
            float(
                np.nanmean(
                    [
                        rho_mat[i, j]
                        for i in range(len(task_names))
                        for j in range(len(task_names))
                        if i != j
                    ]
                )
            ),
            3,
        ),
    }
    json_path = Path("paper/cross_task/ranking_stability.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)
    print(f"wrote {json_path}")
    print(f"\nMean off-diagonal ρ = {rec['mean_offdiag_rho']}  (1.0 = identical rankings)")


if __name__ == "__main__":
    main()
