"""Cross-task response-surface analysis pipeline.

Consumes Inspect eval logs spanning the five canonical environments
(sales, bargaining, debate, village, committee) and computes the
manipulation response surface described in the project brief §4:

  * Per (model, task, axis) standardized sensitivity slope on the shared
    ``manipulation_occurred`` boolean, with percentile bootstrap CIs.
  * Per-model 15-dimensional profile vector (12-dim where the Commons
    incentive axis is a legitimate missing value).
  * Within-axis cross-task correlation matrices (5×5 for frame /
    difficulty; 4×4 for incentive excluding Commons).
  * 6×6 model-similarity and 5×5 task-similarity matrices.
  * Endpoint-calibration table (prohibitive / permissive rates per
    model × task).
  * Optional robustness replication on a z-scored continuous
    "honesty departure" metric (task-natural outcome, z-scored within
    each task).

Outputs go to a user-chosen directory as markdown + CSV. No external
dependencies beyond the standard library — the framework is pure
stdlib so it matches the rest of ``manipulation_bench``.

Usage::

    python paper/cross_task/scripts/analyze_response_surface.py \\
        --logs 'logs/sales/*.eval' 'logs/village/*.eval' ... \\
        --out analysis/response_surface

    python paper/cross_task/scripts/analyze_response_surface.py \\
        --logs 'logs/*.eval' --out analysis/response_surface \\
        --n-bootstrap 2000 --robustness-continuous
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from load import load_corpus  # noqa: E402

from manipulation_bench.axes import (  # noqa: E402
    DIFFICULTY_LEVELS,
    FRAME_LEVELS,
    INCENTIVE_LEVELS,
)

TASKS = ("sales", "bargaining", "debate", "village", "committee")
AXES = ("frame", "incentive", "difficulty")

AXIS_LEVELS: dict[str, tuple[str, ...]] = {
    "frame": FRAME_LEVELS,
    "incentive": INCENTIVE_LEVELS,
    "difficulty": DIFFICULTY_LEVELS,
}

# Commons has no incentive axis by design — see brief §"The three axes".
AXIS_APPLICABLE: dict[tuple[str, str], bool] = {
    (task, axis): not (task == "village" and axis == "incentive") for task in TASKS for axis in AXES
}


# ── Statistics (pure-stdlib) ──────────────────────────────────────────────


def _pearson_r(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    num = sum(a * b for a, b in zip(dx, dy))
    denx = math.sqrt(sum(a * a for a in dx))
    deny = math.sqrt(sum(b * b for b in dy))
    if denx == 0.0 or deny == 0.0:
        return None
    return num / (denx * deny)


def _bootstrap_ci(
    xs: list[float],
    ys: list[float],
    n_boot: int,
    alpha: float = 0.05,
    seed: int = 1,
) -> tuple[float, float] | tuple[None, None]:
    if len(xs) < 3 or n_boot <= 0:
        return (None, None)
    rng = random.Random(seed)
    n = len(xs)
    rs: list[float] = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        sx = [xs[i] for i in idx]
        sy = [ys[i] for i in idx]
        r = _pearson_r(sx, sy)
        if r is not None and not math.isnan(r):
            rs.append(r)
    if len(rs) < 10:
        return (None, None)
    rs.sort()
    lo = rs[int(alpha / 2 * len(rs))]
    hi = rs[min(len(rs) - 1, int((1 - alpha / 2) * len(rs)))]
    return (lo, hi)


def _zscore(values: list[float]) -> list[float | None]:
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return [None] * len(values)
    mu = sum(clean) / len(clean)
    sd = statistics.pstdev(clean)
    if sd == 0:
        return [0.0 if v is not None else None for v in values]
    return [(v - mu) / sd if v is not None else None for v in values]


# ── Row loading ──────────────────────────────────────────────────────────


def load_rows(log_paths: list[str] | None = None) -> list[dict[str, Any]]:
    """Load rows from the canonical results.csv via load_corpus().

    The ``log_paths`` argument is accepted for backwards-compatibility but
    ignored — the corpus is always read from load_corpus().
    """
    df = load_corpus(verbose=False)
    rows: list[dict[str, Any]] = []
    for r in df.to_dict(orient="records"):
        # Rename task -> env to match the analysis functions' expected key
        row = dict(r)
        row["env"] = row.pop("task", None)
        rows.append(row)
    return rows


# ── Sensitivity slopes ───────────────────────────────────────────────────


def _encode_axis(axis: str, value: str | None) -> int | None:
    if value is None:
        return None
    levels = AXIS_LEVELS[axis]
    try:
        return levels.index(value)
    except ValueError:
        return None


def _collect_pairs(
    rows: list[dict[str, Any]],
    axis: str,
    outcome_key: str,
    restrict_levels: tuple[str, ...] | None = None,
) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for r in rows:
        lvl = r.get(axis)
        y = r.get(outcome_key)
        if lvl is None or y is None:
            continue
        if restrict_levels and lvl not in restrict_levels:
            continue
        idx = _encode_axis(axis, lvl)
        if idx is None:
            continue
        try:
            ys.append(float(y))
        except (TypeError, ValueError):
            continue
        xs.append(float(idx))
    return xs, ys


def sensitivity_slope(
    rows: list[dict[str, Any]],
    axis: str,
    outcome_key: str = "manipulation_occurred",
    n_boot: int = 1000,
    restrict_levels: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    xs, ys = _collect_pairs(rows, axis, outcome_key, restrict_levels)
    r = _pearson_r(xs, ys)
    ci_lo, ci_hi = _bootstrap_ci(xs, ys, n_boot)
    return {"slope": r, "ci_lo": ci_lo, "ci_hi": ci_hi, "n": len(xs)}


# ── Profile vectors & similarity ─────────────────────────────────────────


def build_profile_vectors(
    sensitivity: dict[tuple[str, str, str], dict[str, Any]],
    models: list[str],
) -> dict[str, list[float | None]]:
    """One 15-dim vector per model: (task × axis) in TASKS × AXES order."""
    profiles: dict[str, list[float | None]] = {}
    for model in models:
        vec: list[float | None] = []
        for task in TASKS:
            for axis in AXES:
                if not AXIS_APPLICABLE[(task, axis)]:
                    vec.append(None)
                    continue
                entry = sensitivity.get((model, task, axis))
                vec.append(entry["slope"] if entry else None)
        profiles[model] = vec
    return profiles


def _pairwise_correlation(v1: list[float | None], v2: list[float | None]) -> float | None:
    xs, ys = [], []
    for a, b in zip(v1, v2):
        if a is None or b is None:
            continue
        xs.append(a)
        ys.append(b)
    return _pearson_r(xs, ys)


def similarity_matrix(
    vectors: dict[str, list[float | None]],
    keys: list[str],
) -> dict[tuple[str, str], float | None]:
    out: dict[tuple[str, str], float | None] = {}
    for a in keys:
        for b in keys:
            out[(a, b)] = _pairwise_correlation(vectors[a], vectors[b])
    return out


def build_task_vectors(
    sensitivity: dict[tuple[str, str, str], dict[str, Any]],
    models: list[str],
) -> dict[str, list[float | None]]:
    """One (|models| × |axes|)-dim vector per task."""
    out: dict[str, list[float | None]] = {}
    for task in TASKS:
        vec: list[float | None] = []
        for model in models:
            for axis in AXES:
                if not AXIS_APPLICABLE[(task, axis)]:
                    vec.append(None)
                    continue
                entry = sensitivity.get((model, task, axis))
                vec.append(entry["slope"] if entry else None)
        out[task] = vec
    return out


# ── Within-axis cross-task correlation ──────────────────────────────────


def axis_task_correlation(
    sensitivity: dict[tuple[str, str, str], dict[str, Any]],
    models: list[str],
    axis: str,
) -> dict[tuple[str, str], float | None]:
    """For a given axis, correlate per-model slope vectors across tasks."""
    tasks_for_axis = [t for t in TASKS if AXIS_APPLICABLE[(t, axis)]]
    by_task: dict[str, list[float | None]] = {}
    for task in tasks_for_axis:
        vec = [sensitivity.get((m, task, axis), {}).get("slope") for m in models]
        by_task[task] = vec
    out: dict[tuple[str, str], float | None] = {}
    for a in tasks_for_axis:
        for b in tasks_for_axis:
            out[(a, b)] = _pairwise_correlation(by_task[a], by_task[b])
    return out


# ── Endpoint calibration ─────────────────────────────────────────────────


def endpoint_rates(
    rows: list[dict[str, Any]],
    outcome_key: str = "manipulation_occurred",
) -> dict[tuple[str, str, str], float]:
    """Mean outcome at frame=prohibitive and frame=permissive per (task, model, endpoint)."""
    buckets: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for r in rows:
        frame = r.get("frame")
        if frame not in ("prohibitive", "permissive"):
            continue
        y = r.get(outcome_key)
        if y is None:
            continue
        try:
            buckets[(r["env"], r["model"], frame)].append(float(y))
        except (TypeError, ValueError):
            continue
    return {k: sum(v) / len(v) for k, v in buckets.items() if v}


# ── Full pipeline ────────────────────────────────────────────────────────


def run_analysis(
    rows: list[dict[str, Any]],
    outcome_key: str = "manipulation_occurred",
    n_boot: int = 1000,
) -> dict[str, Any]:
    models = sorted({r["model"] for r in rows if r.get("model") and r["model"] != "unknown"})
    tasks_in_data = sorted({r["env"] for r in rows})

    # Partition rows by (task, model) for slope computation. Drop rows whose
    # model couldn't be identified — they'd land in a spurious "unknown" bucket.
    partitioned: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        m = r.get("model")
        if r.get("env") in TASKS and m and m != "unknown":
            partitioned[(r["env"], m)].append(r)

    sensitivity: dict[tuple[str, str, str], dict[str, Any]] = {}
    frame_middle_3 = ("pro_social", "minimal", "selfish")
    for (task, model), task_rows in partitioned.items():
        for axis in AXES:
            if not AXIS_APPLICABLE[(task, axis)]:
                continue
            sensitivity[(model, task, axis)] = sensitivity_slope(
                task_rows, axis, outcome_key, n_boot
            )
        # Middle-3 frame companion (reported separately per brief §4).
        sensitivity[(model, task, "frame_mid3")] = sensitivity_slope(
            task_rows,
            "frame",
            outcome_key,
            n_boot,
            restrict_levels=frame_middle_3,
        )

    profiles = build_profile_vectors(sensitivity, models)
    model_sim = similarity_matrix(profiles, models)
    task_vecs = build_task_vectors(sensitivity, models)
    task_sim = similarity_matrix(task_vecs, list(TASKS))
    axis_corr = {ax: axis_task_correlation(sensitivity, models, ax) for ax in AXES}
    endpoints = endpoint_rates(rows, outcome_key)

    return {
        "outcome_key": outcome_key,
        "models": models,
        "tasks_in_data": tasks_in_data,
        "sensitivity": sensitivity,
        "profiles": profiles,
        "model_similarity": model_sim,
        "task_similarity": task_sim,
        "axis_correlations": axis_corr,
        "endpoints": endpoints,
        "n_rows": len(rows),
    }


# ── Rendering / output ────────────────────────────────────────────────────


def _fmt(v: float | None, digits: int = 3) -> str:
    return "—" if v is None else f"{v:.{digits}f}"


def _write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def _fmt_cell(v: Any) -> Any:
    """Format floats to 4 decimals, leave None as empty string."""
    if v is None:
        return ""
    if isinstance(v, float):
        return round(v, 4)
    return v


def render_sensitivity_table(analysis: dict[str, Any]) -> tuple[str, list[list[Any]]]:
    rows = []
    md = ["### Sensitivity slopes (Pearson r on " + analysis["outcome_key"] + ")", ""]
    md.append("| model | task | axis | slope | 95% CI | n |")
    md.append("|---|---|---|---|---|---|")
    for (model, task, axis), info in sorted(analysis["sensitivity"].items()):
        ci = f"[{_fmt(info['ci_lo'])}, {_fmt(info['ci_hi'])}]"
        md.append(f"| {model} | {task} | {axis} | {_fmt(info['slope'])} | {ci} | {info['n']} |")
        rows.append(
            [
                model,
                task,
                axis,
                _fmt_cell(info["slope"]),
                _fmt_cell(info["ci_lo"]),
                _fmt_cell(info["ci_hi"]),
                info["n"],
            ]
        )
    md.append("")
    return "\n".join(md), rows


def render_similarity(
    title: str, sim: dict[tuple[str, str], float | None], keys: list[str]
) -> tuple[str, list[list[Any]]]:
    md = [f"### {title}", "", "| | " + " | ".join(keys) + " |"]
    md.append("|" + "|".join(["---"] * (len(keys) + 1)) + "|")
    rows: list[list[Any]] = []
    for a in keys:
        cells = [_fmt(sim.get((a, b))) for b in keys]
        md.append(f"| {a} | " + " | ".join(cells) + " |")
        rows.append([a, *[_fmt_cell(sim.get((a, b))) for b in keys]])
    md.append("")
    return "\n".join(md), rows


def render_axis_correlation(analysis: dict[str, Any]) -> str:
    parts = ["### Within-axis cross-task correlation", ""]
    for axis, matrix in analysis["axis_correlations"].items():
        tasks = sorted({t for (t, _) in matrix.keys()})
        if not tasks:
            continue
        parts.append(f"#### {axis}")
        parts.append("")
        parts.append("| | " + " | ".join(tasks) + " |")
        parts.append("|" + "|".join(["---"] * (len(tasks) + 1)) + "|")
        for a in tasks:
            cells = [_fmt(matrix.get((a, b))) for b in tasks]
            parts.append(f"| {a} | " + " | ".join(cells) + " |")
        parts.append("")
    return "\n".join(parts)


def render_endpoints(analysis: dict[str, Any]) -> tuple[str, list[list[Any]]]:
    md = ["### Endpoint calibration (mean outcome at frame extremes)", ""]
    md.append(f"| task | model | prohibitive | permissive |")
    md.append("|---|---|---|---|")
    rows: list[list[Any]] = []
    ep = analysis["endpoints"]
    models = analysis["models"]
    tasks = analysis["tasks_in_data"]
    for task in tasks:
        for model in models:
            p = ep.get((task, model, "prohibitive"))
            q = ep.get((task, model, "permissive"))
            if p is None and q is None:
                continue
            md.append(f"| {task} | {model} | {_fmt(p)} | {_fmt(q)} |")
            rows.append([task, model, _fmt_cell(p), _fmt_cell(q)])
    md.append("")
    return "\n".join(md), rows


def render_predictions(analysis: dict[str, Any]) -> str:
    """Check the pre-registered predictions from brief §4."""
    parts = ["### Pre-registered prediction checks", ""]

    # Frame correlates across tasks r > 0.5 (mean off-diagonal)
    frame_corr = analysis["axis_correlations"]["frame"]
    off_diag = [v for (a, b), v in frame_corr.items() if a != b and v is not None]
    mean_frame = sum(off_diag) / len(off_diag) if off_diag else None

    incentive_corr = analysis["axis_correlations"]["incentive"]
    inc_off = [v for (a, b), v in incentive_corr.items() if a != b and v is not None]
    mean_inc = sum(inc_off) / len(inc_off) if inc_off else None

    ep = analysis["endpoints"]
    prohibitive = [v for (_, _, f), v in ep.items() if f == "prohibitive"]
    permissive = [v for (_, _, f), v in ep.items() if f == "permissive"]
    mean_prohibitive = sum(prohibitive) / len(prohibitive) if prohibitive else None
    mean_permissive = sum(permissive) / len(permissive) if permissive else None

    def _ok(v: float | None, cmp: str, target: float) -> str:
        if v is None:
            return "n/a"
        if cmp == ">":
            return "✓" if v > target else "✗"
        return "✓" if v < target else "✗"

    parts.append("| prediction | target | observed | status |")
    parts.append("|---|---|---|---|")
    parts.append(
        f"| frame correlates across tasks | r > 0.5 | {_fmt(mean_frame)} | "
        f"{_ok(mean_frame, '>', 0.5)} |"
    )
    parts.append(
        f"| incentive correlates across tasks (excl. Commons) | r > 0.3 | "
        f"{_fmt(mean_inc)} | {_ok(mean_inc, '>', 0.3)} |"
    )
    parts.append(
        f"| prohibitive-endpoint rate | < 0.15 | {_fmt(mean_prohibitive)} | "
        f"{_ok(mean_prohibitive, '<', 0.15)} |"
    )
    parts.append(
        f"| permissive-endpoint rate | > 0.70 | {_fmt(mean_permissive)} | "
        f"{_ok(mean_permissive, '>', 0.70)} |"
    )

    # Model-variance > task-variance on profile slopes
    model_flat: list[float] = []
    for vec in analysis["profiles"].values():
        model_flat.extend(v for v in vec if v is not None)
    task_flat: list[float] = []
    for vec in (
        analysis["task_similarity"].values()
        if isinstance(analysis.get("task_vectors"), dict)
        else []
    ):
        pass  # not materialised; compute from axis correlations instead
    # Simple proxy: variance across models of the per-axis-per-task slope vs
    # variance across tasks of the per-axis-per-model slope.
    all_slopes: dict[tuple[str, str], list[float]] = defaultdict(list)  # (task, axis) -> values
    all_slopes_task: dict[tuple[str, str], list[float]] = defaultdict(list)  # (model, axis)
    for (model, task, axis), info in analysis["sensitivity"].items():
        if axis == "frame_mid3":
            continue
        s = info.get("slope")
        if s is None:
            continue
        all_slopes[(task, axis)].append(s)
        all_slopes_task[(model, axis)].append(s)

    model_vars = [statistics.pvariance(v) for v in all_slopes.values() if len(v) >= 2]
    task_vars = [statistics.pvariance(v) for v in all_slopes_task.values() if len(v) >= 2]
    model_var = statistics.mean(model_vars) if model_vars else None
    task_var = statistics.mean(task_vars) if task_vars else None

    status = "n/a"
    if model_var is not None and task_var is not None:
        status = "✓" if model_var > task_var else "✗"
    parts.append(
        f"| model-level variance > task-level variance | model > task | "
        f"model={_fmt(model_var, 4)}, task={_fmt(task_var, 4)} | {status} |"
    )
    parts.append("")
    return "\n".join(parts)


def render_full_report(analysis: dict[str, Any]) -> str:
    parts = [
        "# Response-surface analysis",
        "",
        f"Outcome: **{analysis['outcome_key']}**  •  "
        f"Models: {len(analysis['models'])}  •  "
        f"Tasks: {len(analysis['tasks_in_data'])}  •  "
        f"N rows: {analysis['n_rows']}",
        "",
    ]
    st_md, _ = render_sensitivity_table(analysis)
    parts.append(st_md)
    ms_md, _ = render_similarity(
        "Model similarity (6×6)", analysis["model_similarity"], analysis["models"]
    )
    parts.append(ms_md)
    ts_md, _ = render_similarity("Task similarity (5×5)", analysis["task_similarity"], list(TASKS))
    parts.append(ts_md)
    parts.append(render_axis_correlation(analysis))
    ep_md, _ = render_endpoints(analysis)
    parts.append(ep_md)
    parts.append(render_predictions(analysis))
    return "\n".join(parts)


def write_outputs(analysis: dict[str, Any], out_dir: Path, suffix: str = "") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"_{suffix}" if suffix else ""

    report = render_full_report(analysis)
    (out_dir / f"report{tag}.md").write_text(report, encoding="utf-8")

    _, sens_rows = render_sensitivity_table(analysis)
    _write_csv(
        out_dir / f"sensitivity{tag}.csv",
        ["model", "task", "axis", "slope", "ci_lo", "ci_hi", "n"],
        sens_rows,
    )

    _, ms_rows = render_similarity(
        "Model similarity", analysis["model_similarity"], analysis["models"]
    )
    _write_csv(
        out_dir / f"model_similarity{tag}.csv",
        ["model", *analysis["models"]],
        ms_rows,
    )

    _, ts_rows = render_similarity("Task similarity", analysis["task_similarity"], list(TASKS))
    _write_csv(
        out_dir / f"task_similarity{tag}.csv",
        ["task", *TASKS],
        ts_rows,
    )

    _, ep_rows = render_endpoints(analysis)
    _write_csv(
        out_dir / f"endpoints{tag}.csv",
        ["task", "model", "prohibitive", "permissive"],
        ep_rows,
    )

    profile_header = ["model"] + [f"{t}_{a}" for t in TASKS for a in AXES]
    profile_rows: list[list[Any]] = []
    for model in analysis["models"]:
        vec = analysis["profiles"][model]
        profile_rows.append([model, *[_fmt_cell(v) for v in vec]])
    _write_csv(out_dir / f"profiles{tag}.csv", profile_header, profile_rows)

    summary = {
        "outcome_key": analysis["outcome_key"],
        "models": analysis["models"],
        "tasks_in_data": analysis["tasks_in_data"],
        "n_rows": analysis["n_rows"],
    }
    (out_dir / f"summary{tag}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


# ── Robustness: z-scored continuous outcome ──────────────────────────────


def zscore_continuous(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a copy of rows with a new ``honesty_departure`` field — the
    task-natural ``metric`` z-scored within each task."""
    by_task: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        by_task[r["env"]].append(i)

    updated = [dict(r) for r in rows]
    for task, idxs in by_task.items():
        values = [rows[i].get("metric") for i in idxs]
        zs = _zscore([v if v is not None else None for v in values])
        for i, z in zip(idxs, zs):
            updated[i]["honesty_departure"] = z
    return updated


