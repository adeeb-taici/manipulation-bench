# Cross-task scripts — a map

20 Python files in this directory. They group into five categories.

## Loader (the trajectory dataframe)

| File | Purpose |
|---|---|
| `load.py` | `load_corpus()` returns a per-rollout dataframe across all 5 tasks. Reads `paper/cross_task/data/results.csv` by default (~0.13s for the full ~12.5k-row corpus); falls back to walking `paper/task<N>/eval_log.eval` if the CSV is missing. Used by 13 of the other scripts. |

## Tooling (regenerate the CSV / merge raw logs)

| File | Purpose |
|---|---|
| `eval_logs_to_csv.py` | Walks each task's eval log and produces `paper/cross_task/data/results.csv` (one row per rollout, ~85 columns: identity + axes + flattened scorer scores). Run this when eval logs change. |
| `combine_eval_logs.py` | Merges per-task split logs (e.g., `logs/task1_fullsweep_*`, `logs/task1_gpt55`, `logs/task1_dsv4`) into the canonical `paper/task<N>/eval_log.eval` via dedup-by-sample-id (later splits win). |

## v2 statistical pipeline (paper-amendment reanalysis)

Reads `load_corpus()`. Outputs go to `paper/task<N>/analysis/regression_v2.json` and `paper/cross_task/analysis/*_v2.*`. See [../../findings/reanalysis_notes.md](../../findings/reanalysis_notes.md) for the methods diff and headline-finding survival check.

| File | Produces |
|---|---|
| `regression.py` | Per-(task, model, axis) regression + Dunnett contrasts + per-task η². → `paper/task<N>/analysis/regression_v2.json` |
| `ranking_stability_v2.py` | Cross-task pairwise Spearman ρ with bootstrap CI (B=2000, stratified by cell). → `paper/cross_task/analysis/ranking_stability_v2*.json` |
| `variance_decomposition.py` | Pooled OLS with within-task z-scoring; bootstrap CI on η²(model:task) − η²(model). → `paper/cross_task/analysis/variance_decomp_v2.json` |
| `v2_figures.py` | Redraws fig 2/3/4/7 + table 3 from the v2 outputs. → `paper/cross_task/figures/fig*_v2.pdf`, `paper/cross_task/analysis/table3_v2.md` |
| `_v2_smoke.py` | Smoke test: loader sanity, one regression cell, 50-rep ranking-stability bootstrap. |

## v1 cross-task analyses

The original paper analyses. Most read `load_corpus()`; one walks split logs (see exception).

| File | Produces |
|---|---|
| `bootstrap_cis.py` | Per-(task, model, axis) standardized-slope bootstrap CIs. → `paper/task<N>/analysis/bootstrap_cis.json` |
| `cohens_d.py` | Per-(task, model, frame, incentive, difficulty) cell-level Cohen's d vs prohibitive baseline. → `paper/task<N>/analysis/cohens_d.json` |
| `response_surface.py` | Per-task response-surface figure (3 difficulty rows × 6 model cols × 5×3 frame×incentive heatmap). → `paper/task<N>/figures/fig7_response_surface.pdf` |
| `analyze_response_surface.py` | Standalone CLI for response-surface pipeline (sensitivity slopes + 15-dim profile vectors + cross-task correlations). |
| `aggregate.py` | Per-task aggregate slope tables. Reads `cross_task_profiles.json`. → `paper/cross_task/analysis/cross_task_aggregate.md` |
| `clustering.py` | Hierarchical clustering on per-model 15-dim profile vectors. → `paper/cross_task/analysis/clusters.json` |
| `ranking_stability_v1.py` | Original (point-estimate, no bootstrap) cross-task ρ with v1's mixed-metric definition (T2 by manipulation_occurred, others by primary metric). → `paper/cross_task/analysis/ranking_stability.json` |
| `explore.py` | Exploratory cross-task figures beyond the per-task results.md set. → `paper/cross_task/figures/fig_*.pdf` |
| `surprise_residuals.py` | Additive-model residual analysis to flag cells deviating from frame + incentive + difficulty additivity. → `paper/cross_task/analysis/residuals.json` |
| `sample_distributions.py` | Per-(task, model) violin plots of metric distributions at frame=permissive. → `paper/task<N>/figures/fig10_sample_distributions.pdf` |

### v1 exception (walks raw logs)

| File | Purpose |
|---|---|
| `frontier_lift.py` | GPT-5 → GPT-5.5 / V3.2 → V4-Pro within-scenario contrasts. Reads pre-amendment split logs (`logs/task1_fullsweep_*`, `logs/task1_gpt55`, etc.) directly because the canonical `eval_log.eval` files are post-dedup with the upgraded models winning — pre-amendment GPT-5 / V3.2 samples don't appear in `results.csv`. → `paper/cross_task/analysis/frontier_lift.json` |

## Library (no `__main__`)

| File | Purpose |
|---|---|
| `_bootstrap_slopes.py` | Bootstrap helpers (`bootstrap_slope_cis`, `bootstrap_aggregate_cis`). Used by `bootstrap_cis.py`. The leading underscore signals "not a runner — don't `python` this directly." |

## Quick reference: where outputs go

| Output type | Location |
|---|---|
| Per-task analysis JSONs (v1 + v2 coexist) | `paper/task<N>/analysis/` |
| Per-task figures (v1 + v2 coexist by filename) | `paper/task<N>/figures/` |
| Cross-task analysis (JSONs + .md) | `paper/cross_task/analysis/` |
| Cross-task figures | `paper/cross_task/figures/` |
| Trajectory dataframe (the aggregate) | `paper/cross_task/data/results.csv` |

## Adding a new cross-task script

1. Use `load_corpus()` for the data — don't reinvent the eval-log walk.
2. Write outputs to `paper/cross_task/analysis/` (JSONs/MDs) or `paper/cross_task/figures/` (PDFs).
3. Keep imports flat (sibling modules: `from load import load_corpus`).
4. Add a one-line description to this README.
