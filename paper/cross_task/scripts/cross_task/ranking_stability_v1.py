"""Cross-task model-ranking stability.

For each task, rank the 6 models by their permissive-frame manipulation
rate (the most-manipulable endpoint). Then compute pairwise Spearman ρ
across all 10 task pairs. Strong ρ = same model ordering across tasks
(stable trait); weak ρ = task-specific behaviour.

Outputs:
  paper/cross_task/figures/fig_ranking_stability.pdf  (5×5 ρ matrix)
  paper/cross_task/analysis/ranking_stability.json
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load import load_corpus

DISPLAY = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5": "GPT-5.5",
    "Gemini-3.1-Pro": "Gemini 3.1 Pro",
    "Grok-4": "Grok 4",
    "Llama-3.3-70B": "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
}

TASKS = [
    {"name": "T1 Bargaining", "short_name": "bargaining"},
    {"name": "T2 Debate",     "short_name": "debate"},
    {"name": "T3 Village",    "short_name": "village"},
    {"name": "T4 Sales",      "short_name": "sales"},
    {"name": "T5 Committee",  "short_name": "committee"},
]


def load_permissive_rates(task, full_df):
    """Mean metric per model under frame=permissive (averaged over inc+diff)."""
    df_task = full_df[
        (full_df["task"] == task["short_name"]) & (full_df["frame"] == "permissive")
    ]
    result = {}
    for model, group in df_task.groupby("model"):
        vals = group["metric"].dropna().tolist()
        if vals:
            display = DISPLAY.get(model, model)
            result[display] = float(np.mean(vals))
    return result


def main():
    print("Loading permissive-frame rates per task ...")
    full_df = load_corpus(verbose=False)
    # Preserves v1's mixed-metric definition: T2 ranks models by detection rate, not belief shift.
    full_df.loc[full_df["task"] == "debate", "metric"] = full_df.loc[full_df["task"] == "debate", "manipulation_occurred"]
    per_task = {}
    for task in TASKS:
        rates = load_permissive_rates(task, full_df)
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
    out = Path("paper/cross_task/figures") / "fig_ranking_stability.pdf"
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
    json_path = Path("paper/cross_task/analysis/ranking_stability.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)
    print(f"wrote {json_path}")
    print(f"\nMean off-diagonal rho = {rec['mean_offdiag_rho']}  (1.0 = identical rankings)")


if __name__ == "__main__":
    main()
