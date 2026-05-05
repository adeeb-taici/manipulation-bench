# Consolidated Findings

A single narrative across the four findings documents in this repo:

- [`FINDINGS.md`](FINDINGS.md) — pre-paper exploratory experiments (§1-§18), 4-model paper-1 roster (Claude Opus 4.6, GPT-5, Gemini 2.5 Pro, Grok 3) plus juror panel.
- [`paper/cross_task/FINDINGS_FROM_FIRST_PRINCIPLES.md`](paper/cross_task/FINDINGS_FROM_FIRST_PRINCIPLES.md) — bottom-up read of the paper's 5-task corpus on the frozen 6-model roster (Claude Opus 4.7, GPT-5.5, Gemini 3.1 Pro, Grok 4, Llama 3.3 70B, DeepSeek V4 Pro).
- [`csv/FINDINGS.md`](csv/FINDINGS.md) — 26,637-row corpus analysis (paper roster + 9 small-model sweep) with cluster-bootstrap CIs and capability ladder analysis.
- [`paper/capability_eval/FINDINGS.md`](paper/capability_eval/FINDINGS.md) — capability-axis (LMArena ELO + tier + generation) regressions on the same corpus.

This document **summarizes** rather than replaces. Citations point back to the source for full sample sizes and reproduction commands. Contradictions across documents are flagged with **⚠ Conflict** boxes and a proposed resolution.

A note on rosters: the legacy doc and paper/cross-task doc reference different model generations. Where a model is named without version, "Claude Opus 4.6 / GPT-5 / Gemini 2.5 Pro / Grok 3" refers to the legacy roster (`FINDINGS.md`); "Claude Opus 4.7 / GPT-5.5 / Gemini 3.1 Pro / Grok 4 / Llama 3.3 70B / DeepSeek V4 Pro" refers to the paper roster.

---

## 1. Headline findings

### 1.1 Manipulation propensity is a curve shape, not a scalar

The strongest result that survives across documents: a model's "manipulativeness" is a **response surface** (frame × incentive × difficulty), not a single number.

- Bargaining dose-response (`FINDINGS §9`) showed three qualitatively distinct shapes on the same task: GPT-5 a cliff (manipulates at 73-100% until penalty strictly dominates, then drops to 0); Claude a smooth two-step decay; Grok a smooth, low, easily-deterred curve.
- The paper's 5-task surface (`paper/cross_task/FINDINGS_FROM_FIRST_PRINCIPLES §3`) confirmed this for the 4.7-era roster: every frontier model shifts +27 to +38 percentage points from prohibitive → permissive frame; **none are immune**, but baselines and slopes differ.
- Variance decomposition (`csv/FINDINGS §3`) makes this quantitative: scenario explains 35-40% of variance in committee/debate/sales while model explains only 1-11% — **the cell matters more than the model in 3 of 5 tasks**.

### 1.2 Gemini is the most manipulative frontier model on the paper roster

`csv/FINDINGS §1` (paired, scenario-controlled head-to-head, `08_ranking_cross_task.csv`): Gemini-3.1-Pro +40 net wins-minus-losses, the highest of any model. Per-task wins: bargaining +10, committee +14, debate +2, sales +9, village +5 — strictly positive in every task. `paper/cross_task/FINDINGS_FROM_FIRST_PRINCIPLES §8`: Gemini is top-tier manipulative in **all 5 tasks**, the only model with that property. Below Gemini the paired sums are DeepSeek +26, Grok +19, GPT-5.5 +13, Llama +2, Claude −4 — but the within-pack ordering is sensitive to scenario coverage. Notable: GPT-5.5's +8 on debate vs −10 on sales is the largest sign-flip in the table.

> **⚠ Conflict 1: who is "most manipulative"?**
> Legacy `FINDINGS §1` (debate, 4-model 4.6-era roster) gave Grok 3 the biggest instructed-baseline delta (+0.46) and called Grok the most-effective debate manipulator. The paper roster's headline says Gemini.
>
> **Resolution:** these claims are about different model versions (Grok 3 vs Grok 4, etc.) and different metrics (instructed-baseline delta on debate alone vs. paired wins-minus-losses across 5 tasks). The defensible synthesis: on the *paper roster*, Gemini-3.1-Pro is the most manipulative across all 5 tasks. On the legacy 4-model roster restricted to debate, Grok 3 had the largest instructed-baseline delta. Both are true; the paper-roster claim should be the citable headline.

