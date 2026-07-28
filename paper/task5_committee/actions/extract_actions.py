"""Extract per-rating actions from T5 committee eval logs.

One row per (sample, agent, candidate, phase). Each agent rates 4 candidates
on 4 criteria across 2 phases (initial/private_rating, final_rating). The mean
rating across criteria is the per-row metric. The interested party (one agent)
has a private affiliation with a favored candidate; we flag it via metadata.

Action data lives in the solver's StoreModel, accessed via
`sample.store["InteractionState:turns"]`. Each turn with phase
``private_rating`` or ``final_rating`` carries a ``metadata.action`` like
``"ratings:{...}"`` whose JSON body is candidate_id -> criterion -> int.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from inspect_ai.log import read_eval_log_samples

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_LOGS = [
    REPO_ROOT / "paper/task5_committee/eval_log.eval",
    REPO_ROOT / "paper/task5_committee/eval_log_small_model_sweep.eval",
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


def _agent_models(sample: Any) -> tuple[dict[str, str | None], str | None]:
    """Return (agent_name -> model label, interested_party_name).

    T5's model_mapping is keyed by agent_name (agent_1..agent_5).
    """
    md = sample.metadata or {}
    sc = md.get("scenario") or {}
    inner = sc.get("metadata") or {}
    mm = inner.get("model_mapping") or {}
    out: dict[str, str | None] = {}
    interested: str | None = None
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
        amd = agent.get("metadata") or {}
        if amd.get("interested_party"):
            interested = name
    if interested is None:
        env = inner.get("environment") or {}
        interested = env.get("interested_party_name")
    return out, interested


def _parse_ratings_action(action_str: str) -> dict[str, dict[str, float]] | None:
    if not action_str or not action_str.startswith("ratings:"):
        return None
    try:
        return json.loads(action_str[len("ratings:"):])
    except (json.JSONDecodeError, ValueError):
        return None


def _rows_from_sample(sample: Any, log_path: Path, variant: str) -> Iterable[dict[str, Any]]:
    inner = _scenario_meta(sample)
    env = inner.get("environment") or {}
    favored = inner.get("favored_candidate") or env.get("favored_candidate")

    models, interested_name = _agent_models(sample)

    store = getattr(sample, "store", {}) or {}
    turns = store.get("InteractionState:turns") or []
    if not turns:
        return

    base = {
        "task": "committee",
        "variant": variant,
        "log_path": str(log_path.relative_to(REPO_ROOT)) if log_path.is_absolute() else str(log_path),
        "sample_id": sample.id,
        "frame": inner.get("frame"),
        "incentive": inner.get("incentive"),
        "difficulty": inner.get("difficulty"),
        "slate_id": inner.get("slate_id") or inner.get("scenario_id") or env.get("slate_id"),
        "favored_candidate": favored,
        "interested_party_name": interested_name,
        "interested_model_label": inner.get("interested_model_label"),
    }

    for turn in turns:
        tmd = turn.get("metadata") or {}
        phase = tmd.get("phase")
        if phase not in ("private_rating", "final_rating"):
            continue
        phase_label = "initial" if phase == "private_rating" else "final"
        agent = turn.get("speaker")
        ratings = _parse_ratings_action(tmd.get("action") or "")
        if not ratings:
            continue
        for candidate_id, crit_dict in ratings.items():
            if not isinstance(crit_dict, dict):
                continue
            vals = [v for v in crit_dict.values() if isinstance(v, (int, float))]
            if not vals:
                continue
            yield {
                **base,
                "agent": agent,
                "model": models.get(agent),
                "is_interested_party": int(agent == interested_name) if agent and interested_name else None,
                "phase": phase_label,
                "round": turn.get("round"),
                "candidate_id": candidate_id,
                "is_favored": int(candidate_id == favored) if favored else None,
                "mean_rating": sum(vals) / len(vals),
                "n_criteria": len(vals),
                "ratings_json": json.dumps(crit_dict),
            }


def _resolve_log_paths(glob_arg: str | None) -> list[Path]:
    if glob_arg:
        return sorted(Path(p) for p in glob.glob(glob_arg) if Path(p).suffix == ".eval")
    return [p for p in DEFAULT_LOGS if p.exists()]


COLUMNS = [
    "task", "variant", "log_path", "sample_id", "slate_id",
    "frame", "incentive", "difficulty",
    "favored_candidate", "interested_party_name", "interested_model_label",
    "agent", "model", "is_interested_party",
    "phase", "round", "candidate_id", "is_favored",
    "mean_rating", "n_criteria", "ratings_json",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--logs", type=str, default=None)
    args = parser.parse_args()

    log_paths = _resolve_log_paths(args.logs)
    if not log_paths:
        print("[t5 actions] no input logs found", file=sys.stderr); sys.exit(1)

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
            print(f"[t5 actions] {path.relative_to(REPO_ROOT) if path.is_absolute() else path}: {log_rows} rows", file=sys.stderr)
    print(f"[t5 actions] wrote {n_rows} rows from {n_samples} samples -> {args.output.relative_to(REPO_ROOT) if args.output.is_absolute() else args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
