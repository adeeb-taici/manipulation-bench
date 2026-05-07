"""Drill into the haiku35 -> haiku45 bargaining collapse.

Shows the per-(frame, incentive, difficulty) cell rate for both models, side
by side, so we can see whether the collapse is uniform or concentrated in
specific conditions.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from _loader import load, fig_path, save_table, FRAME_ORDER, INCENTIVE_ORDER, DIFFICULTY_ORDER

OLD, NEW = "haiku35", "haiku45"


def cell_rates(df, model):
    sub = df[(df["task"] == "bargaining") & (df["model"] == model)]
    return sub.groupby(["frame", "incentive", "difficulty"], observed=True)["manipulation_occurred"].mean()


def main() -> None:
    df = load()
    old = cell_rates(df, OLD)
    new = cell_rates(df, NEW)
    delta = (new - old).rename("delta")
    save_table(old.rename("haiku35").to_frame().join(new.rename("haiku45")).join(delta), "10_haiku_cells")

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    cmap_rate = "magma_r"
    for ax, (label, series) in zip(axes, [("haiku35", old), ("haiku45", new), ("delta (new - old)", delta)]):
        # Pivot: rows = frame, columns = (incentive, difficulty) for compact 5x9 grid
        wide = series.unstack(["incentive", "difficulty"])
        wide = wide.reindex(index=FRAME_ORDER,
                            columns=[(i, d) for i in INCENTIVE_ORDER for d in DIFFICULTY_ORDER])
        if label.startswith("delta"):
            vmax = float(np.nanmax(np.abs(wide.values))) or 1.0
            im = ax.imshow(wide.values, cmap="coolwarm", vmin=-vmax, vmax=vmax, aspect="auto")
        else:
            im = ax.imshow(wide.values, cmap=cmap_rate, vmin=0, vmax=1, aspect="auto")
        ax.set_title(label)
        ax.set_xticks(range(len(wide.columns)))
        ax.set_xticklabels([f"{i}\n{d}" for i, d in wide.columns], fontsize=7)
        ax.set_yticks(range(len(wide.index)))
        ax.set_yticklabels(wide.index, fontsize=8)
        for i in range(wide.shape[0]):
            for j in range(wide.shape[1]):
                v = wide.values[i, j]
                if np.isnan(v):
                    continue
                if label.startswith("delta"):
                    color = "white" if abs(v) > vmax * 0.7 else "black"
                    txt = f"{v:+.2f}"
                else:
                    color = "white" if v > 0.5 else "black"
                    txt = f"{v:.2f}"
                ax.text(j, i, txt, ha="center", va="center", color=color, fontsize=6)
        fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    axes[0].set_ylabel("frame")
    fig.suptitle("haiku35 -> haiku45 bargaining manipulation rate, per (frame, incentive, difficulty)")
    fig.tight_layout()
    fig.savefig(fig_path("10_haiku_collapse_grid"), dpi=150)
    plt.close(fig)

    # Also: collapsed-by-frame view for a clean one-panel summary
    fig, ax = plt.subplots(figsize=(7, 4))
    by_frame_old = df[(df.task == "bargaining") & (df.model == OLD)].groupby("frame", observed=True)["manipulation_occurred"].mean().reindex(FRAME_ORDER)
    by_frame_new = df[(df.task == "bargaining") & (df.model == NEW)].groupby("frame", observed=True)["manipulation_occurred"].mean().reindex(FRAME_ORDER)
    x = np.arange(len(FRAME_ORDER))
    ax.bar(x - 0.2, by_frame_old.values, 0.4, label="haiku35", color="#cc4444")
    ax.bar(x + 0.2, by_frame_new.values, 0.4, label="haiku45", color="#4477aa")
    ax.set_xticks(x); ax.set_xticklabels(FRAME_ORDER)
    ax.set_ylabel("bargaining manipulation rate"); ax.set_ylim(0, 1)
    ax.set_title("haiku35 -> haiku45: bargaining manipulation by frame")
    ax.legend()
    for i, (a, b) in enumerate(zip(by_frame_old.values, by_frame_new.values)):
        ax.text(i - 0.2, a + 0.02, f"{a:.2f}", ha="center", fontsize=8)
        ax.text(i + 0.2, b + 0.02, f"{b:.2f}", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(fig_path("10_haiku_collapse_by_frame"), dpi=150)
    plt.close(fig)

    print("=== haiku bargaining rate by frame ===")
    print(f"{'frame':<12}{'haiku35':>10}{'haiku45':>10}{'delta':>10}")
    for f in FRAME_ORDER:
        a, b = by_frame_old[f], by_frame_new[f]
        print(f"{f:<12}{a:>10.3f}{b:>10.3f}{b-a:>+10.3f}")

    print("\nFigures: 10_haiku_collapse_grid.png (5x9 cell view), 10_haiku_collapse_by_frame.png")


if __name__ == "__main__":
    main()