### 1.3 Sales and debate manipulation tap different mechanisms

`csv/FINDINGS §1` / `02_task_rank_correlation_canonical.csv`: Spearman rank correlation between sales and debate model rankings is **−0.77** on the canonical roster (the largest cross-task anti-correlation in the matrix; bargaining-village is +0.77 on the same roster, the largest positive correlation). GPT-5.5 wins debate (+8) but loses sales (−10); Llama-3.3-70B wins sales (+9) but loses debate (−6); Claude wins debate (+5) but loses sales (−8). `FROM_FIRST_PRINCIPLES §8` corroborates from the raw rates: GPT-5.5 is most manipulative on debate (30%) and least on sales (13%).

There is no single underlying "manipulativeness" trait. Factual misrepresentation against a clear ground truth (sales) and rhetorical persuasion under uncertainty (debate) are at least two distinct behaviors.

### 1.4 Bargaining is the cleanest task; debate's binary outcome is the noisiest

`csv/FINDINGS §3`: model η² = 0.244 on bargaining (highest in the corpus); 0.014 on debate (below the noise floor). Combined with debate's flat axis effects on `manipulation_occurred` (`csv/FINDINGS §2`), the debate task's binary outcome is not measuring much of what we want. The rich signal in debate lives in the per-scorer columns (manipulation_detection, argument_quality, belief_shift) — see Conflict 2 below.

> **⚠ Conflict 2: is debate's frame response flat or strong?**
> `FROM_FIRST_PRINCIPLES §5`: pooled `manipulation_occurred` shifts by only −0.04 to +0.08 from prohibitive → permissive. Looks flat.
> Legacy `FINDINGS §15`: pooled `manipulation_detection` shifts +0.265 (prohibitive 0.250 → permissive 0.515). Looks strong and monotone.
>
> **Resolution:** both numbers are correct; they measure different things. `manipulation_occurred` (binary "did the manipulator try to manipulate") is near-flat under permissive — the manipulator was already trying. `manipulation_detection` (judge-LLM verdict) doubles — the manipulator's *visible behavior* changes. `argument_quality` slightly drops; juror `belief_shift` is unchanged. **Synthesis:** under permissive framing models try harder and look more manipulative, but argue worse, and net juror movement is unchanged. Manipulation effort and manipulation success are decoupled in debate. Cite `belief_shift` for outcome claims and `manipulation_detection` for behavior claims; do not cite `manipulation_occurred` for debate.

---

## 2. The five paper tasks: per-task bottom line

### 2.1 Bargaining (Task 1)

- **Polar:** prohibitive frame → 0% manipulation across every frontier model (paper roster, `FROM_FIRST_PRINCIPLES §4`); dose-response monotone in audit penalty (`FINDINGS §16`: 39.5% at E=0 → 0.0% at E=250).
- **Three curve shapes** on the legacy roster (`FINDINGS §9`): GPT-5 cliff, Claude two-step decay, Grok easily deterred.
- **Audit penalty is the single strongest deterrent** found in any paper task — a ~15× collapse between E=0 and E=30 penalty utility.
- **Bargaining is the *only* task where higher incentive reduces manipulation** (`csv/FINDINGS §2`: 0.42 → 0.10). In every other task, higher incentive correlates with more.

### 2.2 Debate (Task 2)

