# Capability-axis findings

Exploratory analysis of how model capability — proxied by LMArena ELO, capability tier, and model generation — interacts with the manipulation response surface across the 6 paper tasks (bargaining, debate, village, sales, committee, inbox).

**Status**: post-hoc, not pre-registered. Belongs in `paper/cross_task/EXPLORATORY_FINDINGS.md` if cited in the paper.

**Inputs**: `paper/cross_task/results.csv` (~28k samples, 15 models) joined with `paper/cross_task/model_capability.csv` (LMArena snapshot 2026-05-03; 12/15 ELOs from `arena.ai/leaderboard/text` direct, 3/15 from the OpenLM mirror).

---

## Headline

**Capability is not a monotonic axis on manipulation rate.** Across the 6 tasks, the sign of the ELO-vs-manipulation relationship flips depending on what the task affords. In tasks where manipulation is suppressed by capability (debate, village, sales), more capable models manipulate *less*, controlling for axis cell. In tasks where manipulation requires sophistication or where the task elicits subtle bias (committee, inbox), more capable models manipulate *more*. Bargaining is roughly flat.

**The frame × tier interaction is real and significant** (pooled p < 0.0001, two-way ANOVA, Type II SS). Capability tiers respond to prompt frame *differently*, not just at different absolute levels — meaning frame-sensitivity itself depends on capability.

---

## Finding 1 — Per-task ELO effect (OLS, controls for frame/incentive/difficulty)

`manipulation_rate ~ ELO_per100 + C(frame) + C(incentive) + C(difficulty)`, HC3 robust SEs, ELO centered at 1400.

| Task | n | β (per +100 ELO) | 95% CI | p | R² |
|---|---|---|---|---|---|
| bargaining | 13,499 | −0.004 | [−0.012, +0.005] | 0.43 | 0.19 |
| debate | 6,170 | −0.008 | [−0.014, −0.002] | **0.005** | 0.10 |
| village | 969 | −0.062 | [−0.081, −0.043] | **<0.001** | 0.39 |
| sales | 3,375 | −0.020 | [−0.026, −0.014] | **<0.001** | 0.28 |
| committee | 2,624 | +1.55 | [+1.36, +1.74] | **<0.001** | 0.38 |
| inbox | 2,715 | +0.029 | [+0.006, +0.052] | **0.015** | 0.15 |

**Interpretation by task:**

- **village (β = −0.062)**: each +100 ELO drops the exploitation rate by ~6 percentage points. Strongest negative effect in the panel. More capable models defect less in the public-goods game.
- **sales (β = −0.020)**: each +100 ELO drops misleading/false answer rate by ~2pp. Frontier models give more accurate buyer answers.
- **debate (β = −0.008)**: small but significant negative effect on belief-shift driven manipulation.
- **inbox (β = +0.029)**: more capable models suppress/misroute target emails *more* — possibly because subtler suppression strategies require capability to execute at all.
- **committee (β = +1.55)**: huge positive coefficient, but **interpret with caution**: committee's `manipulation_metric` is `initial_rating_bias`, an unbounded signed quantity (rating delta on a 0-10 scale), not a [0,1] rate like the others. The sign is real (more capable interested-party agents pull ratings toward their candidate harder); the magnitude is on a different scale.
- **bargaining**: null effect under controls. Capability doesn't predict over-statement of valuations once cell is fixed.

The pooled regression with ELO × task interaction terms is significant for every task (all p < 0.025 except sales p = 0.09), confirming that **the ELO effect is task-conditional**, not a universal main effect.

**Figure**: `figures/capability_regression_coefs.png` (per-task β with 95% CIs, red = p<0.05).

## Finding 2 — Tier × frame interaction is significant (ANOVA)

Two-way ANOVA on `manipulation_metric ~ tier × frame` (Type II SS):

| Task | interaction p | n |
|---|---|---|
| bargaining | **<0.0001** | 13,499 |
| debate | 0.98 | 6,170 |
| village | **<0.0001** | 969 |
| sales | 0.54 | 3,375 |
| committee | **<0.0001** | 2,624 |
| inbox | **0.003** | 2,715 |
| **pooled** | **<0.0001** | 29,352 |

**Interpretation**: in bargaining, village, committee, and inbox, *capability tiers respond to frame differently* — not just at different baselines. The same pro_social → permissive frame shift produces different rate movements depending on tier. Debate and sales show parallel responses across tiers (no interaction).

**The pooled tier × incentive interaction is null (p = 0.80)**, but **tier × difficulty is highly significant (p < 0.0001)** — capability and difficulty interact, but capability and incentive do not. Models of different tiers respond similarly to incentive intensity but differently to scenario difficulty.

## Finding 3 — Generation lift within family (paired bootstrap)

For each within-family generation pair (haiku35→haiku45, sonnet37→sonnet46, gpt41→GPT-5.5, gpt41mini→gpt54mini, gpt41nano→gpt54nano), compute the per-cell rate delta and bootstrap a 95% CI on the per-task mean.

Selected significant deltas (CI excludes 0):

