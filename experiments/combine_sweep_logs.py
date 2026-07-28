"""Combine paper eval logs with the OpenAI/Claude sweep logs.

Produces extended .eval files at paper/task<N>/eval_log_extended.eval that contain
the original paper roster (6 frontier models) PLUS the sweep additions, so all
analysis tools can see them as one combined log.

Originals at paper/task<N>/eval_log.eval are NOT modified.

Sample IDs include the model label (e.g. ..._gpt54nano_seed36), so paper samples
and sweep samples never collide on dedup. Verified before running.

Usage:
    python experiments/combine_sweep_logs.py
"""

from __future__ import annotations

import glob
from pathlib import Path

from inspect_ai.log import EvalLog, read_eval_log, write_eval_log


# Patterns are evaluated in order. Later sources override earlier ones on
# sample-id collision (same convention as combine_eval_logs.py). Paper logs
# come first as the canonical base.
TASK_SPLITS: dict[str, list[str]] = {
    "paper/task1_bargaining/eval_log_extended.eval": [
        "paper/task1_bargaining/eval_log.eval",
        "logs/openai_sweep/gpt54nano_t1/*.eval",
        "logs/openai_sweep/gpt54mini_t1/*.eval",
        "logs/openai_sweep/gpt41nano_t1/*.eval",
        "logs/openai_sweep/gpt41mini_t1/*.eval",
        "logs/openai_sweep/gpt41_t1/*.eval",
        "logs/claude_sweep/haiku35_t1/*.eval",
        "logs/claude_sweep/haiku45_t1/*.eval",
        "logs/claude_sweep/sonnet37_t1/*.eval",
        "logs/claude_sweep/sonnet46_t1/*.eval",
    ],
    "paper/task4_sales/eval_log_extended.eval": [
        "paper/task4_sales/eval_log.eval",
        "logs/openai_sweep/gpt54nano_t4/*.eval",
        "logs/openai_sweep/gpt54mini_t4/*.eval",
        "logs/openai_sweep/gpt41nano_t4/*.eval",
        "logs/openai_sweep/gpt41mini_t4/*.eval",
        "logs/openai_sweep/gpt41_t4/*.eval",
        "logs/claude_sweep/haiku35_t4/*.eval",
        "logs/claude_sweep/haiku45_t4/*.eval",
        "logs/claude_sweep/sonnet37_t4/*.eval",
        "logs/claude_sweep/sonnet46_t4/*.eval",
    ],
    "paper/task5_committee/eval_log_extended.eval": [
        "paper/task5_committee/eval_log.eval",
        "logs/openai_sweep/gpt54nano_t5/*.eval",
        "logs/openai_sweep/gpt54mini_t5/*.eval",
        "logs/openai_sweep/gpt41nano_t5/*.eval",
        "logs/openai_sweep/gpt41mini_t5/*.eval",
        "logs/openai_sweep/gpt41_t5/*.eval",
        "logs/claude_sweep/haiku35_t5/*.eval",
        "logs/claude_sweep/haiku45_t5/*.eval",
        "logs/claude_sweep/sonnet37_t5/*.eval",
        "logs/claude_sweep/sonnet46_t5/*.eval",
    ],
    "paper/task3_village/eval_log_extended.eval": [
        "paper/task3_village/eval_log.eval",
        "logs/openai_sweep/gpt54nano_t3/*.eval",
        "logs/openai_sweep/gpt54mini_t3/*.eval",
        "logs/openai_sweep/gpt41nano_t3/*.eval",
        "logs/openai_sweep/gpt41mini_t3/*.eval",
        "logs/openai_sweep/gpt41_t3/*.eval",
        # Claude T3 not yet run — add patterns here when available.
    ],
    # T2 omitted: not run for sweep (Opus judge cost).
}


def combine(out_path_str: str, patterns: list[str]) -> None:
    out_path = Path(out_path_str)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {out_path_str} ===")

    log_paths: list[str] = []
    for pat in patterns:
        for p in sorted(glob.glob(pat)):
            log_paths.append(p)

    if not log_paths:
        print(f"  no logs matched {patterns}; skipping")
        return

    logs: list[EvalLog] = []
    for p in log_paths:
        log = read_eval_log(p)
        n = len(log.samples or [])
        print(f"  read {p}  ({n} samples, status={log.status})")
        logs.append(log)

    # Dedup by sample id, later sources win
    seen: dict[str, object] = {}
    for log in logs:
        for s in log.samples or []:
            seen[s.id] = s
    merged = list(seen.values())

    # Use the paper log's header as canonical (it has the full role roster
    # declared). Sweep logs only declare 1-2 roles, which would lose context.
    canonical = logs[0].model_copy(deep=True)
    canonical.samples = merged
    canonical.status = "success"
    canonical.location = str(out_path)
    if canonical.eval and canonical.eval.dataset:
        canonical.eval.dataset.samples = len(merged)

    write_eval_log(canonical, location=str(out_path))
    print(f"  wrote {out_path}  ({len(merged)} samples merged)")


def main() -> None:
    for out_path, patterns in TASK_SPLITS.items():
        combine(out_path, patterns)


if __name__ == "__main__":
    main()
