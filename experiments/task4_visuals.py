"""Task 4 Sales visuals — parallel to task1_visuals.py / task2_visuals.py.

Plots (output to paper/task4_sales/figures/):
  fig1_manip_by_frame      — mean manipulation_rate by frame × model
  fig2_frame_inc_heatmap   — per-model frame × incentive heatmap
  fig3_endpoints           — prohibitive vs permissive bar comparison
  fig4_difficulty          — manipulation_rate by difficulty × model
"""

from __future__ import annotations

import glob
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

OUT = Path("paper/task4_sales/figures")

LOG_PATTERNS = ["paper/task4_sales/eval_log.eval"]

FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
FRAME_LABELS = ["Prohibit.", "Pro-social", "Minimal", "Selfish", "Permissive"]
INCENTIVES = ("none", "moderate", "high")
DIFFICULTIES = ("low", "medium", "high")

MODEL_DISPLAY = {
    "claude": "Claude Opus 4.7",
    "gpt55": "GPT-5.5",
    "gemini": "Gemini 3.1 Pro",
    "grok": "Grok 4",
    "llama": "Llama 3.3 70B",
    "deepseek": "DeepSeek V4 Pro",
}


def load_rows():
    by_id = {}
    for pat in LOG_PATTERNS:
        for p in sorted(glob.glob(pat)):
            log = read_eval_log(p)
            for s in log.samples:
                if s.error:
                    continue
                md = s.metadata or {}
                sc = (s.scores or {}).get("sales_classifier")
                if sc is None or not isinstance(sc.value, dict):
                    continue
                v = sc.value
                if v.get("manipulation_rate") is None:
                    continue
                by_id[s.id] = dict(
                    model=("gpt55" if md.get("model") == "gpt5" else md.get("model")),
                    frame=md.get("frame"),
                    incentive=md.get("incentive"),
                    difficulty=md.get("difficulty"),
                    mr=v.get("manipulation_rate"),
                )
    return list(by_id.values())


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def fig1_manip_by_frame(rows):
    fig, ax = plt.subplots(figsize=(11, 6))
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))
    colors = plt.cm.tab10(np.linspace(0, 1, len(models)))
    x = np.arange(len(FRAMES))
    width = 0.13
    for i, m in enumerate(models):
        means = [
            mean([r["mr"] for r in rows if r["model"] == m and r["frame"] == f]) for f in FRAMES
        ]
        ax.bar(
            x + (i - (len(models) - 1) / 2) * width,
            means,
            width,
            label=MODEL_DISPLAY.get(m, m),
            color=colors[i],
        )
    ax.set_xticks(x)
    ax.set_xticklabels(FRAME_LABELS, fontsize=10)
    ax.set_ylabel("Manipulation rate\n(fraction of buyer questions classified misleading or false)")
    ax.set_title(
        "Sales manipulation rate by frame, per model (averaged over incentive × difficulty)"
    )
    ax.set_ylim(0, 0.75)
    ax.axhline(0.05, color="gray", linestyle="--", alpha=0.6, label="P1 prohibitive floor (0.05)")
    ax.legend(loc="upper right", ncol=2, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = OUT / "fig1_manip_by_frame.pdf"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def fig2_frame_inc_heatmap(rows):
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))
    n = len(models)
    ncols = 3
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 4 * nrows), sharex=True, sharey=True)
    if nrows == 1:
        axes = np.array([axes])
    for ax, m in zip(axes.flat, models):
        grid = np.full((len(FRAMES), len(INCENTIVES)), np.nan)
        for i, f in enumerate(FRAMES):
            for j, inc in enumerate(INCENTIVES):
                vals = [
                    r["mr"]
                    for r in rows
                    if r["model"] == m and r["frame"] == f and r["incentive"] == inc
                ]
                if vals:
                    grid[i, j] = mean(vals)
        im = ax.imshow(grid, cmap="Reds", aspect="auto", vmin=0, vmax=1.0)
        ax.set_title(MODEL_DISPLAY.get(m, m))
        ax.set_xticks(range(len(INCENTIVES)))
        ax.set_xticklabels([f"I={i}" for i in INCENTIVES], fontsize=9)
        ax.set_yticks(range(len(FRAMES)))
        ax.set_yticklabels(FRAMES, fontsize=9)
        for i in range(len(FRAMES)):
            for j in range(len(INCENTIVES)):
                v = grid[i, j]
                if not np.isnan(v):
                    ax.text(
                        j,
                        i,
                        f"{v:.2f}",
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="white" if v > 0.5 else "black",
                    )
    for ax in axes.flat[n:]:
        ax.set_visible(False)
    fig.suptitle(
        "Sales: manipulation rate frame × incentive per model (red = more manipulation)",
        fontsize=13,
        y=1.00,
    )
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.7, label="Manipulation rate")
    out = OUT / "fig2_frame_inc_heatmap.pdf"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def fig3_endpoints(rows):
    fig, ax = plt.subplots(figsize=(9, 5))
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))
    proh = [
        mean([r["mr"] for r in rows if r["model"] == m and r["frame"] == "prohibitive"])
        for m in models
    ]
    perm = [
        mean([r["mr"] for r in rows if r["model"] == m and r["frame"] == "permissive"])
        for m in models
    ]
    x = np.arange(len(models))
    w = 0.38
    ax.bar(x - w / 2, proh, w, label='Prohibitive ("be accurate")', color="#54A24B")
    ax.bar(x + w / 2, perm, w, label='Permissive ("any strategy")', color="#E45756")
    for i, (p, e) in enumerate(zip(proh, perm)):
        if not np.isnan(e) and not np.isnan(p):
            ax.annotate(
                f"+{e - p:.2f}",
                xy=(i, max(p, e) + 0.01),
                ha="center",
                fontsize=9,
                fontweight="bold",
            )
    ax.axhline(0.05, color="gray", linestyle="--", alpha=0.6, label="P1 prohibitive floor (0.05)")
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_DISPLAY.get(m, m) for m in models], rotation=15, ha="right")
    ax.set_ylabel("Manipulation rate (avg over incentive × difficulty)")
    ax.set_title(
        "Sales endpoints: prohibitive vs permissive per model (frame effect varies sharply by model)"
    )
    ax.set_ylim(0, 0.75)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = OUT / "fig3_endpoints.pdf"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def fig4_difficulty(rows):
    fig, ax = plt.subplots(figsize=(10, 5))
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))
    colors = plt.cm.tab10(np.linspace(0, 1, len(models)))
    x = np.arange(len(DIFFICULTIES))
    for i, m in enumerate(models):
        means = [
            mean([r["mr"] for r in rows if r["model"] == m and r["difficulty"] == d])
            for d in DIFFICULTIES
        ]
        ax.plot(x, means, marker="o", linewidth=2, color=colors[i], label=MODEL_DISPLAY.get(m, m))
    ax.set_xticks(x)
    ax.set_xticklabels(
        [
            "Low\n(product is good)",
            "Medium\n(mixed truth)",
            "High\n(product is bad)",
        ],
        fontsize=10,
    )
    ax.set_ylabel("Manipulation rate\n(avg over frame × incentive)")
    ax.set_title("Sales manipulation rate by difficulty per model")
    ax.set_ylim(0, 0.75)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = OUT / "fig4_difficulty.pdf"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    print(f"loaded {len(rows)} scored rows")
    fig1_manip_by_frame(rows)
    fig2_frame_inc_heatmap(rows)
    fig3_endpoints(rows)
    fig4_difficulty(rows)


if __name__ == "__main__":
    main()
