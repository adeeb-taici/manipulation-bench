"""Extract per-message triage actions from T6 inbox eval logs into a long-form CSV.

One row per (sample, message_id). Columns include axis metadata, the agent's
chosen action, ground-truth `correct_action`, `topic_tag` (target/benign), and
`is_correct`. Designed for qualitative cross-model analysis (per-action heatmaps,
compliance-type classification, etc.) — complementing the per-sample scorer
summary in `paper/cross_task/results.csv`.

Usage:
    python paper/task6_inbox/actions/extract_actions.py
    python paper/task6_inbox/actions/extract_actions.py --logs 'logs/openai_sweep/*_t6/*.eval'
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
    REPO_ROOT / "paper/task6_inbox/eval_log.eval",
    *sorted(REPO_ROOT.glob("logs/openai_sweep/*_t6/*.eval")),
    *sorted(REPO_ROOT.glob("logs/claude_sweep/*_t6/*.eval")),
]

DEFAULT_OUTPUT = Path(__file__).parent / "actions.csv"


def _variant_for(path: Path) -> str:
    if "openai_sweep" in path.parts or "claude_sweep" in path.parts:
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
    inbox: list[dict] = md.get("inbox") or []
    if not inbox:
        return

    msg_meta = {m["message_id"]: m for m in inbox}

    actions: dict[str, dict[str, Any]] = {}
    for msg in sample.messages or []:
        if getattr(msg, "role", None) != "assistant":
            continue
        for tc in (getattr(msg, "tool_calls", None) or []):
            if tc.function != "triage_message":
                continue
            mid = tc.arguments.get("message_id")
            if mid is None or mid in actions:
                continue
            actions[mid] = {
                "agent_action": tc.arguments.get("action"),
                "agent_reasoning": (tc.arguments.get("reasoning") or "")[:500] or None,
                "reply_draft_present": bool(tc.arguments.get("reply_draft")),
            }

    base = {
        "task": "inbox",
        "variant": variant,
        "log_path": str(log_path.relative_to(REPO_ROOT)) if log_path.is_absolute() else str(log_path),
        "sample_id": sample.id,
        "model": _resolve_model_label(sample),
        "frame": md.get("frame"),
        "incentive": md.get("incentive"),
        "difficulty": md.get("difficulty"),
        "suppression_target": md.get("suppression_target"),
        "n_inbox": len(inbox),
    }

    for mid, msg in msg_meta.items():
        act = actions.get(mid, {})
        agent_action = act.get("agent_action")
        correct_action = msg.get("correct_action")
        yield {
            **base,
            "message_id": mid,
            "topic_tag": msg.get("topic_tag"),
            "from_": msg.get("from"),
            "subject": (msg.get("subject") or "")[:200],
            "correct_action": correct_action,
            "agent_action": agent_action,
            "is_correct": (
                None if agent_action is None else (agent_action == correct_action)
            ),
            "agent_reasoning": act.get("agent_reasoning"),
            "reply_draft_present": act.get("reply_draft_present"),
        }


def _resolve_log_paths(glob_arg: str | None) -> list[Path]:
    if glob_arg:
        return sorted(Path(p) for p in glob.glob(glob_arg) if Path(p).suffix == ".eval")
    return [p for p in DEFAULT_LOGS if p.exists()]


COLUMNS = [
    "task", "variant", "log_path", "sample_id", "model",
    "frame", "incentive", "difficulty", "suppression_target",
    "n_inbox", "message_id", "topic_tag", "from_", "subject",
    "correct_action", "agent_action", "is_correct",
    "reply_draft_present", "agent_reasoning",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--logs", type=str, default=None)
    args = parser.parse_args()

    log_paths = _resolve_log_paths(args.logs)
    if not log_paths:
        print("[t6 actions] no input logs found", file=sys.stderr)
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
            print(f"[t6 actions] {path.relative_to(REPO_ROOT) if path.is_absolute() else path}: {log_rows} rows", file=sys.stderr)

    print(f"[t6 actions] wrote {n_rows} rows from {n_samples} samples -> {args.output.relative_to(REPO_ROOT) if args.output.is_absolute() else args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
