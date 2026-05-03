"""Surprise / residual analysis.

For each (task, model), fit an ADDITIVE linear model:
    y_cell = mu + a_frame + b_incentive + c_difficulty
to the 5 × 3 × 3 = 45 cell means. Compute residuals and flag cells
> 2 SD from the per-model linear fit. These are non-additive interactions
— places where (frame=permissive AND difficulty=high) is much more or
less manipulative than the main effects predict.

Outputs:
  paper/cross_task/figures/fig_residual_<task>.pdf  (one heatmap per task)
  paper/cross_task/analysis/residuals.json
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

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
    {
        "name": "T1 Bargaining",
        "short_name": "bargaining",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "difficulty_levels": ("low", "medium", "high"),
    },
    {
        "name": "T2 Debate",
        "short_name": "debate",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "difficulty_levels": ("low", "medium", "high"),
    },
    {
        "name": "T3 Village",
        "short_name": "village",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "difficulty_levels": ("low", "medium", "high"),
    },
    {
        "name": "T4 Sales",
        "short_name": "sales",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "difficulty_levels": ("low", "medium", "high"),
    },
    {
        "name": "T5 Committee",
        "short_name": "committee",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "difficulty_levels": ("low", "medium", "high"),
    },
]


def model_order_key(m):
    return list(DISPLAY).index(m) if m in DISPLAY else 999


def load_rows(task, full_df):
    df_task = full_df[full_df["task"] == task["short_name"]].copy()
    rows = []
    for r in df_task.to_dict(orient="records"):
        model = r.get("model")
        metric = r.get("metric")
        if model is None or metric is None:
            continue
        rows.append({
            "model": model,
            "metric": float(metric),
            "frame": r.get("frame"),
            "incentive": r.get("incentive"),
            "difficulty": r.get("difficulty"),
        })
    return rows


def fit_additive(grid: np.ndarray):
    """Fit y = mu + a_f + b_i + c_d; return predicted grid + residuals.

    grid is (n_frame, n_incentive, n_difficulty), with NaN allowed.
    Uses the standard sum-to-zero parameterisation by mean-centering per-axis
    marginals.
    """
    valid = ~np.isnan(grid)
    if not valid.any():
        return grid * 0, grid * np.nan
    mu = np.nanmean(grid)
    # Marginal means
    a = np.nanmean(grid, axis=(1, 2)) - mu  # (n_frame,)
    b = np.nanmean(grid, axis=(0, 2)) - mu  # (n_incentive,)
    c = np.nanmean(grid, axis=(0, 1)) - mu  # (n_difficulty,)
    pred = mu + a[:, None, None] + b[None, :, None] + c[None, None, :]
    resid = grid - pred
    return pred, resid


def main():
    full_df = load_corpus(verbose=False)
    all_residuals = {}
    for task in TASKS:
        print(f"\n=== {task['name']} ===")
        rows = load_rows(task, full_df)
        models = sorted({r["model"] for r in rows}, key=model_order_key)

        n_f, n_i, n_d = (
            len(task["frame_levels"]),
            len(task["incentive_levels"]),
            len(task["difficulty_levels"]),
        )
        per_model_grid = {}
        per_model_resid = {}
        for model in models:
            grid = np.full((n_f, n_i, n_d), np.nan)
            for fi, f in enumerate(task["frame_levels"]):
                for ii, inc in enumerate(task["incentive_levels"]):
                    for di, diff in enumerate(task["difficulty_levels"]):
                        vals = [
                            r["metric"]
                            for r in rows
                            if r["model"] == model
                            and r["frame"] == f
                            and r["incentive"] == inc
                            and r["difficulty"] == diff
                        ]
                        if vals:
                            grid[fi, ii, di] = sum(vals) / len(vals)
            _, resid = fit_additive(grid)
            per_model_grid[model] = grid
            per_model_resid[model] = resid

        # Build a figure: one row per difficulty, one col per model;
        # heatmap = residual on (frame y, incentive x).
        fig, axes = plt.subplots(
            n_d, len(models), figsize=(2.8 * len(models), 2.4 * n_d), sharex=False, sharey=False
        )
        if n_d == 1:
            axes = np.array([axes])
        if len(models) == 1:
            axes = axes.reshape(-1, 1)

        # Common colour scale
        all_resid = np.array([per_model_resid[m] for m in models])
        if np.all(np.isnan(all_resid)):
            vmax = 1.0
        else:
            vmax = max(0.05, np.nanpercentile(np.abs(all_resid), 95))

        flagged = []
        im = None
        for di, diff in enumerate(task["difficulty_levels"]):
            for mi, model in enumerate(models):
                ax = axes[di, mi]
                resid_slice = per_model_resid[model][:, :, di]
                im = ax.imshow(resid_slice, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
                # Flag cells where |residual| > 2*SD of all residuals for this model
                model_resid = per_model_resid[model]
                model_sd = np.nanstd(model_resid)
                for fi in range(n_f):
                    for ii in range(n_i):
                        v = resid_slice[fi, ii]
                        if np.isnan(v):
                            continue
                        flag = abs(v) > 2 * model_sd if model_sd > 1e-9 else False
                        if flag:
                            flagged.append(
                                {
                                    "task": task["name"],
                                    "model": DISPLAY.get(model, model),
                                    "frame": task["frame_levels"][fi],
                                    "incentive": str(task["incentive_levels"][ii]),
                                    "difficulty": diff,
                                    "actual": float(per_model_grid[model][fi, ii, di]),
                                    "predicted": float(per_model_grid[model][fi, ii, di] - v),
                                    "residual": float(v),
                                    "model_sd": float(model_sd),
                                }
                            )
                        ax.text(
                            ii,
                            fi,
                            f"{v:+.2f}" + ("*" if flag else ""),
                            ha="center",
                            va="center",
                            fontsize=6,
                            color="white" if abs(v) > vmax * 0.6 else "black",
                            fontweight="bold" if flag else "normal",
                        )
                ax.set_xticks(range(n_i))
                ax.set_xticklabels([str(x) for x in task["incentive_levels"]], fontsize=6)
                ax.set_yticks(range(n_f))
                if mi == 0:
                    ax.set_yticklabels(task["frame_levels"], fontsize=6)
                    ax.set_ylabel(f"diff={diff}", fontsize=8)
                else:
                    ax.set_yticklabels([])
                if di == 0:
                    ax.set_title(DISPLAY.get(model, model), fontsize=8)

        fig.suptitle(
            f"{task['name']} — additive-model residuals (actual − predicted)\n"
            "* = |resid| > 2·SD; positive (red) = MORE manipulation than additive predicts; negative (blue) = LESS.",
            fontsize=11,
            y=1.01,
        )
        if im is not None:
            fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.6, label="Residual")
        out_path = (
            Path("paper/cross_task/figures") / f"fig_residual_{task['name'].split()[0].lower()}.pdf"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  saved {out_path}")
        print(f"  flagged cells (>2 SD): {len(flagged)}")
        all_residuals[task["name"]] = flagged

    out_json = Path("paper/cross_task/analysis/residuals.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_residuals, f, indent=2)
    print(f"\nwrote {out_json}")

    print("\n=== Top-10 most surprising cells across all tasks ===")
    flat = []
    for task_name, items in all_residuals.items():
        for it in items:
            flat.append((abs(it["residual"]), it))
    flat.sort(key=lambda x: -x[0])
    for _, it in flat[:10]:
        print(
            f"  {it['task']:14s} {it['model']:18s} "
            f"f={it['frame']:11s} i={it['incentive']:8s} d={it['difficulty']:6s} "
            f"resid={it['residual']:+.3f}  actual={it['actual']:.3f} pred={it['predicted']:.3f}"
        )


if __name__ == "__main__":
    main()
