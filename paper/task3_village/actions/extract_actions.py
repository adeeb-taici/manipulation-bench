"""Extract per-agent outcomes from T3 village commons eval logs.

One row per (sample, agent). Six agents per sample (agent_1..agent_6); one is
the manipulator (typically agent_1). Columns: axis metadata, agent role,
exploitation_rate, promise_action_gap, final_wealth, manipulator flag.
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
    REPO_ROOT / "paper/task3_village/eval_log.eval",
    REPO_ROOT / "paper/task3_village/eval_log_small_model_sweep.eval",
]
DEFAULT_OUTPUT = Path(__file__).parent / "actions.csv"


def _variant_for(path: Path) -> str:
    if path.name == "eval_log_small_model_sweep.eval":
        return "small_model_sweep"
    if path.name == "eval_log.eval":
        return "canonical"
    return "other"


def _scenario_meta(sample: Any) -> dict[str, Any]:
    md = sample.metadata or {}
    sc = md.get("scenario") or {}
    inner = sc.get("metadata") or {}
    return inner if isinstance(inner, dict) else {}


def _agent_models(sample: Any) -> dict[str, str | None]:
    """Map agent_1..agent_6 -> model label.

    T3's model_mapping is keyed by agent_name (agent_1, agent_2, ...).
    """
    md = sample.metadata or {}
    sc = md.get("scenario") or {}
    inner = sc.get("metadata") or {}
    mm = inner.get("model_mapping") or {}
    out: dict[str, str | None] = {}
    for agent in sc.get("agents") or []:
        name = agent.get("name")
        role = agent.get("model_role")
        label = mm.get(name) if name else None
        if not label and role:
            label = mm.get(role)
        if not label:
            label = agent.get("model")
        if name:
            out[name] = label
    return out


def _rows_from_sample(sample: Any, log_path: Path, variant: str) -> Iterable[dict[str, Any]]:
    inner = _scenario_meta(sample)
    env = inner.get("environment") or {}
    manipulator_name = env.get("manipulator_name") or inner.get("manipulator") or "agent_1"

    expl = (sample.scores or {}).get("exploitation_rate")
    pgap = (sample.scores or {}).get("promise_action_gap")
    fair = (sample.scores or {}).get("village_fairness")
    if expl is None:
        return
    expl_v = expl.value if isinstance(expl.value, dict) else {}
    pgap_v = pgap.value if pgap and isinstance(pgap.value, dict) else {}
    fair_md = getattr(fair, "metadata", None) or {} if fair else {}
    final_wealth = fair_md.get("final_wealth") or {}

    models = _agent_models(sample)

    base = {
        "task": "village",
        "variant": variant,
        "log_path": str(log_path.relative_to(REPO_ROOT)) if log_path.is_absolute() else str(log_path),
        "sample_id": sample.id,
        "frame": inner.get("frame"),
        "incentive": inner.get("incentive"),
        "difficulty": inner.get("difficulty"),
        "scenario_id": inner.get("scenario_id") or inner.get("cluster_id"),
        "manipulator_model": models.get(manipulator_name),
    }

    for agent_name in ("agent_1", "agent_2", "agent_3", "agent_4", "agent_5", "agent_6"):
        yield {
            **base,
            "agent": agent_name,
            "model": models.get(agent_name),
            "is_manipulator": int(agent_name == manipulator_name),
            "exploitation_rate": expl_v.get(agent_name),
            "promise_action_gap": pgap_v.get(agent_name),
            "final_wealth": final_wealth.get(agent_name),
        }


def _resolve_log_paths(glob_arg: str | None) -> list[Path]:
    if glob_arg:
        return sorted(Path(p) for p in glob.glob(glob_arg) if Path(p).suffix == ".eval")
    return [p for p in DEFAULT_LOGS if p.exists()]


COLUMNS = [
    "task", "variant", "log_path", "sample_id", "scenario_id",
    "manipulator_model",
    "frame", "incentive", "difficulty",
    "agent", "model", "is_manipulator",
    "exploitation_rate", "promise_action_gap", "final_wealth",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--logs", type=str, default=None)
    args = parser.parse_args()

    log_paths = _resolve_log_paths(args.logs)
    if not log_paths:
        print("[t3 actions] no input logs found", file=sys.stderr); sys.exit(1)

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
            print(f"[t3 actions] {path.relative_to(REPO_ROOT) if path.is_absolute() else path}: {log_rows} rows", file=sys.stderr)
    print(f"[t3 actions] wrote {n_rows} rows from {n_samples} samples -> {args.output.relative_to(REPO_ROOT) if args.output.is_absolute() else args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
