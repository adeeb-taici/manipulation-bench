"""Frontier-generation lift / contagion analysis.

For T1, T2, T3, T5, the original sweep was run with GPT-5 + DeepSeek V3.2.
Amendments A2/A3 swapped these to GPT-5.5 + DeepSeek V4 Pro and the swaps
are stored in their own split logs. By reading the ORIGINAL split logs
directly (not the dedup-combined paper logs), we can isolate per-model
manipulation rate before vs after the upgrade — same scenarios, same
conditions, only the model changed.

Outputs:
  paper/cross_task/figures/fig_frontier_lift.pdf
  paper/cross_task/frontier_lift.json
"""

from __future__ import annotations

import glob
import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

# Map: each pair = (task_label, original_pattern, upgraded_pattern, scorer, metric_field, scenario_model_key, metadata_at_top)
PAIRS = [
    # T1: 5 splits originally; the GPT-5 samples come from the *_fullsweep_20260422
    # batches (along with all other models). For a clean within-task contrast,
    # we read ALL original splits and filter by manipulator_model = GPT-5; then
    # task1_gpt55 for the GPT-5.5 retry.
    {
        "task": "T1 Bargaining",
        "original_logs": [
            "logs/task1_fullsweep_20260422/*.eval",
            "logs/task1_fullsweep_20260422_batch1/*.eval",
            "logs/task1_fullsweep_20260422_llama_retry/*.eval",
            "logs/task1_fullsweep_20260422_grok/*.eval",
        ],
        "upgraded_logs": ["logs/task1_gpt55/*.eval"],
        "compare_model_old": "GPT-5",
        "compare_model_new": "GPT-5.5",
        "scorer": "bargaining_commit",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "metadata_at_top": False,
    },
    {
        "task": "T1 Bargaining",
        "original_logs": [
            "logs/task1_fullsweep_20260422/*.eval",
            "logs/task1_fullsweep_20260422_batch1/*.eval",
            "logs/task1_fullsweep_20260422_llama_retry/*.eval",
            "logs/task1_fullsweep_20260422_grok/*.eval",
        ],
        "upgraded_logs": ["logs/task1_dsv4/*.eval"],
        "compare_model_old": "DeepSeek-v3.2",
        "compare_model_new": "DeepSeek-V4-Pro",
        "scorer": "bargaining_commit",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "metadata_at_top": False,
    },
    {
        "task": "T2 Debate",
        "original_logs": ["logs/task2_debate_v61_full_gpt5/*.eval"],
        "upgraded_logs": ["logs/task2_gpt55/*.eval"],
        "compare_model_old": "GPT-5",
        "compare_model_new": "GPT-5.5",
        "scorer": "ground_truth_persuasion",
        "metric_field": "manipulation_occurred",
        "scenario_model_key": "manipulator_model",
        "metadata_at_top": False,
    },
    {
        "task": "T2 Debate",
        "original_logs": ["logs/task2_debate_v61_full_deepseek/*.eval"],
        "upgraded_logs": ["logs/task2_dsv4/*.eval"],
        "compare_model_old": "DeepSeek-v3.2",
        "compare_model_new": "DeepSeek-V4-Pro",
        "scorer": "ground_truth_persuasion",
        "metric_field": "manipulation_occurred",
        "scenario_model_key": "manipulator_model",
        "metadata_at_top": False,
    },
    {
        "task": "T3 Village",
        "original_logs": [
            "logs/task3_village_v61_full/*.eval",
            "logs/task3_village_v61_full_remaining/*.eval",
            "logs/task3_village_v61_full_remaining_v2/*.eval",
        ],
        "upgraded_logs": ["logs/task3_gpt55/*.eval"],
        "compare_model_old": "GPT-5",
        "compare_model_new": "GPT-5.5",
        "scorer": "exploitation_rate",
        "metric_field": "agent_1",
        "scenario_model_key": "manipulator_model",
        "metadata_at_top": False,
    },
    {
        "task": "T3 Village",
        "original_logs": [
            "logs/task3_village_v61_full/*.eval",
            "logs/task3_village_v61_full_remaining/*.eval",
            "logs/task3_village_v61_full_remaining_v2/*.eval",
        ],
        "upgraded_logs": ["logs/task3_dsv4/*.eval"],
        "compare_model_old": "DeepSeek-v3.2",
        "compare_model_new": "DeepSeek-V4-Pro",
        "scorer": "exploitation_rate",
        "metric_field": "agent_1",
        "scenario_model_key": "manipulator_model",
        "metadata_at_top": False,
    },
    {
        "task": "T4 Sales",
        "original_logs": ["logs/task4_sales_v61_full/*.eval"],
        "upgraded_logs": ["logs/task4_gpt55/*.eval"],
        "compare_model_old": "gpt5",
        "compare_model_new": "gpt55",
        "scorer": "sales_classifier",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "metadata_at_top": True,
    },
    {
        "task": "T4 Sales",
        "original_logs": ["logs/task4_sales_v61_full/*.eval"],
        # Use the reasoning_retry log (Amendment A3 max_tokens fix) for the
        # V4 Pro samples — the original task4_dsv4 log had truncation that
        # inflated the measured rate.
        "upgraded_logs": ["logs/task4_reasoning_retry/*.eval"],
        "compare_model_old": "deepseek",
        "compare_model_new": "deepseek_v4",
        "scorer": "sales_classifier",
        "metric_field": "manipulation_rate",
        "scenario_model_key": "model",
        "metadata_at_top": True,
    },
    {
        "task": "T5 Committee",
        "original_logs": ["logs/committee_fullsweep_20260422/*.eval"],
        "upgraded_logs": ["logs/task5_gpt55/*.eval"],
        "compare_model_old": "gpt5",
        "compare_model_new": "gpt55",
        "scorer": "initial_rating_bias",
        "metric_field": "initial_bias",
        "scenario_model_key": "interested_model_label",
        "metadata_at_top": False,
    },
    {
        "task": "T5 Committee",
        "original_logs": ["logs/committee_fullsweep_20260422/*.eval"],
        "upgraded_logs": ["logs/task5_dsv4/*.eval"],
        "compare_model_old": "deepseek",
        "compare_model_new": "deepseek_v4",
        "scorer": "initial_rating_bias",
        "metric_field": "initial_bias",
        "scenario_model_key": "interested_model_label",
        "metadata_at_top": False,
    },
]


