# Leave-one-model-out (LOMO) robustness — findings

Reviewer objection: six models is too few. Each cohort model is dropped in turn
and the paper's four headline claims are recomputed on the remaining five, using
the committed analysis code (see `lomo_robustness.py` docstring for the exact
reuse map).

Reproduction check: the full-roster run of every section reproduces the
published number exactly (§4.3 → 17/18, 18/18, p = 0.106; Table 2 dominance
ratios → 2.24× / 4.05× / 3.13× / 3.33× / 1.84×; v2 mean off-diagonal ρ → 0.329).

## Stable under all six exclusions

**Dominant axis: 6/6 environments unchanged, for every exclusion. Zero flips.**
This is the strongest result in the analysis. No environment's dominant axis
depends on any single model.

**Directional partition: holds in all six.** Assertive environments keep mean
`Delta_D > 0`, commissive keep mean `Delta_D < 0`, every time.

**Commissive sign agreement: 15/15 in all six exclusions** (full roster 18/18).

**Fisher exact on the 6-environment 2×2: identical in all six** — the table is
`[[3,0],[0,3]]` under every exclusion, one-sided p = 0.0500. Perfectly stable,
but it is sitting on its own floor (a perfect 3/3 split cannot do better than
1/C(6,3) = 0.05), so it carries little information.

## Unstable — report these

**1. The §4.3 cluster-robust p-value is not robust. It ranges 0.028 → 0.205
against a full-roster 0.106, and crosses 0.05 in both directions.**

| Excluded | coef | p (cluster-robust) | p (i.i.d.) |
|---|---:|---:|---:|
| — full roster | +0.440 | **0.106** | 0.152 |
| Claude Opus 4.7 | +0.325 | **0.028** | 0.313 |
| DeepSeek V4 Pro | +0.343 | 0.060 | 0.317 |
| GPT-5.5 | +0.401 | 0.077 | 0.264 |
| Llama 3.3 70B | +0.420 | 0.096 | 0.248 |
| Grok 4 | +0.441 | 0.114 | 0.231 |
| Gemini 3.1 Pro | +0.708 | **0.205** | 0.005 |

Dropping **Claude Opus 4.7** makes the partition significant at α = 0.05
(p = 0.028). Dropping **Gemini 3.1 Pro** nearly doubles the coefficient
(+0.440 → +0.708) yet *worsens* the cluster-robust p to 0.205 — while the
i.i.d. p moves the opposite way, 0.152 → 0.005. Gemini is a high-leverage
between-cluster outlier: removing it tightens the within-cluster fit (i.i.d. SE
falls) but leaves the six environment-level means more dispersed relative to
G = 6 clusters, so the sandwich SE rises. With G = 6 and df = 5 the test has
very little power to begin with; that the sign of the conclusion depends on
which model is dropped is the honest headline.

**2. Cross-environment rank instability (v2) swings by a factor of 13.**
Full roster mean off-diagonal ρ = 0.329; LOMO range 0.040 (drop Gemini) →
0.541 (drop GPT-5.5). The qualitative claim direction is not preserved: at
ρ = 0.040 rankings look essentially uncorrelated, at ρ = 0.541 moderately
correlated. Spearman on 5 models admits only six distinct values, so this
statistic is coarse by construction.

**3. Assertive sign agreement is 14/15 under five exclusions and 15/15 when
Gemini is dropped** (full roster 17/18). The single full-roster exception is
**Gemini 3.1 Pro × T5 Committee**, whose difficulty slope is +0.016 against
five strongly negative ones. Dropping Gemini removes the only exception.

## T5 Committee and T6 Inbox specifically

**T5 Committee never flips, and is less fragile than expected.** Its
top-vs-second ratio ranges 1.61× (drop Claude) → 2.36× (drop Gemini) against
1.84× full-roster. Dropping Gemini *strengthens* difficulty dominance, because
Gemini is the one model whose T5 difficulty slope is near zero.

**T6 Inbox is the fragile environment, not T5.** On top-vs-second its
full-roster ratio is 1.32× — tighter than T5's 1.84× — and dropping Llama
3.3 70B takes it to **1.06×** (frame 0.094 vs incentive 0.089, effectively a
tie). It does not flip, but it is the closest any environment comes.

Note `task6_inbox/results.md` advertises "6.14×" for T6; that is
frame-vs-*difficulty*, the quantity P-T6.4 pre-registered, not top-vs-second.
Both are in the CSV (`ratio_top_over_second`, `ratio_frame_over_difficulty`).

## T3 Village — dominance ratio with and without incentive

T3's second-largest axis is incentive, so its ratio depends on whether the
incentive axis is eligible. `analyze_response_surface.py:73` declares Village
has no incentive axis by design; `aggregate.py` / `SUMMARY.md` (which produced
the published table) treat it as real. Both reported:

