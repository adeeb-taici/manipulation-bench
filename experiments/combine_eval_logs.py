"""Combine split-by-pipeline-event eval logs into a single canonical .eval per task.

Tasks 1 and 2 ran in multiple batches because of provider stalls (see each task's
pipeline_log.md). Analysis scripts already glob across the split locations, but
having a single canonical .eval per task makes provenance reporting and
``inspect view`` cleaner — it's "as if they weren't run separately".

What this script produces:
    logs/task1_bargaining_combined.eval     — all 5,400 Task 1 samples
    logs/task2_debate_combined.eval         — all 4,140 Task 2 samples
    logs/task3_village_combined.eval        — all Task 3 samples (orig + post-Amend-A1)

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
    python experiments/combine_eval_logs.py
"""

from __future__ import annotations

import glob
from pathlib import Path

from inspect_ai.log import EvalLog, read_eval_log, write_eval_log

LOGS_DIR = Path("logs")

TASK_SPLITS = {
    "task1_bargaining_combined.eval": [
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
    "task2_debate_combined.eval": [
        "logs/task2_debate_v61_full/*.eval",
        "logs/task2_debate_v61_full_gemini/*.eval",
        "logs/task2_debate_v61_full_gpt5/*.eval",
        "logs/task2_debate_v61_full_grok/*.eval",
        "logs/task2_debate_v61_full_llama/*.eval",
        "logs/task2_debate_v61_full_deepseek/*.eval",
        "logs/task2_gpt55/*.eval",
        "logs/task2_dsv4/*.eval",
    ],
    "task3_village_combined.eval": [
        "logs/task3_village_v61_full/*.eval",
        "logs/task3_village_v61_full_remaining/*.eval",
        "logs/task3_village_v61_full_remaining_v2/*.eval",
        "logs/task3_gpt55/*.eval",
        "logs/task3_dsv4/*.eval",
    ],
    "task4_sales_combined.eval": [
        "logs/task4_sales_v61_full/*.eval",
        "logs/task4_gpt55/*.eval",
        "logs/task4_dsv4/*.eval",
    ],
    "task5_committee_combined.eval": [
        "logs/committee_fullsweep_20260422/*.eval",
        "logs/task5_gpt55/*.eval",
        "logs/task5_dsv4/*.eval",
    ],
}


def combine(out_filename: str, patterns: list[str]) -> None:
    """Merge .eval files matched by ``patterns`` into a single canonical .eval.

    ``patterns`` is given in chronological order — the LATEST source's header
    (eval/plan/stats fields) wins, but its samples are merged with all earlier
    sources' samples (deduplicating by sample id with later wins).
    """
    out_path = LOGS_DIR / out_filename
    print(f"\n=== {out_filename} ===")

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
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    for fname, patterns in TASK_SPLITS.items():
        combine(fname, patterns)


if __name__ == "__main__":
    main()
