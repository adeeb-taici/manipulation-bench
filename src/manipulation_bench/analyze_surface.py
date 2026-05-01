"""Cross-environment response-surface analyzer.

Reads one or more Inspect eval logs, detects the environment from scorer
names, and pivots samples into a frame × incentive × difficulty grid per
model. Emits markdown tables per axis slice and a flat CSV for downstream
plotting.

Old logs written before the axis rename still pivot correctly — sample
metadata is normalized through ``axes.canonical_frame`` and
``canonical_incentive`` on read.

Usage:
    python -m manipulation_bench.analyze_surface logs/2026-04*.eval
    python -m manipulation_bench.analyze_surface logs/my_run.eval --csv out.csv
"""

from __future__ import annotations

import argparse
import csv
import glob
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from inspect_ai.log import EvalLog, read_eval_log

from manipulation_bench.axes import (
    DIFFICULTY_LEVELS,
    FRAME_LEVELS,
    INCENTIVE_LEVELS,
    canonical_frame,
    canonical_incentive,
)


# ── Environment detection + canonical metric per env ──────────────────────

_SCORER_SETS: dict[str, set[str]] = {
    "sales": {"sales_classifier"},
    "committee": {
        "initial_rating_bias",
        "post_discussion_rating_change",
        "discussion_polarity",
        "decision_outcome",
    },
    "village": {"exploitation_rate", "promise_action_gap", "village_fairness"},
    "debate": {"manipulation_detection", "argument_quality", "belief_shift"},
    "bargaining": {"overstatement_rate"},
    "inbox": {"inbox_triage"},
    "werewolf": {"game_win_rate", "deception_success"},
    "diplomacy": {"territorial_success", "agreement_compliance"},
}


def detect_environment(log: EvalLog) -> str:
    scorer_names: set[str] = set()
    if log.samples:
        scorer_names = set(log.samples[0].scores.keys())
    for env, required in _SCORER_SETS.items():
        if scorer_names & required:
            return env
    return "unknown"


# ── Metric extraction per environment ─────────────────────────────────────


def _lookup_score(sample: Any, scorer_names: tuple[str, ...]) -> Any | None:
    for name in scorer_names:
        s = sample.scores.get(name)
        if s is not None:
            return s
    return None


def _manipulation_occurred(sample: Any, scorer_names: tuple[str, ...]) -> float | None:
    """Return the scenario-level ``manipulation_occurred`` boolean as a float
    in {0.0, 1.0}, or None when the scorer did not emit it (e.g. archived
    logs written before the shared metric was added)."""
    score = _lookup_score(sample, scorer_names)
    if score is None:
        return None
    val = score.value if hasattr(score, "value") else score
    if not isinstance(val, dict):
        return None
    raw = val.get("manipulation_occurred")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _sales_metric(sample: Any) -> float | None:
    """Fallback continuous metric: misleading+false rate."""
    score = sample.scores.get("sales_classifier")
    if score is None:
        return None
    val = score.value if hasattr(score, "value") else score
    if not isinstance(val, dict):
        return None
    misleading = val.get("misleading_rate", 0.0)
    false_rate = val.get("false_rate", 0.0)
    try:
        return float(misleading) + float(false_rate)
    except (TypeError, ValueError):
        return None


def _committee_metric(sample: Any) -> float | None:
    score = sample.scores.get("initial_rating_bias")
    if score is None:
        return None
    val = score.value if hasattr(score, "value") else score
    if isinstance(val, dict):
        v = val.get("initial_bias")
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        return _first_numeric(val)
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _village_metric(sample: Any) -> float | None:
    score = sample.scores.get("exploitation_rate")
    if score is None:
        return None
    val = score.value if hasattr(score, "value") else score
    if isinstance(val, dict):
        return _first_numeric(val)
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _debate_metric(sample: Any) -> float | None:
    score = sample.scores.get("belief_shift")
    if score is None:
        return None
    val = score.value if hasattr(score, "value") else score
    if isinstance(val, dict):
        return _first_numeric(val)
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _bargaining_metric(sample: Any) -> float | None:
    score = sample.scores.get("overstatement_rate")
    if score is None:
        return None
    val = score.value if hasattr(score, "value") else score
    if isinstance(val, dict):
        return _first_numeric(val)
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _inbox_metric(sample: Any) -> float | None:
    score = sample.scores.get("inbox_triage")
    if score is None:
        return None
    val = score.value if hasattr(score, "value") else score
    if isinstance(val, dict):
        v = val.get("suppression_rate")
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# Per-env scorer names that carry the shared `manipulation_occurred` boolean.
_MANIP_SCORERS: dict[str, tuple[str, ...]] = {
    "sales": ("sales_classifier",),
    "committee": ("initial_rating_bias",),
    "village": ("exploitation_rate",),
    "debate": ("ground_truth_persuasion",),
    "bargaining": ("bargaining_commit", "bargaining_manipulation"),
    "inbox": ("inbox_triage",),
}