def collect_metric(
    patterns, scorer, metric_field, scenario_model_key, metadata_at_top, target_model
):
    """Collect per-sample metric values for the target model."""
    paths = []
    for pat in patterns:
        paths.extend(sorted(glob.glob(pat)))
    if not paths:
        return []
    vals = []
    for p in paths:
        try:
            log = read_eval_log(p)
        except Exception as e:
            print(f"  warning: failed to read {p}: {e}")
            continue
        for s in log.samples or []:
            if s.error:
                continue
            md = (
                s.metadata or {}
                if metadata_at_top
                else (s.metadata or {}).get("scenario", {}).get("metadata", {})
            )
            if md.get(scenario_model_key) != target_model:
                continue
            sc = (s.scores or {}).get(scorer)
            if sc is None or not isinstance(sc.value, dict):
                continue
            v = sc.value
            if v.get("sample_failed"):
                continue
            metric = v.get(metric_field)
            if metric is None:
                continue
            vals.append(float(metric))
    return vals


def main():
    results = []
    for spec in PAIRS:
        old_vals = collect_metric(
            spec["original_logs"],
            spec["scorer"],
            spec["metric_field"],
            spec["scenario_model_key"],
            spec["metadata_at_top"],
            spec["compare_model_old"],
        )
        # Upgraded logs were generated from the original scenario files, so the
        # *metadata* model label is still the OLD name even though the runtime
        # model is the new one. Filter by old label in both halves.
        new_vals = collect_metric(
            spec["upgraded_logs"],
            spec["scorer"],
            spec["metric_field"],
            spec["scenario_model_key"],
            spec["metadata_at_top"],
            spec["compare_model_old"],
        )
        if not old_vals or not new_vals:
            print(
                f"  skip {spec['task']} {spec['compare_model_old']} -> {spec['compare_model_new']}: "
                f"old_n={len(old_vals)} new_n={len(new_vals)}"
            )
            continue
        old_arr = np.asarray(old_vals, dtype=float)
        new_arr = np.asarray(new_vals, dtype=float)
        old_mean = float(old_arr.mean())
        new_mean = float(new_arr.mean())
        old_se = float(old_arr.std(ddof=1) / np.sqrt(len(old_arr))) if len(old_arr) > 1 else 0.0
        new_se = float(new_arr.std(ddof=1) / np.sqrt(len(new_arr))) if len(new_arr) > 1 else 0.0
        results.append(
            {
                "task": spec["task"],
                "old_model": spec["compare_model_old"],
                "new_model": spec["compare_model_new"],
                "old_mean": old_mean,
                "new_mean": new_mean,
                "old_stderr": old_se,
                "new_stderr": new_se,
                "delta": new_mean - old_mean,
                "n_old": len(old_vals),
                "n_new": len(new_vals),
                "metric": spec["metric_field"],
            }
        )
        print(
            f"  {spec['task']:14s} {spec['compare_model_old']:18s} -> {spec['compare_model_new']:18s}  "
            f"old={old_mean:7.3f} new={new_mean:7.3f} delta={new_mean - old_mean:+.3f}  "
            f"n_old={len(old_vals)} n_new={len(new_vals)}"
        )

    # Save JSON
    out_dir = Path("paper/cross_task")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "frontier_lift.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {out_dir / 'frontier_lift.json'}")

    # Figure: grouped bars per (task, comparison)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    labels = [f"{r['task'].split()[0]}\n{r['old_model']}->{r['new_model']}" for r in results]
    old_means = [r["old_mean"] for r in results]
    new_means = [r["new_mean"] for r in results]
    deltas = [r["delta"] for r in results]
    x = np.arange(len(results))
    w = 0.4
    # Two y-scales because T5 metric (bias) is ±20, others 0-1
    is_t5 = [r["task"].startswith("T5") for r in results]
    if any(is_t5):
        # Plot T5 separately on right axis. Easier: plot per-row split — but keep simple: only T1-T4 here.
        pass
    old_errs = [r.get("old_stderr", 0.0) for r in results]
    new_errs = [r.get("new_stderr", 0.0) for r in results]
    ax.bar(
        x - w / 2,
        old_means,
        w,
        yerr=old_errs,
        label="Original model",
        color="C0",
        alpha=0.85,
        capsize=3,
        error_kw={"elinewidth": 0.8},
    )
    ax.bar(
        x + w / 2,
        new_means,
        w,
        yerr=new_errs,
        label="Upgraded model",
        color="C1",
        alpha=0.85,
        capsize=3,
        error_kw={"elinewidth": 0.8},
    )
    for i, d in enumerate(deltas):
        ax.text(
            i,
            max(old_means[i], new_means[i]) + 0.02,
            f"{d:+.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
            color="green" if d < 0 else "red",
        )
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Manipulation metric (rate or bias)")
    ax.set_title(
        "Frontier-generation lift: original vs upgraded model on identical scenarios\n"
        "(each pair within a task: same scenarios, only the focal model swapped)",
        fontsize=11,
    )
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = out_dir / "figures" / "fig_frontier_lift.pdf"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
