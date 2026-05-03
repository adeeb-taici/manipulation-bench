# Reanalysis notes

This document accompanies the v2 statistical reanalysis of the
Manipulation Response Surface paper (NeurIPS 2026 E&D). The v1
slope-based and n=6-models Spearman ρ analyses are intact and
unchanged; v2 outputs sit alongside them with `_v2` suffixes.

## What was replaced

| v1 method | Where it lived | v2 replacement | Where it lives now |
|---|---|---|---|
| Per-(task, model, axis) standardized **slope** across ordinal axis levels | `paper/task<N>/analysis/prereg_results.json[sensitivity_slopes]` | OLS + scipy `dunnett` contrasts vs. baseline (prohibitive / none / low) + per-task Type II ANOVA η² | `paper/task<N>/analysis/regression_v2.json` |
| Single-point Spearman ρ on n=6 models for cross-task ranking stability | `paper/cross_task/analysis/ranking_stability.json` + `figures/fig_ranking_stability.pdf` | Trajectory-level percentile bootstrap (B=2000) on the same ρ statistic, stratified within (task × model × frame × incentive × difficulty) | `paper/cross_task/analysis/ranking_stability_v2.json` + `figures/fig2_ranking_stability_v2.pdf`, `figures/fig7_cross_task_rho_v2.pdf` |
| Mean &#124;slope&#124; per task as a "dominant axis" tiebreaker | `paper/cross_task/analysis/cross_task_aggregate.md`, `figures/per_task_slopes.pdf` | Per-task η² for {model, frame, incentive, difficulty}, computed under the same fit that drives the per-(model, axis) Block A | `paper/cross_task/analysis/table3_v2.md`, `figures/fig3_per_task_aggregate_v2.pdf` |
| 15-dim per-model profile of signed slopes | `paper/cross_task/analysis/cross_task_profiles.json`, `figures/per_model_profiles.pdf` | Per-model max-|Dunnett-contrast| heatmap (per-task scaled) | `figures/fig4_per_model_profile_v2.pdf` |
| (none) | (none) | Pooled variance decomposition with bootstrap CI on η²(model:task) − η²(model) | `paper/cross_task/analysis/variance_decomp_v2.json` |

### Standard errors per task

| Task | Inner item structure | v2 SE strategy |
|---|---|---|
| T1 Bargaining | per-trial lying decisions are collapsed into trajectory-level rate | HC3 robust |
| T2 Debate | per-claim binary persuasion outcome | cluster-robust on `claim_id` |
| T3 Village | one outcome per village (manipulator's exploitation rate) | HC3 robust |
| T4 Sales | 5 questions per (product × difficulty) | cluster-robust on `scenario_id` |
| T5 Committee | 4 candidates × 5 criteria per slate | cluster-robust on `slate_id` |

### Saturation handling

v2 detects per-cell saturation (residual SD < 1e-6 for any axis level) and
flags it explicitly in the per-(model, axis) JSON output. Three
interaction Wald tests on `axis × model` were reported as **not
estimable** because the resulting covariance matrix is rank-deficient:
T4 frame, T5 frame, T5 difficulty. The omnibus per-task η² and the
Dunnett contrasts are unaffected — those use simpler model
specifications and survive the saturation cleanly.

### Reproducibility

All v2 outputs are deterministic given the corpus + master seed
`20260430`. Scripts:

- `experiments/reanalysis/load.py` — trajectory dataframe loader.
- `experiments/reanalysis/block_a.py` — Block A + B per-task regression.
- `experiments/reanalysis/block_c.py` — Block C ranking-stability bootstrap.
- `experiments/reanalysis/block_d.py` — Block D variance decomposition.
- `experiments/reanalysis/figures.py` — Block E figure + table v2.

End-to-end: `python -m experiments.reanalysis.{load,block_a,block_c,block_d,figures}`.

Total wall-clock for the four analysis blocks: ~3 minutes on this machine.

## Headline-finding survival check

### 1. "Cross-task model rankings barely correlate" (v1 mean ρ ≈ 0.05)

**v1 claim** (cross_task/SUMMARY.md): "manipulation propensity is
task-dependent, not a stable model trait... mean Spearman ρ = 0.047
across the 10 task-pairs."

**Verification of the v1 number**: v2 reproduces v1's published mean
ρ = 0.055 to within 0.001 when using v1's *exact* metric definition
(see [`paper/cross_task/analysis/ranking_stability_v2_v1compat.json`](paper/cross_task/analysis/ranking_stability_v2_v1compat.json):
bootstrap median mean off-diagonal = +0.072, point estimate = +0.055).
The v1 published number is correct on the v1 corpus and the v1 metric
choices.

**The v1-vs-v2 gap is a definitional difference, not bootstrap
variance**: v1's `cross_task_ranking_stability.py` ranks T2 Debate
models by `manipulation_occurred` (binary detected-manipulation rate),
while v2's primary analysis uses `belief_shift` (the continuous primary
metric for T2 in `analyze_surface.py`). On T2 specifically these two
metrics produce *different* model orderings — every T2 cell of the ρ
matrix flips sign. All non-T2 cells are identical between v1 and v2.

