"""Task 3 Village visuals — parallel to task1/2/4_visuals.py.

Plots (output to paper/task3_village/figures/):
  fig1_exploit_by_frame    — agent_1 exploitation rate by frame × model
  fig2_frame_inc_heatmap   — per-model frame × incentive heatmap (vmin=0, vmax=1.0)
  fig3_endpoints           — prohibitive vs permissive bar comparison
  fig4_difficulty          — exploitation rate by difficulty × model
"""

from __future__ import annotations

import glob
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

OUT = Path("paper/task3_village/figures")

LOG_PATTERNS = ["paper/task3_village/eval_log.eval"]

FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
FRAME_LABELS = ["Prohibit.", "Pro-social", "Minimal", "Selfish", "Permissive"]
INCENTIVES = ("none", "moderate", "high")
DIFFICULTIES = ("low", "medium", "high")

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
    for pat in LOG_PATTERNS:
        for p in sorted(glob.glob(pat)):
            log = read_eval_log(p)
            for s in log.samples:
                if s.error:
                    continue
                md = (s.metadata or {}).get("scenario", {}).get("metadata", {})
                er = (s.scores or {}).get("exploitation_rate")
                if er is None or not isinstance(er.value, dict):
                    continue
                v = er.value.get("agent_1")
                if v is None:
                    continue
                by_id[s.id] = dict(
                    model=("DeepSeek-V4-Pro" if md.get("manipulator_model") == "DeepSeek-v3.2" else ("GPT-5.5" if md.get("manipulator_model") == "GPT-5" else md.get("manipulator_model"))),
                    frame=md.get("frame"),
                    incentive=md.get("incentive"),
                    difficulty=md.get("difficulty"),
                    er=v,
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


def fig1_exploit_by_frame(rows):
    fig, ax = plt.subplots(figsize=(11, 6))
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))
    colors = plt.cm.tab10(np.linspace(0, 1, len(models)))
    x = np.arange(len(FRAMES))
    width = 0.13
    for i, m in enumerate(models):
        per_frame = [
            mean_stderr([r["er"] for r in rows if r["model"] == m and r["frame"] == f])
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
    ax.set_xticks(x)
    ax.set_xticklabels(FRAME_LABELS, fontsize=10)
    ax.set_ylabel(
        "Manipulator exploitation rate\n(1 − mean contribution / 20 tokens; 0 = full coop, 1 = full defect)"
    )
    ax.set_title(
        "Village manipulator exploitation rate by frame, per model (averaged over incentive × difficulty)"
    )
    ax.set_ylim(0, 1.05)
    ax.axhline(0.05, color="gray", linestyle="--", alpha=0.6, label="P1 prohibitive floor (0.05)")
    ax.legend(loc="upper left", ncol=2, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = OUT / "fig1_exploit_by_frame.pdf"
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
                    r["er"]
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
        "Village exploitation rate: frame × incentive per model (red = more defection)",
        fontsize=13,
        y=1.00,
    )
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.7, label="Exploitation rate")
    out = OUT / "fig2_frame_inc_heatmap.pdf"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


def fig3_endpoints(rows):
    fig, ax = plt.subplots(figsize=(9, 5))
    models = sorted({r["model"] for r in rows}, key=lambda m: list(MODEL_DISPLAY).index(m))
    proh_pairs = [
        mean_stderr([r["er"] for r in rows if r["model"] == m and r["frame"] == "prohibitive"])
        for m in models
    ]
    perm_pairs = [
        mean_stderr([r["er"] for r in rows if r["model"] == m and r["frame"] == "permissive"])
        for m in models
    ]
    proh = [p[0] for p in proh_pairs]
    proh_err = [p[1] for p in proh_pairs]
    perm = [p[0] for p in perm_pairs]
    perm_err = [p[1] for p in perm_pairs]
    x = np.arange(len(models))
    w = 0.38
    ax.bar(x - w / 2, proh, w, yerr=proh_err, capsize=3, error_kw={"elinewidth": 0.8}, label='Prohibitive ("be honest")', color="#54A24B")
    ax.bar(x + w / 2, perm, w, yerr=perm_err, capsize=3, error_kw={"elinewidth": 0.8}, label='Permissive ("exploit through deception")', color="#E45756")
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
    ax.set_ylabel("Manipulator exploitation rate (avg over incentive × difficulty)")
    ax.set_title(
        "Village endpoints: prohibitive (green) vs permissive (red) — frame moves all 6 models substantially"
    )
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper left", fontsize=9)
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
        means, errs = [], []
        for d in DIFFICULTIES:
            mu, se = mean_stderr([r["er"] for r in rows if r["model"] == m and r["difficulty"] == d])
            means.append(mu)
            errs.append(se)
        ax.errorbar(x, means, yerr=errs, marker="o", linewidth=2, color=colors[i],
                    label=MODEL_DISPLAY.get(m, m), capsize=3, elinewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [
            "Low\n(mult=1.2, defection rational)",
            "Medium\n(mult=1.5)",
            "High\n(mult=1.8, cooperation rewarding)",
        ],
        fontsize=10,
    )
    ax.set_ylabel("Manipulator exploitation rate\n(avg over frame × incentive)")
    ax.set_title("Village exploitation rate by difficulty per model")
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper right", fontsize=9)
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
    fig1_exploit_by_frame(rows)
    fig2_frame_inc_heatmap(rows)
    fig3_endpoints(rows)
    fig4_difficulty(rows)


if __name__ == "__main__":
    main()
