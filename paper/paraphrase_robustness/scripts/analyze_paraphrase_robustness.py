"""Paraphrase-robustness analysis (PREREG section 5).

Reads the paraphrase-sweep eval logs (T3 Village + T4 Sales), computes:
  - Per-paraphrase per-model frame slope at the held-fixed cell
  - Across-models mean |frame slope| per paraphrase version
  - Pooled-across-paraphrases |frame slope| with SE across the 3 versions
  - Dominance ratios against Table 2's non-frame axis slope

Reference axis-slope anchors (from paper/cross_task/cross_task_aggregate.md
and the per-task results.md A.4 tables):
  T3 Village: |frame|=0.168, |incentive|=0.054, |difficulty|=0.023
  T4 Sales:   |frame|=0.026, |incentive|=0.010, |difficulty|=0.087

T3 dominance contrast: frame vs. incentive (Table 2 ratio 3.1x).
T4 dominance contrast: difficulty vs. frame (Table 2 ratio 3.3x).

Pass criteria (PREREG section 5.3):
  P-A (T3): |paraphrase frame slope| / 0.054 >= 1.5 for all v in {1, 2, 3}
  P-B (T4): 0.087 / |paraphrase frame slope| >= 1.65 for all v in {1, 2, 3}
  P-C: max_v ratio / min_v ratio <= 4 on both tasks

Outputs:
  paper/paraphrase_robustness/analysis/results.json
  paper/paraphrase_robustness/analysis/appendix_table.md

Usage:
  python paper/paraphrase_robustness/scripts/analyze_paraphrase_robustness.py \
    --t3-log paper/paraphrase_robustness/eval_log_t3.eval \
    --t4-log paper/paraphrase_robustness/eval_log_t4.eval

Reads from a single combined log if both --t3-log and --t4-log point to the
same file (the analyzer auto-detects per-sample by scorer presence).
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import read_eval_log

# Anchors from main paper Table 2 (cross_task/cross_task_aggregate.md)
# T1 Bargaining: incentive 0.250 (DOMINANT), frame 0.108 (secondary), difficulty 0.030.
# Dominance contrast: incentive vs frame (Table 2 ratio 2.3x).
T1_FRAME_TABLE2 = 0.108
T1_INCENTIVE_TABLE2 = 0.250
T1_DOMINANCE_RATIO_TABLE2 = T1_INCENTIVE_TABLE2 / T1_FRAME_TABLE2  # ≈ 2.3
PASS_PT1_FLOOR = 1.15  # incentive >= 1.15x frame across all v (2.3 / 2 = 1.15)

T3_INCENTIVE_TABLE2 = 0.054
T3_FRAME_TABLE2 = 0.168
T4_FRAME_TABLE2 = 0.026
T4_DIFFICULTY_TABLE2 = 0.087

T3_DOMINANCE_RATIO_TABLE2 = T3_FRAME_TABLE2 / T3_INCENTIVE_TABLE2  # ≈ 3.1
T4_DOMINANCE_RATIO_TABLE2 = T4_DIFFICULTY_TABLE2 / T4_FRAME_TABLE2  # ≈ 3.3

PASS_PA_FLOOR_T3 = 1.5  # frame >= 1.5x incentive across all v
PASS_PB_FLOOR_T4 = 1.65  # difficulty >= 1.65x frame across all v
PASS_PC_RANGE = 4.0  # max_v / min_v ratio <= 4 (i.e., all 3 within 2x)

FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
PARAPHRASE_VERSIONS = (1, 2, 3)
T1_MODELS = (
    "Claude-Opus-4.7",
    "GPT-5.5",
    "Gemini-3.1-Pro",
    "Grok-4",
    "Llama-3.3-70B",
    "DeepSeek-V4-Pro",
)
T3_MODELS = T1_MODELS  # same display labels for the cross-model dimension
T4_MODELS = ("claude", "gpt55", "gemini", "grok", "llama", "deepseek")


def safe_mean(xs: list[float]) -> float:
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float("nan") if not xs else sum(xs) / len(xs)


def slope(values: list[float]) -> float:
    valid = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if len(valid) < 2:
        return float("nan")
    n = len(values)
    xs = list(range(n))
    xbar = sum(xs) / n
    ybar = sum(values) / n
    num = sum((xs[i] - xbar) * (values[i] - ybar) for i in range(n))
    den = sum((xs[i] - xbar) ** 2 for i in range(n))
    return num / den if den else float("nan")


def _normalize_model_label(label: str | None) -> str | None:
    if label is None:
        return None
    if label == "GPT-5":
        return "GPT-5.5"
    if label == "DeepSeek-v3.2":
        return "DeepSeek-V4-Pro"
    return label


_normalize_t3_model = _normalize_model_label  # back-compat alias


def load_t1_rows(log_path: str) -> list[dict]:
    log = read_eval_log(log_path)
    by_id = {}
    for s in log.samples:
        if s.error:
            continue
        scenario_meta = (s.metadata or {}).get("scenario", {}).get("metadata", {})
        if scenario_meta.get("experiment") != "paraphrase_robustness_t1":
            continue
        bs = (s.scores or {}).get("bargaining_commit")
        if bs is None or not isinstance(bs.value, dict):
            continue
        rate = bs.value.get("manipulation_rate")
        if rate is None or bs.value.get("sample_failed"):
            continue
        by_id[s.id] = dict(
            model=_normalize_model_label(scenario_meta.get("model")),
            frame=scenario_meta.get("frame"),
            paraphrase_version=int(scenario_meta.get("paraphrase_version", 1)),
            metric=float(rate),
        )
    return list(by_id.values())


def load_t3_rows(log_path: str) -> list[dict]:
    log = read_eval_log(log_path)
    by_id = {}
    for s in log.samples:
        if s.error:
            continue
        scenario_meta = (s.metadata or {}).get("scenario", {}).get("metadata", {}) or s.metadata or {}
        if scenario_meta.get("experiment") != "paraphrase_robustness_t3":
            # Skip samples that aren't part of this addendum
            continue
        er = (s.scores or {}).get("exploitation_rate")
        if er is None or not isinstance(er.value, dict):
            continue
        m_er = er.value.get("agent_1")
        if m_er is None:
            continue
        by_id[s.id] = dict(
            model=_normalize_t3_model(scenario_meta.get("manipulator_model")),
            frame=scenario_meta.get("frame"),
            paraphrase_version=int(scenario_meta.get("paraphrase_version", 1)),
            metric=float(m_er),
        )
    return list(by_id.values())


def load_t4_rows(log_path: str) -> list[dict]:
    log = read_eval_log(log_path)
    by_id = {}
    for s in log.samples:
        if s.error:
            continue
        md = s.metadata or {}
        if md.get("experiment") != "paraphrase_robustness_t4":
            continue
        sc = (s.scores or {}).get("sales_classifier")
        if sc is None or not isinstance(sc.value, dict):
            continue
        rate = sc.value.get("manipulation_rate")
        if rate is None:
            continue
        model = md.get("model")
        if model == "gpt5":
            model = "gpt55"
        by_id[s.id] = dict(
            model=model,
            frame=md.get("frame"),
            paraphrase_version=int(md.get("paraphrase_version", 1)),
            metric=float(rate),
        )
    return list(by_id.values())


def per_paraphrase_per_model_slopes(
    rows: list[dict], models: tuple[str, ...]
) -> dict[int, dict[str, float]]:
    """Returns {paraphrase_version: {model: frame_slope}}."""
    out: dict[int, dict[str, float]] = {}
    for v in PARAPHRASE_VERSIONS:
        per_model: dict[str, float] = {}
        for m in models:
            frame_means = []
            for f in FRAMES:
                vals = [
                    r["metric"]
                    for r in rows
                    if r["model"] == m and r["frame"] == f and r["paraphrase_version"] == v
                ]
                frame_means.append(safe_mean(vals))
            per_model[m] = slope(frame_means)
        out[v] = per_model
    return out


def aggregate_slopes(per_model_slopes: dict[int, dict[str, float]]) -> dict:
    """For each paraphrase version, compute across-models mean |slope|.
    Then pool across versions: mean and SE."""
    per_v_abs_means: dict[int, float] = {}
    for v, per_model in per_model_slopes.items():
        abs_slopes = [
            abs(s) for s in per_model.values() if not math.isnan(s)
        ]
        per_v_abs_means[v] = safe_mean(abs_slopes)
    pooled_mean = safe_mean(list(per_v_abs_means.values()))
    pooled_sd = (
        statistics.stdev(per_v_abs_means.values())
        if len([v for v in per_v_abs_means.values() if not math.isnan(v)]) >= 2
        else float("nan")
    )
    pooled_se = (
        pooled_sd / math.sqrt(len(per_v_abs_means))
        if not math.isnan(pooled_sd)
        else float("nan")
    )
    return dict(
        per_v_abs_means=per_v_abs_means,
        pooled_abs_mean=pooled_mean,
        pooled_abs_sd=pooled_sd,
        pooled_abs_se=pooled_se,
    )


def evaluate_pass_criteria(
    t1_per_v: dict[int, float] | None,
    t3_per_v: dict[int, float] | None,
    t4_per_v: dict[int, float] | None,
) -> dict:
    def range_ratio(d: dict[int, float]) -> float:
        vals = [v for v in d.values() if not math.isnan(v) and not math.isinf(v) and v > 0]
        if len(vals) < 2:
            return float("nan")
        return max(vals) / min(vals)

    out = dict(anchors=dict(
        t1_incentive_table2=T1_INCENTIVE_TABLE2,
        t1_frame_table2=T1_FRAME_TABLE2,
        t1_dominance_ratio_table2=T1_DOMINANCE_RATIO_TABLE2,
        t3_incentive_table2=T3_INCENTIVE_TABLE2,
        t4_difficulty_table2=T4_DIFFICULTY_TABLE2,
        t3_dominance_ratio_table2=T3_DOMINANCE_RATIO_TABLE2,
        t4_dominance_ratio_table2=T4_DOMINANCE_RATIO_TABLE2,
        pass_pt1_floor=PASS_PT1_FLOOR,
        pass_pa_floor=PASS_PA_FLOOR_T3,
        pass_pb_floor=PASS_PB_FLOOR_T4,
        pass_pc_range=PASS_PC_RANGE,
    ))

    # T1: dominance ratio = T1_INCENTIVE_TABLE2 / |frame slope|
    if t1_per_v:
        t1_ratios = {
            v: T1_INCENTIVE_TABLE2 / t1_per_v[v] if t1_per_v[v] > 0 else float("inf")
            for v in PARAPHRASE_VERSIONS
        }
        out["t1_dominance_ratios"] = t1_ratios
        out["t1_dominance_range_ratio"] = range_ratio(t1_ratios)
        out["pt1_pass"] = all(r >= PASS_PT1_FLOOR for r in t1_ratios.values())
    else:
        out["t1_dominance_ratios"] = None
        out["t1_dominance_range_ratio"] = float("nan")
        out["pt1_pass"] = None

    # T3
    if t3_per_v:
        t3_ratios = {v: t3_per_v[v] / T3_INCENTIVE_TABLE2 for v in PARAPHRASE_VERSIONS}
        out["t3_dominance_ratios"] = t3_ratios
        out["t3_dominance_range_ratio"] = range_ratio(t3_ratios)
        out["pa_pass"] = all(r >= PASS_PA_FLOOR_T3 for r in t3_ratios.values())
    else:
        out["t3_dominance_ratios"] = None
        out["t3_dominance_range_ratio"] = float("nan")
        out["pa_pass"] = None

    # T4
    if t4_per_v:
        t4_ratios = {
            v: T4_DIFFICULTY_TABLE2 / t4_per_v[v] if t4_per_v[v] > 0 else float("inf")
            for v in PARAPHRASE_VERSIONS
        }
        out["t4_dominance_ratios"] = t4_ratios
        out["t4_dominance_range_ratio"] = range_ratio(t4_ratios)
        out["pb_pass"] = all(r >= PASS_PB_FLOOR_T4 for r in t4_ratios.values())
    else:
        out["t4_dominance_ratios"] = None
        out["t4_dominance_range_ratio"] = float("nan")
        out["pb_pass"] = None

    # PC: magnitude stability across whichever tasks were run
    pc_components = [
        out["t1_dominance_range_ratio"],
        out["t3_dominance_range_ratio"],
        out["t4_dominance_range_ratio"],
    ]
    pc_components = [r for r in pc_components if not math.isnan(r)]
    out["pc_pass"] = all(r <= PASS_PC_RANGE for r in pc_components) if pc_components else None

    # Overall: PASS if all relevant per-task criteria + PC pass.
    relevant_passes = [
        v for k, v in out.items()
        if k in ("pt1_pass", "pa_pass", "pb_pass", "pc_pass") and v is not None
    ]
    out["overall_verdict"] = "PASS" if relevant_passes and all(relevant_passes) else "FAIL"
    return out


def _verdict_marker(passing: bool | None) -> str:
    return "PASS" if passing is True else ("FAIL" if passing is False else "n/a")


def _emit_task_section(
    label: str,
    cell_desc: str,
    table_anchor_text: str,
    agg: dict,
    ratios: dict[int, float] | None,
    pass_floor: float,
    range_ratio: float,
    pooled_anchor: float,
    is_dominant_axis: bool,
) -> str:
    """Emit one task's table section. ``is_dominant_axis``: True if frame is
    the dominant axis (T3 case → ratio = frame/anchor); False if frame is
    the SECONDARY axis (T1, T4 cases → ratio = anchor/frame)."""
    lines: list[str] = []
    lines.append(f"\n## {label} ({cell_desc})\n")
    lines.append(
        f"| Paraphrase | |frame slope| | Dominance ratio ({table_anchor_text}) | "
        f"vs. Table 2 |\n"
    )
    lines.append("|---|---:|---:|:---:|\n")
    if not ratios:
        lines.append("| (no samples) | — | — | n/a |\n")
        return "".join(lines)
    for v in PARAPHRASE_VERSIONS:
        s = agg["per_v_abs_means"][v]
        r = ratios[v]
        marker = "PASS" if r >= pass_floor else "FAIL"
        lines.append(f"| v{v} | {s:.4f} | {r:.2f}x | {marker} |\n")
    pooled_se = agg["pooled_abs_se"]
    se_str = f"+/- {pooled_se:.4f}" if not math.isnan(pooled_se) else "(SE n/a)"
    pooled_mean = agg["pooled_abs_mean"]
    if is_dominant_axis:
        pooled_ratio = pooled_mean / pooled_anchor if pooled_anchor > 0 else float("nan")
    else:
        pooled_ratio = pooled_anchor / pooled_mean if pooled_mean > 0 else float("inf")
    lines.append(
        f"| **Pooled** | **{pooled_mean:.4f}** {se_str} | "
        f"**{pooled_ratio:.2f}x** | range: {range_ratio:.2f}x |\n"
    )
    return "".join(lines)


def emit_appendix_table(t1: dict | None, t3: dict | None, t4: dict | None, criteria: dict) -> str:
    lines: list[str] = []
    lines.append("# Paraphrase-Robustness Appendix Table\n")
    lines.append(
        "Per-task across-models mean |frame slope| at the held-fixed cell, by "
        "paraphrase version (1 = original, 2 = formal-imperative, 3 = "
        "conversational). Dominance ratio compares to the corresponding "
        "Table 2 anchor. Pooled row averages over the three versions; SE is "
        "between-version SD divided by sqrt(3).\n"
    )

    if t1:
        lines.append(_emit_task_section(
            "T1 Bargaining", "held-fixed: incentive=moderate, difficulty=low",
            "incentive/frame", t1, criteria.get("t1_dominance_ratios"),
            PASS_PT1_FLOOR, criteria["t1_dominance_range_ratio"],
            T1_INCENTIVE_TABLE2, is_dominant_axis=False,
        ))
    if t3:
        lines.append(_emit_task_section(
            "T3 Village", "held-fixed: incentive=high, difficulty=low",
            "frame/incentive", t3, criteria.get("t3_dominance_ratios"),
            PASS_PA_FLOOR_T3, criteria["t3_dominance_range_ratio"],
            T3_INCENTIVE_TABLE2, is_dominant_axis=True,
        ))
    if t4:
        lines.append(_emit_task_section(
            "T4 Sales", "held-fixed: incentive=moderate, difficulty=medium",
            "difficulty/frame", t4, criteria.get("t4_dominance_ratios"),
            PASS_PB_FLOOR_T4, criteria["t4_dominance_range_ratio"],
            T4_DIFFICULTY_TABLE2, is_dominant_axis=False,
        ))

    lines.append("\n## Verdict\n")
    if t1:
        lines.append(
            f"- **(P-T1)** T1 directional consistency (incentive >= "
            f"{PASS_PT1_FLOOR}x frame on every v): **{_verdict_marker(criteria['pt1_pass'])}**\n"
        )
    if t3:
        lines.append(
            f"- **(P-A)** T3 directional consistency (frame >= "
            f"{PASS_PA_FLOOR_T3}x incentive on every v): **{_verdict_marker(criteria['pa_pass'])}**\n"
        )
    if t4:
        lines.append(
            f"- **(P-B)** T4 directional consistency (difficulty >= "
            f"{PASS_PB_FLOOR_T4}x frame on every v): **{_verdict_marker(criteria['pb_pass'])}**\n"
        )
    lines.append(
        f"- **(P-C)** Magnitude stability (max/min ratio <= {PASS_PC_RANGE}): "
        f"**{_verdict_marker(criteria['pc_pass'])}**"
    )
    range_parts = []
    if t1:
        range_parts.append(f"T1 range {criteria['t1_dominance_range_ratio']:.2f}x")
    if t3:
        range_parts.append(f"T3 range {criteria['t3_dominance_range_ratio']:.2f}x")
    if t4:
        range_parts.append(f"T4 range {criteria['t4_dominance_range_ratio']:.2f}x")
    if range_parts:
        lines.append(f" ({'; '.join(range_parts)})")
    lines.append("\n")
    lines.append(f"\n**Overall: {criteria['overall_verdict']}**\n")
    return "".join(lines)


def emit_appendix_subsection(
    t1: dict | None, t3: dict | None, t4: dict | None, criteria: dict
) -> str:
    """Draft 2-3 sentence interpretation for the appendix."""
    overall = criteria["overall_verdict"]

    parts = [
        "## Frame-axis paraphrase robustness (app:frame-robustness)\n\n"
    ]

    tasks_run = []
    if t1:
        tasks_run.append("T1 Bargaining (commissive)")
    if t3:
        tasks_run.append("T3 Village (commissive, frame-dominant)")
    if t4:
        tasks_run.append("T4 Sales (assertive, difficulty-dominant)")
    tasks_str = " and ".join(tasks_run)

    parts.append(
        f"To address concern that the headline frame-dominance claim could be an "
        f"artifact of single prompt wording per cell, we ran the two-paraphrase "
        f"robustness check pre-registered in Appendix~\\ref{{app:paraphrase-prereg}}. "
        f"Two new paraphrases per frame level (formal-imperative and conversational) "
        f"were authored on {tasks_str}, held fixed at a representative "
        f"(incentive, difficulty) cell per task and scored under identical "
        f"generation parameters as the main sweep.\n\n"
    )

    summary_clauses = []
    if t1 and criteria.get("t1_dominance_ratios"):
        t1_ratio = (
            T1_INCENTIVE_TABLE2 / t1["pooled_abs_mean"]
            if t1["pooled_abs_mean"] > 0
            else float("inf")
        )
        summary_clauses.append(
            f"On T1 Bargaining, incentive remains {t1_ratio:.1f}x frame pooled "
            f"across the three paraphrases (Table~2 anchor: "
            f"{T1_DOMINANCE_RATIO_TABLE2:.1f}x), confirming the commissive-task "
            f"frame slope is paraphrase-stable around its secondary-axis magnitude"
        )
    if t3 and criteria.get("t3_dominance_ratios"):
        t3_ratio = t3["pooled_abs_mean"] / T3_INCENTIVE_TABLE2
        summary_clauses.append(
            f"on T3 Village, frame remains {t3_ratio:.1f}x incentive pooled "
            f"(Table~2 anchor: {T3_DOMINANCE_RATIO_TABLE2:.1f}x)"
        )
    if t4 and criteria.get("t4_dominance_ratios"):
        t4_ratio = (
            T4_DIFFICULTY_TABLE2 / t4["pooled_abs_mean"]
            if t4["pooled_abs_mean"] > 0
            else float("inf")
        )
        summary_clauses.append(
            f"on T4 Sales, difficulty remains {t4_ratio:.1f}x frame pooled "
            f"(Table~2 anchor: {T4_DOMINANCE_RATIO_TABLE2:.1f}x)"
        )

    range_clauses = []
    if t1:
        range_clauses.append(f"T1 {criteria['t1_dominance_range_ratio']:.2f}x")
    if t3:
        range_clauses.append(f"T3 {criteria['t3_dominance_range_ratio']:.2f}x")
    if t4:
        range_clauses.append(f"T4 {criteria['t4_dominance_range_ratio']:.2f}x")

    if overall == "PASS":
        parts.append(
            f"Results: the dominance ratios remain directionally and "
            f"magnitude-stable. {'; '.join(summary_clauses)}. The max-min range "
            f"across paraphrases stays within 2x on each task "
            f"({'; '.join(range_clauses)}). The dominance claims for the tested "
            f"tasks are not sensitive to the specific frame wording chosen.\n"
        )
    elif criteria.get("pc_pass") is False and (
        criteria.get("pa_pass") is not False
        and criteria.get("pb_pass") is not False
        and criteria.get("pt1_pass") is not False
    ):
        parts.append(
            f"Results: directional dominance is preserved across all tested "
            f"tasks ({'; '.join(summary_clauses)}), but magnitude varies more "
            f"than 2x across paraphrases on at least one task "
            f"({'; '.join(range_clauses)}). The dominance direction is robust "
            f"to wording, but the precise magnitudes reported in Table~2 should "
            f"be read as paraphrase-conditioned.\n"
        )
    else:
        failed = []
        if criteria.get("pt1_pass") is False:
            failed.append("T1 incentive-dominance fails on at least one paraphrase")
        if criteria.get("pa_pass") is False:
            failed.append("T3 frame-dominance fails on at least one paraphrase")
        if criteria.get("pb_pass") is False:
            failed.append("T4 difficulty-dominance fails on at least one paraphrase")
        parts.append(
            f"Results: {'; '.join(failed)}. Per-paraphrase numbers are reported "
            f"in the table below. The headline claim is partially "
            f"wording-dependent and we qualify it accordingly in "
            f"Section~\\ref{{sec:limitations}}.\n"
        )

    return "".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--t1-log", default=None, help="path to T1 paraphrase eval log (optional)")
    ap.add_argument("--t3-log", default=None, help="path to T3 paraphrase eval log (optional)")
    ap.add_argument("--t4-log", default=None, help="path to T4 paraphrase eval log (optional)")
    ap.add_argument(
        "--out-dir",
        default="paper/paraphrase_robustness/analysis",
        help="output directory",
    )
    args = ap.parse_args()
    if not (args.t1_log or args.t3_log or args.t4_log):
        ap.error("at least one of --t1-log, --t3-log, --t4-log is required")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    t1_agg = t3_agg = t4_agg = None
    t1_per_v_per_model = t3_per_v_per_model = t4_per_v_per_model = None
    n1 = n3 = n4 = 0

    if args.t1_log:
        print(f"Loading T1 log {args.t1_log}...")
        rows = load_t1_rows(args.t1_log)
        n1 = len(rows)
        print(f"  {n1} T1 paraphrase samples")
        if rows:
            t1_per_v_per_model = per_paraphrase_per_model_slopes(rows, T1_MODELS)
            t1_agg = aggregate_slopes(t1_per_v_per_model)
    if args.t3_log:
        print(f"Loading T3 log {args.t3_log}...")
        rows = load_t3_rows(args.t3_log)
        n3 = len(rows)
        print(f"  {n3} T3 paraphrase samples")
        if rows:
            t3_per_v_per_model = per_paraphrase_per_model_slopes(rows, T3_MODELS)
            t3_agg = aggregate_slopes(t3_per_v_per_model)
    if args.t4_log:
        print(f"Loading T4 log {args.t4_log}...")
        rows = load_t4_rows(args.t4_log)
        n4 = len(rows)
        print(f"  {n4} T4 paraphrase samples")
        if rows:
            t4_per_v_per_model = per_paraphrase_per_model_slopes(rows, T4_MODELS)
            t4_agg = aggregate_slopes(t4_per_v_per_model)

    criteria = evaluate_pass_criteria(
        t1_agg["per_v_abs_means"] if t1_agg else None,
        t3_agg["per_v_abs_means"] if t3_agg else None,
        t4_agg["per_v_abs_means"] if t4_agg else None,
    )

    results = dict(verdict=criteria)
    if t1_agg:
        results["t1"] = dict(
            per_paraphrase_per_model_slopes=t1_per_v_per_model,
            aggregate=t1_agg,
            n_samples=n1,
        )
    if t3_agg:
        results["t3"] = dict(
            per_paraphrase_per_model_slopes=t3_per_v_per_model,
            aggregate=t3_agg,
            n_samples=n3,
        )
    if t4_agg:
        results["t4"] = dict(
            per_paraphrase_per_model_slopes=t4_per_v_per_model,
            aggregate=t4_agg,
            n_samples=n4,
        )
    (out_dir / "results.json").write_text(json.dumps(results, indent=2, default=str))
    table = emit_appendix_table(t1_agg, t3_agg, t4_agg, criteria)
    (out_dir / "appendix_table.md").write_text(table, encoding="utf-8")
    subsection = emit_appendix_subsection(t1_agg, t3_agg, t4_agg, criteria)
    (out_dir / "appendix_subsection_draft.md").write_text(subsection, encoding="utf-8")

    print()
    print(table)
    print()
    print("Wrote:")
    print(f"  {out_dir / 'results.json'}")
    print(f"  {out_dir / 'appendix_table.md'}")
    print(f"  {out_dir / 'appendix_subsection_draft.md'}")


if __name__ == "__main__":
    main()
