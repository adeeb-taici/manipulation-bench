"""Forest plot: per-(task, model) incentive=high vs incentive=none manipulation-rate delta.

For each task in the paper roster and each frontier model, compute
    delta = P(manipulation_occurred=1 | incentive=high)
          - P(manipulation_occurred=1 | incentive=none)
holding nothing else constant (pooled over frame × difficulty × scenario).
95% CI via 2000-rep nonparametric bootstrap on per-task scenario rows.

Reads paper/cross_task/data/results.csv and writes:
  paper/cross_task/scripts/newer/out/incentive_forest.csv
  paper/cross_task/figures/newer/incentive_forest.png
  paper/cross_task/figures/newer/incentive_forest.pdf
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[4]
CSV = REPO / "paper" / "cross_task" / "data" / "results.csv"
OUT_CSV = Path(__file__).resolve().parent / "out" / "incentive_forest.csv"
FIG_DIR = REPO / "paper" / "cross_task" / "figures" / "newer"

TASKS = ["bargaining", "debate", "village", "sales", "committee"]
MODELS = [
    "Claude-Opus-4.7",
    "GPT-5.5",
    "Gemini-3.1-Pro",
    "Grok-4",
    "Llama-3.3-70B",
    "DeepSeek-V4-Pro",
]
N_BOOT = 2000
SEED = 20260504


def boot_ci(high: np.ndarray, none: np.ndarray, n_boot: int, rng: np.random.Generator) -> tuple[float, float]:
    if len(high) == 0 or len(none) == 0:
        return (np.nan, np.nan)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        h = rng.choice(high, size=len(high), replace=True)
        n = rng.choice(none, size=len(none), replace=True)
        diffs[i] = h.mean() - n.mean()
    return (float(np.quantile(diffs, 0.025)), float(np.quantile(diffs, 0.975)))


def main() -> None:
    df = pd.read_csv(CSV, low_memory=False)
    df = df[df["task"].isin(TASKS) & df["model"].isin(MODELS)].copy()
    df = df.dropna(subset=["manipulation_occurred", "incentive"])
    df["manipulation_occurred"] = df["manipulation_occurred"].astype(float)

    rng = np.random.default_rng(SEED)
    rows = []
    for task in TASKS:
        for model in MODELS:
            sub = df[(df["task"] == task) & (df["model"] == model)]
            high = sub.loc[sub["incentive"] == "high", "manipulation_occurred"].to_numpy()
            none = sub.loc[sub["incentive"] == "none", "manipulation_occurred"].to_numpy()
            if len(high) == 0 or len(none) == 0:
                continue
            delta = high.mean() - none.mean()
            ci_lo, ci_hi = boot_ci(high, none, N_BOOT, rng)
            rows.append({
                "task": task,
                "model": model,
                "rate_none": float(none.mean()),
                "rate_high": float(high.mean()),
                "delta": float(delta),
                "ci_lo": ci_lo,
                "ci_hi": ci_hi,
                "n_none": int(len(none)),
                "n_high": int(len(high)),
            })

    out = pd.DataFrame(rows)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"wrote {OUT_CSV} ({len(out)} rows)")

    # Forest plot: 5 task panels stacked vertically, 6 model rows each.
    fig, axes = plt.subplots(
        nrows=len(TASKS), ncols=1,
        figsize=(8.5, 1.0 + 1.05 * len(TASKS)),
        sharex=True,
    )
    x_lo = float(np.nanmin([out["ci_lo"].min(), -0.05])) - 0.02
    x_hi = float(np.nanmax([out["ci_hi"].max(), 0.05])) + 0.02

    for ax, task in zip(axes, TASKS):
        sub = out[out["task"] == task].set_index("model").reindex(MODELS).reset_index()
        ys = np.arange(len(MODELS))[::-1]  # top-to-bottom = MODELS order
        for y, (_, r) in zip(ys, sub.iterrows()):
            if pd.isna(r["delta"]):
                continue
            color = "#c0392b" if r["delta"] > 0 else "#2c5fa0"
            ax.errorbar(
                r["delta"], y,
                xerr=[[r["delta"] - r["ci_lo"]], [r["ci_hi"] - r["delta"]]],
                fmt="o", color=color, ecolor=color,
                markersize=5, capsize=2.5, linewidth=1.2,
            )
        ax.axvline(0, color="black", linewidth=0.6, zorder=0)
        ax.set_yticks(ys)
        ax.set_yticklabels(MODELS, fontsize=8)
        ax.set_xlim(x_lo, x_hi)
        ax.set_ylim(-0.7, len(MODELS) - 0.3)
        ax.set_title(task.capitalize(), fontsize=10, loc="left", pad=2)
        ax.tick_params(axis="x", labelsize=8)
        ax.grid(axis="x", alpha=0.25, linewidth=0.5)

    axes[-1].set_xlabel(
        "Δ manipulation rate  (incentive=high  −  incentive=none)",
        fontsize=10,
    )
    fig.suptitle(
        "Per-task effect of incentive=high on manipulation rate",
        fontsize=11, y=0.995,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.985))

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        path = FIG_DIR / f"incentive_forest.{ext}"
        fig.savefig(path, dpi=200, bbox_inches="tight")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
