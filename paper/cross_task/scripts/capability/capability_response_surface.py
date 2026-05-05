"""Tier-faceted response surface: same 5-frame x 3-incentive heatmap as the
main paper, but averaged within each capability tier instead of per-model.

For each task, emits a row of 3 heatmaps (small / average / flagship) showing
mean manipulation rate per (frame, incentive) cell, plus a difficulty-row
variant (frame x difficulty per tier).

Outputs:
  paper/cross_task/figures/capability/response_surface_by_tier__frame_x_incentive.png
  paper/cross_task/figures/capability/response_surface_by_tier__frame_x_difficulty.png
  paper/cross_task/analysis/response_surface_by_tier.json
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np

from _capability_io import (
    ANALYSIS_DIR,
    DIFFICULTIES,
    FIG_DIR,
    FRAMES,
    INCENTIVES,
    TASKS,
    TIERS,
    aggregate,
    ensure_dirs,
    load_joined,
)


def _grid(df, task, tier, x_levels, y_levels, x_col, y_col):
    sub = df[(df["task"] == task) & (df["tier"] == tier)]
    sub = sub[sub[x_col].isin(x_levels) & sub[y_col].isin(y_levels)]
    if sub.empty:
        return np.full((len(y_levels), len(x_levels)), np.nan), np.zeros((len(y_levels), len(x_levels)), dtype=int)
    agg = aggregate(sub, [y_col, x_col])
    rate = np.full((len(y_levels), len(x_levels)), np.nan)
    n = np.zeros((len(y_levels), len(x_levels)), dtype=int)
    for _, row in agg.iterrows():
        i = y_levels.index(row[y_col])
        j = x_levels.index(row[x_col])
        rate[i, j] = row["rate"]
        n[i, j] = int(row["n"])
    return rate, n


def plot_grid(df, x_col, x_levels, y_col, y_levels, out_path, title):
    fig, axes = plt.subplots(len(TASKS), len(TIERS), figsize=(11, 2.4 * len(TASKS)),
                              constrained_layout=True)
    json_out: dict = {}
    for ti, task in enumerate(TASKS):
        json_out[task] = {}
        for tj, tier in enumerate(TIERS):
            ax = axes[ti, tj]
            rate, n = _grid(df, task, tier, x_levels, y_levels, x_col, y_col)
            json_out[task][tier] = {
                "rate": [[None if np.isnan(v) else float(v) for v in row] for row in rate],
                "n": n.tolist(),
                "x_levels": x_levels,
                "y_levels": y_levels,
            }
            im = ax.imshow(rate, aspect="auto", cmap="RdYlBu_r", vmin=0, vmax=1)
            for i in range(len(y_levels)):
                for j in range(len(x_levels)):
                    if not np.isnan(rate[i, j]):
                        ax.text(j, i, f"{rate[i, j]:.2f}", ha="center", va="center",
                                fontsize=6, color="white" if rate[i, j] > 0.5 else "black")
            if ti == 0:
                ax.set_title(tier, fontsize=10)
            if tj == 0:
                ax.set_ylabel(f"{task}\n{y_col}", fontsize=8)
            ax.set_yticks(range(len(y_levels)))
            ax.set_yticklabels(y_levels, fontsize=7)
            ax.set_xticks(range(len(x_levels)))
            ax.set_xticklabels(x_levels, rotation=30, ha="right", fontsize=7)
    fig.suptitle(title, fontsize=12)
    fig.colorbar(im, ax=axes.ravel().tolist(), fraction=0.015, pad=0.02)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return json_out


def main() -> None:
    ensure_dirs()
    df = load_joined()

    fxi = plot_grid(
        df, "incentive", INCENTIVES, "frame", FRAMES,
        FIG_DIR / "response_surface_by_tier__frame_x_incentive.png",
        "Manipulation rate by frame x incentive, faceted by capability tier",
    )
    fxd = plot_grid(
        df, "difficulty", DIFFICULTIES, "frame", FRAMES,
        FIG_DIR / "response_surface_by_tier__frame_x_difficulty.png",
        "Manipulation rate by frame x difficulty, faceted by capability tier",
    )

    with open(ANALYSIS_DIR / "response_surface_by_tier.json", "w", encoding="utf-8") as f:
        json.dump({"frame_x_incentive": fxi, "frame_x_difficulty": fxd}, f, indent=2)

    print(f"Wrote {FIG_DIR / 'response_surface_by_tier__frame_x_incentive.png'}")
    print(f"Wrote {FIG_DIR / 'response_surface_by_tier__frame_x_difficulty.png'}")
    print(f"Wrote {ANALYSIS_DIR / 'response_surface_by_tier.json'}")


if __name__ == "__main__":
    main()
