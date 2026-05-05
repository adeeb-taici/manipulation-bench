# Methods

Every statistical procedure run across the corpus, terse.

## Data sources

| Name | Rows | Source file |
|---|---|---|
| Response-surface CSV | 26,637 (all) / 13,573 (canonical-6) | `paper/cross_task/data/results.csv` |
| Capability-axis CSV | ~29k (with inbox) | `paper/cross_task/data/results.csv` joined with `model_capability.csv` |
| Bargaining eval log | 5,400 samples | `paper/task1_bargaining/eval_log.eval` |

**Canonical-6 roster:** Claude Opus 4.7, GPT-5.5, Gemini 3.1 Pro, Grok 4, Llama 3.3 70B, DeepSeek V4 Pro.

**Axes (canonical levels):**
- Frame: prohibitive, pro_social, minimal, selfish, permissive
- Incentive: none, moderate, high
- Difficulty: low, medium, high

**Primary outcome:** `manipulation_occurred` (binary). **Secondary:** `manipulation_metric` (task-specific, not pooled across tasks).

## 1. Variance / effect-size decomposition

**Per-axis spread.** Within each task, max(rate) − min(rate) of `manipulation_occurred` across each axis's levels.

**η² (eta-squared) decomposition.** Variance fraction by model, scenario, frame, incentive, difficulty. Per task.

**Two-way ANOVA, Type II SS.** `manipulation_metric ~ tier × frame` and `~ tier × incentive`. Per-task and pooled.

## 2. Regression

**Per-task OLS.** `manipulation_rate ~ ELO_per100 + C(frame) + C(incentive) + C(difficulty)`. HC3 SEs. ELO centered at 1400. n per task: bargaining 13,499; debate 6,170; village 969; sales 3,375; committee 2,624; inbox 2,715.

**Pooled OLS with ELO × task interaction.** Tests task-conditional ELO effect.

**Mixed-effects (LPM, ML).** `manipulation_occurred ~ C(model) + C(task) + C(frame) + C(incentive) + C(difficulty)` with random intercept on cluster (5,980 levels; falls back scenario_id → per-row synthetic). n=13,573, canonical-6. Powell optimizer (lbfgs hit singular RE covariance; FE coefficients stable across optimizers).

**Reference cell:** Claude Opus 4.7 × bargaining × prohibitive × incentive=none × difficulty=low.

## 3. Bootstrap and uncertainty

**Cluster bootstrap, 1000 resamples** over `scenario_group` for committee, debate, sales (where cluster_id populated).

**Row bootstrap, 1000 resamples** for bargaining and village (no scenario identifier).

**ICC** of `manipulation_occurred` across `scenario_group`. Reported per task.

**CI-narrowness ratio.** Width(row-boot CI) / Width(cluster-boot CI), per (model, task) cell.

**Forest-plot bootstrap.** Per (task, model) cell: Δ = P(manip | inc=high) − P(manip | inc=none), pooled over frame × difficulty. 95% CI from 2,000-rep nonparametric resample. 30 cells (5 tasks × 6 models).

## 4. Paired comparisons

**Scenario-controlled paired bootstrap.** For each (model A, model B, scenario) triple: win/loss/tie on `manipulation_occurred`. Aggregate to net wins-minus-losses per model. Run on canonical-6 and small-model-augmented sets separately.

**Within-family ladder slopes.** Regression of manipulation rate on family size step. Anthropic (haiku → sonnet → opus); OpenAI gpt41 (nano → mini → full); per task.

**Within-generation pair deltas.** Per-cell mean Δ between same-family generations (haiku 3.5 → 4.5; sonnet 3.7 → 4.6; etc.). Bootstrap CIs.

## 5. Rank correlation

**Spearman ρ between per-task model rankings.** Pairwise across 5 paper tasks (10 pairs). Computed on permissive-frame manipulation rate.

## 6. Interaction tests

**Task × model F-test (LRT).** M0: `~ C(model) + C(task)`. M1: `~ C(model) * C(task)`. Compare via `anova_lm`. n=13,573 canonical-6.

**Per-cell residuals from M0.** Mean(actual) − Mean(predicted_M0) per (model, task) cell. Identifies which cells drive the interaction.

## 7. Multiple-testing corrections

**Inputs:** 14 reported p-values (per-task ELO regressions × 6; tier × frame ANOVAs × 7; tier × incentive ANOVA × 1).

**Methods:** Holm-Bonferroni, Benjamini-Hochberg FDR. Both global (across all 14) and within-family (per panel).

## 8. Tier-bucket comparisons

**Frontier > mid > small bucket means.** Per-task aggregate manipulation rate by capability tier. Direction-only; supports regression slopes qualitatively.

## 9. Per-claim / per-juror diagnostics

**Per-claim contribution to aggregate persuasion.** Fraction of total persuasion events attributable to each claim. Identifies outlier-driven inflation.

**Per-juror prior decomposition.** Starting confidence vs ending confidence per juror. Separates genuine persuasion from prior reversion.

## 10. Dose-response

**7-level audit-penalty sweep (legacy).** Bargaining manipulation rate as a function of E ∈ {0, 5, 10, 20, 30, 60, 80}. Fit per model. Shape-classification (cliff / smooth-decay / easily-deterred); not a single slope.

## 11. Trace inspection

**Matched-pair extraction.** Bargaining eval log indexed by (model, frame, difficulty, v_a, v_b, rep). Pairs differing only in `expected_penalty` (E=0 vs E=250) on permissive×high. 12 pairs across 6 models. Discussion turns extracted from `store["InteractionState:turns"]`.

## 12. Hand-validation

**Sales scorer.** Author-coded 30 stratified samples vs deterministic classifier. Pre-registered ≥90% threshold. Passed at 100%.

**Committee polarity scorer.** Author-coded 26 samples vs rule-based classifier. Pre-registered ≥85% threshold. Failed at 76.9%; metric dropped per Amendment A5.

**Inbox substrate.** Stratified-30 hand review of typed `topic_tag` and `correct_action` fields. Pre-registered ≥95% agreement. Deferred; gates final publication, not held-out-test verdict.

## 13. Pre-registered prediction outcomes

**P1–P7 verdicts.** Per-task table. Outcomes: ✓ / ✗ / weak / N/A. Documented in `paper/task<N>/results.md`.

**T6 held-out test (P-T6.1–P-T6.7).** Locked before any T6 real-roster scenario ran. Channel classification (P-T6.4), incentive-inert (P-T6.5), frame-dominant conditional (P-T6.6) all held; P-T6.1 (prohibitive floor) and P-T6.2 (permissive amplification) failed on per-model signatures.

## What was NOT done

- Logistic mixed-effects (would require pymer4/R or PyMC; LPM used instead).
- Permutation test on Spearman ρ (10 task-pairs, descriptive only).
- Power analysis / minimum-detectable-effect on null axes.
- Inter-rater reliability for LLM-judge scorers (Cohen's κ, Krippendorff's α).
- Test-retest / temperature-variance replication.
- Per-agent within-scenario consistency analysis.
- Time-within-trajectory metrics (early vs late round manipulation).
- Per-scenario cross-task correlation (only per-model rankings correlated).
- Refusal / non-compliance carve-out.
- Token-count / response-length analysis.
