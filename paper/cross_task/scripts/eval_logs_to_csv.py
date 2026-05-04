"""Flatten paper eval logs into a single tidy CSV.

One row per sample (rollout) across the 5 paper tasks × {canonical,
small_model_sweep} log variants. Columns: identity/setup + normalized
manipulation_metric + flattened <scorer>__<key> scores.

Re-runnable. Does not modify or delete any source data.

Usage:
    python paper/cross_task/scripts/eval_logs_to_csv.py
    python paper/cross_task/scripts/eval_logs_to_csv.py -o foo.csv
    python paper/cross_task/scripts/eval_logs_to_csv.py --logs 'logs/*.eval'
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from inspect_ai.log import read_eval_log, read_eval_log_samples

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(REPO_ROOT / "src"))

from load import _row_from_sample, _flatten_metadata  # noqa: E402

DEFAULT_LOGS = [
    REPO_ROOT / "paper/task1_bargaining/eval_log.eval",
    REPO_ROOT / "paper/task1_bargaining/eval_log_small_model_sweep.eval",
    REPO_ROOT / "paper/task2_debate/eval_log.eval",
    REPO_ROOT / "paper/task2_debate/eval_log_small_model_sweep.eval",
    REPO_ROOT / "paper/task3_village/eval_log.eval",
    REPO_ROOT / "paper/task3_village/eval_log_small_model_sweep.eval",
    REPO_ROOT / "paper/task4_sales/eval_log.eval",
    REPO_ROOT / "paper/task4_sales/eval_log_small_model_sweep.eval",
    REPO_ROOT / "paper/task5_committee/eval_log.eval",
    REPO_ROOT / "paper/task5_committee/eval_log_small_model_sweep.eval",
    REPO_ROOT / "paper/task6_inbox/eval_log.eval",
]

# T6 has no combined sweep log yet; pick up per-model sweeps from logs/*_sweep/<label>_t6/.
# Matches patterns:
#   logs/openai_sweep/gpt41_t6/<timestamp>_inbox-bench_<id>.eval
#   logs/openai_sweep/gpt41nano_t6_pilot/...      <- pilot variant, kept distinct
#   logs/anthropic_sweep/haiku35_t6/<timestamp>_inbox-bench_<id>.eval
DEFAULT_T6_SWEEP_GLOBS = [
    "logs/openai_sweep/*_t6/*.eval",
    "logs/openai_sweep/*_t6_pilot/*.eval",
    "logs/anthropic_sweep/*_t6/*.eval",
    "logs/anthropic_sweep/*_t6_pilot/*.eval",
]

DEFAULT_OUTPUT = REPO_ROOT / "paper/cross_task/results.csv"

TASK_DIR_TO_KEY = {
    "task1_bargaining": "bargaining",
    "task2_debate": "debate",
    "task3_village": "village",
    "task4_sales": "sales",
    "task5_committee": "committee",
    "task6_inbox": "inbox",
}


def _resolve_log_paths(glob_arg: str | None) -> list[Path]:
    """Default: paper combined logs + T6 per-model sweep logs that exist on disk."""
    if glob_arg:
        return sorted(Path(p) for p in glob.glob(glob_arg) if Path(p).suffix == ".eval")
    paths = [p for p in DEFAULT_LOGS if p.exists()]
    for pattern in DEFAULT_T6_SWEEP_GLOBS:
        paths.extend(
            Path(p) for p in glob.glob(str(REPO_ROOT / pattern))
            if Path(p).suffix == ".eval"
        )
    # Stable ordering, deduplicated.
    return sorted({p.resolve() for p in paths})


_SWEEP_DIR_RE = re.compile(
    r"^(?P<label>[a-z0-9]+)_t(?P<n>\d+)(?P<pilot>_pilot)?$"
)
_SWEEP_TASK_BY_N = {
    "1": "bargaining", "2": "debate", "3": "village",
    "4": "sales",      "5": "committee", "6": "inbox",
}


def _infer_task_variant(path: Path) -> tuple[str, str]:
    """Infer (task, variant) from log path.

    Recognized layouts:
      - paper/taskN_<env>/eval_log.eval                          -> (env, canonical)
      - paper/taskN_<env>/eval_log_small_model_sweep.eval        -> (env, small_model_sweep)
      - paper/taskN_<env>/eval_log_extended.eval                 -> (env, extended)
      - logs/{openai,anthropic}_sweep/<label>_tN[_pilot]/*.eval  -> (env_for_N, small_model_sweep)
    """
    parts = path.parts

    # Per-model sweep directory: logs/<provider>_sweep/<label>_tN[_pilot]/<file>.eval
    for i, part in enumerate(parts):
        if part.endswith("_sweep") and i + 1 < len(parts):
            m = _SWEEP_DIR_RE.match(parts[i + 1])
            if m and m.group("n") in _SWEEP_TASK_BY_N:
                variant = "pilot" if m.group("pilot") else "small_model_sweep"
                return _SWEEP_TASK_BY_N[m.group("n")], variant

    task = "unknown"
    for part in parts:
        # Try specific-env regex first (handles filenames like task3_village_sweep_42.eval)
        m = re.search(r"task\d+_(bargaining|debate|village|sales|committee|inbox)", part)
        if m:
            key = m.group(0)
            if key in TASK_DIR_TO_KEY:
                task = TASK_DIR_TO_KEY[key]
                break
        # Then try strict directory-name match (handles task1_bargaining/ etc.)
        m = re.fullmatch(r"task\d+_\w+", part)
        if m and m.group(0) in TASK_DIR_TO_KEY:
            task = TASK_DIR_TO_KEY[m.group(0)]
            break

    name = path.name
    if name == "eval_log_extended.eval":
        variant = "extended"
    elif name == "eval_log_small_model_sweep.eval":
        variant = "small_model_sweep"
    elif name == "eval_log.eval":
        variant = "canonical"
    else:
        variant = "other"
    return task, variant


def _flatten_scores(scores: dict[str, Any] | None) -> dict[str, Any]:
    """Flatten sample.scores into <scorer>__<key> columns."""
    if not scores:
        return {}
    out: dict[str, Any] = {}
    for scorer_name, score in scores.items():
        value = getattr(score, "value", None)
        if value is None:
            continue
        if isinstance(value, dict):
            for k, v in value.items():
                out[f"{scorer_name}__{k}"] = v
        else:
            out[scorer_name] = value
    return out


EXTRA_SETUP_KEYS = ("scenario_id", "manipulator", "num_agents", "topology", "topic")


def _extra_setup_fields(sample: Any, md: dict[str, Any]) -> dict[str, Any]:
    """Pull setup columns beyond what _row_from_sample already produces."""
    out: dict[str, Any] = {"epoch": getattr(sample, "epoch", None)}
    for k in EXTRA_SETUP_KEYS:
        out[k] = md.get(k)
    mm = md.get("model_mapping")
    out["model_mapping"] = json.dumps(mm) if mm is not None else None
    return out


def _rows_from_log(path: Path) -> list[dict[str, Any]]:
    """Read one .eval log and produce one row per scored, non-errored sample.

    Uses read_eval_log_samples() so only one sample is held in memory at a time
    from Inspect's side.  The test suite can monkeypatch read_eval_log_samples on
    this module to inject fake data.
    """
    task, variant = _infer_task_variant(path)
    if task == "unknown":
        print(f"[eval_logs_to_csv] {path}: unknown task, skipping", file=sys.stderr)
        return []

    rows: list[dict[str, Any]] = []
    for sample in read_eval_log_samples(str(path), all_samples_required=False):
        base = _row_from_sample(sample, task)
        if base is None:
            continue

        md = _flatten_metadata(sample)
        row: dict[str, Any] = {
            "task": task,
            "variant": variant,
            "log_path": str(path),
            "sample_id": base["sample_id"],
            "model": base["model"],
            "frame": base["frame"],
            "incentive": base["incentive"],
            "difficulty": base["difficulty"],
            "cluster_id": base["cluster_id"],
            "manipulation_metric": base["metric"],
            "manipulation_occurred": base["manipulation_occurred"],
        }
        row.update(_extra_setup_fields(sample, md))
        row.update(_flatten_scores(sample.scores))
        rows.append(row)
    print(f"[eval_logs_to_csv] {path.name}: {len(rows)} rows", file=sys.stderr)
    return rows


IDENTITY_COLUMNS = [
    "task", "variant", "log_path",
    "sample_id", "epoch", "scenario_id", "cluster_id",
    "model", "manipulator",
    "frame", "incentive", "difficulty",
    "num_agents", "topology", "topic", "model_mapping",
]

NORMALIZED_METRIC_COLUMNS = ["manipulation_metric", "manipulation_occurred"]


def _order_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Pin identity prefix, then normalized metric, then alphabetized scorer cols."""
    present = list(df.columns)
    leading = [c for c in IDENTITY_COLUMNS if c in present]
    metric = [c for c in NORMALIZED_METRIC_COLUMNS if c in present]
    leading_set = set(leading) | set(metric)
    rest = sorted(c for c in present if c not in leading_set)
    return df[leading + metric + rest]


def _order_column_names(cols: Iterable[str]) -> list[str]:
    """Same ordering as _order_columns but operates on a list of column names."""
    present = list(cols)
    leading = [c for c in IDENTITY_COLUMNS if c in present]
    metric = [c for c in NORMALIZED_METRIC_COLUMNS if c in present]
    leading_set = set(leading) | set(metric)
    rest = sorted(c for c in present if c not in leading_set)
    return leading + metric + rest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--logs",
        type=str,
        default=None,
        help="Glob for input .eval logs (overrides default 9 paper logs)",
    )
    args = parser.parse_args()

    log_paths = _resolve_log_paths(args.logs)
    if not log_paths:
        print("[eval_logs_to_csv] no input logs found", file=sys.stderr)
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        all_keys: set[str] = set()
        total_rows = 0

        # Pass 1: process one log at a time, dump rows to per-log JSONL temp files,
        # track union of all column names.  Memory for each log is freed before the next.
        tmp_files: list[Path] = []
        for i, path in enumerate(log_paths):
            rows = _rows_from_log(path)
            if not rows:
                continue
            for row in rows:
                all_keys.update(row.keys())
            tmp_file = tmp_path / f"log_{i}.jsonl"
            with tmp_file.open("w", encoding="utf-8") as f:
                for row in rows:
                    f.write(json.dumps(row, default=str) + "\n")
            total_rows += len(rows)
            tmp_files.append(tmp_file)
            del rows  # free memory before opening next log

        if not tmp_files:
            print("[eval_logs_to_csv] no samples extracted", file=sys.stderr)
            sys.exit(1)

        # Determine final ordered column list from union of all keys seen.
        ordered_cols = _order_column_names(all_keys)

        # Pass 2: stream each JSONL temp file into the output CSV.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", newline="", encoding="utf-8") as csv_fh:
            writer = csv.DictWriter(
                csv_fh,
                fieldnames=ordered_cols,
                extrasaction="ignore",
            )
            writer.writeheader()
            for tmp_file in tmp_files:
                with tmp_file.open("r", encoding="utf-8") as jf:
                    for line in jf:
                        writer.writerow(json.loads(line))

    print(
        f"[eval_logs_to_csv] wrote {total_rows} rows × {len(ordered_cols)} cols"
        f" -> {args.output}"
    )


if __name__ == "__main__":
    main()