| Excluded | with incentive | without incentive |
|---|---:|---:|
| — full roster | 3.13× | 7.34× |
| Claude Opus 4.7 | 3.03× | 6.81× |
| GPT-5.5 | 4.12× | 10.57× |
| Gemini 3.1 Pro | 3.47× | 8.35× |
| Grok 4 | 2.74× | 5.94× |
| Llama 3.3 70B | 3.04× | 7.14× |
| DeepSeek V4 Pro | 2.81× | 6.88× |

Frame dominates either way, under every exclusion. The contradiction changes
the ratio's magnitude by ~2.3×, never the conclusion.

## Caveats on how these numbers were computed

- **§4.3 clusters are environments, not models.** G stays at 6 and df at 5
  under every exclusion; only the row count changes (36 → 30). LOMO does not
  degrade the cluster structure.
- **Two independent pipelines.** §4.3 uses joint three-axis OLS on
  `paper/cross_task/data/results.csv`; the dominance table uses univariate
  per-axis slopes from each task's `prereg_results.json`. They agree
  qualitatively but are different estimators and their slopes will not match
  line-for-line.
- **T6 dominance is an extension, not a published quantity.** `aggregate.py`'s
  `TASKS` list stops at T5, so Table 2 is a 5-environment table. T6 rows here
  apply the same estimator to T6's committed `prereg_results.json`.
- **T5's per-model slopes are hardcoded to 3 dp** in `aggregate.py:T5_SLOPES`,
  transcribed from `results.md` §A.4; T5 has no `prereg_results.json`. LOMO on
  T5 inherits that rounding. Not regenerated, per instruction.
- **T6's `prereg_results.json` keys GPT-5.5 as `gpt5`** where T4 uses `gpt55`.
  An earlier version of this note claimed the shared remap lacks a `gpt5` entry
  and would silently drop the model; **that was wrong**, and is corrected here.
  `load.py:MODEL_REMAP` already maps `gpt5 -> GPT-5.5`, and
  `aggregate.load_task_slopes("task6_inbox")` returns all six canonical models
  unaided (verified). The claim came from the older hardcoded `T4_MODEL_MAP` in
  the pre-consolidation `cross_task_analysis.py`, which did lack the key.
  `T6_KEY_FIX` in `lomo_robustness.py` is therefore redundant — it maps to the
  same value the shared remap already produces, so it is retained only as an
  explicit assertion and changes no number. The key naming remains
  *inconsistent* across tasks, which is a tidiness issue, not a correctness one.
- **Fisher is a reconstruction, not a reproduction.** No committed code computes
  it. The "~0.011" in `task6_inbox/prereg.md:132` / `results.md:276` is
  explicitly retracted by `paper/figures/t6_permutation_test.md`.
- **No bootstrap is involved in the dominance ratios** — that pipeline is fully
  deterministic, so the pre-registered N=1000 seeds do not apply to it.
- **Rank instability uses v2** (`ranking_stability_v2.py`, the version
  `ANALYSIS_INVENTORY.md` marks core/§4.1), point estimates only. v1
  (`ranking_stability.json`, mean ρ = 0.055) is marked deprecated.

## Bootstrap CI widths (separate scope — different reviewer response)

Read from the committed `bootstrap_cis.json` artifacts; not re-run, so these are
the archived numbers. Median 95% CI width on per-(model, axis) slopes:

| Environment | median CI width | n cells |
|---|---:|---:|
| T1 Bargaining | 0.0455 | 18 |
| T2 Debate | 0.0305 | 18 |
| T3 Village | 0.1147 | 18 |
| T4 Sales | 0.0326 | 18 |
| T5 Committee | 1.0565 | 18 |
| **T6 Inbox** | **— no artifact** | **0** |

T5's width is on the 0–20 bias scale, not a 0–1 rate scale, so it is not
comparable to T1–T4. **T6 is a true gap**: no `bootstrap_cis.json` exists and
T6 has no seed in `run_bootstrap_cis.py`. Per instruction it is reported as a
gap rather than filled. (T5 is *not* a CI gap — its `bootstrap_cis.json` is
committed; T5's gap is that its dominance-table slopes live hardcoded in
`aggregate.py` instead of a JSON.)

## Follow-up 1 — the three ρ statistics (`rho_reconciliation.py`)

The abstract's two ρ figures come from **different pipelines**. All three
candidates below are the same aggregation (Spearman across the 6 models per
environment pair, then the mean of the *signed* off-diagonal over 10 T1–T5
pairs) and all reproduce exactly from committed code:

