#!/usr/bin/env bash
# Re-run all analysis scripts that produce paper artifacts.
#
# Usage:
#   paper/run_all.sh                    # run everything (default)
#   paper/run_all.sh --csv              # just regenerate results.csv from eval logs
#   paper/run_all.sh --prereg           # per-task PREREG analyses + visuals
#   paper/run_all.sh --v1               # v1 cross-task analyses
#   paper/run_all.sh --v2               # v2 statistical reanalysis pipeline
#   paper/run_all.sh --exploratory      # post-PREREG exploratory pivots
#   paper/run_all.sh --corpus           # 26k-row corpus analyses (csv/ legacy)
#   paper/run_all.sh --capability       # capability axis (LMArena ELO/tier/generation)
#   paper/run_all.sh --newer            # newer statistical analyses (mixed-effects, bootstrap, refusal scan)
#
# Run from the repo root: `paper/run_all.sh`.
# Each step prints its name; failures stop the script (set -e).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-python3}"

run() {
    echo
    echo "=== $1 ==="
    "$PYTHON" "$1"
}

run_csv() {
    run paper/cross_task/scripts/cross_task/eval_logs_to_csv.py
}

run_prereg() {
    for t in 1_bargaining 2_debate 3_village 4_sales 5_committee; do
        run "paper/task${t}/scripts/task${t%%_*}_prereg_analysis.py"
        run "paper/task${t}/scripts/task${t%%_*}_visuals.py"
    done
}

run_v1() {
    run paper/cross_task/scripts/cross_task/bootstrap_cis.py
    run paper/cross_task/scripts/cross_task/cohens_d.py
    run paper/cross_task/scripts/cross_task/response_surface.py
    run paper/cross_task/scripts/cross_task/aggregate.py
    run paper/cross_task/scripts/cross_task/clustering.py
    run paper/cross_task/scripts/cross_task/ranking_stability_v1.py
    run paper/cross_task/scripts/cross_task/explore.py
    run paper/cross_task/scripts/cross_task/surprise_residuals.py
    run paper/cross_task/scripts/cross_task/sample_distributions.py
    run paper/cross_task/scripts/cross_task/frontier_lift.py
}

run_v2() {
    run paper/cross_task/scripts/cross_task/regression.py
    run paper/cross_task/scripts/cross_task/ranking_stability_v2.py
    run paper/cross_task/scripts/cross_task/variance_decomposition.py
    run paper/cross_task/scripts/cross_task/v2_figures.py
}

run_exploratory() {
    run paper/task1_bargaining/scripts/t1_lie_magnitude.py
    run paper/task2_debate/scripts/t2_per_claim.py
    run paper/task3_village/scripts/t3_promise_gap.py
    run paper/task4_sales/scripts/t4_per_question_type.py
}

run_corpus() {
    # The 26k-row corpus pipeline. _loader.py reads paper/cross_task/data/corpus.csv.
    # Numbered scripts use sibling-import from _loader, so they're run as `python <path>`
    # from repo root with PYTHONPATH including the corpus dir.
    local corpus_dir="paper/cross_task/scripts/corpus"
    PYTHONPATH="$corpus_dir:${PYTHONPATH:-}" run "$corpus_dir/01_overview.py"
    PYTHONPATH="$corpus_dir:${PYTHONPATH:-}" run "$corpus_dir/02_model_ranking.py"
    PYTHONPATH="$corpus_dir:${PYTHONPATH:-}" run "$corpus_dir/03_axis_effects.py"
    PYTHONPATH="$corpus_dir:${PYTHONPATH:-}" run "$corpus_dir/04_interactions.py"
    PYTHONPATH="$corpus_dir:${PYTHONPATH:-}" run "$corpus_dir/05_variance_decomposition.py"
    PYTHONPATH="$corpus_dir:${PYTHONPATH:-}" run "$corpus_dir/06_cluster_bootstrap_ci.py"
    PYTHONPATH="$corpus_dir:${PYTHONPATH:-}" run "$corpus_dir/07_within_task_correlations.py"
    PYTHONPATH="$corpus_dir:${PYTHONPATH:-}" run "$corpus_dir/08_paired_head_to_head.py"
    PYTHONPATH="$corpus_dir:${PYTHONPATH:-}" run "$corpus_dir/09_capability_analysis.py"
    PYTHONPATH="$corpus_dir:${PYTHONPATH:-}" run "$corpus_dir/10_haiku_collapse.py"
}

run_capability() {
    # Capability axis. capability_*.py imports _capability_io via sibling-import.
    local cap_dir="paper/cross_task/scripts/capability"
    PYTHONPATH="$cap_dir:${PYTHONPATH:-}" run "$cap_dir/capability_analysis.py"
    PYTHONPATH="$cap_dir:${PYTHONPATH:-}" run "$cap_dir/capability_anova.py"
    PYTHONPATH="$cap_dir:${PYTHONPATH:-}" run "$cap_dir/capability_clustering.py"
    PYTHONPATH="$cap_dir:${PYTHONPATH:-}" run "$cap_dir/capability_frontier_lift.py"
    PYTHONPATH="$cap_dir:${PYTHONPATH:-}" run "$cap_dir/capability_regression.py"
    PYTHONPATH="$cap_dir:${PYTHONPATH:-}" run "$cap_dir/capability_response_surface.py"
}

run_newer() {
    # Newer statistical analyses. Self-contained — no sibling imports.
    # 04_incentive_traces and 05_refusal_scan walk eval logs (slow; minutes each).
    # 05_spearman_bootstrap is a B=2000 bootstrap (multi-minute).
    run paper/cross_task/scripts/newer/01_mixed_effects.py
    run paper/cross_task/scripts/newer/02_task_model_interaction.py
    run paper/cross_task/scripts/newer/03_multiple_testing.py
    run paper/cross_task/scripts/newer/04_incentive_traces.py
    run paper/cross_task/scripts/newer/05_refusal_scan.py
    run paper/cross_task/scripts/newer/05_spearman_bootstrap.py
    run paper/cross_task/scripts/newer/incentive_forest.py
}

# Dispatch
case "${1:-all}" in
    --csv)          run_csv ;;
    --prereg)       run_prereg ;;
    --v1)           run_v1 ;;
    --v2)           run_v2 ;;
    --exploratory)  run_exploratory ;;
    --corpus)       run_corpus ;;
    --capability)   run_capability ;;
    --newer)        run_newer ;;
    all|--all|"")
        run_csv
        run_prereg
        run_v1
        run_v2
        run_exploratory
        run_corpus
        run_capability
        run_newer
        ;;
    -h|--help)
        sed -n '2,15p' "$0"
        ;;
    *)
        echo "Unknown argument: $1" >&2
        echo "Run with -h for usage." >&2
        exit 1
        ;;
esac

echo
echo "=== done ==="
