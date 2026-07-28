# Newer analyses — three statistical gaps from the prior synthesis

Three analyses requested to plug gaps identified during the cross-document review of the four prior findings files. All three run against `paper/cross_task/data/results.csv` (canonical frontier-6 roster: Claude Opus 4.7, GPT-5.5, Gemini 3.1 Pro, Grok 4, Llama 3.3 70B, DeepSeek V4 Pro). Scripts in `scripts/`, raw outputs in `out/`.

---

## 1. Mixed-effects regression with random intercept on scenario cluster

**Model:** `manipulation_occurred ~ C(model) + C(task) + C(frame) + C(incentive) + C(difficulty)` with random intercept on `cluster` (5,980 distinct clusters; falls back to scenario_id then per-row synthetic clusters for tasks without scenario IDs). Linear mixed model (LPM) — coefficients are percentage-point shifts. ML estimation, `powell` optimizer (lbfgs hit a singular matrix). n = 13,573.

**Why this matters:** the prior corpus relied on scenario-paired bootstrap to handle within-cluster dependence. That's conservative but can't give one coherent "controlling for everything, model X has Z log-odds" coefficient table. The mixed model absorbs the cluster confound and lets every fixed-effect coefficient be read directly.

**Fixed-effect headline (top 10 by |coef|):**

| Term | Coef (pp) | 95% CI | p |
|---|---|---|---|
| Task = committee (vs bargaining ref) | +0.407 | [+0.301, +0.512] | <1e-13 |
| Frame = permissive (vs prohibitive ref) | **+0.322** | [+0.302, +0.343] | <1e-200 |
| Task = village | +0.309 | [+0.273, +0.345] | <1e-62 |
| Frame = selfish | +0.258 | [+0.238, +0.278] | <1e-136 |
| **Model = Gemini-3.1-Pro** (vs Claude Opus 4.7 ref) | **+0.176** | [+0.154, +0.198] | <1e-54 |
| Frame = minimal | +0.165 | [+0.145, +0.186] | <1e-56 |
| Incentive = high | −0.149 | [−0.165, −0.133] | <1e-70 |
| Frame = pro_social | +0.134 | [+0.113, +0.154] | <1e-37 |
| Model = DeepSeek-V4-Pro | +0.122 | [+0.100, +0.144] | <1e-26 |
| Model = Grok-4 | +0.118 | [+0.096, +0.141] | <1e-25 |

Reference cell: Claude Opus 4.7 × bargaining × prohibitive × incentive=none × difficulty=low. Group (cluster) variance: 0.033.

**What this confirms vs the prior corpus:**

- **Frame is the dominant prompt lever, even after controlling for everything else.** Permissive vs prohibitive moves manipulation by +32.2 percentage points (CI [+30, +34]). This is consistent with §1.1 of the synthesis but tighter and now coefficient-form rather than spread-form.
- **Task is comparable to or larger than frame.** Switching from bargaining to committee adds +40.7 pp; switching to village adds +30.9 pp. This is the cleanest evidence to date for §1.3 ("task is a bigger lever than model"): even with model and axes controlled, task dummies dominate.
- **Concrete penalties beat described incentives, again.** Incentive = "high" subtracts −14.9 pp; moderate subtracts −6.5 pp. This is pooled across tasks, so the bargaining-only suppression (audit penalty) is mixing with the (essentially flat) other tasks. Within-task incentive coefficients would be sharper.
- **Model rankings now have a single global ordering** (Claude reference; lower is more honest):
  - Llama-3.3-70B ≈ Claude-Opus-4.7 (Llama +0.036 over Claude)
  - GPT-5.5 +0.091
  - Grok-4 +0.118
  - DeepSeek-V4-Pro +0.122
  - **Gemini-3.1-Pro +0.176** (the largest model dummy)
  - This matches the paired-bootstrap ordering (Gemini > DeepSeek > Grok > GPT > Llama > Claude) but quantifies the gaps in pp.
- **Difficulty is small but real.** Medium and high difficulty each add ~+6 pp over low, which is much smaller than the frame or task effects but not zero.

