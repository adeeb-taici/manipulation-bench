"""Flatten paper eval logs into a single tidy CSV.

One row per sample (rollout) across the 5 paper tasks × {canonical, extended}
log variants. Columns: identity/setup + normalized manipulation_metric +
flattened <scorer>__<key> scores.

Re-runnable. Does not modify or delete any source data.

Usage:
    python paper/cross_task/scripts/eval_logs_to_csv.py
    python paper/cross_task/scripts/eval_logs_to_csv.py -o foo.csv
    python paper/cross_task/scripts/eval_logs_to_csv.py --logs 'logs/*.eval'
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from inspect_ai.log import read_eval_log

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from experiments.reanalysis.load import _row_from_sample, _flatten_metadata  # noqa: E402

DEFAULT_LOGS = [
    REPO_ROOT / "paper/task1_bargaining/eval_log.eval",
    REPO_ROOT / "paper/task1_bargaining/eval_log_extended.eval",
    REPO_ROOT / "paper/task2_debate/eval_log.eval",
    REPO_ROOT / "paper/task3_village/eval_log.eval",
    REPO_ROOT / "paper/task3_village/eval_log_extended.eval",
    REPO_ROOT / "paper/task4_sales/eval_log.eval",
    REPO_ROOT / "paper/task4_sales/eval_log_extended.eval",
    REPO_ROOT / "paper/task5_committee/eval_log.eval",
    REPO_ROOT / "paper/task5_committee/eval_log_extended.eval",
]

DEFAULT_OUTPUT = REPO_ROOT / "paper/cross_task/results.csv"

TASK_DIR_TO_KEY = {
    "task1_bargaining": "bargaining",
    "task2_debate": "debate",
    "task3_village": "village",
    "task4_sales": "sales",
    "task5_committee": "committee",
}


def _resolve_log_paths(glob_arg: str | None) -> list[Path]:
    """Default: 9 paper logs that exist on disk. Glob: explicit override."""
    if glob_arg:
        return sorted(Path(p) for p in glob.glob(glob_arg) if Path(p).suffix == ".eval")
    return [p for p in DEFAULT_LOGS if p.exists()]


def _infer_task_variant(path: Path) -> tuple[str, str]:
    """Infer (task, variant) from log path."""
    task = "unknown"
    for part in path.parts:
        m = re.match(r"task\d+_\w+", part)
        if m:
            task = TASK_DIR_TO_KEY.get(m.group(0), "unknown")
            break
        m = re.search(r"task\d+_(bargaining|debate|village|sales|committee)", part)
        if m:
            task = TASK_DIR_TO_KEY.get(m.group(0), "unknown")
            break

    name = path.name
    if name == "eval_log_extended.eval":
        variant = "extended"
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
    """Read one .eval log and produce one row per scored, non-errored sample."""
    task, variant = _infer_task_variant(path)
    if task == "unknown":
        print(f"[eval_logs_to_csv] {path}: unknown task, skipping", file=sys.stderr)
        return []

    log = read_eval_log(str(path))
    rows: list[dict[str, Any]] = []
    for sample in log.samples or []:
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

    rows: list[dict[str, Any]] = []
    for path in log_paths:
        rows.extend(_rows_from_log(path))

    if not rows:
        print("[eval_logs_to_csv] no samples extracted", file=sys.stderr)
        sys.exit(1)

    df = pd.DataFrame.from_records(rows)
    df = _order_columns(df)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"[eval_logs_to_csv] wrote {len(df)} rows × {len(df.columns)} cols -> {args.output}")


if __name__ == "__main__":
    main()