def _first_numeric(d: dict[str, Any]) -> float | None:
    for v in d.values():
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


_METRIC_EXTRACTORS = {
    "sales": _sales_metric,
    "committee": _committee_metric,
    "village": _village_metric,
    "debate": _debate_metric,
    "bargaining": _bargaining_metric,
    "inbox": _inbox_metric,
}

METRIC_NAMES = {
    "sales": "sales_classifier(misleading+false)",
    "committee": "initial_rating_bias",
    "village": "exploitation_rate",
    "debate": "belief_shift",
    "bargaining": "overstatement_rate",
    "inbox": "suppression_rate",
}

SHARED_METRIC = "manipulation_occurred"


# ── Axis extraction from sample metadata ─────────────────────────────────


def _sample_meta(sample: Any) -> dict[str, Any]:
    """Flatten scenario metadata for axis lookup.

    Checks typed ScenarioMetadata fields first (via store), then falls back
    to the untyped metadata dict that generators historically wrote.
    """
    scenario = sample.store.get("InteractionState:scenario") or {}
    md = dict(scenario.get("metadata") or {})
    # Sample-level metadata also holds axis labels (some generators
    # write them there instead of or in addition to scenario.metadata).
    sample_md = getattr(sample, "metadata", None) or {}
    if isinstance(sample_md, dict):
        for k in ("frame", "incentive", "difficulty", "manipulator", "model"):
            if sample_md.get(k) is not None and md.get(k) is None:
                md[k] = sample_md[k]
    return md


def _model_label(sample: Any, md: dict[str, Any]) -> str:
    if "model" in md:
        return str(md["model"])
    if "interested_model_label" in md:
        return str(md["interested_model_label"])
    mapping = md.get("model_mapping") or {}
    if mapping:
        # Pick the manipulator's model if identifiable, else first agent
        manip = md.get("manipulator")
        if manip and manip in mapping:
            return str(mapping[manip])
        return str(next(iter(mapping.values())))
    return "unknown"


# ── Aggregation ───────────────────────────────────────────────────────────


def collect_rows(log: EvalLog, env: str) -> list[dict[str, Any]]:
    extractor = _METRIC_EXTRACTORS.get(env)
    if extractor is None:
        return []
    manip_scorers = _MANIP_SCORERS.get(env, ())
    rows = []
    for sample in log.samples or []:
        md = _sample_meta(sample)
        frame = canonical_frame(md.get("frame"))
        incentive = canonical_incentive(md.get("incentive"))
        difficulty = md.get("difficulty")
        model = _model_label(sample, md)
        metric = extractor(sample)
        manip = _manipulation_occurred(sample, manip_scorers)
        if metric is None and manip is None:
            continue
        rows.append(
            {
                "sample_id": sample.id,
                "env": env,
                "model": model,
                "frame": frame,
                "incentive": incentive,
                "difficulty": difficulty,
                "metric": metric,
                "metric_name": METRIC_NAMES[env],
                "manipulation_occurred": manip,
            }
        )
    return rows