**What it changes:** the prior corpus had Claude as "mid-pack once paired" (−4 net wins-minus-losses) but the raw rate looked clean (mean 0.353). The mixed model agrees with the paired version: with cluster, axes, and task all controlled, **Claude Opus 4.7 is the lowest-coefficient model in the canonical roster** (it's the reference; every other canonical model has a positive dummy at p<0.002). The "scenario-coverage artifact" framing was correct — but once you control properly, Claude is not just mid-pack, it's at the bottom of the canonical roster on a per-cell basis.

**Caveats:**

- LPM (linear) on a binary outcome — coefficients are interpretable as pp shifts but predicted probabilities can fall outside [0,1] in extreme cells. A logistic mixed model (`pymer4`/R or PyMC) would tighten this.
- Bargaining and village have no scenario_id, so their "clusters" are per-row — effectively no clustering for those tasks. The cluster variance estimate (0.033) is dominated by committee/debate/sales.
- The random-effects covariance came back singular in the lbfgs run; powell converged but the warning suggests the cluster variance is on the boundary. The fixed-effect coefficients are stable across optimizers.

**Output files:** `out/01_mixed_effects_coefs.csv`, `out/01_mixed_effects_summary.txt`.

---

## 2. Task × model interaction test

**Test:** F-test between
- **M0:** `manipulation_occurred ~ C(model) + C(task)` (additive)
- **M1:** `manipulation_occurred ~ C(model) * C(task)` (with interaction)

Canonical roster only, n = 13,573.

**Result:**

| | R² | AIC |
|---|---|---|
| M0 (additive) | 0.103 | 16,514.9 |
| M1 (with interaction) | 0.142 | 15,970.1 |

| Test | df₁ | F | p |
|---|---|---|---|
| M1 vs M0 (interaction LRT) | 25 | **24.26** | **2.4 × 10⁻¹⁰⁹** |

Incremental R² from interaction: **+0.0385** (the interaction term explains an additional ~3.9% of variance beyond the additive main effects, on top of M0's 10.3%).

**What this confirms vs the prior corpus:** §1.3 of the synthesis claimed "task is a bigger lever than model" and "the most-manipulative model reshuffles by task" — both descriptive. This test gives the formal version: **the model × task interaction is real, large, and survives any reasonable multiple-testing threshold**. The single best summary of the data is *not* a model-rank-with-task-as-noise; the rankings genuinely differ across tasks.

**Where the additive model fails most** (top cells by |residual|, where residual = actual − M0 prediction):

| Model | Task | n | Actual | M0 predicted | Residual |
|---|---|---|---|---|---|
| **Llama-3.3-70B** | inbox | 180 | 0.678 | 0.261 | **+0.417** |
| **GPT-5.5** | inbox | 180 | 0.017 | 0.331 | **−0.314** |
| **Claude-Opus-4.7** | inbox | 180 | 0.011 | 0.228 | **−0.217** |
| Llama-3.3-70B | sales | 225 | 0.360 | 0.183 | +0.177 |
| Claude-Opus-4.7 | debate | 690 | 0.267 | 0.139 | +0.128 |
| GPT-5.5 | sales | 225 | 0.133 | 0.253 | −0.120 |
| GPT-5.5 | committee | 180 | 0.622 | 0.726 | −0.104 |
| Llama-3.3-70B | village | 87 | 0.460 | 0.557 | −0.097 |
| Gemini-3.1-Pro | committee | 180 | 0.900 | 0.807 | +0.093 |
| Llama-3.3-70B | bargaining | 900 | 0.157 | 0.248 | −0.092 |

**The single biggest source of interaction is inbox.** Llama suppresses inbox emails ~68% of the time when its overall and per-task baselines predict 26%; GPT-5 and Claude almost never suppress (1-2%) when predicted at 23-33%. Inbox alone is responsible for a disproportionate chunk of the interaction signal — sales and debate also contribute (Llama is the worst on sales at +0.18 over additive; Claude is worse on debate at +0.13) but inbox dominates.

**What it changes:** inbox is the single most important task to keep in any "is the model rank stable across tasks" conversation. It single-handedly inverts the ranking on a fairly large cohort. The §1.3 claim "task is bigger than model" is accurate but understated — it's not just that task contributes more variance than model; the *interaction between them* is itself large and significant.

**Output files:** `out/02_interaction_test.txt`, `out/02_cell_residuals.csv`.

---

## 3. Multiple-testing correction across the prior p-values

**Inputs:** all reported p-values from `capability_eval.md` (per-task ELO regressions, F1; tier × frame and tier × incentive ANOVAs, F2). 14 tests total. Other documents report descriptive statistics (η², spreads, correlations) without formal p-values, so they're not in this correction.

**Method:** Holm-Bonferroni and Benjamini-Hochberg FDR, both globally across all 14 tests and within-family (per-task ELO panel as one family; tier × frame ANOVA panel as another).

**Result summary:**

| | Significant @ 0.05 raw | Survives Holm global | Survives BH-FDR global | Survives Holm within-family | Survives BH within-family |
|---|---|---|---|---|---|
| Count (out of 14) | 10 | **9** | 10 | 10 | 10 |

**The one finding that drops under global Holm correction:**

| Family | Test | p_raw | p_holm_global | Survives? |
|---|---|---|---|---|
| ELO_per_task | **inbox β = +0.029** | 0.015 | 0.075 | **No (Holm global)** — but yes under BH (0.021) and yes within-family (0.030) |

Everything else survives every correction comfortably:
- All 4 highly significant ELO regressions (village β=−0.062, sales β=−0.020, committee β=+1.55, plus debate β=−0.008 at p=0.005) survive.
- All 5 highly significant tier × frame ANOVA cells (bargaining, village, committee, inbox, pooled) survive.
- The original null results (bargaining ELO p=0.43, sales tier × frame p=0.54, debate tier × frame p=0.98, tier × incentive p=0.80) remain non-significant — multiple-testing makes weak nulls weaker, not stronger.

**What this confirms vs the prior corpus:** the capability-axis study's main claims are robust to multiple-testing. The strongest of them (committee capability hurts; village/sales/debate capability helps; tier × frame interaction is real in 4 of 6 tasks) all survive Holm-global, the strictest correction.

**What it changes:** the **inbox ELO coefficient is the only finding that becomes ambiguous under correction.** The capability-axis study cited it as significant at 0.015. Globally Holm-corrected, it's 0.075 — fails the conventional cutoff. Under BH-FDR (which has more power) or within-family Holm (where you only correct across the 6 ELO regressions, not the full 14-test panel), it survives. Defensible synthesis: **the inbox capability-hurts result is real but weaker than the headline p-value suggests; do not cite it as "highly significant" in the paper without specifying the correction.**

**Caveats:**

- The reported p-values include several "<0.0001" entries that I've encoded as 0.0001 (the document doesn't give the exact tail). Real p's are smaller, so corrections are conservative — anything that survives at p_raw=1e-4 survives at the true value too.
- η² spreads, ICCs, Spearman ρ, and paired-bootstrap net wins were reported without formal p-values in the source documents and are not included here. A future pass should re-derive p's for those (e.g., permutation tests on Spearman ρ, bootstrap CIs that exclude 0 for paired wins).

**Output file:** `out/03_multiple_testing.csv`.

---

## 4. Per-(task, model) incentive=high forest plot

**Question this answers:** the §1 mixed model put `incentive=high` at −14.9 pp, pooled. Is that a unified cross-task phenomenon or an artifact of pooling tasks where the axis means different things?

**What was computed:** for every (task, model) cell in the canonical roster, the manipulation-rate delta
```
Δ = P(manipulation_occurred=1 | incentive=high) − P(manipulation_occurred=1 | incentive=none)
```
pooled over frame × difficulty. 95% CI from a 2,000-rep nonparametric bootstrap. The metric is the cross-task `manipulation_occurred` boolean each task's primary scorer emits, so all five tasks share a 0–1 axis (no standardization needed). 30 cells: 5 tasks × 6 models.

**Result by task:**

| Task | Direction | Δ range | Cells with CI excluding 0 |
|---|---|---|---|
| Bargaining | **Negative** (deters) | −0.04 to −0.79 | 6/6 |
| Debate | **Null** | −0.01 to +0.05 | 0/6 |
| Sales | **Null** | −0.01 to +0.11 | 0/6 |
| Village | **Positive** (more manipulation) | −0.05 to +0.40 | 3/6 |
| Committee | **Positive** (more manipulation) | +0.05 to +0.27 | 2/6 |

Bargaining is the **only** task where high incentive deters manipulation. In Village and Committee the same axis label produces the opposite-signed effect.

**Why the sign flips.** The mechanism is documented in [`incentive_traces.md`](incentive_traces.md): Bargaining's `incentive=high` is a numeric audit penalty that enters the agent's expected-value calculation (`max(payoff_truth, payoff_lie − 250)`), and models write the arithmetic out and conclude lying is dominated. The other four tasks operationalize "high incentive" as prompt language about stakes (stronger payoff framing, token-balance bonus emphasis) — sentences the agent reads but that don't change any term in its objective. When the only effect is making the goal feel more salient, agents pursue it harder, which in Village and Committee means *more* exploitation and rating bias.

So the axis label is doing three structurally different things across the response surface:
- **Bargaining**: structurally binding penalty → expected-value math changes → manipulation drops.
- **Debate, Sales**: stakes language with no decision-math footprint → null effect.
- **Village, Committee**: stakes language that strengthens the manipulable objective → manipulation rises.

The pooled −14.9 pp coefficient is the average of these three regimes weighted by sample size. It is not the slope of a unified phenomenon.

**Notable model-level points:**

- **Bargaining, Llama-3.3-70B** is the lone weak responder (Δ = −0.04, CI [−0.10, +0.02]). Its baseline overstatement at incentive=none (0.18) is also the lowest in the cohort, so there is less room to deter; the audit penalty might also fail to land if Llama doesn't reliably do the EV arithmetic the other models do.
- **Bargaining, DeepSeek-V4-Pro** is the largest deterrence (Δ = −0.76, baseline 0.76 → high 0.00). Consistent with the trace in `INCENTIVE_TRACES.md` where DeepSeek goes from a 6-orders-of-magnitude inflation race to committing truthfully.
- **Village, Grok-4** is the largest positive flip (Δ = +0.40). Under the propensity prompt, raising the stated bonus reads as "you should care more about the bonus," producing more free-riding.
- **Committee, GPT-5.5 and DeepSeek** show CI-significant positive effects (+0.27, +0.18). The interested party rates its favored candidate more aggressively when the prompt emphasizes the stakes — sentence-level priming on a goal the agent already has.

**What this changes:** the §1 mixed-effects table reports `incentive=high` as a single coefficient. The forest plot shows that coefficient should be replaced with a per-task breakdown, or at minimum surrounded by language distinguishing **binding incentives** (Bargaining: a cost in the agent's payoff math) from **stated stakes** (everywhere else: prompt language only). The two regimes have opposite-signed effects in the data; averaging them produces a number that is mechanically correct but conceptually misleading — it suggests a single phenomenon where the data show three. This sharpens the §4.6 "binding-vs-inert" framing in the paper from a categorical claim to one that is now quantified at the (task, model) cell level.

**Output files:** `out/incentive_forest.csv`, `figures/incentive_forest.png`, `figures/incentive_forest.pdf`.

---

## Reproduction

```bash
cd paper/cross_task/scripts/newer
python3 01_mixed_effects.py        # ~10s, writes out/01_*
python3 02_task_model_interaction.py  # ~3s, writes out/02_*
python3 03_multiple_testing.py     # <1s, writes out/03_*
python3 incentive_forest.py        # ~5s, writes out/incentive_forest.csv + figures/incentive_forest.{png,pdf}
```

Inputs: `paper/cross_task/data/results.csv` (29,352 rows; 13,573 after restricting to canonical frontier-6).

Dependencies: `pandas`, `numpy`, `statsmodels`, `scipy`, `matplotlib`. All present in the project's existing environment.