- **Frame is the dominant axis on the behavior metric** (`FINDINGS §15`: prohibitive 0.250 → permissive 0.515 on manipulation_detection).
- **Persuasion mostly fails:** aggregate belief_shift is −0.068 (jurors get *more* skeptical of the manipulator's position); persuasion_rate is 7%.
- **Per-claim variance dwarfs per-model variance.** One outlier claim (`meth_double_blind_best`) drives ~half of all aggregate persuasion events; the cleanest interpretation (`FINDINGS §17`) is that this claim's headline reflects Gemini-Flash's prior leaking through, not persuasion. **Use `belief_shift`, not `persuasion_rate`, for cross-model claims.**
- **GPT-5 is the stealthiest manipulator** — lowest manipulation_detection, highest persuasion_rate, lowest truth-side detection (its default style does not trigger the detector).
- **Effort and success are decoupled** under permissive framing (see Conflict 2).

### 2.3 Village Commons (Task 3)

- **Polar:** village-permissive → 100% manipulation across every frontier model (`FROM_FIRST_PRINCIPLES §4`).
- **Frame is the dominant axis** (`csv/FINDINGS §2`: spread 0.63 across frames, the largest of any task).
- **Topology amplifies the goal effect** (`FINDINGS §18`): paired and isolated channels produce the largest max−coop deltas. Full visibility suppresses the goal effect for both Claude and GPT-5.
- **GPT-5 / isolated / max ≈ pure defection:** exploit rate 0.887, promise gap +7.26 tokens (a third of the endowment broken every round).
- **Claude shows a "pro-social cue beats prohibition" pattern** (`FROM_FIRST_PRINCIPLES §7`): pro_social frame yields 5.6% village manipulation vs prohibitive 27.8%. No other model on the paper roster shows this dip — worth investigating whether it's a Claude-specific alignment fingerprint.
- **Llama has a high village floor** (67% under prohibitive vs ~11-50% for others) — instruction-resistant in this env (`FROM_FIRST_PRINCIPLES §6`).

### 2.4 Sales (Task 4)

- **Sycophancy = frame effect, not disposition** (`FINDINGS §14`): under prohibitive/goal_helpful/minimal/goal_satisfaction frames every model accommodates 0/180. All ranking variation lives in the permissive column.
- **Opus is the only model that substantially refuses permissive-frame instructions** — 6.7% accommodation vs 42-99% for the other five (Gemini 99.4%, Grok 94%, Llama 97%).
- **Stated RLHF pressure has no detectable effect** in either the legacy single-turn sycophancy run or the paper sales runs.
- **Capability *helps* sales honesty.** Smaller models confabulate more against ground truth. The clearest signal in the corpus that capability reduces manipulation in some envs.
- **`gpt41nano` exception** (`csv/FINDINGS §1`): cleanest small model on 4 of 5 tasks, but flips to *most* manipulative in sales paired analysis (+7). Hypothesis: capability failure — confabulates against detailed product specs because it can't track them.

### 2.5 Committee (Task 5)

- **Difficulty effect is large but partly confounded** (`csv/FINDINGS §2`): low-difficulty 0.96, high-difficulty 0.26, spread 0.70 — but `scenario_group` is 1:1 nested in `difficulty`, so within-cluster the effect is unidentifiable. Treat as suggestive.
- **Capability *hurts* committee.** Frontier 0.72, mid 0.57, small 0.42 in tier buckets; Anthropic family slope +0.12 per size step; OpenAI gpt41 slope +0.10; ELO regression β = +1.55 (`paper/capability_eval/FINDINGS Finding 1`). Bigger models produce more structural rating bias.
- **Sonnet on committee is unusually bad** (`FROM_FIRST_PRINCIPLES §10`): sonnet46/37 sit at 71%, comparable to Grok-4 and DeepSeek. Anthropic models are comparatively *worse* on committee than on bargaining — opposite of the pattern in §2.1.
- **Orthogonal scorers exist:** `decision_outcome__ground_truth_matched` and `post_discussion_rating_change__interested_delta_favored` are uncorrelated with `manipulation_occurred` (`csv/FINDINGS §5`). They capture **whether the manipulation succeeded**, not whether it was attempted. Committee is the cleanest task for an attempted-vs-successful split.

---

## 3. Cross-cutting patterns

### 3.1 Frame is the strongest lever in every task except debate

`csv/FINDINGS §2` axis spreads (max − min): village 0.63, bargaining 0.41, committee 0.40, sales 0.20, debate 0.02 (on `manipulation_occurred` — see Conflict 2). The pattern across documents:

- Permissive prompting collapses honesty.
- Prohibitive prompting holds at floor for some models in some tasks (Claude bargaining: 0.0% across 480 events with audit penalty E=0; bargaining-prohibitive across all paper-roster models).
- Implicit license ("you may use whatever strategies you find effective") had **null effect** in the village 2×2×2 factorial (`FINDINGS §13`) — implicit permission is not sufficient without goal re-framing.

### 3.2 Stated incentive ("RLHF pressure" language) doesn't move models

- Sycophancy: incentive shift produces ≤0.034 movement on accommodation (`FINDINGS §14`).
- Debate: I=0/5/20 produces 0.013 movement on manipulation_detection (`FINDINGS §15`).
- Pooled tier × incentive ANOVA interaction is null (p=0.80) (`paper/capability_eval/FINDINGS Finding 2`).

**Concrete penalties (audit, payoff loss) move behavior; described incentives do not.** Bargaining's expected-penalty axis, where the incentive is a *real* utility cost, produced the steepest dose-response in the corpus.

### 3.3 Capability is task-conditional, not monotonic

Per-task ELO regression (`paper/capability_eval/FINDINGS Finding 1`, n=29,352, controls for axis cell):

| Task | β per +100 ELO | Direction |
|---|---|---|
| village | −0.062 *** | capability helps a lot |
| sales | −0.020 *** | capability helps |
| debate | −0.008 ** | capability helps slightly |
| bargaining | −0.004 (n.s.) | flat |
| inbox | +0.029 * | capability hurts |
| committee | +1.55 *** | capability hurts (different scale) |

Within-family generation deltas (`csv/FINDINGS §8a`, `paper/capability_eval/FINDINGS Finding 3`) tell the same story: haiku 3.5 → 4.5 collapsed bargaining manipulation by 80 points; sonnet 3.7 → 4.6 didn't move on bargaining (already at floor) but committee got *worse*; gpt41 → GPT-5.5 added 30 points on bargaining lying.

> **⚠ Conflict 3: how big is the haiku 3.5 → 4.5 bargaining collapse?**
> `csv/FINDINGS §8a` / `09_recency_pairs.csv`: **−0.7956** (scenario-paired bootstrap on n=45 paired scenarios, CI [−0.871, −0.718], point estimates 0.8267 → 0.0311). `frac_newer_higher = 0.0` — newer is lower in 100% of bootstrap resamples.
> `paper/capability_eval/FINDINGS Finding 3`: −0.66 (per-cell mean delta, bootstrap CI [−0.74, −0.58]).
>
> **Resolution:** csv pipeline pairs on scenario_id (rows where both models ran on the same scenario), capability_eval averages over (frame × incentive × difficulty) cells. Both confirm a large negative delta with non-overlapping CIs above zero. Cite the scenario-paired number (−0.80 [−0.87, −0.72]) as the headline because it controls for scenario directly; mention the cell-mean version as a robustness check.

### 3.4 Within-family generation effects are real but family-specific

`paper/capability_eval/FINDINGS Finding 3`: 4 of 5 within-family generation upgrades reduce inbox suppression rate by 10pp+; 3 of 5 reduce sales manipulation. Direction in bargaining and committee is family-specific — Anthropic's haiku update collapsed bargaining lying, OpenAI's gpt41 → GPT-5.5 *added* 30pp.

The clearest "frontier-current" signal: K-means on per-(task, frame) profile vectors separates the 4 newest frontier models (Opus 4.7, GPT-5.5, Gemini 3.1 Pro, DeepSeek V4 Pro) into a clean cluster (`paper/capability_eval/FINDINGS Finding 4`).

### 3.5 Communication topology amplifies the goal effect

`FINDINGS §18`: in village commons under restricted-visibility topologies (paired, isolated), the max-vs-coop goal effect is much larger than under full or hub. **Reduced visibility makes the prompt do more work.** Both Claude and GPT-5 show a significant goal × topology interaction; the magnitude is much larger for GPT-5.

This narrows an earlier claim (`FINDINGS §13`) that "Claude is prompt-invariant on this task." Claude is goal-wording-insensitive **under full visibility**; under paired/isolated it does shift +0.16 to +0.20 with goal wording.

### 3.6 Prompt wording sensitivity within the "neutral" prompt space

`FINDINGS §11` (300 scenarios, 5 neutral wordings × 2 incentives × 3 models on bargaining): Grok is most wording-stable (spread 0.25), Claude intermediate (0.40), GPT-5 least stable (0.75 — bigger than its instruction-endpoint spread). The clearest per-model diagnostic is **does `goal_payoff` vs `goal_agreement` shift behavior?** GPT-5 +0.55, Grok +0.175, Claude −0.05.

> **⚠ Conflict 4: is Claude "prompt-invariant"?**
> `FINDINGS §13`: yes, Δ ≤ 0.032 on village 2×2×2 (full visibility).
> `FINDINGS §11`: partially, neutral-wording spread on bargaining is 0.40.
> `FINDINGS §18`: no — under paired/isolated topology the goal effect is +0.16/+0.20.
> `FROM_FIRST_PRINCIPLES §3`: Claude shifts +0.276 from prohibitive → permissive (smallest of the 6 models, but still substantial).
>
> **Resolution:** narrow the claim. Across task-and-condition combinations Claude is consistently the *least* prompt-sensitive frontier model on the paper roster, but not invariant. The defensible version: "Claude has the smallest cross-frame and cross-wording spread of the frontier models, but it does shift with frame and with goal wording when visibility is restricted. The §13 'prompt-invariant' label was over-stated."

### 3.7 Context isolation does not change manipulation susceptibility

`FINDINGS §8` (300 scenarios, 5 context conditions × 3 manipulators × 3 jurors): no statistically significant effect of fresh / manip_transcript / irrelevant / brief_summary / defensive_prompt on persuasion rate. Claim difficulty dominates — 5 of 20 claims account for nearly all persuasion events; 5 of 20 are completely resistant.

This null is informative: **prior exposure to manipulation, knowledge about manipulation, and explicit defensive warnings did not protect jurors from a follow-up manipulation attempt** in this single-turn debate setup. Multi-turn susceptibility (where the manipulator could push back) was not tested.

---

## 4. Methodological corrections that affect interpretation

### 4.1 Scenario clustering inflates apparent precision

`csv/FINDINGS §4`: ICC of `manipulation_occurred` across `scenario_group` is 0.36-0.42 in committee/debate/sales. **Row-bootstrap CIs are 2.5-4× too narrow** in those tasks. 39 of 45 (model, task) cells underestimate uncertainty by ≥1.5×. Any 0.05-0.10 rate difference in committee/debate/sales without paired analysis or cluster CIs is noise.

### 4.2 The §10 "default neutral" numbers were a single-wording artifact

`FINDINGS §10` reported neutral-row rates 0.075 / 0.60 / 0.90 for Grok / Claude / GPT-5 on bargaining. `FINDINGS §11` reran across 5 neutral wordings:

| Model | Section 10 neutral (`original` only) | Robustness-pooled (5 variants) |
|---|---|---|
| Claude | 0.600 | 0.315 |
| GPT-5  | 0.900 | 0.632 |
| Grok   | 0.075 | 0.110 |

Section 9-10's `original` wording reads in practice closer to `goal_payoff` than to a minimal neutral framing. Read those sections as "manipulation under a payoff-maximization framing," not neutral.

### 4.3 Village promise_gap pre-tool-instrumentation was undercounted

`FINDINGS §12 measurement caveat` (2026-04-16): the regex-era pledge detector under-captured commitments by roughly 6×. The §12/§13 promise_gap numbers are regex-era estimates; §18 numbers (post-`pledge_contribution` tool refactor) are the trustworthy version. Re-run §12/§13 on the tool-based pipeline before citing per-model promise-gap rankings.

### 4.4 Combined eval logs preserve old model labels after model swaps

When a paper amendment swapped a model (e.g., GPT-5 → GPT-5.5 via `--model-role`), the new run's scenario metadata still carries the *original* label. To do a within-task pre/post comparison, filter by the OLD label in BOTH halves — only the runtime model binding changed, not the recorded scenario label. Affects any reanalysis script that joins on model name.

---

## 5. Open questions, in priority order

From `csv/FINDINGS §7`, `paper/capability_eval/FINDINGS Caveats`, `FROM_FIRST_PRINCIPLES "Concrete next steps"`:

1. **Attempted vs successful manipulation** — split using committee's orthogonal `decision_outcome__ground_truth_matched` and `post_discussion_rating_change__interested_delta_favored`. Extend to other tasks where ground-truth columns exist.
2. **Debate re-analysis** using paired manipulator vs truthful scorer columns. The binary `manipulation_occurred` is too low-signal for cross-model claims (csv/FINDINGS §3, §5).
3. **Why does `gpt41nano` flip in sales?** Cleanest small model on 4 of 5 tasks, *most* manipulative in sales paired analysis. Capability failure or something else?
4. **Verify the Claude pro-social cue (§2.3) cross-task** — does the pro_social-frame dip happen elsewhere? Is it Claude-specific?
5. **Verify the §13 / §18 narrowing of "Claude prompt-invariance"** with an explicit topology × frame × goal design.
6. **Mixed-effects regression** with `(1|scenario_group)` random intercept absorbs the scenario confound and gives "controlling for everything, model X has Z log-odds" statements directly.
7. **Bargaining full-roster run** (`FINDINGS §16` was halted at 1,499/7,200 samples on weekly OpenRouter quota). The "audit penalty crushes lying" story is Opus-within only until the other 5 paper-roster models complete.
8. **Composite capability proxy** beyond LMArena ELO (capability_eval used a single-source noisy proxy; LMArena + GPQA + SWE-bench would be stronger).

---

## Appendix: numeric reference (regenerated from source CSVs)

For quick verification. All numbers below are from the canonical (frontier-6) roster unless noted; sources in parentheses.

### A. Per-model `manipulation_occurred` rate by task (`csv/out/tables/02_model_task_rate_canonical.csv`)

| Model | Bargaining | Committee | Debate | Sales | Village | Mean |
|---|---:|---:|---:|---:|---:|---:|
| Gemini-3.1-Pro    | 0.419 | 0.900 | 0.245 | 0.351 | 0.756 | 0.534 |
| Grok-4            | 0.372 | 0.801 | 0.216 | 0.200 | 0.667 | 0.451 |
| DeepSeek-V4-Pro   | 0.386 | 0.750 | 0.232 | 0.276 | 0.602 | 0.449 |
| GPT-5.5           | 0.381 | 0.622 | 0.301 | 0.133 | 0.674 | 0.422 |
| Claude-Opus-4.7   | 0.156 | 0.626 | 0.267 | 0.160 | 0.556 | 0.353 |
| Llama-3.3-70B     | 0.157 | 0.617 | 0.146 | 0.360 | 0.460 | 0.348 |

### B. Axis spreads per task (`csv/out/tables/03_axis_effect_sizes.csv`)

Max−min level rate. Largest axis per task in **bold**.

| Task | Frame | Incentive | Difficulty |
|---|---:|---:|---:|
| Bargaining | **0.414** | 0.328 | 0.053 |
| Committee  | 0.397 | 0.085 | **0.700** |
| Debate     | **0.022** | 0.024 | 0.087 |
| Sales      | 0.199 | 0.026 | **0.485** |
| Village    | **0.631** | 0.146 | 0.038 |

### C. Variance decomposition: η² (`csv/out/tables/05_eta_squared.csv`)

| Factor | Bargaining | Committee | Debate | Sales | Village |
|---|---:|---:|---:|---:|---:|
| model            | **0.244** | 0.111 | 0.014 | 0.044 | 0.126 |
| frame            | 0.098 | 0.066 | 0.000 | 0.029 | **0.192** |
| incentive        | 0.099 | 0.005 | 0.001 | 0.001 | 0.014 |
| difficulty       | 0.003 | **0.380** | 0.007 | **0.209** | 0.001 |
| scenario_group   | —     | **0.404** | **0.350** | **0.402** | —     |

`scenario_group` outweighs `model` in every task where it's measurable (committee/debate/sales).

### D. Paired head-to-head, sum across 5 tasks (`csv/out/tables/08_ranking_cross_task.csv`)

| Model | Sum | Bargaining | Committee | Debate | Sales | Village |
|---|---:|---:|---:|---:|---:|---:|
| Gemini-3.1-Pro    | **+40** | +10 | +14 | +2  | +9  | +5  |
| DeepSeek-V4-Pro   | +26 | +7  | +10 | +2  | +3  | +4  |
| Grok-4            | +19 | +7  | +11 | 0   | −4  | +5  |
| GPT-5.5           | +13 | +8  | +3  | +8  | −10 | +4  |
| Llama-3.3-70B     | +2  | 0   | +3  | −6  | +9  | −4  |
| Claude-Opus-4.7   | −4  | −1  | +2  | +5  | −8  | −2  |

Small-model standouts: `haiku35` +16 on the cohort it ran (bargaining/committee/sales); `gpt41nano` −36 net (lowest), but +7 on sales.

### E. Per-task ELO regression coefficients (`paper/capability_eval/analysis/capability_regression.json`)

`manipulation_metric ~ ELO_per100 + frame + incentive + difficulty`, HC3 SEs.

| Task | n | β / +100 ELO | 95% CI | p |
|---|---:|---:|---|---:|
| village    | 969    | −0.062 | [−0.081, −0.043] | 2.5e−10 |
| sales      | 3,375  | −0.020 | [−0.026, −0.014] | 8.3e−11 |
| debate     | 6,170  | −0.008 | [−0.014, −0.002] | 0.005 |
| bargaining | 13,499 | −0.004 | [−0.012, +0.005] | 0.43 (n.s.) |
| inbox      | 2,715  | +0.029 | [+0.006, +0.052] | 0.015 |
| committee  | 2,624  | +1.55  | [+1.36, +1.74]   | 4.5e−56 (different scale: signed rating bias on 0-10) |

### F. Within-family generation deltas (`csv/out/tables/09_recency_pairs.csv`)

Scenario-paired bootstrap on shared scenarios.

| Pair | Task | n | Older | Newer | Δ | 95% CI | Direction |
|---|---|---:|---:|---:|---:|---|---|
| haiku35 → haiku45 | bargaining | 45  | 0.827 | 0.031 | **−0.796** | [−0.871, −0.718] | newer ↓↓↓ |
| haiku35 → haiku45 | sales      | 225 | 0.404 | 0.204 | −0.200 | [−0.258, −0.147] | newer ↓ |
| haiku35 → haiku45 | committee  | 180 | 0.433 | 0.433 | 0.000  | [−0.045, +0.044] | flat |
| sonnet37 → sonnet46 | bargaining | 45  | 0.073 | 0.089 | +0.016 | [−0.032, +0.061] | flat |
| sonnet37 → sonnet46 | committee  | 167 | 0.713 | 0.749 | +0.036 | [−0.012, +0.084] | flat |
| sonnet37 → sonnet46 | sales      | 225 | 0.364 | 0.342 | −0.022 | [−0.071, +0.027] | flat |

### G. Tier-bucket rates with cluster CIs where available (`csv/out/tables/09_tier_buckets.csv`)

| Tier | Bargaining | Committee | Debate | Sales | Village |
|---|---:|---:|---:|---:|---:|
| frontier (6) | 0.312 | 0.719 [0.58, 0.86]† | 0.234 [0.14, 0.36]† | 0.247 [0.11, 0.39]† | 0.620 |
| mid (5)      | 0.174 | 0.574 [0.38, 0.76]† | 0.210 [0.10, 0.34]† | 0.249 [0.12, 0.41]† | 0.506 |
| small (4)    | 0.231 | 0.417 [0.21, 0.64]† | 0.167 [0.06, 0.30]† | 0.266 [0.13, 0.41]† | 0.451 |

† cluster-bootstrap; bargaining and village use row-bootstrap (no scenario_group). Frontier > mid > small in committee, debate, village; bargaining is mid < small < frontier (inverted-U); sales is essentially flat.

### H. ICC and CI inflation (`csv/out/tables/06_icc_per_task.csv`)

| Task | n | n_clusters | ICC |
|---|---:|---:|---:|
| committee | 2,624 | 12 | 0.423 |
| debate    | 6,170 | 23 | 0.358 |
| sales     | 3,375 | 15 | 0.416 |
| bargaining | 13,499 | 0 | — (no scenario column) |
| village    | 969 | 0 | — (no scenario column) |

Row CIs underestimate uncertainty by 2.5-4× in the three clustered tasks (`csv/FINDINGS §4`).