| Pipeline | Object correlated | T2 metric | Rows | mean ρ | LOMO range | debate–sales |
|---|---|---|---|---:|---|---:|
| **v1** (abstract) | per-model mean at frame=permissive | `manipulation_occurred` | permissive only | **0.055** | −0.130 … +0.199 | −0.543 |
| v2 | per-model mean at frame=permissive | `belief_shift` | permissive only | 0.329 | +0.040 … +0.541 | +0.943 |
| corpus | per-model `manipulation_occurred` rate | `manipulation_occurred` | **all** canonical | 0.194 | +0.040 … +0.280 | **−0.771** |

v1 and v2 are the **same estimator differing in exactly one input column** —
T2's metric. Every non-T2 cell is identical; every T2 cell flips sign.
`analysis/ranking_stability_v2_v1compat.json` runs the v2 code with v1's metric
and returns 0.0552, confirming it. The corpus pipeline is a genuinely different
object (all canonical rows, not permissive-only).

**Citation splice in the abstract**: it pairs v1's mean (0.055) with "one pair
(sales vs. debate) reaching ρ = −0.77", but −0.771 is a cell of the *corpus*
matrix. In v1, debate–sales is −0.543 and the most negative pair is
debate–village at −0.600. Both numbers are individually reproducible; they are
not from the same matrix.

**LOMO on the paper's headline (v1) is −0.130 … +0.199 — it straddles zero under
every exclusion**, so the "essentially zero / poor predictor" reading is robust
to roster composition. (The 0.040 … 0.541 range reported earlier in this file
was on v2, which is *not* the abstract's statistic.)

## Follow-up 2 — Table 2 T1/T2 provenance and the T1 P4 verdict

**T1 P4**: the code produces part (a) 6/6, part (b) 5/6, verdict **PASS**
(`task1_bargaining/analysis/prereg_results.json:p4`, echoed at
`task1_bargaining/results.md:47`). So `✓ (5/6)` is correct and traceable — the
5/6 is part (b). main's `partial (4/6)` matches nothing the code emits; 4/6 is
the *threshold* in P4's docstring ("≥4/6 models"), which is the likely source of
the confusion.

**Table 2 T1/T2**: main's `0.108 / 0.030 → 2.3×` and `0.061 → 4.4×` have **no
single computational source**. The machine-generated
`analysis/cross_task_aggregate.md` has only ever held:

| date | T1 frame/inc/diff → ratio | T2 frame/inc/diff → ratio |
|---|---|---|
| 2026-04-26 | 0.102 / 0.217 / 0.029 → 2.1× | 0.011 / 0.012 / 0.064 → 5.3× |
| 2026-04-26 | 0.106 / 0.208 / 0.030 → 2.0× | 0.010 / 0.012 / 0.061 → 5.2× |
| 2026-04-27 → now | **0.112 / 0.250 / 0.034 → 2.2×** | **0.007 / 0.014 / 0.056 → 4.0×** |

main's row is a **partial hand-update**: T1's incentive (0.250) and T2's
frame/incentive (0.007/0.014) are post-2026-04-27 values, while T1's difficulty
(0.030) and T2's difficulty (0.061) are pre-2026-04-27 values. T1 frame 0.108
and both ratios (2.3×, 4.4×) appear in **no** generated version ever. The ratios
are internally consistent with their own mixed row (0.250/0.108 = 2.31;
0.061/0.014 = 4.36), which is what manual recomputation would produce.

Lineage: `d69b5ed` (2026-04-27) introduced `0.108 … 2.3×`; `8fffb75`
("Pre-submission cleanup", 2026-05-06) **corrected it** to `0.112 … 2.2×`; merge
`bae6a51` on main then **silently discarded that correction**, taking the stale
side. post-submission kept the fix. Both branches contain `8fffb75`.

**Not determinable from this repo**: what the *submitted PDF* says. There is no
`.tex`, `.bib`, or manuscript PDF in the repo or anywhere in its history — only
generated figure PDFs. Someone must read the submission to establish which row
it carries.

## Follow-up 3 — pre-specified robustness battery (`partition_robustness.py`)

Regression `Delta_D ~ 1 + assertive`, clusters = environment (G = 6).

| Excluded | coef | CR1 p | wild cluster p (Webb, 2-sided) | RI exact 1-sided |
|---|---:|---:|---:|---:|
| — full roster | +0.440 | 0.106 | 0.079 | 0.050 (rank 1/20) |
| Claude Opus 4.7 | +0.325 | 0.028 | 0.016 | 0.050 (rank 1/20) |
| GPT-5.5 | +0.401 | 0.077 | 0.050 | 0.050 (rank 1/20) |
| Gemini 3.1 Pro | +0.708 | 0.205 | 0.182 | 0.050 (rank 1/20) |
| Grok 4 | +0.441 | 0.114 | 0.082 | 0.050 (rank 1/20) |
| Llama 3.3 70B | +0.420 | 0.096 | 0.066 | 0.050 (rank 1/20) |
| DeepSeek V4 Pro | +0.343 | 0.060 | 0.032 | 0.050 (rank 1/20) |

Wild cluster bootstrap: Webb six-point weights, null imposed, B = 9,999, seed
20260728. Webb rather than Rademacher because G = 6 gives only 2⁶ = 64 distinct
Rademacher draws, flooring that p-value at 1/64; Webb gives 6⁶ = 46,656.

**Randomization inference is the cleanest result here.** Across all 20 possible
3-vs-3 partitions of the six environments, the pre-registered assignment
{committee, debate, sales} yields the **largest** coefficient — rank 1 of 20 —
under the full roster *and* under every single-model exclusion. Exact one-sided
p = 0.050, which is the **attainable minimum**: 1/C(6,3) = 0.05 is a hard
ceiling on this design's power, independent of effect size or how many models
are added. Adding models adds rows but no clusters.

**Power limitation, stated plainly.** `assertive` is a deterministic function of
environment, so it does not vary within cluster: the contrast is cluster-level
with 6 clusters in a 3-vs-3 split, and the effective sample size is **6, not
36**. Only 13.4% of Delta_D's sum of squares is between-cluster (86.6% is
across models within an environment). This test has very little power by
construction, and no roster change can fix that.

