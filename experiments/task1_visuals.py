"""Task 1 Bargaining visuals — parallel to experiments/task5_visuals.py."""

from __future__ import annotations

import glob
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

OUT = Path("paper/task1_bargaining/figures")

# Single canonical combined log; produced by experiments/combine_eval_logs.py.
LOGS = ["paper/task1_bargaining/eval_log.eval"]

FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
FRAME_LABELS = [
    "Prohibitive\n(be honest)",
    "Pro-social\n(reach agreement)",
    "Minimal\n(no instruction)",
    "Selfish\n(maximize payoff)",
    "Permissive\n(you may exaggerate)",
]
INCS = (0, 80, 250)
INC_LABELS = ["E=0\n(no penalty)", "E=80\n(break-even)", "E=250\n(strict dominance)"]
DIFFS = ("low", "medium", "high")

MODEL_DISPLAY = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5": "GPT-5.5",
    "Gemini-3.1-Pro": "Gemini 3.1 Pro",
    "Grok-4": "Grok 4",
    "Llama-3.3-70B": "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
}


def load_rows():
    by_id = {}
    for p in LOGS:
        log = read_eval_log(p)
        for s in log.samples:
            if s.error:
                continue
            md = (s.metadata or {}).get("scenario", {}).get("metadata", {})
            bs = (s.scores or {}).get("bargaining_commit")
            if bs is None or not isinstance(bs.value, dict):
                continue
            v = bs.value
            if v.get("sample_failed"):
                continue
            by_id[s.id] = dict(
                model=(
                    "DeepSeek-V4-Pro"
                    if md["model"] == "DeepSeek-v3.2"
                    else ("GPT-5.5" if md["model"] == "GPT-5" else md["model"])
                ),
                frame=md["frame"],
                incentive=md["expected_penalty"],
                difficulty=md["difficulty"],
                mr=v.get("manipulation_rate"),
            )
    return list(by_id.values())


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else float("nan")


def mean_stderr(xs):
    """Mean and standard error of mean. Returns (mean, 0) if singleton/empty."""
    xs = [x for x in xs if x is not None]
    if not xs:
        return float("nan"), 0.0
    if len(xs) == 1:
        return float(xs[0]), 0.0
    arr = np.asarray(xs, dtype=float)
    return float(arr.mean()), float(arr.std(ddof=1) / np.sqrt(len(arr)))


