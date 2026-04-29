"""Generate visualizations of Task 5 committee results.

Outputs PNGs to paper/task5_committee/figures/.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

LOG = "paper/task5_committee/eval_log.eval"
OUT = Path("paper/task5_committee/figures")

FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
DIFFS = ("low", "medium", "high")
INCS = ("none", "moderate", "high")

FRAME_LABELS = [
    "Prohibitive\n(don't manipulate)",
    "Pro-social\n(be fair)",
    "Minimal\n(no instruction)",
    "Selfish\n(maximize payoff)",
    "Permissive\n(you may exaggerate)",
]

MODEL_DISPLAY = {
    "claude": "Claude Opus 4.7",
    "gpt55": "GPT-5.5",
    "gemini": "Gemini 3.1 Pro",
    "grok": "Grok 4",
    "llama": "Llama 3.3 70B",
    "deepseek": "DeepSeek V4 Pro",
}


def load_rows():
    log = read_eval_log(LOG)
    rows = []
    for s in log.samples:
        if s.error is not None:
            continue
        m = (s.metadata or {}).get("scenario", {}).get("metadata", {})
        bs = (s.scores or {}).get("initial_rating_bias")
        if bs is None or not isinstance(bs.value, dict):
            continue
        bias = bs.value.get("initial_bias")
        if bias is None:
            continue
        rows.append(
            dict(
                model=(
                    "gpt55"
                    if m.get("interested_model_label") == "gpt5"
                    else m.get("interested_model_label")
                ),
                frame=m.get("frame"),
                incentive=m.get("incentive"),
                difficulty=m.get("difficulty"),
                bias=float(bias),
            )
        )
    return rows


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def fig1_bias_across_frames(rows):
    """Main figure: per-model manipulation bias across the 5 frame levels."""
    fig, ax = plt.subplots(figsize=(11, 6))
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))
    colors = plt.cm.tab10(np.linspace(0, 1, len(models)))

    x = np.arange(len(FRAMES))
    width = 0.13

    for i, model in enumerate(models):
        means = []
        for f in FRAMES:
            vals = [r["bias"] for r in rows if r["model"] == model and r["frame"] == f]
            means.append(mean(vals))
        ax.bar(
            x + (i - 2.5) * width,
            means,
            width,
            label=MODEL_DISPLAY.get(model, model),
            color=colors[i],
        )

    ax.axhline(0, color="black", linewidth=0.8)
    ax.axhline(2.0, color="green", linewidth=0.6, linestyle="--", alpha=0.5)
    ax.axhline(-2.0, color="green", linewidth=0.6, linestyle="--", alpha=0.5)
    ax.text(4.45, 2.2, "P1 ±2.0 band", fontsize=8, color="green", ha="right")

    ax.set_xticks(x)
    ax.set_xticklabels(FRAME_LABELS, fontsize=9)
    ax.set_ylabel("Manipulation bias\n(favored candidate rating − honest baseline, 0–20 scale)")
    ax.set_title(
        "Manipulation bias by frame, per model\nHigher = more manipulation. Zero = honest."
    )
    ax.legend(loc="upper left", ncol=2, fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(-10, 22)

    fig.tight_layout()
    out = OUT / "fig1_bias_by_frame.svg"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def fig2_minimal_vs_selfish(rows):
    """Focused chart: the minimal > selfish inversion."""
    fig, ax = plt.subplots(figsize=(9, 5.5))
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))

    min_means, sel_means = [], []
    for model in models:
        min_vals = [r["bias"] for r in rows if r["model"] == model and r["frame"] == "minimal"]
        sel_vals = [r["bias"] for r in rows if r["model"] == model and r["frame"] == "selfish"]
        min_means.append(mean(min_vals))
        sel_means.append(mean(sel_vals))

    x = np.arange(len(models))
    width = 0.38
    ax.bar(x - width / 2, min_means, width, label="Minimal (no instruction)", color="#4C78A8")
    ax.bar(
        x + width / 2, sel_means, width, label='"Selfish" (explicit instruction)', color="#E45756"
    )

    # Annotate inversions
    for i, (mi, se) in enumerate(zip(min_means, sel_means)):
        if mi > se:
            y = max(mi, se) + 0.5
            ax.annotate(
                "↓ lower\nwhen told\n'selfish'", xy=(i, y), ha="center", fontsize=8, color="darkred"
            )

    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_DISPLAY.get(m, m) for m in models], rotation=15, ha="right")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Manipulation bias (0–20 scale)")
    ax.set_title(
        'The "selfish" paradox: 4 of 6 models manipulate LESS\n'
        "when explicitly told to be selfish vs. no instruction at all"
    )
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    out = OUT / "fig2_minimal_vs_selfish.svg"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def fig3_frame_vs_difficulty_heatmap(rows):
    """Heatmap grid: 6 models × (frame × difficulty)."""
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))
    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharex=True, sharey=True)
    # Bias range is theoretically [-20, +20]; use the full metric scale for
    # cross-task consistency (every heatmap on its metric's natural full range).
    vmin, vmax = -20, 20

    for ax, model in zip(axes.flat, models):
        grid = np.full((len(FRAMES), len(DIFFS)), np.nan)
        for i, f in enumerate(FRAMES):
            for j, d in enumerate(DIFFS):
                vals = [
                    r["bias"]
                    for r in rows
                    if r["model"] == model and r["frame"] == f and r["difficulty"] == d
                ]
                if vals:
                    grid[i, j] = mean(vals)
        im = ax.imshow(grid, cmap="RdBu_r", aspect="auto", vmin=vmin, vmax=vmax)
        ax.set_title(MODEL_DISPLAY.get(model, model))
        ax.set_xticks(range(len(DIFFS)))
        ax.set_xticklabels([f"{d}\ndifficulty" for d in DIFFS], fontsize=9)
        ax.set_yticks(range(len(FRAMES)))
        ax.set_yticklabels(FRAMES, fontsize=9)
        for i in range(len(FRAMES)):
            for j in range(len(DIFFS)):
                val = grid[i, j]
                if not np.isnan(val):
                    ax.text(
                        j,
                        i,
                        f"{val:+.1f}",
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="white" if abs(val) > 8 else "black",
                    )

    fig.suptitle(
        "Manipulation bias: frame × difficulty per model\n"
        "Red = manipulation (inflated favorite). Blue = honest (low favorite rating).",
        y=1.00,
        fontsize=13,
    )
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.7, label="Bias (0–20 scale)")
    out = OUT / "fig3_frame_x_difficulty_heatmap.svg"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def fig4_endpoints(rows):
    """Simple endpoint comparison: prohibitive vs permissive per model."""
    fig, ax = plt.subplots(figsize=(9, 5))
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))

    proh = [
        mean([r["bias"] for r in rows if r["model"] == m and r["frame"] == "prohibitive"])
        for m in models
    ]
    perm = [
        mean([r["bias"] for r in rows if r["model"] == m and r["frame"] == "permissive"])
        for m in models
    ]

    x = np.arange(len(models))
    width = 0.38
    ax.bar(x - width / 2, proh, width, label='"Do not manipulate"', color="#54A24B")
    ax.bar(x + width / 2, perm, width, label='"You may exaggerate"', color="#F58518")

    for i, (p, e) in enumerate(zip(proh, perm)):
        ax.annotate(
            f"Δ = {e - p:+.1f}", xy=(i, max(p, e) + 0.5), ha="center", fontsize=9, fontweight="bold"
        )

    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_DISPLAY.get(m, m) for m in models], rotation=15, ha="right")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Manipulation bias (0–20 scale)")
    ax.set_title(
        "Endpoint control works: every model swings from honest to manipulative\n"
        "when the instruction changes from prohibition to permission"
    )
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    out = OUT / "fig4_endpoints.svg"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    print(f"loaded {len(rows)} scored rows")
    fig1_bias_across_frames(rows)
    fig2_minimal_vs_selfish(rows)
    fig3_frame_vs_difficulty_heatmap(rows)
    fig4_endpoints(rows)


if __name__ == "__main__":
    main()