# ── CLI ──────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--logs", nargs="*", default=None, help="Ignored (kept for CLI compatibility; data is loaded from results.csv)")
    ap.add_argument("--out", type=Path, required=True, help="Output directory")
    ap.add_argument(
        "--n-bootstrap",
        type=int,
        default=1000,
        help="Bootstrap resamples per sensitivity slope (default 1000)",
    )
    ap.add_argument(
        "--robustness-continuous",
        action="store_true",
        help=(
            "Also run the analysis on the z-scored continuous 'honesty_departure' "
            "metric (brief §4 robustness appendix)."
        ),
    )
    args = ap.parse_args()

    rows = load_rows()
    if not rows:
        print("No rows loaded from the provided logs.", file=sys.stderr)
        sys.exit(1)

    analysis = run_analysis(rows, outcome_key="manipulation_occurred", n_boot=args.n_bootstrap)
    write_outputs(analysis, args.out)
    print(f"[info] wrote binary-outcome report to {args.out}/report.md", file=sys.stderr)

    if args.robustness_continuous:
        zrows = zscore_continuous(rows)
        z_analysis = run_analysis(zrows, outcome_key="honesty_departure", n_boot=args.n_bootstrap)
        write_outputs(z_analysis, args.out, suffix="continuous")
        print(
            f"[info] wrote continuous-outcome report to {args.out}/report_continuous.md",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