def fig1_lied_by_frame(rows):
    fig, ax = plt.subplots(figsize=(11, 6))
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))
    colors = plt.cm.tab10(np.linspace(0, 1, len(models)))
    x = np.arange(len(FRAMES))
    width = 0.13
    for i, m in enumerate(models):
        per_frame = [
            mean_stderr([r["mr"] for r in rows if r["model"] == m and r["frame"] == f])
            for f in FRAMES
        ]
        means = [v[0] for v in per_frame]
        errs = [v[1] for v in per_frame]
        ax.bar(
            x + (i - (len(models) - 1) / 2) * width,
            means,
            width,
            yerr=errs,
            label=MODEL_DISPLAY.get(m, m),
            color=colors[i],
            capsize=2,
            error_kw={"elinewidth": 0.7},
        )
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(FRAME_LABELS, fontsize=9)
    ax.set_ylabel("Lying rate\n(fraction of agents stating >110% of true value)")
    ax.set_title("Lying rate by frame, per model (averaged over penalty and difficulty)")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper left", ncol=2, fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = OUT / "fig1_lied_by_frame.pdf"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def fig2_penalty_collapse(rows):
    fig, ax = plt.subplots(figsize=(10, 6))
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))
    colors = plt.cm.tab10(np.linspace(0, 1, len(models)))

    x = np.arange(len(INCS))
    for i, m in enumerate(models):
        means, errs = [], []
        for inc in INCS:
            mu, se = mean_stderr(
                [
                    r["mr"]
                    for r in rows
                    if r["model"] == m and r["incentive"] == inc and r["frame"] != "prohibitive"
                ]
            )
            means.append(mu)
            errs.append(se)
        ax.errorbar(
            x,
            means,
            yerr=errs,
            marker="o",
            linewidth=2,
            color=colors[i],
            label=MODEL_DISPLAY.get(m, m),
            capsize=3,
            elinewidth=0.8,
        )

    ax.set_xticks(x)
    ax.set_xticklabels(INC_LABELS, fontsize=10)
    ax.set_ylabel("Lying rate\n(averaged across non-prohibitive frames)")
    ax.set_title(
        "Economic penalty collapses lying\n(non-prohibitive frames only; max manipulation gain ≈ 80)"
    )
    ax.set_ylim(-0.05, 1.05)
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    ax.axvline(1, color="gray", linestyle="--", alpha=0.4)
    ax.text(1.02, 0.98, "break-even", fontsize=8, color="gray", ha="left", va="top")
    fig.tight_layout()
    out = OUT / "fig2_penalty_collapse.pdf"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def fig3_frame_penalty_heatmap(rows):
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))
    n = len(models)
    ncols = 3
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 4 * nrows), sharex=True, sharey=True)
    if nrows == 1:
        axes = np.array([axes])
    for ax, m in zip(axes.flat, models):
        grid = np.full((len(FRAMES), len(INCS)), np.nan)
        for i, f in enumerate(FRAMES):
            for j, inc in enumerate(INCS):
                vals = [
                    r["mr"]
                    for r in rows
                    if r["model"] == m and r["frame"] == f and r["incentive"] == inc
                ]
                if vals:
                    grid[i, j] = mean(vals)
        im = ax.imshow(grid, cmap="Reds", aspect="auto", vmin=0, vmax=1)
        ax.set_title(MODEL_DISPLAY.get(m, m))
        ax.set_xticks(range(len(INCS)))
        ax.set_xticklabels([f"E={e}" for e in INCS], fontsize=9)
        ax.set_yticks(range(len(FRAMES)))
        ax.set_yticklabels(FRAMES, fontsize=9)
        for i in range(len(FRAMES)):
            for j in range(len(INCS)):
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
    # Hide unused axes
    for ax in axes.flat[n:]:
        ax.set_visible(False)
    fig.suptitle("Lying rate: frame × penalty per model (red = more lying)", fontsize=13, y=1.00)
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.7, label="Lying rate")
    out = OUT / "fig3_frame_penalty_heatmap.pdf"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def fig4_endpoints(rows):
    fig, ax = plt.subplots(figsize=(9, 5))
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))
    proh_pairs = [
        mean_stderr([r["mr"] for r in rows if r["model"] == m and r["frame"] == "prohibitive"])
        for m in models
    ]
    perm_pairs = [
        mean_stderr([r["mr"] for r in rows if r["model"] == m and r["frame"] == "permissive"])
        for m in models
    ]
    proh = [p[0] for p in proh_pairs]
    proh_err = [p[1] for p in proh_pairs]
    perm = [p[0] for p in perm_pairs]
    perm_err = [p[1] for p in perm_pairs]
    x = np.arange(len(models))
    w = 0.38
    ax.bar(
        x - w / 2,
        proh,
        w,
        yerr=proh_err,
        label='"Be honest"',
        color="#54A24B",
        capsize=3,
        error_kw={"elinewidth": 0.8},
    )
    ax.bar(
        x + w / 2,
        perm,
        w,
        yerr=perm_err,
        label='"You may exaggerate"',
        color="#E45756",
        capsize=3,
        error_kw={"elinewidth": 0.8},
    )
    for i, (p, e) in enumerate(zip(proh, perm)):
        if not np.isnan(e):
            ax.annotate(
                f"+{e - p:.2f}",
                xy=(i, max(p, e) + 0.02),
                ha="center",
                fontsize=9,
                fontweight="bold",
            )
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_DISPLAY.get(m, m) for m in models], rotation=15, ha="right")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Lying rate (averaged over penalty and difficulty)")
    ax.set_title("Endpoint control works: 0% lying under prohibition, up to 60%+ under permission")
    ax.set_ylim(-0.02, 0.75)
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = OUT / "fig4_endpoints.pdf"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    print(f"loaded {len(rows)} scored rows")
    fig1_lied_by_frame(rows)
    fig2_penalty_collapse(rows)
    fig3_frame_penalty_heatmap(rows)
    fig4_endpoints(rows)


if __name__ == "__main__":
    main()
