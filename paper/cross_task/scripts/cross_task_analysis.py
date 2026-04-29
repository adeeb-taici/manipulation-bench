"""Cross-task response-surface analysis.

Loads each task's prereg_results.json and assembles:
  1. The cross-task 15-dimensional per-model profile vector (5 tasks × 3 axes).
  2. Per-task aggregate: mean absolute slope across 6 models, per axis.
  3. Per-model profile vector (frame/incentive/difficulty slopes per task).
  4. Cross-task verdict matrix.

Outputs:
  paper/cross_task/cross_task_profiles.json         # machine-readable profiles
  paper/cross_task/cross_task_aggregate.md          # per-task aggregate table
  paper/cross_task/figures/cross_task_heatmap.pdf   # 6-model × 15-dim heatmap
  paper/cross_task/figures/per_task_slopes.pdf      # per-task mean |slope| per axis
  paper/cross_task/figures/per_model_profiles.pdf   # 6 small-multiples per model
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT_DIR = Path("paper/cross_task")
FIG_DIR = OUT_DIR / "figures"

TASKS = [
    ("task1_bargaining", "T1 Bargaining", "lied_rate"),
    ("task2_debate", "T2 Debate", "manipulation_occurred"),
    ("task3_village", "T3 Village", "exploitation_rate"),
    ("task4_sales", "T4 Sales", "manipulation_rate"),
    ("task5_committee", "T5 Committee", "initial_rating_bias"),
]
AXES = ("frame", "incentive", "difficulty")

# Each task's prereg_results.json uses different model-key conventions.
# T1/T2/T3 use full label like "Claude-Opus-4.7"; T4 uses lowercase "claude";
# T5's prereg_results.json wasn't authored under the new analysis script
# (predates it), so we fall back to a manual pulled-numbers map for T5.

CANONICAL_MODELS = (
    "Claude-Opus-4.7",
    "GPT-5.5",
    "Gemini-3.1-Pro",
    "Grok-4",
    "Llama-3.3-70B",
    "DeepSeek-V4-Pro",
)

T4_MODEL_MAP = {
    "claude": "Claude-Opus-4.7",
    "gpt55": "GPT-5.5",
    "gemini": "Gemini-3.1-Pro",
    "grok": "Grok-4",
    "llama": "Llama-3.3-70B",
    "deepseek": "DeepSeek-V4-Pro",
}

# Task 5's analysis script doesn't emit prereg_results.json in the same shape,
# so embed its slopes directly from results.md §A.4 (recompute from
# paper/task5_committee/scripts/task5_prereg_analysis.py if data changes). Updated 2026-04-26
# to reflect the GPT-5 → GPT-5.5 swap (PREREG Amendment A3).
T5_SLOPES = {
    "Claude-Opus-4.7": {"frame": 0.281, "incentive": 0.117, "difficulty": -0.911},
    "GPT-5.5": {"frame": 0.307, "incentive": 0.202, "difficulty": -0.676},
    "Gemini-3.1-Pro": {"frame": 0.434, "incentive": 0.430, "difficulty": 0.016},
    "Grok-4": {"frame": 0.372, "incentive": 0.135, "difficulty": -0.537},
    "Llama-3.3-70B": {"frame": 0.287, "incentive": 0.018, "difficulty": -0.713},
    "DeepSeek-V4-Pro": {"frame": 0.280, "incentive": 0.181, "difficulty": -0.765},
}


def load_task_slopes(task_dir: str) -> dict:
    """Return {canonical_model: {axis: slope}} for a given task."""
    p = Path("paper") / task_dir / "analysis" / "prereg_results.json"
    if task_dir == "task5_committee":
        # T5 is hardcoded above
        return T5_SLOPES
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    slopes_by_key = d.get("sensitivity_slopes", {})
    out = {}
    for key, slopes in slopes_by_key.items():
        # T4 uses lowercase keys; map to canonical
        canonical = T4_MODEL_MAP.get(key, key)
        if canonical not in CANONICAL_MODELS:
            continue
        out[canonical] = {
            "frame": slopes.get("frame_slope", float("nan")),
            "incentive": slopes.get("incentive_slope", float("nan")),
            "difficulty": slopes.get("difficulty_slope", float("nan")),
        }
    return out


def assemble_profiles() -> dict:
    """{model: {task_dir: {axis: slope}}}."""
    profiles = {m: {} for m in CANONICAL_MODELS}
    for task_dir, _disp, _metric in TASKS:
        slopes = load_task_slopes(task_dir)
        for m in CANONICAL_MODELS:
            profiles[m][task_dir] = slopes.get(m, {a: float("nan") for a in AXES})
    return profiles


def task_aggregate(profiles: dict) -> list[dict]:
    """Per-task: mean |slope| per axis, across 6 models, plus stderr."""
    rows = []
    for task_dir, disp, _metric in TASKS:
        agg = {"task_dir": task_dir, "task": disp}
        for axis in AXES:
            vals = []
            for m in CANONICAL_MODELS:
                v = profiles[m][task_dir].get(axis)
                if v is not None and not (isinstance(v, float) and math.isnan(v)):
                    vals.append(abs(v))
            agg[axis] = sum(vals) / len(vals) if vals else float("nan")
            if len(vals) > 1:
                arr = np.asarray(vals, dtype=float)
                agg[f"{axis}_stderr"] = float(arr.std(ddof=1) / np.sqrt(len(arr)))
            else:
                agg[f"{axis}_stderr"] = 0.0
        # Identify dominant axis
        ranked = sorted(((agg[a], a) for a in AXES), reverse=True)
        agg["dominant_axis"] = ranked[0][1]
        agg["dominant_value"] = ranked[0][0]
        agg["second_axis"] = ranked[1][1]
        agg["second_value"] = ranked[1][0]
        agg["dominance_ratio"] = (
            ranked[0][0] / ranked[1][0]
            if ranked[1][0] > 0 and not math.isnan(ranked[1][0])
            else float("inf")
        )
        rows.append(agg)
    return rows


def cross_task_heatmap(profiles: dict, out_path: Path) -> None:
    """6-model × 15-dim heatmap of |slope| values."""
    grid = np.full((len(CANONICAL_MODELS), len(TASKS) * len(AXES)), np.nan)
    col_labels = []
    for ti, (td, disp, _) in enumerate(TASKS):
        for ai, axis in enumerate(AXES):
            col_labels.append(f"{disp[:2]}-{axis[:4]}")
            for mi, m in enumerate(CANONICAL_MODELS):
                v = profiles[m][td].get(axis)
                if v is not None and not (isinstance(v, float) and math.isnan(v)):
                    grid[mi, ti * 3 + ai] = abs(v)

    fig, ax = plt.subplots(figsize=(13, 5))
    # Different tasks have different metric scales — Committee bias is 0-20,
    # others are rate 0-1. Per-task column normalization to compare *within* a
    # task across models, but show absolute slope on the colorbar.
    # Use task-relative normalization for color via task-per-task vmax.
    per_task_max = []
    for ti in range(len(TASKS)):
        block = grid[:, ti * 3 : ti * 3 + 3]
        per_task_max.append(np.nanmax(block) if not np.all(np.isnan(block)) else 1.0)

    # For visual consistency, scale each task's columns to [0, 1] of its block max
    norm_grid = grid.copy()
    for ti in range(len(TASKS)):
        block = grid[:, ti * 3 : ti * 3 + 3]
        denom = per_task_max[ti] if per_task_max[ti] > 0 else 1.0
        norm_grid[:, ti * 3 : ti * 3 + 3] = block / denom

    im = ax.imshow(norm_grid, cmap="Reds", aspect="auto", vmin=0, vmax=1)
    ax.set_yticks(range(len(CANONICAL_MODELS)))
    ax.set_yticklabels(CANONICAL_MODELS)
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=45, ha="right", fontsize=8)
    # Vertical separators between tasks
    for ti in range(1, len(TASKS)):
        ax.axvline(ti * 3 - 0.5, color="black", linewidth=1.0)

    # Annotate with absolute slope values
    for mi in range(len(CANONICAL_MODELS)):
        for ci in range(len(col_labels)):
            v = grid[mi, ci]
            if not np.isnan(v):
                norm_v = norm_grid[mi, ci]
                ax.text(
                    ci,
                    mi,
                    f"{v:.2f}",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white" if norm_v > 0.5 else "black",
                )

    ax.set_title(
        "Cross-task per-model |slope| profile (color: per-task max-normalized; cell value: absolute |slope|)"
    )
    fig.colorbar(im, ax=ax, shrink=0.7, label="Within-task relative |slope|")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out_path}")


def per_task_slopes_chart(agg: list[dict], out_path: Path) -> None:
    """Bar chart: per-task mean |slope| per axis."""
    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(TASKS))
    width = 0.27
    colors = {"frame": "#4C78A8", "incentive": "#F58518", "difficulty": "#54A24B"}
    for i, axis in enumerate(AXES):
        vals = [a[axis] for a in agg]
        errs = [a.get(f"{axis}_stderr", 0.0) for a in agg]
        ax.bar(
            x + (i - 1) * width,
            vals,
            width,
            yerr=errs,
            label=axis,
            color=colors[axis],
            capsize=3,
            error_kw={"elinewidth": 0.8},
        )

    ax.set_xticks(x)
    ax.set_xticklabels([a["task"] for a in agg], fontsize=10)
    ax.set_ylabel("Mean |slope| across 6 models  (error = stderr across models)")
    ax.set_title(
        "Cross-task aggregate: which axis dominates per task?\n"
        "Frame dominates only in Bargaining + Village; difficulty dominates in Debate / Sales / Committee."
    )
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out_path}")


def per_model_profiles_chart(profiles: dict, out_path: Path) -> None:
    """Small-multiples: 6 panels (one per model), each showing per-task |slope|
    on each axis. Helps spot per-model cross-task signatures."""
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), sharey=True)
    colors = {"frame": "#4C78A8", "incentive": "#F58518", "difficulty": "#54A24B"}
    for ax, m in zip(axes.flat, CANONICAL_MODELS):
        x = np.arange(len(TASKS))
        width = 0.27
        for i, axis in enumerate(AXES):
            vals = []
            for td, _, _ in TASKS:
                v = profiles[m][td].get(axis)
                vals.append(
                    abs(v)
                    if (v is not None and not (isinstance(v, float) and math.isnan(v)))
                    else 0
                )
            ax.bar(x + (i - 1) * width, vals, width, label=axis, color=colors[axis])
        ax.set_xticks(x)
        ax.set_xticklabels([t[1] for t in TASKS], fontsize=8, rotation=15)
        ax.set_title(m)
        ax.grid(axis="y", alpha=0.3)
    axes[0, 0].set_ylabel("Mean |slope|")
    axes[1, 0].set_ylabel("Mean |slope|")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.98, 0.98))
    fig.suptitle(
        "Per-model cross-task |slope| profiles (15-dim per-model vector visualized)",
        fontsize=13,
        y=1.00,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out_path}")


def emit_aggregate_md(agg: list[dict], profiles: dict, out_path: Path) -> None:
    lines = [
        "# Cross-task response-surface aggregate",
        "",
        "Auto-generated from each task's `paper/<task>/analysis/prereg_results.json` (T1-T4) and embedded T5 numbers (since T5 uses a different per-model JSON shape). See [paper/cross_task/scripts/cross_task_analysis.py](paper/cross_task/scripts/cross_task_analysis.py).",
        "",
        "## Per-task aggregate: mean |slope| across 6 models",
        "",
        "| Task | Headline metric | Frame | Incentive | Difficulty | Dominant axis | Dominance ratio (top/2nd) |",
        "|---|---|---:|---:|---:|---|---:|",
    ]
    for a, (td, disp, metric) in zip(agg, TASKS):
        ratio = a["dominance_ratio"]
        ratio_s = f"{ratio:.1f}×" if not math.isinf(ratio) else "∞"
        lines.append(
            f"| {disp} | `{metric}` | {a['frame']:.3f} | {a['incentive']:.3f} | {a['difficulty']:.3f} | **{a['dominant_axis']}** | {ratio_s} |"
        )
    lines += [
        "",
        "Notes on metric scales:",
        "- T1 / T2 / T3 / T4 use rates in [0, 1]; slopes are also in rate-per-axis-step units.",
        "- T5 uses bias on a 0–20 rating scale; its slopes are in standardized (per-pooled-SD) units, larger in absolute magnitude than the rate-based slopes.",
        "- For cross-task comparison of *which axis dominates within a task*, the relative size of slopes within a row is what matters, not the absolute number.",
        "",
        "## Per-model 15-dim profile vector",
        "",
        "Each model's profile = 5 tasks × 3 axes = 15 entries (signed slopes).",
        "",
    ]
    for m in CANONICAL_MODELS:
        lines.append(f"### {m}")
        lines.append("")
        lines.append("| Task | Frame slope | Incentive slope | Difficulty slope |")
        lines.append("|---|---:|---:|---:|")
        for td, disp, _ in TASKS:
            s = profiles[m][td]
            f_v = s.get("frame")
            i_v = s.get("incentive")
            d_v = s.get("difficulty")
            f_s = f"{f_v:+.3f}" if isinstance(f_v, (int, float)) and not math.isnan(f_v) else "—"
            i_s = f"{i_v:+.3f}" if isinstance(i_v, (int, float)) and not math.isnan(i_v) else "—"
            d_s = f"{d_v:+.3f}" if isinstance(d_v, (int, float)) and not math.isnan(d_v) else "—"
            lines.append(f"| {disp} | {f_s} | {i_s} | {d_s} |")
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"saved {out_path}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    profiles = assemble_profiles()
    agg = task_aggregate(profiles)

    # Save machine-readable
    def jsafe(x):
        if isinstance(x, dict):
            return {k: jsafe(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [jsafe(v) for v in x]
        if isinstance(x, float) and math.isnan(x):
            return None
        if isinstance(x, float) and math.isinf(x):
            return None
        return x

    out_json = OUT_DIR / "cross_task_profiles.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(jsafe(dict(profiles=profiles, aggregate=agg)), f, indent=2, default=str)
    print(f"saved {out_json}")

    emit_aggregate_md(agg, profiles, OUT_DIR / "cross_task_aggregate.md")
    cross_task_heatmap(profiles, FIG_DIR / "cross_task_heatmap.pdf")
    per_task_slopes_chart(agg, FIG_DIR / "per_task_slopes.pdf")
    per_model_profiles_chart(profiles, FIG_DIR / "per_model_profiles.pdf")

    # Print headline table
    print()
    print("Per-task aggregate:")
    for a, (td, disp, metric) in zip(agg, TASKS):
        ratio = a["dominance_ratio"]
        ratio_s = f"{ratio:.1f}x" if not math.isinf(ratio) else "inf"
        print(
            f"  {disp:<14}  frame={a['frame']:.3f}  inc={a['incentive']:.3f}  diff={a['difficulty']:.3f}   dominant={a['dominant_axis']} ({ratio_s})"
        )


if __name__ == "__main__":
    main()
