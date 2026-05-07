"""Extract per-question sales responses from T4 eval logs into a long-form CSV.

One row per (sample, question). Columns: axis metadata, the buyer question,
agent response text, ground-truth check_type/true_value/misleading_values, and
the deterministic classifier output (accurate/misleading/false). Designed for
qualitative cross-model analysis complementing the per-sample summary in
`paper/cross_task/results.csv`.

Usage:
    python paper/task4_sales/actions/extract_actions.py
    python paper/task4_sales/actions/extract_actions.py --logs '...'
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
    REPO_ROOT / "paper/task4_sales/eval_log.eval",
    REPO_ROOT / "paper/task4_sales/eval_log_small_model_sweep.eval",
]

DEFAULT_OUTPUT = Path(__file__).parent / "actions.csv"


def _variant_for(path: Path) -> str:
    if path.name == "eval_log_small_model_sweep.eval":
        return "small_model_sweep"
    if path.name == "eval_log.eval":
        return "canonical"
    return "other"


def _resolve_model_label(sample: Any) -> str | None:
    md = sample.metadata or {}
    label = md.get("model")
    if label:
        return label
    role = md.get("model_role")
    mm = md.get("model_mapping") or {}
    if role and role in mm:
        return mm[role]
    return None


def _rows_from_sample(sample: Any, log_path: Path, variant: str) -> Iterable[dict[str, Any]]:
    md = sample.metadata or {}
    questions: list[dict] = md.get("questions") or []
    ground_truth: list[dict] = md.get("ground_truth") or []
    responses: list[str] = md.get("responses") or []

    if not questions:
        return

    gt_by_qid = {gt.get("q_id"): gt for gt in ground_truth}

    classifications_by_qid: dict[str, dict] = {}
    sc = (sample.scores or {}).get("sales_classifier")
    if sc is not None:
        scorer_md = getattr(sc, "metadata", None) or {}
        for c in scorer_md.get("classifications", []) or []:
            classifications_by_qid[c.get("q_id")] = c

    base = {
        "task": "sales",
        "variant": variant,
        "log_path": str(log_path.relative_to(REPO_ROOT)) if log_path.is_absolute() else str(log_path),
        "sample_id": sample.id,
        "model": _resolve_model_label(sample),
        "frame": md.get("frame"),
        "incentive": md.get("incentive"),
        "difficulty": md.get("difficulty"),
        "product": md.get("product"),
        "scenario_id": md.get("scenario_id"),
    }

    for idx, q in enumerate(questions):
        qid = q.get("q_id")
        gt = gt_by_qid.get(qid, {})
        cls = classifications_by_qid.get(qid, {})
        response_text = responses[idx] if idx < len(responses) else None
        misleading_vals = gt.get("misleading_values")
        yield {
            **base,
            "q_idx": idx,
            "q_id": qid,
            "question_text": (q.get("text") or "")[:500],
            "check_type": gt.get("check_type"),
            "true_answer_desc": gt.get("true_answer_desc"),
            "true_value": gt.get("true_value"),
            "unit": gt.get("unit"),
            "misleading_values": (
                json.dumps(misleading_vals) if misleading_vals not in (None, []) else None
            ),
            "response_text": (response_text or "")[:2000] if response_text else None,
            "classification": cls.get("classification"),
            "classifier_rule": (cls.get("trace") or {}).get("rule"),
            "classifier_matched": (cls.get("trace") or {}).get("matched"),
        }


def _resolve_log_paths(glob_arg: str | None) -> list[Path]:
    if glob_arg:
        return sorted(Path(p) for p in glob.glob(glob_arg) if Path(p).suffix == ".eval")
    return [p for p in DEFAULT_LOGS if p.exists()]


COLUMNS = [
    "task", "variant", "log_path", "sample_id", "model",
    "frame", "incentive", "difficulty", "product", "scenario_id",
    "q_idx", "q_id", "question_text",
    "check_type", "true_answer_desc", "true_value", "unit", "misleading_values",
    "response_text",
    "classification", "classifier_rule", "classifier_matched",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--logs", type=str, default=None)
    args = parser.parse_args()

    log_paths = _resolve_log_paths(args.logs)
    if not log_paths:
        print("[t4 actions] no input logs found", file=sys.stderr)
        sys.exit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    n_rows = 0
    n_samples = 0
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for path in log_paths:
            variant = _variant_for(path)
            log_rows = 0
            for sample in read_eval_log_samples(str(path), all_samples_required=False):
                n_samples += 1
                for row in _rows_from_sample(sample, path, variant):
                    writer.writerow(row)
                    log_rows += 1
            n_rows += log_rows
            print(f"[t4 actions] {path.relative_to(REPO_ROOT) if path.is_absolute() else path}: {log_rows} rows", file=sys.stderr)

    print(f"[t4 actions] wrote {n_rows} rows from {n_samples} samples -> {args.output.relative_to(REPO_ROOT) if args.output.is_absolute() else args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
