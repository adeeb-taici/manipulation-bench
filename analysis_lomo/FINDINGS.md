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
