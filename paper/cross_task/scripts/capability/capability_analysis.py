"""Capability-axis analysis: join model_capability.csv with results.csv to test
whether manipulation rate scales with model capability (ELO) and how it varies
across capability tiers and model generations.

Outputs:
  paper/cross_task/analysis/capability_analysis.json   — machine-readable summary
  paper/cross_task/figures/capability/capability_elo_scatter.png  — per-task ELO vs rate
  paper/cross_task/figures/capability/capability_tier_heatmap.png — tier x frame x task
  paper/cross_task/figures/capability/capability_gen_delta.png    — current vs prev pairs
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]  # paper/cross_task
RESULTS = ROOT / "data" / "results.csv"
CAPABILITY = ROOT / "data" / "model_capability.csv"
ANALYSIS_DIR = ROOT / "analysis"
FIG_DIR = ROOT / "figures" / "capability"

TASKS = ["bargaining", "debate", "village", "sales", "committee", "inbox"]
FRAMES = ["prohibitive", "pro_social", "minimal", "selfish", "permissive"]
TIERS = ["small", "average", "flagship"]

# Within-family generation pairs for paired delta analysis.
GEN_PAIRS = [
    ("haiku35", "haiku45"),
    ("sonnet37", "sonnet46"),
    ("gpt41", "GPT-5.5"),
    ("gpt41mini", "gpt54mini"),
    ("gpt41nano", "gpt54nano"),
]


def load_capability() -> dict[str, dict]:
    out = {}
    with open(CAPABILITY, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["elo"] = float(row["elo"])
            out[row["model"]] = row
    return out


def load_results():
    rows = []
    with open(RESULTS, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            v = row.get("manipulation_metric", "")
            if v in ("", None):
                continue
            try:
                row["manipulation_metric"] = float(v)
            except ValueError:
                continue
            rows.append(row)
    return rows


def per_model_task_rate(rows) -> dict[tuple[str, str], float]:
    bucket = defaultdict(list)
    for r in rows:
        bucket[(r["task"], r["model"])].append(r["manipulation_metric"])
    return {k: mean(v) for k, v in bucket.items()}


def per_model_task_frame_rate(rows) -> dict[tuple[str, str, str], float]:
    bucket = defaultdict(list)
    for r in rows:
        if r.get("frame") not in FRAMES:
            continue
        bucket[(r["task"], r["model"], r["frame"])].append(r["manipulation_metric"])
    return {k: mean(v) for k, v in bucket.items()}


def elo_correlations(cap, rates):
    """Per-task Spearman ρ between ELO and manipulation rate."""
    out = {}
    for task in TASKS:
        xs, ys, models = [], [], []
        for (t, m), rate in rates.items():
            if t != task or m not in cap:
                continue
            xs.append(cap[m]["elo"])
            ys.append(rate)
            models.append(m)
        if len(xs) < 4:
            out[task] = {"n": len(xs), "rho": None, "p": None, "models": models}
            continue
        rho, p = spearmanr(xs, ys)
        out[task] = {
            "n": len(xs),
            "rho": float(rho),
            "p": float(p),
            "models": models,
            "elos": xs,
            "rates": ys,
        }
    return out


def tier_breakdown(cap, rates):
    """Mean rate per (task, tier)."""
    bucket = defaultdict(list)
    for (t, m), rate in rates.items():
        if m not in cap:
            continue
        bucket[(t, cap[m]["tier"])].append(rate)
    return {f"{t}__{tier}": mean(v) for (t, tier), v in bucket.items()}


def tier_frame_breakdown(cap, frame_rates):
    """Mean rate per (task, tier, frame) for the heatmap."""
    bucket = defaultdict(list)
    for (t, m, f), rate in frame_rates.items():
        if m not in cap:
            continue
        bucket[(t, cap[m]["tier"], f)].append(rate)
    return {(t, tier, f): mean(v) for (t, tier, f), v in bucket.items()}


def generation_deltas(cap, rates):
    """For each within-family pair, the rate delta (current - prev) per task."""
    out = {}
    for prev, current in GEN_PAIRS:
        if prev not in cap or current not in cap:
            continue
        deltas = {}
        for task in TASKS:
            p = rates.get((task, prev))
            c = rates.get((task, current))
            if p is None or c is None:
                continue
            deltas[task] = {"prev_rate": p, "current_rate": c, "delta": c - p}
        out[f"{prev}->{current}"] = deltas
    return out


# ----- plotting -----


def plot_elo_scatter(corr, cap, out_path):
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
    for ax, task in zip(axes.flat, TASKS):
        d = corr.get(task, {})
        if not d.get("elos"):
            ax.set_title(f"{task} (no data)")
            ax.axis("off")
            continue
        elos = d["elos"]
        rates = d["rates"]
        models = d["models"]
        tiers = [cap[m]["tier"] for m in models]
        colors = {"small": "#7fb3d5", "average": "#f5b041", "flagship": "#cb4335"}
        ax.scatter(elos, rates, c=[colors[t] for t in tiers], s=80, edgecolors="black")
        for x, y, m in zip(elos, rates, models):
            ax.annotate(m, (x, y), fontsize=7, xytext=(3, 3), textcoords="offset points")
        if len(elos) >= 2:
            slope, intercept = np.polyfit(elos, rates, 1)
            xs = np.array([min(elos), max(elos)])
            ax.plot(xs, slope * xs + intercept, "k--", alpha=0.4, linewidth=1)
        rho = d.get("rho")
        p = d.get("p")
        title = f"{task}  (n={d['n']}, rho={rho:.2f}, p={p:.3f})" if rho is not None else f"{task}  (n={d['n']})"
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("LMArena ELO")
        ax.set_ylabel("manipulation rate")
        ax.grid(True, alpha=0.3)
    fig.suptitle("Manipulation rate vs model capability (ELO), per task", fontsize=13)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_tier_heatmap(tier_frame, out_path):
    fig, axes = plt.subplots(2, 3, figsize=(15, 7), constrained_layout=True)
    for ax, task in zip(axes.flat, TASKS):
        grid = np.full((len(TIERS), len(FRAMES)), np.nan)
        for i, tier in enumerate(TIERS):
            for j, frame in enumerate(FRAMES):
                v = tier_frame.get((task, tier, frame))
                if v is not None:
                    grid[i, j] = v
        im = ax.imshow(grid, aspect="auto", cmap="RdYlBu_r", vmin=0, vmax=1)
        ax.set_xticks(range(len(FRAMES)))
        ax.set_xticklabels(FRAMES, rotation=30, ha="right", fontsize=8)
        ax.set_yticks(range(len(TIERS)))
        ax.set_yticklabels(TIERS, fontsize=9)
        ax.set_title(task, fontsize=10)
        for i in range(len(TIERS)):
            for j in range(len(FRAMES)):
                if not np.isnan(grid[i, j]):
                    ax.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center", fontsize=7,
                            color="white" if grid[i, j] > 0.5 else "black")
        fig.colorbar(im, ax=ax, fraction=0.04)
    fig.suptitle("Manipulation rate by tier x frame, per task", fontsize=13)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def plot_gen_deltas(gen, out_path):
    pairs = list(gen.keys())
    if not pairs:
        return
    fig, ax = plt.subplots(figsize=(12, 5), constrained_layout=True)
    width = 0.13
    x = np.arange(len(pairs))
    for i, task in enumerate(TASKS):
        vals = [gen[p].get(task, {}).get("delta", np.nan) for p in pairs]
        ax.bar(x + (i - 2.5) * width, vals, width, label=task)
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(pairs, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("manipulation_rate (current - prev)")
    ax.set_title("Per-task manipulation-rate change across model generations (within family)")
    ax.legend(fontsize=8, ncol=3)
    ax.grid(True, alpha=0.3, axis="y")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main():
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    cap = load_capability()
    rows = load_results()
    rates = per_model_task_rate(rows)
    frame_rates = per_model_task_frame_rate(rows)

    corr = elo_correlations(cap, rates)
    tiers = tier_breakdown(cap, rates)
    tier_frame = tier_frame_breakdown(cap, frame_rates)
    gen = generation_deltas(cap, rates)

    summary = {
        "elo_spearman_per_task": {t: {k: v for k, v in d.items() if k not in ("elos", "rates")} for t, d in corr.items()},
        "mean_rate_by_task_tier": tiers,
        "generation_pair_deltas": gen,
        "n_models_in_capability": len(cap),
    }
    out_json = ANALYSIS_DIR / "capability_analysis.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    plot_elo_scatter(corr, cap, FIG_DIR / "capability_elo_scatter.png")
    plot_tier_heatmap(tier_frame, FIG_DIR / "capability_tier_heatmap.png")
    plot_gen_deltas(gen, FIG_DIR / "capability_gen_delta.png")

    print(f"Wrote {out_json}")
    print(f"Wrote {FIG_DIR / 'capability_elo_scatter.png'}")
    print(f"Wrote {FIG_DIR / 'capability_tier_heatmap.png'}")
    print(f"Wrote {FIG_DIR / 'capability_gen_delta.png'}")
    print()
    print("ELO-rate Spearman per task:")
    for t in TASKS:
        d = corr.get(t, {})
        if d.get("rho") is not None:
            sig = " *" if d["p"] < 0.05 else ""
            print(f"  {t:12s}  n={d['n']:2d}  rho={d['rho']:+.3f}  p={d['p']:.3f}{sig}")
        else:
            print(f"  {t:12s}  n={d.get('n',0)} (insufficient)")


if __name__ == "__main__":
    main()
