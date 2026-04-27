"""Cohen's d secondary analysis for T1-T4 against prohibitive baseline.

For each cell ``(model, frame, incentive, difficulty)``, compute:
    d = (mean_current − mean_reference) / pooled_SD
where reference is the same (model, incentive, difficulty) with
frame=prohibitive.

Saturated-cell handling: where pooled_SD < 1e-6, report the raw mean
difference instead of d (with a footnote-friendly flag).

Outputs:
  paper/task<N>/<dir>/analysis/cohens_d.json
  paper/task<N>/<dir>/figures/fig6_cohens_d_heatmap.png
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from statistics import pstdev

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

TASKS = [
    {
        "name": "T1 Bargaining",
        "dir": "task1_bargaining",
        "log": "paper/task1_bargaining/eval_log.eval",
        "scorer": "bargaining_commit",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": (0, 80, 250),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {
            "frame": "frame",
            "incentive": "expected_penalty",
            "difficulty": "difficulty",
        },
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
    },
    {
        "name": "T2 Debate",
        "dir": "task2_debate",
        "log": "paper/task2_debate/eval_log.eval",
        "scorer": "ground_truth_persuasion",
        "metric_field": "manipulation_occurred",
        "scenario_model_key": "manipulator_model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {"frame": "frame", "incentive": "incentive", "difficulty": "difficulty"},
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
    },
    {
        "name": "T3 Village",
        "dir": "task3_village",
        "log": "paper/task3_village/eval_log.eval",
        "scorer": "exploitation_rate",
        "metric_field": "agent_1",
        "scenario_model_key": "manipulator_model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {"frame": "frame", "incentive": "incentive", "difficulty": "difficulty"},
        "metadata_at_top": False,
        "model_remap": {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"},
    },
    {
        "name": "T4 Sales",
        "dir": "task4_sales",
        "log": "paper/task4_sales/eval_log.eval",
        "scorer": "sales_classifier",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "frame_levels": ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
        "incentive_levels": ("none", "moderate", "high"),
        "difficulty_levels": ("low", "medium", "high"),
        "axis_keys": {"frame": "frame", "incentive": "incentive", "difficulty": "difficulty"},
        "metadata_at_top": True,
        "model_remap": {"deepseek": "deepseek_v4", "gpt5": "gpt55"},
    },
]

DISPLAY = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5": "GPT-5.5",
    "Gemini-3.1-Pro": "Gemini 3.1 Pro",
    "Grok-4": "Grok 4",
    "Llama-3.3-70B": "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
    "claude": "Claude Opus 4.7",
    "gpt55": "GPT-5.5",
    "gemini": "Gemini 3.1 Pro",
    "grok": "Grok 4",
    "llama": "Llama 3.3 70B",
    "deepseek_v4": "DeepSeek V4 Pro",
}

CANONICAL_ORDER = {
    "Claude-Opus-4.7": 0,
    "GPT-5.5": 1,
    "Gemini-3.1-Pro": 2,
    "Grok-4": 3,
    "Llama-3.3-70B": 4,
    "DeepSeek-V4-Pro": 5,
    "claude": 0,
    "gpt55": 1,
    "gemini": 2,
    "grok": 3,
    "llama": 4,
    "deepseek_v4": 5,
}


def load_rows(task: dict) -> list[dict]:
    log = read_eval_log(task["log"])
    rows = []
    for s in log.samples or []:
        if s.error:
            continue
        if task.get("metadata_at_top"):
            md = s.metadata or {}
        else:
            md = (s.metadata or {}).get("scenario", {}).get("metadata", {})
        sc = (s.scores or {}).get(task["scorer"])
        if sc is None or not isinstance(sc.value, dict):
            continue
        v = sc.value
        if v.get("sample_failed"):
            continue
        metric = v.get(task["metric_field"])
        if metric is None:
            continue
        model = md.get(task["scenario_model_key"])
        if model in task.get("model_remap", {}):
            model = task["model_remap"][model]
        row = {"model": model, "metric": metric}
        for axis_name, sm_field in task["axis_keys"].items():
            row[axis_name] = md.get(sm_field)
        rows.append(row)
    return rows


def cohens_d_per_cell(rows: list[dict], task: dict) -> list[dict]:
    """For each (model, frame!=prohibitive, incentive, difficulty), compute d
    against the (model, incentive, difficulty, frame=prohibitive) reference."""
    out = []
    by_cell = defaultdict(list)
    for r in rows:
        key = (r["model"], r["frame"], r["incentive"], r["difficulty"])
        by_cell[key].append(r["metric"])
    for model in {r["model"] for r in rows}:
        for inc in task["incentive_levels"]:
            for diff in task["difficulty_levels"]:
                ref_vals = by_cell.get((model, "prohibitive", inc, diff), [])
                if len(ref_vals) < 2:
                    continue
                ref_mean = sum(ref_vals) / len(ref_vals)
                ref_sd = pstdev(ref_vals)
                for f in task["frame_levels"]:
                    if f == "prohibitive":
                        continue
                    cur = by_cell.get((model, f, inc, diff), [])
                    if len(cur) < 2:
                        continue
                    cur_mean = sum(cur) / len(cur)
                    cur_sd = pstdev(cur)
                    n1, n2 = len(cur), len(ref_vals)
                    pooled = (
                        math.sqrt(((n1 - 1) * cur_sd**2 + (n2 - 1) * ref_sd**2) / (n1 + n2 - 2))
                        if (n1 + n2 - 2) > 0
                        else 0
                    )
                    if pooled < 1e-6:
                        d = float("nan")  # saturated; report raw diff instead
                        saturated = True
                    else:
                        d = (cur_mean - ref_mean) / pooled
                        saturated = False
                    out.append(
                        {
                            "model": model,
                            "frame": f,
                            "incentive": inc,
                            "difficulty": diff,
                            "ref_mean": ref_mean,
                            "cur_mean": cur_mean,
                            "raw_diff": cur_mean - ref_mean,
                            "pooled_sd": pooled,
                            "cohens_d": d,
                            "saturated": saturated,
                        }
                    )
    return out


def fig_cohens_d_heatmap(task: dict, d_records: list[dict]) -> None:
    """For each model, a frame × (incentive, difficulty) heatmap of d values."""
    models = sorted({r["model"] for r in d_records}, key=lambda m: CANONICAL_ORDER.get(m, 99))
    n_inc = len(task["incentive_levels"])
    n_diff = len(task["difficulty_levels"])
    n_frame = len(task["frame_levels"]) - 1  # exclude prohibitive (reference)
    # Per model: frame (4 rows) × (inc × diff = 9 cols) heatmap
    fig, axes = plt.subplots(2, 3, figsize=(16, 8), sharey=True)
    for ax, model in zip(axes.flat, models):
        grid = np.full((n_frame, n_inc * n_diff), np.nan)
        for fi, f in enumerate([fl for fl in task["frame_levels"] if fl != "prohibitive"]):
            for ci, inc in enumerate(task["incentive_levels"]):
                for di, diff in enumerate(task["difficulty_levels"]):
                    rec = next(
                        (
                            r
                            for r in d_records
                            if r["model"] == model
                            and r["frame"] == f
                            and r["incentive"] == inc
                            and r["difficulty"] == diff
                        ),
                        None,
                    )
                    if rec is None:
                        continue
                    if rec["saturated"]:
                        # use raw diff scaled to ~d range (assume d ≈ 5 at saturation)
                        v = 5 if rec["raw_diff"] > 0 else -5
                    else:
                        v = rec["cohens_d"]
                    grid[fi, ci * n_diff + di] = v

        im = ax.imshow(grid, cmap="RdBu_r", vmin=-5, vmax=5, aspect="auto")
        ax.set_title(DISPLAY.get(model, model), fontsize=10)
        ax.set_yticks(range(n_frame))
        ax.set_yticklabels([f for f in task["frame_levels"] if f != "prohibitive"], fontsize=8)
        col_labels = []
        for inc in task["incentive_levels"]:
            for diff in task["difficulty_levels"]:
                col_labels.append(f"{inc}\n{diff}")
        ax.set_xticks(range(n_inc * n_diff))
        ax.set_xticklabels(col_labels, fontsize=6, rotation=0)
        # Vertical separator between incentive groups
        for k in range(1, n_inc):
            ax.axvline(k * n_diff - 0.5, color="black", linewidth=0.8)
        for fi in range(n_frame):
            for j in range(n_inc * n_diff):
                v = grid[fi, j]
                if not np.isnan(v):
                    ax.text(
                        j,
                        fi,
                        f"{v:.1f}",
                        ha="center",
                        va="center",
                        fontsize=7,
                        color="white" if abs(v) > 2.5 else "black",
                    )

    # Hide unused axes
    for ax in axes.flat[len(models) :]:
        ax.set_visible(False)
    fig.colorbar(
        im,
        ax=axes.ravel().tolist(),
        shrink=0.7,
        label="Cohen's d (capped at ±5; saturated cells flagged at ±5)",
    )
    fig.suptitle(
        f"{task['name']} — Cohen's d for each cell vs. prohibitive baseline (same incentive × difficulty)\nRows: frames (excluding prohibitive). Columns: (incentive, difficulty) pairs.",
        fontsize=12,
        y=1.00,
    )
    fig.tight_layout()
    out = Path("paper") / task["dir"] / "figures" / "fig6_cohens_d_heatmap.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {out}")


def main():
    for task in TASKS:
        print(f"\n=== {task['name']} ===")
        rows = load_rows(task)
        print(f"  loaded {len(rows)} rows")
        records = cohens_d_per_cell(rows, task)
        print(f"  computed {len(records)} cell-level d values")

        out_dir = Path("paper") / task["dir"] / "analysis"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_json = out_dir / "cohens_d.json"

        def sanitize(x):
            if isinstance(x, dict):
                return {k: sanitize(v) for k, v in x.items()}
            if isinstance(x, (list, tuple)):
                return [sanitize(v) for v in x]
            if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
                return None
            return x

        # Summary aggregates: mean |d| per model, max d per model
        from collections import defaultdict as dd

        by_model = dd(list)
        for r in records:
            if not math.isnan(r["cohens_d"]):
                by_model[r["model"]].append(r["cohens_d"])
        summary = {
            m: {
                "mean_abs_d": sum(abs(x) for x in xs) / len(xs) if xs else float("nan"),
                "max_d": max(xs) if xs else float("nan"),
                "n_cells": len(xs),
            }
            for m, xs in by_model.items()
        }

        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(
                sanitize({"per_cell": records, "summary": summary, "task": task["name"]}),
                f,
                indent=2,
                default=str,
            )
        print(f"  wrote {out_json}")

        fig_cohens_d_heatmap(task, records)


if __name__ == "__main__":
    main()
