"""Combine split-by-pipeline-event eval logs into a single canonical .eval per task.

Tasks 1 and 2 ran in multiple batches because of provider stalls (see each task's
pipeline_log.md). Analysis scripts already glob across the split locations, but
having a single canonical .eval per task makes provenance reporting and
``inspect view`` cleaner — it's "as if they weren't run separately".

What this script produces:
    paper/task1_bargaining/eval_log.eval     — all 5,400 Task 1 samples
    paper/task2_debate/eval_log.eval         — all 4,140 Task 2 samples
    paper/task3_village/eval_log.eval        — all Task 3 samples (orig + post-Amend-A1)

Originals are NOT deleted; they remain in their split folders for reproducibility.

Merge strategy:
    1. Read each split log fully (samples included)
    2. Deduplicate samples by id, with later-running splits winning (matches the
       analyzer's existing behavior — e.g., Llama retry overwrites the original
       failure for the same scenario id)
    3. Concatenate into the latest-split's EvalLog header (most accurate model
       roles + completion-time stats)
    4. Set status = "success" if all dispatched samples are scored
    5. Recompute stats.completed_samples + token totals from the merged sample list

Usage:
    python paper/cross_task/scripts/combine_eval_logs.py
"""

from __future__ import annotations

import glob
from pathlib import Path

from inspect_ai.log import EvalLog, read_eval_log, write_eval_log

TASK_SPLITS = {
    "paper/task1_bargaining/eval_log.eval": [
        "logs/task1_fullsweep_20260422/*.eval",
        "logs/task1_fullsweep_20260422_batch1/*.eval",
        "logs/task1_fullsweep_20260422_llama_retry/*.eval",
        "logs/task1_fullsweep_20260422_grok/*.eval",
        # GPT-5.5 swap (PREREG Amendment A2). Same scenario IDs as the original
        # GPT-5 batch — dedup by sample id keeps the GPT-5.5 samples (later wins),
        # so the OpenAI row reflects GPT-5.5 in the combined log.
        "logs/task1_gpt55/*.eval",
        # DeepSeek V3.2 -> V4 Pro swap (PREREG Amendment A3, official API).
        "logs/task1_dsv4/*.eval",
    ],
    "paper/task2_debate/eval_log.eval": [
        "logs/task2_debate_v61_full/*.eval",
        "logs/task2_debate_v61_full_gemini/*.eval",
        "logs/task2_debate_v61_full_gpt5/*.eval",
        "logs/task2_debate_v61_full_grok/*.eval",
        "logs/task2_debate_v61_full_llama/*.eval",
        "logs/task2_debate_v61_full_deepseek/*.eval",
        "logs/task2_gpt55/*.eval",
        "logs/task2_dsv4/*.eval",
    ],
    "paper/task3_village/eval_log.eval": [
        "logs/task3_village_v61_full/*.eval",
        "logs/task3_village_v61_full_remaining/*.eval",
        "logs/task3_village_v61_full_remaining_v2/*.eval",
        "logs/task3_gpt55/*.eval",
        "logs/task3_dsv4/*.eval",
    ],
    "paper/task4_sales/eval_log.eval": [
        "logs/task4_sales_v61_full/*.eval",
        "logs/task4_gpt55/*.eval",
        "logs/task4_dsv4/*.eval",
        # Amendment A3 (2026-04-29): re-run reasoning-on models
        # (Gemini, Grok, DeepSeek V4 Pro) at max_tokens=16384 to fix
        # truncation. Listed last so dedup-by-sample-id picks the
        # un-truncated samples over the original 4096-budget ones.
        "logs/task4_reasoning_retry/*.eval",
    ],
    "paper/task5_committee/eval_log.eval": [
        "logs/committee_fullsweep_20260422/*.eval",
        "logs/task5_gpt55/*.eval",
        "logs/task5_dsv4/*.eval",
    ],
    "paper/task6_inbox/eval_log.eval": [
        # T6 ran as a single batch with all six paper-roster models.
        "logs/task6_inbox_fullsweep/*.eval",
    ],
}


def combine(out_path_str: str, patterns: list[str]) -> None:
    """Merge .eval files matched by ``patterns`` into a single canonical .eval.

    ``patterns`` is given in chronological order — the LATEST source's header
    (eval/plan/stats fields) wins, but its samples are merged with all earlier
    sources' samples (deduplicating by sample id with later wins).
    """
    out_path = Path(out_path_str)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {out_path_str} ===")

    # Collect all log paths (in pattern order)
    log_paths: list[str] = []
    for pat in patterns:
        for p in sorted(glob.glob(pat)):
            log_paths.append(p)

    if not log_paths:
        print(f"  no logs matched {patterns}; skipping")
        return

    # Read all logs (full samples)
    logs: list[EvalLog] = []
    for p in log_paths:
        log = read_eval_log(p)
        n_samples = len(log.samples or [])
        print(f"  read {p}  ({n_samples} samples, status={log.status})")
        logs.append(log)

    # Deduplicate samples by id, later sources win
    seen: dict[str, object] = {}
    for log in logs:
        for s in log.samples or []:
            seen[s.id] = s
    merged_samples = list(seen.values())

    # Use the FIRST log's header (its dataset.samples declares the full sweep
    # target — e.g., Task 1 = 5,400 — whereas later splits only declare their
    # subset). Override its samples list with the merged superset.
    canonical = logs[0].model_copy(deep=True)
    canonical.samples = merged_samples
    canonical.status = "success"
    canonical.location = str(out_path)

    # NOTE: per-split stats and results are kept from the first log (writer
    # requires non-None EvalStats). They reflect only one batch and may be
    # misleading. Analysis scripts always recompute from samples — they don't
    # consult log.results — so this is fine in practice.

    # Update header sample count to reflect the merged total (some splits had
    # subset dataset.samples; we want the header to match what's in the file).
    if canonical.eval and canonical.eval.dataset:
        canonical.eval.dataset.samples = len(merged_samples)

    write_eval_log(canonical, location=str(out_path))
    print(f"  wrote {out_path}  ({len(merged_samples)} samples merged)")


def main() -> None:
    for out_path, patterns in TASK_SPLITS.items():
        combine(out_path, patterns)


if __name__ == "__main__":
    main()
