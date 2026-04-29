"""One-shot orchestrator: refresh all T4 outputs after the reasoning retry lands.

Run after `logs/task4_reasoning_retry/*.eval` is complete AND
`paper/task4_sales/eval_log.eval` has been re-combined.

Steps (combine is intentionally OUT — run it separately first; it's the
heaviest step and shouldn't run inside the orchestrator's subprocess.run
because Inspect's read_eval_log holds memory across the whole batch):

  1-3. T4-specific analyses + figures (fast).
  4-13. Cross-task scripts that touch T4 (sequential to avoid I/O thrash).

Each step is idempotent. Re-running just re-overwrites the relevant outputs.
"""

from __future__ import annotations

import subprocess
import sys

STEPS = [
    # T4-specific analyses + figures
    ["python", "experiments/task4_prereg_analysis.py"],
    ["python", "experiments/task4_visuals.py"],
    ["python", "experiments/t4_per_question_type.py"],
    # Cross-task analyses that include T4 (and need to be regenerated for consistency)
    ["python", "experiments/run_response_surface.py"],
    ["python", "experiments/run_bootstrap_cis.py"],
    ["python", "experiments/run_cohens_d.py"],
    ["python", "experiments/sample_distributions.py"],
    ["python", "experiments/surprise_residuals.py"],
    ["python", "experiments/cross_task_ranking_stability.py"],
    ["python", "experiments/cross_task_clustering.py"],
    ["python", "experiments/cross_task_analysis.py"],
    ["python", "experiments/cross_task_explore.py"],
    ["python", "experiments/frontier_lift.py"],
]


def main() -> int:
    for cmd in STEPS:
        print(f"\n=== {' '.join(cmd)} ===\n", flush=True)
        rc = subprocess.run(cmd).returncode
        if rc != 0:
            print(f"\nstep failed with rc={rc}; halting", file=sys.stderr)
            return rc
    print("\nAll T4 refresh steps complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