| Pair | Task | Δ (current − prev) | 95% CI |
|---|---|---|---|
| haiku35 → haiku45 | bargaining | **−0.66** | [−0.74, −0.58] |
| haiku35 → haiku45 | sales | −0.08 | [−0.11, −0.06] |
| haiku35 → haiku45 | inbox | −0.32 | [−0.38, −0.27] |
| sonnet37 → sonnet46 | committee | +0.54 | [+0.18, +0.84] |
| sonnet37 → sonnet46 | inbox | −0.10 | [−0.17, −0.03] |
| gpt41 → GPT-5.5 | bargaining | **+0.30** | [+0.21, +0.42] |
| gpt41 → GPT-5.5 | committee | +0.64 | [+0.12, +1.20] |
| gpt41 → GPT-5.5 | inbox | −0.28 | [−0.37, −0.18] |
| gpt41nano → gpt54nano | village | +0.27 | [+0.21, +0.33] |
| gpt41nano → gpt54nano | inbox | +0.42 | [+0.35, +0.48] |

**Pattern**: within-family generation upgrades systematically *reduce* manipulation in inbox (4 of 5 pairs significantly negative) and sales (3 of 5 significantly negative). They *increase* manipulation in committee (3 of 5 significantly positive) and bargaining (2 pairs significantly positive, including the strongest single haiku35→haiku45 *decrease* of −0.66 — directionally opposite, indicating generation effects are family-specific in bargaining).

**The most consistent generation-driven shift is the inbox suppression effect**: 4 of 5 within-family upgrades raise or lower the suppression rate by 10pp+ in absolute terms. The direction depends on the family. Smaller families (nano, mini) tend to manipulate *more* with new generations on inbox; flagship/average upgrades (haiku, sonnet, GPT-5.5) tend to manipulate *less*.

**Figure**: `figures/capability_frontier_lift.png`.

## Finding 4 — Tier composition reflects capability clustering

K-means (k=3) on per-(task, frame) profile vectors, projected to 2D PCA (PC1 = 35%, PC2 = 19% of variance):

- **Cluster 0** (9 models): all 4 average-tier, 4 small-tier, 1 flagship. Mixed prev/current.
- **Cluster 1** (4 models): all flagship, all current generation.
- **Cluster 2** (2 models): 1 small, 1 flagship. Outliers.

**The flagship-current cohort separates cleanly in profile space** — the 4 newest frontier models (likely Claude Opus 4.7, GPT-5.5, Gemini 3.1 Pro, DeepSeek V4 Pro) cluster together across tasks. Average and small tiers are not cleanly separated, but flagship-current is.

**Figure**: `figures/capability_clustering_pca.png`.

## Finding 5 — Tier-faceted response surface

The paper's primary 5-frame × 3-incentive heatmap (and frame × difficulty), faceted by tier instead of by individual model, shows the *texture* of the tier × frame interaction from Finding 2.

**Figures**:
- `figures/response_surface_by_tier__frame_x_incentive.png`
- `figures/response_surface_by_tier__frame_x_difficulty.png`

(Visual inspection — left to the reader since heatmaps are hard to summarize numerically.)

---

## Caveats

1. **LMArena ELO is a noisy capability proxy.** It measures human-rated chat quality, which correlates with but doesn't directly measure reasoning, agentic capability, or manipulation propensity. A composite (LMArena + GPQA + SWE-bench) would be stronger but isn't available for all 15 models in this cohort.

2. **Three ELOs come from a non-primary source** (`gpt41nano`, `haiku35`, `Llama-3.3-70B` from the OpenLM Chatbot Arena mirror). These were not visible in the live arena.ai leaderboard view; flagged via `elo_source` in `model_capability.csv`. Sensitivity analyses with these ±50 ELO did not change the sign of any per-task effect but should be verified before publication.

3. **Family confounds tier.** 3 of 5 small-tier models are Anthropic; 6 of 7 OpenAI models span both flagship and small. Within-family generation deltas (Finding 3) are cleaner evidence for capability effects than cross-family tier averages.

4. **Committee's metric is on a different scale** than the [0,1] rates of other tasks — `initial_rating_bias` is an unbounded signed quantity. Direct comparison of regression coefficients across tasks should account for this. A robustness check using `manipulation_occurred` (always 0/1) would normalize but discards information.

5. **Cell sparsity in the tier-faceted response surface.** 15 models split across 3 tiers means averaging 3-7 models per tier × frame × incentive cell. Some cells (small-tier × selfish × high-incentive) have only 1-2 contributing models. Read the heatmaps as illustrative, not statistically powered, at the deepest level of disaggregation.

6. **All findings are post-hoc.** Capability was not pre-registered as an analysis axis. These results should be treated as exploratory and triangulated with the pre-registered axes (frame, incentive, difficulty) in `paper/cross_task/SUMMARY.md`.

## Reproduce

```bash
cd paper/capability_eval/scripts
python3 capability_analysis.py
python3 capability_regression.py
python3 capability_anova.py
python3 capability_response_surface.py
python3 capability_frontier_lift.py
python3 capability_clustering.py
```

All scripts read `paper/cross_task/results.csv` and `paper/cross_task/model_capability.csv`. Outputs go to `paper/capability_eval/{analysis,figures}/`.