Leave-one-**environment**-out is more consequential than leave-one-model-out:
dropping T5 Committee moves the coefficient from +0.440 to +0.197 (−55%), far
more than any model exclusion.

## Follow-up 3b — scale confound (`partition_scale_diagnostic.py`, POST-HOC)

**Not pre-specified.** Surfaced by the leverage analysis above and reported for
that reason, not selected from a menu.

`Delta_D` carries each environment's metric units, and those units are not
common: T5 Committee is `initial_bias` on a 0–20 rating scale, every other
environment is a rate in [0, 1]. The per-environment scale proxy
mean(|β_D| + max(|β_F|,|β_I|)) ranges **119×**, from committee 3.993 to debate
0.034. Committee's Delta_D (+0.771) is ~13× the next-largest assertive
environment (sales, +0.061) and dominates the between-cluster signal.

Refitting the identical regression on the unit-invariant

    Delta_rel = (|β_D| − max(|β_F|,|β_I|)) / (|β_D| + max(|β_F|,|β_I|))   ∈ [−1, 1]

which is sign-identical to Delta_D by construction:

| Excluded | Delta_D coef / CR1 p / wild p | **Delta_rel** coef / CR1 p / wild p |
|---|---|---|
| — full roster | +0.440 / 0.106 / 0.079 | **+1.200 / 0.0005 / 0.0068** |
| Claude Opus 4.7 | +0.325 / 0.028 / 0.016 | **+1.213 / 0.0008 / 0.0069** |
| GPT-5.5 | +0.401 / 0.077 / 0.050 | **+1.234 / 0.0006 / 0.0077** |
| Gemini 3.1 Pro | +0.708 / 0.205 / 0.182 | **+1.285 / 0.0000 / 0.0048** |
| Grok 4 | +0.441 / 0.114 / 0.082 | **+1.180 / 0.0005 / 0.0079** |
| Llama 3.3 70B | +0.420 / 0.096 / 0.066 | **+1.127 / 0.0010 / 0.0068** |
| DeepSeek V4 Pro | +0.343 / 0.060 / 0.032 | **+1.158 / 0.0011 / 0.0072** |

On the scale-free version the coefficient is stable (+1.13 … +1.29 vs
+0.32 … +0.71) and significant under **every** exclusion (wild cluster
p ≤ 0.008), with RI still rank 1/20 throughout. Sign agreement is unchanged at
17/18 and 18/18, as it must be.

Interpretation: the *instability* of the published p-value is substantially an
artifact of pooling an unnormalized quantity across a 119× scale range, not
evidence that the partition is fragile. Recommended reporting: cite the RI
result (rank 1/20, p = 0.05 floor, invariant to exclusions) and the scale-free
regression, and present the raw `Delta_D` p-value as underpowered and
scale-contaminated. Even so, the RI floor of 0.05 means no version of this test
can produce strong significance at G = 6 — that limitation should be stated
rather than implied.

## Outputs

- `lomo_dominance.csv` — 42 rows: 7 rosters (full + 6 exclusions) × 6
  environments, with dominant axis, all three mean |slope| values, top-vs-second
  ratio and frame-vs-difficulty ratio.
- `slope_ci_widths.csv` — 90 rows of per-(environment, model, axis) CI widths.
- `lomo_results.json` — everything machine-readable, including a `provenance`
  block naming each source script.
- `REPRODUCED_section4.3_model_task_axis_sensitivity.md` — output of running the
  committed §4.3 script unmodified. Its normal destination
  (`paper/figures/model_task_axis_sensitivity.md`) has no git history on any
  branch, so the paper's §4.3 numbers were never archived; this is that artifact.
