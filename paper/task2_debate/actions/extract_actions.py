"""Extract per-juror belief shifts from T2 debate eval logs.

One row per (sample, condition, juror). Each debate run has two conditions
(truthful, manipulator) and N jurors per condition (typically 3-7). Pre/post
beliefs come from the ground_truth_persuasion scorer's per-juror metadata.
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
    REPO_ROOT / "paper/task2_debate/eval_log.eval",
    REPO_ROOT / "paper/task2_debate/eval_log_small_model_sweep.eval",
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


def _model_label(sample: Any) -> str | None:
    inner = _scenario_meta(sample)
    label = inner.get("manipulator_model") or inner.get("model")
    if label:
        return label
    sc = (sample.metadata or {}).get("scenario") or {}
    mm = inner.get("model_mapping") or {}
    for agent in sc.get("agents") or []:
        role = agent.get("model_role") or ""
        if "manipulator" in role:
            return mm.get(role) or agent.get("model")
    return None


def _rows_from_sample(sample: Any, log_path: Path, variant: str) -> Iterable[dict[str, Any]]:
    inner = _scenario_meta(sample)

    base = {
        "task": "debate",
        "variant": variant,
        "log_path": str(log_path.relative_to(REPO_ROOT)) if log_path.is_absolute() else str(log_path),
        "sample_id": sample.id,
        "model": _model_label(sample),
        "frame": inner.get("frame"),
        "incentive": inner.get("incentive"),
        "difficulty": inner.get("difficulty"),
        "claim_id": inner.get("claim_id") or inner.get("scenario_id") or inner.get("cluster_id"),
        "ground_truth": None,
    }

    gtp = (sample.scores or {}).get("ground_truth_persuasion")
    if gtp is None:
        return
    smd = getattr(gtp, "metadata", None) or {}
    base["ground_truth"] = smd.get("ground_truth")
    per_juror = smd.get("per_juror") or {}

    voting = (sample.scores or {}).get("juror_voting")
    voting_md = getattr(voting, "metadata", None) or {} if voting else {}
    quality = (sample.scores or {}).get("argument_quality")
    quality_v = quality.value if quality and isinstance(quality.value, dict) else {}
    detection = (sample.scores or {}).get("manipulation_detection")
    detection_v = detection.value if detection and isinstance(detection.value, dict) else {}

    for condition in ("truthful", "manipulator"):
        cond_data = per_juror.get(condition)
        if not isinstance(cond_data, dict):
            cond_data = per_juror

        cond_quality = quality_v.get(condition) if isinstance(quality_v, dict) else None
        cond_detection = detection_v.get(condition) if isinstance(detection_v, dict) else None
        cond_voting = voting_md.get(condition) if isinstance(voting_md, dict) else None
        votes = (cond_voting or {}).get("votes") if isinstance(cond_voting, dict) else None
        juror_roles = smd.get("juror_roles") or list(cond_data.keys())

        for idx, juror in enumerate(juror_roles):
            jdata = cond_data.get(juror) if isinstance(cond_data, dict) else None
            if not isinstance(jdata, dict):
                continue
            yield {
                **base,
                "condition": condition,
                "juror": juror,
                "pre_belief": jdata.get("pre_mean"),
                "post_belief": jdata.get("post_mean"),
                "shift": jdata.get("shift"),
                "voted_for_condition": (
                    int(bool(votes[idx])) if votes is not None and idx < len(votes) else None
                ),
                "argument_quality": cond_quality,
                "manipulation_detection": cond_detection,
            }


def _resolve_log_paths(glob_arg: str | None) -> list[Path]:
    if glob_arg:
        return sorted(Path(p) for p in glob.glob(glob_arg) if Path(p).suffix == ".eval")
    return [p for p in DEFAULT_LOGS if p.exists()]


COLUMNS = [
    "task", "variant", "log_path", "sample_id", "claim_id", "model",
    "frame", "incentive", "difficulty",
    "ground_truth", "condition", "juror",
    "pre_belief", "post_belief", "shift", "voted_for_condition",
    "argument_quality", "manipulation_detection",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--logs", type=str, default=None)
    args = parser.parse_args()

    log_paths = _resolve_log_paths(args.logs)
    if not log_paths:
        print("[t2 actions] no input logs found", file=sys.stderr); sys.exit(1)

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
            print(f"[t2 actions] {path.relative_to(REPO_ROOT) if path.is_absolute() else path}: {log_rows} rows", file=sys.stderr)
    print(f"[t2 actions] wrote {n_rows} rows from {n_samples} samples -> {args.output.relative_to(REPO_ROOT) if args.output.is_absolute() else args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
