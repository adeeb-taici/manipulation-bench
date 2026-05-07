"""Extract per-agent valuation submissions from T1 bargaining eval logs.

One row per (sample, agent). Two agents per sample (A, B), each commits a
stated valuation that may deviate from the true valuation. Columns: axis
metadata, agent role, true_value, stated_value, deviation, lied flag.
"""

from __future__ import annotations

import argparse
import csv
import glob
import sys
from pathlib import Path
from typing import Any, Iterable

from inspect_ai.log import read_eval_log_samples

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_LOGS = [
    REPO_ROOT / "paper/task1_bargaining/eval_log.eval",
    REPO_ROOT / "paper/task1_bargaining/eval_log_small_model_sweep.eval",
]
DEFAULT_OUTPUT = Path(__file__).parent / "actions.csv"


def _variant_for(path: Path) -> str:
    if path.name == "eval_log_small_model_sweep.eval":
        return "small_model_sweep"
    if path.name == "eval_log.eval":
        return "canonical"
    return "other"


def _scenario_meta(sample: Any) -> dict[str, Any]:
    """T1 stores all axes inside metadata.scenario.metadata."""
    md = sample.metadata or {}
    sc = md.get("scenario") or {}
    inner = sc.get("metadata") or {}
    return inner if isinstance(inner, dict) else {}


def _resolve_models(sample: Any) -> dict[str, str | None]:
    """Map agent name (a/b) -> model label.

    T1 stores the per-agent model in scenario.metadata.agent_{a,b}_model,
    not in a model_mapping dict. Falls back to scenario.agents[].model.
    """
    md = sample.metadata or {}
    sc = md.get("scenario") or {}
    inner = sc.get("metadata") or {}
    out: dict[str, str | None] = {
        "a": inner.get("agent_a_model"),
        "b": inner.get("agent_b_model"),
    }
    mm = inner.get("model_mapping") or {}
    for agent in sc.get("agents") or []:
        name = agent.get("name")
        role = agent.get("model_role")
        label = (mm.get(name) or mm.get(role)) if (name or role) else None
        if not label:
            label = agent.get("model")
        if name and not out.get(name) and label:
            out[name] = label
    return out


def _rows_from_sample(sample: Any, log_path: Path, variant: str) -> Iterable[dict[str, Any]]:
    inner = _scenario_meta(sample)
    sc = (sample.scores or {}).get("bargaining_commit")
    if sc is None:
        return
    sv = sc.value if isinstance(sc.value, dict) else {}
    smd = getattr(sc, "metadata", None) or {}
    lie_threshold = smd.get("lie_threshold")

    models = _resolve_models(sample)
    manipulator = inner.get("manipulator") or inner.get("manipulator_role")

    base = {
        "task": "bargaining",
        "variant": variant,
        "log_path": str(log_path.relative_to(REPO_ROOT)) if log_path.is_absolute() else str(log_path),
        "sample_id": sample.id,
        "frame": inner.get("frame"),
        "incentive": inner.get("incentive"),
        "difficulty": inner.get("difficulty"),
        "scenario_id": inner.get("scenario_id") or inner.get("cluster_id"),
        "lie_threshold": lie_threshold,
    }

    for agent_letter in ("a", "b"):
        true_v = sv.get(f"agent_{agent_letter}_true")
        stated_v = sv.get(f"agent_{agent_letter}_stated")
        deviation = sv.get(f"agent_{agent_letter}_deviation")
        lied = sv.get(f"agent_{agent_letter}_lied")
        agent_name = f"agent_{agent_letter}"
        model_label = (
            models.get(agent_letter)
            or models.get(agent_name)
            or models.get(f"model_{agent_letter}")
        )
        yield {
            **base,
            "agent": agent_letter,
            "model": model_label,
            "is_manipulator": (
                None if manipulator is None
                else int(manipulator in (agent_name, f"model_{agent_letter}", agent_letter))
            ),
            "true_value": true_v,
            "stated_value": stated_v,
            "deviation": deviation,
            "lied": lied,
        }


def _resolve_log_paths(glob_arg: str | None) -> list[Path]:
    if glob_arg:
        return sorted(Path(p) for p in glob.glob(glob_arg) if Path(p).suffix == ".eval")
    return [p for p in DEFAULT_LOGS if p.exists()]


COLUMNS = [
    "task", "variant", "log_path", "sample_id", "scenario_id", "model",
    "frame", "incentive", "difficulty",
    "agent", "is_manipulator",
    "true_value", "stated_value", "deviation", "lied", "lie_threshold",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--logs", type=str, default=None)
    args = parser.parse_args()

    log_paths = _resolve_log_paths(args.logs)
    if not log_paths:
        print("[t1 actions] no input logs found", file=sys.stderr); sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    n_rows = n_samples = 0
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for path in log_paths:
            variant = _variant_for(path)
            log_rows = 0
            for sample in read_eval_log_samples(str(path), all_samples_required=False):
                n_samples += 1
                for row in _rows_from_sample(sample, path, variant):
                    writer.writerow(row); log_rows += 1
            n_rows += log_rows
            print(f"[t1 actions] {path.relative_to(REPO_ROOT) if path.is_absolute() else path}: {log_rows} rows", file=sys.stderr)

    print(f"[t1 actions] wrote {n_rows} rows from {n_samples} samples -> {args.output.relative_to(REPO_ROOT) if args.output.is_absolute() else args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
