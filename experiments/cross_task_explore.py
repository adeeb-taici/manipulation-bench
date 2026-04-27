"""Exploratory cross-task figures beyond the per-task results.md set.

Generates a portfolio of cross-task pattern visualizations into
paper/cross_task/figures/. Some may not yield interesting findings;
keep what's useful and prune the rest.

Figures produced:
  fig_per_model_frame_curves.png   — 6×5 grid of per-model frame curves per task
  fig_model_similarity_matrix.png  — 6×6 pairwise Spearman ρ on 15-dim profiles
  fig_variance_decomposition.png   — per-task share of variance by axis
  fig_saturation_map.png           — per-model fraction of saturated cells per task
  fig_endpoint_range.png           — permissive−prohibitive range per model per task
  fig_model_ranking_stability.png  — per-model rank per task per axis
  fig_generation_contrast.png      — GPT-5 vs GPT-5.5, V3.2 vs V4 Pro side-by-side
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

OUT = Path("paper/cross_task/figures")
OUT.mkdir(parents=True, exist_ok=True)

# Task config: normalized to a common (model, frame, incentive, difficulty, metric_unit) view.
# For T5 (bias on [-20, 20]), we divide bias by 20 to normalize to [-1, 1].
TASKS = [
    {
        "name": "T1 Bargaining",
        "short": "T1",
        "log": "paper/task1_bargaining/eval_log.eval",
        "scorer": "bargaining_commit",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": (0, 80, 250),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {
            "frame": "frame",
            "incentive": "expected_penalty",
            "difficulty": "difficulty",
        },
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
        "metric_unit": "rate",
    },
    {
        "name": "T2 Debate",
        "short": "T2",
        "log": "paper/task2_debate/eval_log.eval",
        "scorer": "ground_truth_persuasion",
        "metric_field": "manipulation_occurred",
        "scenario_model_key": "manipulator_model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {"frame": "frame", "incentive": "incentive", "difficulty": "difficulty"},
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
        "metric_unit": "rate",
    },
    {
        "name": "T3 Village",
        "short": "T3",
        "log": "paper/task3_village/eval_log.eval",
        "scorer": "exploitation_rate",
        "metric_field": "agent_1",
        "scenario_model_key": "manipulator_model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {"frame": "frame", "incentive": "incentive", "difficulty": "difficulty"},
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
        "metric_unit": "rate",
    },
    {
        "name": "T4 Sales",
        "short": "T4",
        "log": "paper/task4_sales/eval_log.eval",
        "scorer": "sales_classifier",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {"frame": "frame", "incentive": "incentive", "difficulty": "difficulty"},
        "metadata_at_top": True,
        "model_remap": {"deepseek": "deepseek_v4", "gpt5": "gpt55"},
        "metric_unit": "rate",
    },
    {
        "name": "T5 Committee",
        "short": "T5",
        "log": "paper/task5_committee/eval_log.eval",
        "scorer": "initial_rating_bias",
        "metric_field": "initial_bias",
        "scenario_model_key": "interested_model_label",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {"frame": "frame", "incentive": "incentive", "difficulty": "difficulty"},
        "metadata_at_top": False,
        "model_remap": {"deepseek": "deepseek_v4", "gpt5": "gpt55"},
        "metric_unit": "bias_0_20",  # normalize via /20 for cross-task comparisons
    },
]

# Canonical model labels (display names + ordering)
CANONICAL = ["claude", "gpt55", "gemini", "grok", "llama", "deepseek_v4"]
DISPLAY = {
    "claude": "Claude Opus 4.7",
    "gpt55": "GPT-5.5",
    "gemini": "Gemini 3.1 Pro",
    "grok": "Grok 4",
    "llama": "Llama 3.3 70B",
    "deepseek_v4": "DeepSeek V4 Pro",
}

# Map per-task internal model labels -> canonical
TASK_MODEL_MAP = {
    "Claude-Opus-4.7": "claude",
    "GPT-5.5": "gpt55",
    "Gemini-3.1-Pro": "gemini",
    "Grok-4": "grok",
    "Llama-3.3-70B": "llama",
    "DeepSeek-V4-Pro": "deepseek_v4",
    # T4/T5 lowercase
    "claude": "claude",
    "gpt55": "gpt55",
    "gemini": "gemini",
    "grok": "grok",
    "llama": "llama",
    "deepseek_v4": "deepseek_v4",
}


def load_task_rows(task: dict) -> list[dict]:
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
        # Normalize T5 bias to [-1, 1]
        if task["metric_unit"] == "bias_0_20":
            metric = metric / 20.0

        model = md.get(task["scenario_model_key"])
        if model in task.get("model_remap", {}):
            model = task["model_remap"][model]
        canonical = TASK_MODEL_MAP.get(model)
        if canonical is None:
            continue

        row = {"model": canonical, "metric": metric}
        for axis_name, sm_field in task["axis_keys"].items():
            row[axis_name] = md.get(sm_field)
        rows.append(row)
    return rows


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def _slope(values):
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


# ── Figure: per-model frame curves across all 5 tasks (6×5 grid) ──────────
def fig_per_model_frame_curves(all_task_rows: dict[str, list[dict]]) -> None:
    fig, axes = plt.subplots(6, 5, figsize=(18, 18), sharey=False)
    for row_i, model in enumerate(CANONICAL):
        for col_i, task in enumerate(TASKS):
            ax = axes[row_i, col_i]
            rows = [r for r in all_task_rows[task["name"]] if r["model"] == model]
            frame_means = []
            for f in task["frame_levels"]:
                vals = [r["metric"] for r in rows if r["frame"] == f]
                frame_means.append(_mean(vals))
            ax.plot(range(5), frame_means, marker="o", linewidth=1.6, color="#4C78A8")
            ax.fill_between(range(5), 0, frame_means, alpha=0.15, color="#4C78A8")
            ax.set_xticks(range(5))
            ax.set_xticklabels(["pr", "ps", "min", "sf", "pm"], fontsize=7)
            ax.grid(True, alpha=0.25)
            if row_i == 0:
                ax.set_title(task["short"], fontsize=10)
            if col_i == 0:
                ax.set_ylabel(DISPLAY[model], fontsize=8)
            ax.tick_params(axis="y", labelsize=7)

    fig.suptitle(
        "Per-model frame curves across 5 tasks (rows = models, cols = tasks)\nx-axis: prohibitive→pro_social→minimal→selfish→permissive. T5 normalized to [-1, 1].",
        fontsize=13,
        y=1.00,
    )
    fig.tight_layout()
    out = OUT / "fig_per_model_frame_curves.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


# ── Figure: model similarity (pairwise Spearman ρ on 15-dim profile) ──────
def fig_model_similarity_matrix(all_task_rows: dict[str, list[dict]]) -> None:
    """For each model, build a 15-dim signed-slope vector
    (5 tasks × {frame, incentive, difficulty}), then compute Spearman ρ
    between each pair of models."""
    profiles = {}
    for model in CANONICAL:
        vec = []
        for task in TASKS:
            rows = [r for r in all_task_rows[task["name"]] if r["model"] == model]
            for axis_name, levels in [
                ("frame", task["frame_levels"]),
                ("incentive", task["incentive_levels"]),
                ("difficulty", task["difficulty_levels"]),
            ]:
                level_means = [
                    _mean([r["metric"] for r in rows if r[axis_name] == lvl]) for lvl in levels
                ]
                vec.append(_slope(level_means))
        profiles[model] = vec

    # Pairwise Spearman ρ
    def rank(xs):
        sorted_idx = sorted(
            range(len(xs)),
            key=lambda i: (
                xs[i] if not (isinstance(xs[i], float) and math.isnan(xs[i])) else float("inf")
            ),
        )
        ranks = [0] * len(xs)
        for r, i in enumerate(sorted_idx):
            ranks[i] = r
        return ranks

    n = len(CANONICAL)
    M = np.full((n, n), np.nan)
    for i, mi in enumerate(CANONICAL):
        for j, mj in enumerate(CANONICAL):
            v1, v2 = profiles[mi], profiles[mj]
            both = [(a, b) for a, b in zip(v1, v2) if not math.isnan(a) and not math.isnan(b)]
            if len(both) < 3:
                continue
            r1 = rank([x[0] for x in both])
            r2 = rank([x[1] for x in both])
            mean1 = sum(r1) / len(r1)
            mean2 = sum(r2) / len(r2)
            num = sum((r1[k] - mean1) * (r2[k] - mean2) for k in range(len(both)))
            den1 = sum((r - mean1) ** 2 for r in r1) ** 0.5
            den2 = sum((r - mean2) ** 2 for r in r2) ** 0.5
            M[i, j] = num / (den1 * den2) if (den1 and den2) else float("nan")

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(M, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels([DISPLAY[m] for m in CANONICAL], rotation=30, ha="right", fontsize=9)
    ax.set_yticklabels([DISPLAY[m] for m in CANONICAL], fontsize=9)
    for i in range(n):
        for j in range(n):
            v = M[i, j]
            if not np.isnan(v):
                ax.text(
                    j,
                    i,
                    f"{v:.2f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if abs(v) > 0.5 else "black",
                )
    fig.colorbar(im, ax=ax, label="Spearman ρ on 15-dim profile vector")
    ax.set_title(
        "Cross-task per-model profile similarity\n(15-dim signed slope vector: 5 tasks × 3 axes)"
    )
    fig.tight_layout()
    out = OUT / "fig_model_similarity_matrix.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


# ── Figure: variance decomposition per task ───────────────────────────────
def fig_variance_decomposition(all_task_rows: dict[str, list[dict]]) -> None:
    """For each task, compute the fraction of total variance in metric
    explained by each axis (between-frame, between-incentive, between-difficulty).
    Within-cell variance is the residual."""
    fig, ax = plt.subplots(figsize=(11, 5))
    task_names = [t["short"] for t in TASKS]
    width = 0.25
    x = np.arange(len(task_names))
    components = {"frame": [], "incentive": [], "difficulty": []}
    for task in TASKS:
        rows = all_task_rows[task["name"]]
        if not rows:
            for c in components:
                components[c].append(0)
            continue
        all_metrics = [r["metric"] for r in rows if r["metric"] is not None]
        if not all_metrics:
            for c in components:
                components[c].append(0)
            continue
        grand_mean = sum(all_metrics) / len(all_metrics)
        total_ss = sum((m - grand_mean) ** 2 for m in all_metrics)

        for axis_name in ("frame", "incentive", "difficulty"):
            # Between-group SS for this axis
            by_level = defaultdict(list)
            for r in rows:
                if r[axis_name] is not None and r["metric"] is not None:
                    by_level[r[axis_name]].append(r["metric"])
            between_ss = sum(
                len(vs) * ((sum(vs) / len(vs)) - grand_mean) ** 2 for vs in by_level.values() if vs
            )
            frac = between_ss / total_ss if total_ss > 0 else 0
            components[axis_name].append(frac)

    colors = {"frame": "#4C78A8", "incentive": "#F58518", "difficulty": "#54A24B"}
    for i, axis in enumerate(["frame", "incentive", "difficulty"]):
        ax.bar(x + (i - 1) * width, components[axis], width, label=axis, color=colors[axis])

    ax.set_xticks(x)
    ax.set_xticklabels(task_names, fontsize=11)
    ax.set_ylabel("Fraction of total variance")
    ax.set_title(
        "Variance decomposition: per-axis between-group share of total variance, per task\n(η²-style; residual = within-cell variance + interaction effects)"
    )
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = OUT / "fig_variance_decomposition.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


# ── Figure: saturation map (% of cells ≥ 0.80 per model per task) ─────────
def fig_saturation_map(all_task_rows: dict[str, list[dict]]) -> None:
    """For each (model, task), compute fraction of (frame, incentive, difficulty)
    cells where mean metric ≥ 0.80. Saturation indicator. T5 normalized."""
    grid = np.zeros((len(CANONICAL), len(TASKS)))
    for col_i, task in enumerate(TASKS):
        rows = all_task_rows[task["name"]]
        for row_i, model in enumerate(CANONICAL):
            sub = [r for r in rows if r["model"] == model]
            cells_total = 0
            cells_saturated = 0
            for f in task["frame_levels"]:
                for i in task["incentive_levels"]:
                    for d in task["difficulty_levels"]:
                        vals = [
                            r["metric"]
                            for r in sub
                            if r["frame"] == f and r["incentive"] == i and r["difficulty"] == d
                        ]
                        if vals:
                            cells_total += 1
                            if (sum(vals) / len(vals)) >= 0.80:
                                cells_saturated += 1
            grid[row_i, col_i] = cells_saturated / cells_total if cells_total else 0

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(grid, cmap="Reds", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(TASKS)))
    ax.set_xticklabels([t["short"] for t in TASKS])
    ax.set_yticks(range(len(CANONICAL)))
    ax.set_yticklabels([DISPLAY[m] for m in CANONICAL])
    for i in range(len(CANONICAL)):
        for j in range(len(TASKS)):
            ax.text(
                j,
                i,
                f"{grid[i, j]:.0%}",
                ha="center",
                va="center",
                fontsize=9,
                color="white" if grid[i, j] > 0.4 else "black",
            )
    fig.colorbar(im, ax=ax, label="Fraction of cells with mean ≥ 0.80")
    ax.set_title(
        "Saturation map: per-model fraction of cells with manipulation ≥ 0.80\n(T5 bias normalized to [-1, 1])"
    )
    fig.tight_layout()
    out = OUT / "fig_saturation_map.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


# ── Figure: endpoint range (permissive − prohibitive) ─────────────────────
def fig_endpoint_range(all_task_rows: dict[str, list[dict]]) -> None:
    grid = np.full((len(CANONICAL), len(TASKS)), np.nan)
    for col_i, task in enumerate(TASKS):
        rows = all_task_rows[task["name"]]
        for row_i, model in enumerate(CANONICAL):
            sub = [r for r in rows if r["model"] == model]
            proh = _mean([r["metric"] for r in sub if r["frame"] == "prohibitive"])
            perm = _mean([r["metric"] for r in sub if r["frame"] == "permissive"])
            if not (math.isnan(proh) or math.isnan(perm)):
                grid[row_i, col_i] = perm - proh

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(grid, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(TASKS)))
    ax.set_xticklabels([t["short"] for t in TASKS])
    ax.set_yticks(range(len(CANONICAL)))
    ax.set_yticklabels([DISPLAY[m] for m in CANONICAL])
    for i in range(len(CANONICAL)):
        for j in range(len(TASKS)):
            v = grid[i, j]
            if not np.isnan(v):
                ax.text(
                    j,
                    i,
                    f"{v:+.2f}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white" if abs(v) > 0.5 else "black",
                )
    fig.colorbar(im, ax=ax, label="Permissive − Prohibitive (frame range)")
    ax.set_title(
        "Endpoint frame range per model per task\n(Larger = more frame-responsive at the endpoints)"
    )
    fig.tight_layout()
    out = OUT / "fig_endpoint_range.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


# ── Figure: model ranking stability (per-model rank per task per axis) ────
def fig_model_ranking_stability(all_task_rows: dict[str, list[dict]]) -> None:
    """For each (task, axis), rank the 6 models 0..5 by absolute slope.
    Plot per-model rank across the 15 (task × axis) combinations."""
    ranks_grid = np.full((len(CANONICAL), len(TASKS) * 3), np.nan)
    col_labels = []
    col_i = 0
    for task in TASKS:
        for axis_name in ("frame", "incentive", "difficulty"):
            levels = (
                task[f"{axis_name}_levels"]
                if axis_name in ("frame", "incentive", "difficulty")
                else None
            )
            if axis_name == "frame":
                levels = task["frame_levels"]
            elif axis_name == "incentive":
                levels = task["incentive_levels"]
            else:
                levels = task["difficulty_levels"]
            rows = all_task_rows[task["name"]]
            slopes = []
            for model in CANONICAL:
                sub = [r for r in rows if r["model"] == model]
                level_means = [
                    _mean([r["metric"] for r in sub if r[axis_name] == lvl]) for lvl in levels
                ]
                slopes.append(abs(_slope(level_means)))
            sorted_idx = sorted(
                range(len(slopes)), key=lambda i: slopes[i] if not math.isnan(slopes[i]) else -1
            )
            for r, i in enumerate(sorted_idx):
                ranks_grid[i, col_i] = r
            col_labels.append(f"{task['short']}-{axis_name[:4]}")
            col_i += 1

    fig, ax = plt.subplots(figsize=(13, 5))
    im = ax.imshow(ranks_grid, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(CANONICAL)))
    ax.set_yticklabels([DISPLAY[m] for m in CANONICAL])
    for i in range(len(CANONICAL)):
        for j in range(ranks_grid.shape[1]):
            v = ranks_grid[i, j]
            if not np.isnan(v):
                ax.text(
                    j,
                    i,
                    f"{int(v)}",
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="white" if v > 2.5 else "black",
                )
    fig.colorbar(im, ax=ax, label="Rank by |slope|: 0 = least sensitive, 5 = most sensitive")
    # Vertical separators between tasks
    for ti in range(1, len(TASKS)):
        ax.axvline(ti * 3 - 0.5, color="black", linewidth=0.8)
    ax.set_title(
        "Model rank stability across tasks × axes (15 combinations)\n(Same model in same column should yield same rank if sensitivity is intrinsic to model)"
    )
    fig.tight_layout()
    out = OUT / "fig_model_ranking_stability.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


# ── Figure: generation contrast (GPT-5 vs 5.5, V3.2 vs V4 Pro) ────────────
def fig_generation_contrast() -> None:
    """Show per-task per-axis the OLD vs NEW model frame-marginal means.
    Pulls original GPT-5 / V3.2 numbers from the historical dsv4 + gpt55 logs
    that have been archived (we still have the raw eval files)."""
    # Need to read OLD logs (pre-swap) and NEW logs (post-swap). For now, plot
    # frame curves for GPT-5 (original) vs GPT-5.5 (current) and V3.2 vs V4 Pro
    # from the per-task historical logs.

    # For this figure, just show frame curves: 4 panels (T1, T2, T3, T4) since
    # T5 needs different scale. Each panel: 4 lines (GPT-5 old, GPT-5.5 new,
    # V3.2 old, V4 Pro new).
    OLD_GPT5_FRAME = {
        "T1": [0.000, 0.497, 0.553, 0.611, 0.608],
        "T2": [0.413, 0.420, 0.326, 0.348, 0.348],
        "T3": [0.024, 0.167, 0.270, 0.587, 0.798],
        "T4": [0.511, 0.542, 0.542, 0.582, 0.609],
    }
    OLD_V32_FRAME = {
        "T1": [0.003, 0.203, 0.167, 0.200, 0.369],
        "T2": [0.217, 0.254, 0.159, 0.188, 0.152],
        "T3": [0.511, 0.628, 0.710, 0.603, 0.862],
        "T4": [0.044, 0.147, 0.222, 0.218, 0.227],
    }
    # New numbers come from the analysis scripts
    NEW_GPT55_FRAME = {
        "T1": [0.000, 0.404, 0.481, 0.609, 0.594],
        "T2": [0.262, 0.348, 0.268, 0.290, 0.341],
        "T3": [0.028, 0.228, 0.402, 0.586, 0.764],
        "T4": [0.031, 0.022, 0.027, 0.027, 0.027],
    }
    NEW_V4_FRAME = {
        "T1": [0.000, 0.328, 0.375, 0.444, 0.472],
        "T2": [0.268, 0.196, 0.217, 0.246, 0.232],
        "T3": [0.107, 0.149, 0.289, 0.252, 0.760],
        "T4": [0.156, 0.240, 0.356, 0.364, 0.404],
    }
    fig, axes = plt.subplots(1, 4, figsize=(18, 5))
    titles = {"T1": "T1 Bargaining", "T2": "T2 Debate", "T3": "T3 Village", "T4": "T4 Sales"}
    for ax, key in zip(axes, ["T1", "T2", "T3", "T4"]):
        x = range(5)
        ax.plot(
            x,
            OLD_GPT5_FRAME[key],
            marker="o",
            linewidth=2,
            label="GPT-5",
            color="#F58518",
            linestyle="--",
        )
        ax.plot(x, NEW_GPT55_FRAME[key], marker="o", linewidth=2, label="GPT-5.5", color="#F58518")
        ax.plot(
            x,
            OLD_V32_FRAME[key],
            marker="s",
            linewidth=2,
            label="DeepSeek V3.2",
            color="#4C78A8",
            linestyle="--",
        )
        ax.plot(
            x, NEW_V4_FRAME[key], marker="s", linewidth=2, label="DeepSeek V4 Pro", color="#4C78A8"
        )
        ax.set_xticks(x)
        ax.set_xticklabels(["pr", "ps", "min", "sf", "pm"], fontsize=9)
        ax.set_title(titles[key])
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
        if key == "T1":
            ax.set_ylabel("Manipulation rate")
    axes[-1].legend(loc="upper left", fontsize=9)
    fig.suptitle(
        "Frontier-generation contrast: GPT-5 → GPT-5.5 (orange) and DeepSeek V3.2 → V4 Pro (blue)\nDashed = original; solid = post-amendment",
        fontsize=13,
        y=1.02,
    )
    fig.tight_layout()
    out = OUT / "fig_generation_contrast.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


def main():
    print("Loading task rows...")
    all_task_rows = {}
    for task in TASKS:
        rows = load_task_rows(task)
        all_task_rows[task["name"]] = rows
        print(f"  {task['name']}: {len(rows)}")

    print("\nGenerating figures...")
    fig_per_model_frame_curves(all_task_rows)
    fig_model_similarity_matrix(all_task_rows)
    fig_variance_decomposition(all_task_rows)
    fig_saturation_map(all_task_rows)
    fig_endpoint_range(all_task_rows)
    fig_model_ranking_stability(all_task_rows)
    fig_generation_contrast()
    print("\nDone.")


if __name__ == "__main__":
    main()