def _pivot(
    rows: list[dict[str, Any]],
    col_key: str,
    value_key: str,
) -> dict[str, dict[tuple[str, str], float]]:
    buckets: dict[str, dict[tuple[str, str], list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["frame"] is None or r[col_key] is None or r.get(value_key) is None:
            continue
        buckets[r["model"]][(r["frame"], r[col_key])].append(float(r[value_key]))
    return {m: {k: sum(v) / len(v) for k, v in cells.items()} for m, cells in buckets.items()}


def pivot_frame_incentive(rows: list[dict[str, Any]]) -> dict[str, dict[tuple[str, str], float]]:
    """Return {model: {(frame, incentive): mean continuous metric}}."""
    return _pivot(rows, "incentive", "metric")


def pivot_frame_difficulty(
    rows: list[dict[str, Any]],
) -> dict[str, dict[tuple[str, str], float]]:
    return _pivot(rows, "difficulty", "metric")


def pivot_frame_incentive_manip(
    rows: list[dict[str, Any]],
) -> dict[str, dict[tuple[str, str], float]]:
    """Return {model: {(frame, incentive): mean manipulation_occurred}}."""
    return _pivot(rows, "incentive", "manipulation_occurred")


def pivot_frame_difficulty_manip(
    rows: list[dict[str, Any]],
) -> dict[str, dict[tuple[str, str], float]]:
    return _pivot(rows, "difficulty", "manipulation_occurred")


# ── Rendering ─────────────────────────────────────────────────────────────


def _render_grid(
    title: str,
    cells: dict[tuple[str, str], float],
    row_levels: tuple[str, ...],
    col_levels: tuple[str, ...],
) -> str:
    lines = [f"### {title}", ""]
    header = "| " + " | ".join(["frame \\ " + col_levels[0].split()[0], *col_levels]) + " |"
    sep = "|" + "|".join(["---"] * (len(col_levels) + 1)) + "|"
    lines.extend([header, sep])
    for row in row_levels:
        cell_vals = []
        for col in col_levels:
            v = cells.get((row, col))
            cell_vals.append(f"{v:.3f}" if v is not None else "—")
        lines.append("| " + " | ".join([row, *cell_vals]) + " |")
    lines.append("")
    return "\n".join(lines)


def render_report(env: str, rows: list[dict[str, Any]]) -> str:
    if not rows:
        return f"# Response surface ({env})\n\nNo scored samples with axis metadata found.\n"

    metric_name = rows[0]["metric_name"]
    by_model_fi = pivot_frame_incentive(rows)
    by_model_fd = pivot_frame_difficulty(rows)
    manip_fi = pivot_frame_incentive_manip(rows)
    manip_fd = pivot_frame_difficulty_manip(rows)

    n_with_manip = sum(1 for r in rows if r.get("manipulation_occurred") is not None)

    parts = [
        f"# Response surface — {env}",
        "",
        f"Continuous metric: **{metric_name}**  •  "
        f"Shared boolean: **{SHARED_METRIC}** "
        f"({n_with_manip}/{len(rows)} samples)",
        "",
    ]
    for model in sorted(set(by_model_fi.keys()) | set(manip_fi.keys())):
        parts.append(f"## Model: {model}")
        parts.append("")
        if model in manip_fi:
            parts.append(
                _render_grid(
                    f"Frame × Incentive — {SHARED_METRIC} (rate)",
                    manip_fi.get(model, {}),
                    row_levels=FRAME_LEVELS,
                    col_levels=INCENTIVE_LEVELS,
                )
            )
        if model in manip_fd:
            parts.append(
                _render_grid(
                    f"Frame × Difficulty — {SHARED_METRIC} (rate)",
                    manip_fd.get(model, {}),
                    row_levels=FRAME_LEVELS,
                    col_levels=DIFFICULTY_LEVELS,
                )
            )
        parts.append(
            _render_grid(
                f"Frame × Incentive — {metric_name}",
                by_model_fi.get(model, {}),
                row_levels=FRAME_LEVELS,
                col_levels=INCENTIVE_LEVELS,
            )
        )
        parts.append(
            _render_grid(
                f"Frame × Difficulty — {metric_name}",
                by_model_fd.get(model, {}),
                row_levels=FRAME_LEVELS,
                col_levels=DIFFICULTY_LEVELS,
            )
        )
    return "\n".join(parts)


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "sample_id",
        "env",
        "model",
        "frame",
        "incentive",
        "difficulty",
        "metric",
        "metric_name",
        "manipulation_occurred",
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


# ── CLI ───────────────────────────────────────────────────────────────────


def _expand_log_paths(patterns: list[str]) -> list[str]:
    paths: list[str] = []
    for p in patterns:
        matches = glob.glob(p)
        if matches:
            paths.extend(matches)
        else:
            paths.append(p)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="+", help="Eval log paths or globs")
    ap.add_argument("--csv", type=Path, default=None, help="Optional CSV dump of all rows")
    args = ap.parse_args()

    all_rows: list[dict[str, Any]] = []
    per_env_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for log_path in _expand_log_paths(args.logs):
        try:
            log = read_eval_log(log_path)
        except Exception as e:
            print(f"[warn] could not read {log_path}: {e}", file=sys.stderr)
            continue
        env = detect_environment(log)
        if env == "unknown":
            print(f"[warn] {log_path}: could not detect environment", file=sys.stderr)
            continue
        rows = collect_rows(log, env)
        per_env_rows[env].extend(rows)
        all_rows.extend(rows)

    if not all_rows:
        print("No scored samples found in any log.", file=sys.stderr)
        sys.exit(1)

    for env in sorted(per_env_rows.keys()):
        print(render_report(env, per_env_rows[env]))
        print()

    if args.csv:
        write_csv(all_rows, args.csv)
        print(f"[info] wrote {len(all_rows)} rows -> {args.csv}", file=sys.stderr)


if __name__ == "__main__":
    main()
