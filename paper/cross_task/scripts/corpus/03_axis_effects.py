"""Marginal effects of frame, incentive, difficulty per task."""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from _loader import load, save_table, fig_path, FRAME_ORDER, INCENTIVE_ORDER, DIFFICULTY_ORDER

AXIS_ORDERS = {"frame": FRAME_ORDER, "incentive": INCENTIVE_ORDER, "difficulty": DIFFICULTY_ORDER}


def axis_means(df: pd.DataFrame, axis: str) -> pd.DataFrame:
    g = df.groupby(["task", axis], observed=True)["manipulation_occurred"].agg(["mean", "count"])
    return g.unstack(axis).reindex(columns=pd.MultiIndex.from_product(
        [["mean", "count"], AXIS_ORDERS[axis]]))


def plot_axis(pivot_means: pd.DataFrame, axis: str, out: str) -> None:
    tasks = list(pivot_means.index)
    levels = AXIS_ORDERS[axis]
    fig, ax = plt.subplots(figsize=(1.2 * len(levels) + 3, 4))
    width = 0.8 / len(tasks)
    x = np.arange(len(levels))
    for i, task in enumerate(tasks):
        vals = pivot_means.loc[task, "mean"].reindex(levels).values
        ax.bar(x + i * width - 0.4 + width / 2, vals, width, label=task)
    ax.set_xticks(x)
    ax.set_xticklabels(levels)
    ax.set_ylabel("manipulation_occurred rate")
    ax.set_title(f"Manipulation rate by {axis} (per task, pooled across models)")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(fig_path(out), dpi=150)
    plt.close(fig)


def frame_x_incentive_heatmap(df: pd.DataFrame, task: str) -> None:
    sub = df[df["task"] == task]
    piv = sub.groupby(["frame", "incentive"], observed=True)["manipulation_occurred"].mean().unstack("incentive")
    piv = piv.reindex(index=FRAME_ORDER, columns=INCENTIVE_ORDER)
    fig, ax = plt.subplots(figsize=(4.5, 4))
    vmax = max(0.6, np.nanmax(piv.values))
    im = ax.imshow(piv.values, cmap="magma_r", vmin=0, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(INCENTIVE_ORDER))); ax.set_xticklabels(INCENTIVE_ORDER)
    ax.set_yticks(range(len(FRAME_ORDER))); ax.set_yticklabels(FRAME_ORDER)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                        color="white" if v > vmax * 0.55 else "black", fontsize=9)
    ax.set_title(f"{task}: frame × incentive")
    ax.set_xlabel("incentive"); ax.set_ylabel("frame")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(fig_path(f"03_frame_incentive_{task}"), dpi=150)
    plt.close(fig)
    save_table(piv.round(4), f"03_frame_incentive_{task}")


def main() -> None:
    df = load()

    effect_rows = []
    for axis in ("frame", "incentive", "difficulty"):
        print(f"=== Manipulation rate by {axis} (per task) ===")
        means = axis_means(df, axis)
        print(means["mean"].round(3), "\n")
        save_table(means, f"03_axis_{axis}")
        plot_axis(means, axis, f"03_axis_{axis}")

        for task in means.index:
            row = means.loc[task, "mean"]
            effect_rows.append({"task": task, "axis": axis,
                                "min_level": row.idxmin(), "min": row.min(),
                                "max_level": row.idxmax(), "max": row.max(),
                                "spread": row.max() - row.min()})

    effects = pd.DataFrame(effect_rows).set_index(["task", "axis"]).round(4)
    print("=== Per-axis effect size (max - min rate within task) ===")
    print(effects, "\n")
    save_table(effects, "03_axis_effect_sizes")

    print("=== Axis with largest effect per task ===")
    biggest = effects.reset_index().sort_values(["task", "spread"], ascending=[True, False]) \
                     .groupby("task").head(1).set_index("task")[["axis", "spread", "min_level", "max_level"]]
    print(biggest, "\n")
    save_table(biggest, "03_dominant_axis_per_task")

    for task in df["task"].unique():
        frame_x_incentive_heatmap(df, task)
    print(f"Wrote frame×incentive heatmaps for: {sorted(df['task'].unique())}")


if __name__ == "__main__":
    main()
