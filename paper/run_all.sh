#!/usr/bin/env bash
# Re-run all analysis scripts that produce paper artifacts.
#
# Usage:
#   paper/run_all.sh                    # run everything (default)
#   paper/run_all.sh --csv              # just regenerate results.csv
#   paper/run_all.sh --prereg           # per-task PREREG analyses + visuals
#   paper/run_all.sh --v1               # v1 cross-task analyses
#   paper/run_all.sh --v2               # v2 statistical reanalysis pipeline
#   paper/run_all.sh --exploratory      # post-PREREG exploratory pivots
#
# Run from the repo root: `paper/run_all.sh`.
# Each step prints its name; failures stop the script (set -e).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

run() {
    echo
    echo "=== $1 ==="
    python "$1"
}

run_csv() {
    run paper/cross_task/scripts/eval_logs_to_csv.py
}

run_prereg() {
    for t in 1_bargaining 2_debate 3_village 4_sales 5_committee; do
        run "paper/task${t}/scripts/task${t%%_*}_prereg_analysis.py"
        run "paper/task${t}/scripts/task${t%%_*}_visuals.py"
    done
}

run_v1() {
    run paper/cross_task/scripts/bootstrap_cis.py
    run paper/cross_task/scripts/cohens_d.py
    run paper/cross_task/scripts/response_surface.py
    run paper/cross_task/scripts/aggregate.py
    run paper/cross_task/scripts/clustering.py
    run paper/cross_task/scripts/ranking_stability_v1.py
    run paper/cross_task/scripts/explore.py
    run paper/cross_task/scripts/surprise_residuals.py
    run paper/cross_task/scripts/sample_distributions.py
    run paper/cross_task/scripts/frontier_lift.py
}

run_v2() {
    run paper/cross_task/scripts/regression.py
    run paper/cross_task/scripts/ranking_stability_v2.py
    run paper/cross_task/scripts/variance_decomposition.py
    run paper/cross_task/scripts/v2_figures.py
}

run_exploratory() {
    run paper/task1_bargaining/scripts/t1_lie_magnitude.py
    run paper/task2_debate/scripts/t2_per_claim.py
    run paper/task3_village/scripts/t3_promise_gap.py
    run paper/task4_sales/scripts/t4_per_question_type.py
}

# Dispatch
case "${1:-all}" in
    --csv)          run_csv ;;
    --prereg)       run_prereg ;;
    --v1)           run_v1 ;;
    --v2)           run_v2 ;;
    --exploratory)  run_exploratory ;;
    all|--all|"")
        run_csv
        run_prereg
        run_v1
        run_v2
        run_exploratory
        ;;
    -h|--help)
        sed -n '2,12p' "$0"
        ;;
    *)
        echo "Unknown argument: $1" >&2
        echo "Run with -h for usage." >&2
        exit 1
        ;;
esac

echo
echo "=== done ==="