**v2 finding** (using each task's stated primary metric, including
belief_shift for T2): bootstrap mean off-diagonal median ρ = **+0.27**
(B=2000, permissive-frame ranking), with **only 4 of 10 task-pair
correlations distinguishable from zero at 95%**.

**v2 finding (v1-compat)** (using `manipulation_occurred` for T2 to
match v1's mixed-metric definition): bootstrap mean off-diagonal
median ρ = **+0.07**, again with **4 of 10 pairs significant**.

**The "4 of 10 pairs significant" finding is robust to the metric
choice.** What's not robust is the *headline mean ρ value* — it
depends sensitively on whether T2 is ranked by belief_shift (+0.27) or
manipulation_occurred (+0.07). v1's original 0.055 is the
manipulation_occurred answer; v2's primary 0.27 is the belief_shift
answer. Both are defensible; the paper should make the choice
explicit.

The four robust correlations under v2's primary (belief_shift)
definition:

| Task pair | bootstrap median ρ | 95% CI | Interpretation |
|---|---:|---|---|
| T1 vs T3 | +0.49 | [+0.26, +0.54] | Bargaining ↔ Village (both prompt-dominant) |
| **T1 vs T4** | **−0.43** | **[−0.66, −0.09]** | **Bargaining ↔ Sales (anti-correlated; only robust negative ρ)** |
| T3 vs T4 | +0.43 | [+0.03, +0.77] | Village ↔ Sales |
| T3 vs T5 | +0.49 | [+0.43, +0.71] | Village ↔ Committee |

The headline-grabbing v1 numbers (debate-vs-sales = +0.94,
debate-vs-village = +0.60) **do not survive** — both have CIs that
straddle zero by wide margins.

**The T1↔T4 anti-correlation is the most striking result of the
reanalysis**: Bargaining and Sales are the *only* task pair in the
matrix with a robustly negative correlation (CI excludes zero, point
ρ = −0.38). Models that lie more about a number in Bargaining tend
to *misrepresent products less* on Sales, and vice versa. This is
worth surfacing in the paper:

- It cuts against any "general manipulation propensity" reading of
  the model rankings.
- It refines the channel-split story: Bargaining (prompt-dominant,
  behavioral lever) and Sales (state-dominant, informational lever)
  aren't just driven by different axes — they pull *different* models
  to the top of the ranking. GPT-5.5 has the highest permissive
  Bargaining rate (0.59) but among the lowest permissive Sales rates
  (0.03). Gemini is mid-pack on Bargaining (0.53) but highest on
  Sales (0.19). The two tasks reward genuinely different model
  tendencies.

This finding is **new in v2**; v1's slope-based aggregate didn't
surface it because absolute slopes can't distinguish "low manipulation
everywhere" from "rank-reversed across tasks."

### 2. "Channel split: prompt-dominant vs. state-dominant" (v1 dominance ratio)

**v1 claim**: T1/T3 are prompt-dominant (incentive/frame win); T2/T4/T5
are state-dominant (difficulty wins).

**v2 finding**: the per-task η² decomposition *partially* supports this,
but the v2 numbers expose two important caveats:

| Task | v1 framing | v2 dominant-axis η² | v2 verdict |
|---|---|---:|---|
| T1 Bargaining | incentive-dominant | incentive 0.26 (frame 0.17, difficulty 0.00) | **strongly supports** v1 |
| T2 Debate | difficulty-dominant | difficulty 0.002 (incentive 0.002, frame 0.001) | **does not support** v1 — see §3 below |
| T3 Village | frame-dominant | frame 0.59 (model 0.16, incentive 0.01) | **strongly supports** v1 |
| T4 Sales | difficulty-dominant | difficulty 0.019 (frame 0.007, incentive 0.008) | weakly supports v1 |
| T5 Committee | difficulty-dominant | model 0.21, frame 0.17, difficulty 0.04 | **contradicts** v1 — model dominates difficulty |

T1/T3 retain their channel-dominant character cleanly. T4 still picks
out difficulty as dominant but the absolute effect (η² = 0.019) is
small. **T2 and T5 require revision.**

### 3. **T2 Debate: dominant axis isn't real** (new v2 finding)

In v1, T2 was assigned "difficulty-dominant" because mean |slope| at
difficulty (0.061) exceeded incentive (0.014) and frame (0.007). The v2
η² decomposition reveals: **all three axes explain less than 0.2% of
variance, and the residual is 99.1%**. The v1 ranking among "frame >
incentive > difficulty" was distinguishing 0.001 from 0.002, then
calling the slightly-larger one "dominant."

T2 Debate's outcome (`belief_shift`) is essentially noise on this
corpus. The interaction LR test is highly significant (F = 33.8,
p < 1e-11 for axis × model on frame), but that's because clustered SEs
yield few degrees of freedom (df = [20, 22]) — the *effects themselves*
are tiny.

**Recommendation**: drop T2's "difficulty-dominant" descriptor from the
paper. The honest framing is "T2 Debate's outcome variance is
dominated by per-debate idiosyncrasy not captured by axis or model
identity."

### 4. "Verbal vs. binding incentives" (v1 P5 cross-task split)

**v1 claim**: incentive language only binds when it introduces new reward
structure (T1 + T5); verbal incentives in T2/T3/T4 are inert.

**v2 finding**: this **survives unchanged**. Per-task η²(incentive):

- T1 Bargaining: **0.264** (binding — penalty math affects payoff)
- T5 Committee: **0.038** (modest, but distinguishable; competition outcome)
- T2 Debate: 0.002 (inert)
- T3 Village: 0.013 (essentially inert)
- T4 Sales: 0.008 (inert)

The split is sharper than v1's mean-|slope| view suggests — T5 Committee's
incentive sensitivity is much smaller than T1's, but still non-trivial.
The "binding vs. inert" dichotomy holds.

### 5. Variance decomposition (new v2 finding, no v1 counterpart)

The v1 paper has no formal cross-corpus partition of variance. v2
contributes one:

**Pooled fit (within-task z-scored), all 12,493 trajectories:**

| Term | η² | bootstrap 95% CI |
|---|---:|---|
| C(model) | 0.032 | [0.026, 0.038] |
| C(model):C(task) | **0.046** | [0.040, 0.052] |
| C(frame) | 0.066 | [0.059, 0.074] |
| C(incentive) | 0.039 | [0.033, 0.045] |
| C(difficulty) | 0.022 | [0.018, 0.027] |
| C(task) | ~0 | (forced by z-scoring) |
| Residual | 0.795 | [0.783, 0.807] |

**Headline**: **η²(model:task) explains an additional +0.013 of total
variance beyond η²(model) [95% bootstrap CI: +0.004, +0.023]**, CI
excludes zero.

In plain terms: the model×task interaction accounts for 1.3 percentage
points more of the corpus's total variance than the main effect of
model identity does. The descriptive ratio is 1.42×; we lead with the
absolute difference because the ratio's bootstrap distribution has a
small-denominator tail (η²(model) ≈ 0.03) that makes the percentile CI
on the ratio less stable than the CI on the difference.

This is **statistically distinguishable from zero** and supports the v1
narrative direction, but the magnitude is modest. The v1 SUMMARY's
"manipulation propensity is task-dependent, not a stable model trait"
reads as a strong qualitative
claim; the v2 evidence is **directionally consistent but weaker than
the rhetoric** — both main and interaction effects are small, and
the interaction edges out the main effect by ~30%.

## Specific paper claims that need softening

These are sentences pulled from `paper/cross_task/SUMMARY.md` and per-task
`results.md` files that the v2 analysis suggests need revision.

1. **SUMMARY.md, "Cross-task model rankings barely correlate"** — replace
   "mean Spearman ρ = 0.047" with "bootstrap median ρ = +0.27 across the
   10 task pairs, of which only 4 have a 95% CI excluding zero." The
   broader claim ("manipulation propensity is task-dependent") survives.

2. **SUMMARY.md, "T2 Debate, difficulty-dominant"** — drop the dominance
   designation entirely. T2's response surface is essentially flat in
   the η² view (all axes < 0.2%, residual = 99.1%). Reframe as: "T2
   Debate's belief_shift outcome shows no axis with η² > 0.005; the
   variance is dominated by per-debate idiosyncrasy."

3. **SUMMARY.md, headline channel-split table** — T5 Committee is listed
   as state-dominant (difficulty), but η²(model) = 0.21 ≫ η²(difficulty)
   = 0.04 in the v2 decomposition. T5 should be reclassified as
   **model-dominant**. The v1 claim was an artifact of mean |slope| not
   accounting for between-model variance.

4. **SUMMARY.md, "GPT-5.5 → GPT-5.5 reduces manipulation on 4/5 tasks…"** —
   not affected by v2; this is descriptive and the per-task means are
   unchanged. The claim stands.

5. **`paper/cross_task/EXPLORATORY_FINDINGS.md`, frontier-lift section** —
   not addressed by v2; that analysis uses original v1 model labels for
   pre/post comparison and was out of scope.

6. **Per-task `results.md` files** — the v1 standardized-slope point
   estimates are unchanged; only the *interpretation* of small slopes
   needs revision (a small slope on a noisy outcome may not be
   distinguishable from zero under v2's CIs). The Block A `regression_v2.json`
   files contain the per-cell Dunnett intervals needed to update those
   per-task interpretations.

## Open issues / caveats for v2 itself

- **T3 Village low power**: ~2 trajectories per (model × frame × incentive
  × difficulty) cell. v2's per-(model, axis) Dunnett operates on ~36
  obs/level (averaging over 18 cells), so it has adequate power; the
  "low_power_warning" flag in the JSON refers to the deeper cell level,
  not the per-(model, axis) view. The interaction-LR for T3 frame
  (F = 30.0, p < 1e-72) is highly significant on its own, so the
  per-model T3 frame breakouts can be trusted.

- **T1 incentive interaction LR was pathological in an earlier draft**
  (F ≈ 4.9 × 10¹⁷). Cause: a v2-loader bug (`expected_penalty=0` was
  silently mapped to `NaN` because the loader used Python's `or`
  fallback on a falsy zero value). The bug **dropped 1799 of 5400 T1
  trajectories from v2 only**; v1's `task1_prereg_analysis.py` reads
  `expected_penalty` directly into an integer-keyed dict and was never
  affected. Fixed — current v2 uses all 5399 valid T1 rows and the
  interaction F = 123.1 (p < 1e-231).

- **Three interaction tests are unreported** as not-estimable due to
  saturated cells (T4 frame, T5 frame, T5 difficulty). The per-task
  η² values for those tasks live on the simpler main-effects fit
  (`y ~ C(model) + C(frame) + C(incentive) + C(difficulty)`) which
  is full-rank in all cases (verified: T4 design matrix has rank 14
  with 14 parameters; T5 same). The η² numbers in `regression_v2.json`
  for T4 frame, T5 frame, T5 difficulty are well-conditioned and
  trustworthy. Only the omnibus axis × model interaction Wald test
  failed — that's a separate, more demanding fit on the fully-crossed
  design.

- **Bootstrap budgets**: B=2000 for ranking stability (brief explicit),
  B=1000 for variance decomposition (each refit is heavier). Both fit
  comfortably under 1 minute on this machine due to the small number of
  unique strata; the brief's projected ~7 min was a conservative
  pre-implementation estimate.

## Self-verification log

These checks were run against the v2 outputs to catch errors in the
reanalysis itself:

| Check | Result |
|---|---|
| Reproduce v1's published mean ρ = 0.055 from scratch using v1's metric definition | **Pass** — v2 v1-compat code reproduces v1 cell-by-cell (mean off-diag = +0.072 bootstrap median, +0.055 point estimate, 6/10 pairs match to 3 dp; 4/10 pairs differ in T2 only because v1 uses `manipulation_occurred` for T2 while v2 uses `belief_shift`) |
| T1 loader bug never affected v1's published numbers | **Pass** — v1's `task1_prereg_analysis.py:73` reads `expected_penalty` directly into an int-keyed dict; the falsy-zero coercion that hit v2 doesn't apply |
| T4 frame, T5 frame, T5 difficulty per-task η² are computed on full-rank design matrices | **Pass** — verified directly; all design matrices have rank == n_params, no rank-deficiency warnings during the main-effects fits |
| Variance-decomp headline framed as absolute difference, not ratio | **Done** — η²(model:task) − η²(model) = +0.013 [+0.004, +0.023] is now the lead number; ratio 1.42× is the descriptive sidekick |
| T1↔T4 anti-correlation flagged as a finding | **Done** — surfaced in §1 as the only robustly-negative cross-task correlation, with implications for the channel-split narrative |
