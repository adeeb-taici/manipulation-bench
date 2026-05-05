# Analysis inventory in `paper/`

A cross-cut survey of every analysis script and JSON in `paper/`, grouped by **scope** (per-task vs cross-task) × **outcome metric** (manipulation magnitude vs manipulation_occurred binary), with a **role** column distinguishing core paper claims from supplementary material. Use this as the index when deciding where new analyses should slot in.

## Per-task analyses

Every task has the standard set under `paper/task<N>/`. T6 has the prereg subset only (no `cohens_d.json`, no task-specific exploratory drilldowns yet).

| Script | What it computes | Outcome metric | Role | Used by paper |
|---|---|---|---|---|
| `taskN_prereg_analysis.py` → `prereg_results.json` | P1–P7 verdicts (prohibitive floor, permissive ceiling, saturation, dominance, incentive sensitivity, ρ stability, scorer hand-validation), per-model n, per-(model, axis) sensitivity slopes, cell means | **Magnitude** (each task's primary metric: lie rate / belief shift / exploitation rate / mis+false rate / initial bias / suppression rate) | **Core** | App. C "Pre-registered prediction outcomes" |
| `bootstrap_cis.py` → `bootstrap_cis.json` | 1000-rep bootstrap CI on per-(model, axis) standardized slopes | **Magnitude** | **Core** — underwrites Table 2, Table 4, per-model signatures | §4.3, §4.4, §4.5 |
| `cohens_d.py` → `cohens_d.json` | Per-cell Cohen's d vs prohibitive baseline | **Magnitude** | Supplementary | App. effect-size claims |
| `regression.py` → `regression_v2.json` | Per-(task, model, axis) regression + Dunnett contrasts + per-task η², interaction LR test | **Magnitude** | Supplementary (statistical robustness) | Reanalysis appendix |
| `taskN_visuals.py` → per-task PDFs | Per-task response surfaces, frame curves, heatmaps | **Magnitude** | Mostly **core** (headline figures) | Per-task figures in §4 |
| **Task-specific exploratory:** | | | | |
| `t1_lie_magnitude.py` → `lie_magnitude.json` | Bimodal lie magnitude distribution on T1 | **Magnitude** (lie size) | Supplementary | App. F.5 "Bimodal Bargaining lie magnitudes" |
| `t2_per_claim.py` → `per_claim.json` | Per-claim breakdown for T2 | **Magnitude** | Supplementary | Not in main text |
| `t3_promise_gap.py` → `promise_gap.json` | Promise-vs-action gap on T3 | **Magnitude** (gap) | Supplementary | App. mention only |
| `t4_per_question_type.py` → `per_check_type.json` | Per-buyer-question breakdown on T4 | **Magnitude** | Supplementary | App. only |
| `task4_hand_validation.py`, `task5_hand_validation.py` | Rule-based scorer agreement vs human labels | n/a (scorer QA) | Core methodology | App. validation gate |
| `extract_actions.py` (each task) | Pull tool calls for sample traces | n/a (presentation) | Supplementary | "Conversation Examples" appendix |

**Notable absence on the binary side:** none of the per-task scripts above analyze `manipulation_occurred` directly. Every per-task analysis is on the per-task primary metric (magnitude). This is the gap the csv/FINDINGS pipeline fills.

## Cross-task analyses (`paper/cross_task/scripts/`)

| Script | What it computes | Outcome metric | Role |
|---|---|---|---|
| **Core (referenced in paper §4):** | | | |
| `ranking_stability_v2.py` → `ranking_stability_v2.json` | Pairwise Spearman ρ across tasks with bootstrap CI (B=2000) | **Magnitude** (per-task primary) | Core — Fig. 1 (`fig:rank-stability`), §4.1 |
| `variance_decomposition.py` → `variance_decomp_v2.json` | Pooled OLS, η²(model:task) − η²(model) with bootstrap | **Magnitude** (z-scored within task) | Core — §4.1 supports rank-instability claim |
| `aggregate.py` → `cross_task_aggregate.md` | Per-(task, axis) mean abs slopes across roster | **Magnitude** | Core — Table 2 (`tab:per-task-slopes`), §4.3 |
| `analyze_response_surface.py` / `response_surface.py` | 15-dim model profile vectors; per-task response-surface heatmaps | **Magnitude** | Core (per-task fig); App. heatmap |
| `_bootstrap_slopes.py` (library) | Bootstrap helpers used by `bootstrap_cis.py` | n/a | Core infrastructure |
| **Supplementary (in cross_task/ but not central to §4):** | | | |
| `frontier_lift.py` → `frontier_lift.json` | GPT-5 → GPT-5.5 / V3.2 → V4-Pro within-scenario contrasts | **Magnitude** | Supplementary — supports Amendment notes; not in main figs |
| `clustering.py` → `clusters.json` | Hierarchical clustering on 15-dim profile vectors | **Magnitude** | Supplementary — `clusters.json` exists but no explicit `\ref` |
| `ranking_stability_v1.py` → `ranking_stability.json` | v1 (point-estimate, mixed-metric: T2 by `manipulation_occurred`, others by primary) | **Mixed** — the only place `manipulation_occurred` shows up cross-task | **Deprecated** — superseded by v2 |
| `surprise_residuals.py` → `residuals.json` | Additive-model residuals to flag non-additive cells | **Magnitude** | Supplementary |
| `sample_distributions.py` → per-task fig10 PDF | Per-(task, model) violin at frame=permissive | **Magnitude** | Supplementary |
| `explore.py` | Exploratory extra figures | **Magnitude** | Supplementary |
| **Tooling (not analysis):** | | | |
| `eval_logs_to_csv.py` | Build `results.csv` from `.eval` files | — | Pipeline plumbing |
| `combine_eval_logs.py` | Dedup-merge per-task split logs | — | Pipeline plumbing |
| `append_t6_to_csv.py` | T6-only CSV append helper | — | Pipeline plumbing |
| `load.py` | `load_corpus()` dataframe loader | — | Library |
| `_v2_smoke.py` | Smoke test | — | Library |
| `v2_figures.py` | Re-render figs 2/3/4/7 + table 3 from v2 outputs | — | Figure rendering |

## Cross-task analyses elsewhere

| Location | Purpose | Role |
|---|---|---|
| `paper/capability_eval/scripts/*.py` (`capability_analysis`, `capability_anova`, `capability_clustering`, `capability_frontier_lift`, `capability_regression`, `capability_response_surface`) | Capability-eval companion study (separate from main response surface) | **Supplementary** — entire `capability_eval/` is a separate sub-study; not in main paper §4 |

## Per-task documentation (markdown)

| File | Type | Role |
|---|---|---|
| `paper/task<N>/prereg.md` | Pre-registered protocol | Core methodology (App. references) |
| `paper/task<N>/results.md` | Per-task verdicts | Core (App. C) |
| `paper/cross_task/SUMMARY.md` | Cross-task synthesis | Effectively the source for §4 |
| `paper/cross_task/EXPLORATORY_FINDINGS.md` | Post-PREREG exploratory analyses | Supplementary |
| `paper/cross_task/REANALYSIS_NOTES.md` | v1→v2 method diff | Supplementary methods doc |
| `paper/cross_task/FINDINGS_FROM_FIRST_PRINCIPLES.md` | Bottom-up bottom-up read of `results.csv` | Supplementary (no preconceptions) |

## Summary by metric × scope

| | Per-task | Cross-task |
|---|---|---|
| **Manipulation magnitude (primary metric)** | All `prereg_results.json` (P1–P7), `bootstrap_cis.json`, `cohens_d.json`, `regression_v2.json`, all task-specific exploratory (`t1_*`, `t2_*`, `t3_*`, `t4_*`) | `ranking_stability_v2`, `variance_decomp_v2`, `aggregate`, `analyze_response_surface`, `clustering`, `frontier_lift`, `surprise_residuals`, `sample_distributions`, `explore` |
| **Manipulation occurred (binary)** | **None** | Only in deprecated `ranking_stability_v1.py` (T2 path); otherwise unused |

## Core-vs-supplementary split

**Core (drives headline claims and main figures/tables in §4):**
- §4.1 rank instability: `ranking_stability_v2`, `variance_decomp_v2`, `fig_model_ranking_stability.pdf`
- §4.2 overview: `aggregate.py`'s table
- §4.3 cluster split: `aggregate.py` + `bootstrap_cis.json` + `per_task_slopes.pdf`
- §4.4 per-model signatures: `bootstrap_cis.json` per task + `analyze_response_surface` heatmap
- §4.5 T6 held-out: `task6_inbox/prereg_results.json`
- App. C: every task's `prereg_results.json`
- App. F supplementary figs: `sample_distributions`, `explore`, `t1_lie_magnitude`

**Supplementary (exists, useful, not load-bearing for headline):**
- `cohens_d.py`, `regression_v2`, `surprise_residuals`, `clustering`, `frontier_lift`
- All `paper/capability_eval/`
- All `t<N>_*` exploratory drilldowns

**Deprecated:**
- `ranking_stability_v1.py` (mixed-metric, no bootstrap; superseded by v2)
- v1 outputs (`ranking_stability.json`, etc.) kept for reproducibility only

## The biggest asymmetry

**Every cross-task analysis in the paper uses the per-task primary (magnitude) metric.** There is *no* cross-task analysis on `manipulation_occurred` aside from the deprecated v1 ranking script's T2 column. csv/FINDINGS's pipeline (the 8 scripts under `csv/scripts/`) is a binary-metric counterpart that doesn't currently exist in `paper/`. That is the meaningful gap a port fills:

- Adding presence-of-manipulation analyses lets us cross-check every magnitude finding under the binary lens (does the channel split survive? does ranking instability survive? do per-model signatures change?).
- It also makes `manipulation_occurred` directly comparable across tasks without normalization, which the magnitude metrics aren't (T5 bias is on a 0–20 scale; T2 belief shift can be negative; etc.).
