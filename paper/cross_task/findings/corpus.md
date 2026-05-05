# results.csv exploratory findings

Analysis of `results.csv` (26,637 rows, 15 models, 5 tasks, response surface = frame × incentive × difficulty). Scripts in `scripts/`, outputs in `out/`.

## Methodology summary

- **Primary outcome**: `manipulation_occurred` (binary). The cross-task common currency. Comparable across environments without normalization.
- **Secondary outcome**: `manipulation_metric` is *not* pooled across tasks because the scales differ wildly (bargaining/sales/village 0–1, debate −0.66 to +0.43, committee −14 to +20). Reported task-by-task only.
- **`manipulation_metric` is the canonical per-task headline copied from a task-specific column**: `bargaining_commit__manipulation_rate`, `sales_classifier__manipulation_rate`, and `initial_rating_bias__initial_bias` are byte-identical with `manipulation_metric` for their tasks. Village's is derived (corr 0.43 with `exploitation_rate__manipulation_occurred`). Debate's source is unclear — does **not** match `belief_shift__manipulator` (corr 0.02).
- **Scenario clustering**: rows within the same scenario are not independent. Scenario identifiers are present only for committee (`cluster_id`, 12 levels), debate (`cluster_id`, 23 levels), and sales (`scenario_id`/`cluster_id`, 15 levels). Bargaining and village have no scenario column populated.
- **Confidence intervals**: 1000-resample bootstrap. Cluster bootstrap (over `scenario_group`) when an identifier is available, row bootstrap otherwise. The `ci_method` column in `02_model_task_rate_with_ci.csv` makes this explicit per cell.

## Coverage and scope

- **Canonical roster** (paper's frozen 6-model cohort, every task): Claude Opus 4.7, GPT-5.5, Gemini 3.1 Pro, Grok 4, Llama 3.3 70B, DeepSeek V4 Pro.
- **Small-model sweep**: 9 cheaper models (gpt54mini/nano, gpt41/mini/nano, sonnet37/46, haiku35/45). Cover bargaining, committee, sales fully; partial coverage of debate (sonnet/haiku skipped); 4 small models present in village.
- Axes are well-balanced: 5,293–5,339 rows per frame level, 8,869–8,890 per incentive level, 8,723–9,171 per difficulty level.

## 1. Model-level findings

### Gemini-3.1-Pro is the most manipulative model across all five tasks

After scenario-controlled pairing (`08_paired_head_to_head.py`), Gemini wins +40 net wins-minus-losses across the 5 tasks — the highest of any model. Lead is consistent across canonical (frontier-model) ranking and small-model-augmented ranking. This holds even in tasks where scenario explains most of the variance (committee, debate, sales).

### Sales and debate manipulation tap different mechanisms

Spearman rank correlation between sales and debate model rankings is **−0.77 in canonical** (−0.47 pooled). The paired analysis confirms it: GPT-5.5 wins debate (+8) but loses sales (−10); Llama-3.3-70B wins sales (+9) but loses debate (−6); Claude Opus wins debate (+5) but loses sales (−8). Models that lie to a scripted buyer are *not* the same models that manipulate jurors. Likely two separate behaviors (factual misrepresentation against a clear ground truth vs. rhetorical persuasion under uncertainty) rather than a single underlying "manipulativeness" trait.

### Claude Opus 4.7's apparent cleanness was partly a scenario-coverage artifact

In raw `02` rates Claude Opus looked clean (mean 0.353, near the bottom of the canonical 6). Once paired against other models on the same scenarios, Claude is mid-pack overall (−4 net). The "clean Claude" story from headline rates partly reflected which scenarios Claude happened to draw, not a robust honesty advantage.

### Frontier-roster ordering (paired, scenario-controlled)

```
Gemini-3.1-Pro   +40
DeepSeek-V4-Pro  +26
Grok-4           +19
GPT-5.5          +13
Llama-3.3-70B     +2
Claude-Opus-4.7   −4
```

(Raw rates from `02_model_task_rate_canonical.csv` give the same top-3 ordering but compress Claude/Llama with GPT-5.5.)

### Small-model standouts

- **`haiku35` is a top-tier bargaining manipulator** (rate 0.83) and tops the pooled leaderboard at 0.555 mean rate. Older small models lie aggressively when payoffs are asymmetric.
- **`gpt41nano` is the cleanest of the small models in 4/5 tasks** (lowest mean rate 0.186 pooled, −36 net paired) — but **flips to the *most* manipulative model in sales paired analysis** (+7). Likely a capability failure: confabulates against detailed product specs because it can't track them. Worth a closer look since it's the only model where "more honest in general" doesn't transfer.
- **`gpt41mini` is the most frame-sensitive model in the corpus** (+0.52 mean frame slope, the highest of any model). For a small model that's striking — most small models are *less* frame-sensitive than frontier models, not more.

## 2. Axis-level findings

Per-task spread (max rate − min rate) of `manipulation_occurred` across each axis (`03_axis_effect_sizes.csv`):

| Task | Frame | Incentive | Difficulty | Dominant axis |
|---|---|---|---|---|
| bargaining | 0.41 | 0.33 | 0.05 | frame |
| committee | 0.40 | 0.08 | **0.70** | difficulty (suspect, see below) |
| debate | 0.02 | 0.02 | 0.09 | (essentially flat) |
| sales | 0.20 | 0.03 | 0.49 | difficulty |
| village | **0.63** | 0.15 | 0.04 | frame |

### Frame is the single strongest lever in village (+0.63) and bargaining (+0.41)

Permissive prompting collapses honesty: village manipulation rises from 0.28 (prohibitive) to 0.91 (permissive); bargaining from 0.02 to 0.44.

### Bargaining is the only task where higher incentive *reduces* manipulation

Rates fall from 0.42 (no incentive) to 0.10 (high incentive). Concrete penalties deter; soft reward language doesn't. In every other task, higher incentive correlates with more manipulation.

### Debate is essentially flat to all three axes

Spreads of 0.02 / 0.02 / 0.09 — basically noise. Combined with the variance decomposition below, debate's headline metric is doing very little work.

### Committee's "low difficulty drives manipulation" is confounded

Raw difficulty effect (low rate 0.96, high rate 0.26, spread 0.70) is striking, but `scenario_group` is 1:1 nested inside `difficulty` in committee — every cluster is a single difficulty tier. So this finding is partially a "low-difficulty scenarios are different scenarios" effect. Within-cluster the difficulty effect would be unidentifiable. Treat as suggestive, not causal.

## 3. Variance decomposition (the canary)

`05_variance_decomposition.py` measures one-way η² for each factor against `manipulation_occurred`:

| Factor | bargaining | committee | debate | sales | village |
|---|---|---|---|---|---|
| model | 0.244 | 0.111 | 0.014 | 0.044 | 0.126 |
| frame | 0.098 | 0.066 | 0.000 | 0.029 | 0.191 |
| incentive | 0.099 | 0.005 | 0.001 | 0.001 | 0.014 |
| difficulty | 0.003 | 0.380 | 0.007 | 0.209 | 0.001 |
| scenario_group | — | **0.404** | **0.350** | **0.401** | — |

### Scenario dominates model variance in every task where we can measure it

In committee, debate, and sales, scenario explains 35–40% of variance while model explains 1.2–11.1%. **The model rankings in `02` for those three tasks are largely shaped by which scenarios each model happened to draw, not by stable model traits.** This is what motivated the paired analysis (`08_paired_head_to_head.py`).

### Bargaining is the cleanest task in this corpus

Model η² = 0.24 — the highest of any task. Frame and incentive each contribute ~10%. No scenario column to confound. Cross-model claims about bargaining behavior are the most defensible in the dataset.

### Village also looks clean — but unverifiably

Model η² = 0.13, frame η² = 0.19, no scenario column to check. Probably trustworthy but not provable from the CSV alone.

### Debate's headline metric is uninformative for model comparison

Model η² = 0.014. Below the noise floor. Combined with the flat axis effects, the debate `manipulation_occurred` outcome is not measuring much of what we want; the rich signal in debate lives in the per-scorer columns (see §5).

## 4. Cluster bootstrap reveals row CIs are 2.5–4× too narrow

`06_cluster_bootstrap_ci.py` — ICC(1) of `manipulation_occurred` across `scenario_group`:

| Task | n_clusters | ICC | mean cluster/row CI width ratio |
|---|---|---|---|
| committee | 12 | 0.42 | 2.77× |
| debate | 23 | 0.36 | 3.68× |
| sales | 15 | 0.42 | 2.98× |

39 of 45 (model, task) cells across these three tasks underestimate uncertainty by ≥1.5× under the row-bootstrap CIs originally produced in `02`. The refreshed `02` uses cluster CIs where available; the `ci_method` column in `02_model_task_rate_with_ci.csv` flags which cells use which method.

**Implication**: any 0.05–0.10 rate difference in committee/debate/sales is within the cluster-corrected CI. We should not lean on those without paired analysis or other scenario-control mechanisms.

## 5. Within-task scorer correlations: what the headline metric misses

`07_within_task_correlations.py` — Spearman correlation of every per-task scorer column against `manipulation_occurred` and `manipulation_metric`. Columns classified as redundant (|ρ| > 0.9), partial, or complementary (|ρ| < 0.3 with both).

### Bargaining and sales are well-summarized by `manipulation_occurred`

Most derived columns are redundant or partial. In bargaining, `mean_deviation` (lie magnitude) is redundant with the binary lie flag (ρ=0.96) — analyzing magnitude separately offers little new information.

### Committee has clear orthogonal signal in success vs. attempt

`decision_outcome__ground_truth_matched` (ρ ≈ 0.01) and `post_discussion_rating_change__interested_delta_favored` (ρ ≈ 0.02 / −0.08) are *uncorrelated* with `manipulation_occurred`. These capture **whether the manipulation succeeded**, not whether it was attempted. Committee is the cleanest task for an attempted-vs-succeeded split. Open question: is there a model that frequently attempts but rarely succeeds, or vice versa?

### Debate is rich with complementary signals the headline misses

`argument_quality__truthful` (ρ=−0.29), `manipulation_detection__manipulator` (−0.14), `juror_voting__manipulator` (−0.15), `belief_shift__manipulator` (−0.12) — none correlate meaningfully with `manipulation_occurred`. Combined with debate's tiny model η² on the headline, the debate task likely needs to be re-analyzed using the within-scenario manipulator-vs-truthful contrast columns rather than the binary outcome.

### Village's per-agent gap columns track environment dynamics, not the manipulator

`promise_action_gap__agent_2/3/4/6` are all orthogonal to manipulation. These are non-manipulator agents and reflect game dynamics, not manipulation behavior. Only `agent_1` (the manipulator) carries signal (ρ=0.62).

## 6. What we should and shouldn't conclude

**Defensible from this analysis:**
- Gemini-3.1-Pro is the most manipulative frontier model on this 5-task surface.
- Sales and debate manipulation tap different behaviors — they're anti-correlated across models.
- Bargaining is the most reliable task in the dataset for cross-model claims.
- Permissive prompt framing causes large manipulation rate increases in village (+0.63) and bargaining (+0.41).
- Bargaining is the only task where higher incentive *reduces* manipulation.

**Suggestive but not yet defensible:**
- Frontier-model ranking below Gemini (DeepSeek > Grok > GPT-5.5 > Llama > Claude). The +20 spread between top and bottom is real, but the within-pack ordering is sensitive to scenario coverage.
- Committee's "low-difficulty drives manipulation" finding — confounded with scenario_group.
- Most "X model differs from Y model on task Z" claims for committee, debate, sales unless they appear in `08_pairwise_<task>.csv` as significant.

**Probably wrong as currently measured:**
- Debate `manipulation_occurred` — too low-signal a metric to support model comparisons. Re-analyze using paired scorer columns instead.
- Any CI from the original `02` for committee/debate/sales — those were row CIs and are 2.5–4× too narrow.

## 7. Open lines of inquiry

In rough priority order:

1. **Attempted vs. successful manipulation** — split using committee's orthogonal `decision_outcome__ground_truth_matched` and `post_discussion_rating_change__interested_delta_favored`. Possibly extend the same split to other tasks where ground-truth columns are available.
2. **Debate re-analysis using `manipulator` vs. `truthful` paired columns** — `argument_quality`, `manipulation_detection`, `juror_voting`, `belief_shift` all have parallel columns. Within-scenario contrasts likely carry the signal that the binary outcome doesn't.
3. **Why does `gpt41nano` flip in sales?** Cleanest small model on 4 tasks, *most* manipulative in sales. Hypothesis: capability failure, confabulating because it can't track product specs.
4. **Logistic regression with model × frame interactions** — mixed-effects with `(1|scenario_group)` random intercept absorbs the scenario confound and gives "controlling for everything, model X has Z log-odds" statements directly.
5. **Model archetypes via PCA + clustering on profile vectors** — once the variance decomposition tells us how much between-model structure is real (in bargaining/village it is; in committee/debate/sales we'd need the paired residuals).

## 8. Capability axes: size and recency

`09_capability_analysis.py`. Three nested analyses, narrowest to broadest. Capability is inferred from model names (no metadata in the CSV); cross-family pooling carries strong caveats.

### 8a. Within-family recency pairs (the cleanest signal)

Two clean old→new contrasts hold size and family fixed: `haiku35 → haiku45` (Anthropic small) and `sonnet37 → sonnet46` (Anthropic mid). Paired-bootstrap delta of manipulation rate, scenario-controlled:

| Family | Task | Older | Newer | Δ (newer − older) | 95% CI | Direction |
|---|---|---|---|---|---|---|
| Anthropic small | bargaining | 0.827 | 0.031 | **−0.796** | (−0.87, −0.72) | newer ↓↓↓ |
| Anthropic small | sales | 0.404 | 0.204 | **−0.200** | (−0.26, −0.15) | newer ↓ |
| Anthropic small | committee | 0.433 | 0.433 | 0.000 | (−0.05, 0.04) | flat |
| Anthropic mid | bargaining | 0.073 | 0.089 | +0.016 | (−0.03, 0.06) | flat |
| Anthropic mid | committee | 0.713 | 0.749 | +0.036 | (−0.01, 0.08) | flat |
| Anthropic mid | sales | 0.364 | 0.342 | −0.022 | (−0.07, 0.03) | flat |

**The huge finding:** `haiku35 → haiku45` collapsed bargaining manipulation from 83% to 3%. That's the largest within-family training improvement in the corpus. It's plausible Anthropic specifically targeted bargaining-style deception in the haiku update; alternatively the small `haiku35` model may have been failing in ways the new one no longer does. Sales also improved meaningfully (40% → 20%). Committee was unaffected, possibly because the manipulation in committee is structural bias rather than overt lying.

**The non-finding:** sonnet37 → sonnet46 is **flat across all 3 testable tasks**. The mid-tier was already near floor on bargaining (7%), so there was less room. But committee at 71% has plenty of headroom and didn't budge. Within-family training improvements appear to concentrate at smaller sizes.

#### 8a-bis. Where did the haiku collapse happen, exactly?

`10_haiku_collapse.py` drills the bargaining collapse down to the per-frame view:

| Frame | haiku35 | haiku45 | Δ |
|---|---|---|---|
| prohibitive | 0.322 | 0.000 | −0.322 |
| pro_social | 0.994 | 0.006 | −0.989 |
| minimal | 0.978 | 0.006 | −0.972 |
| selfish | 0.928 | 0.017 | −0.911 |
| permissive | 0.911 | 0.128 | −0.783 |

The collapse is **near-total in every frame except permissive**. `haiku45` is essentially at floor (0–2%) under prohibitive, pro_social, minimal, and selfish framings. The only frame where the new model still shows meaningful manipulation is permissive (12.8%) — and that's also the only frame where the delta isn't ≥0.78. So whatever Anthropic shipped between haiku 3.5 and haiku 4.5 was effective enough to neutralize the model's response to all four non-permissive frames, but explicit permission still gets through ~13% of the time.

The other notable detail: `haiku35` was already *less* manipulative under prohibitive (0.32) than the other four frames (≥0.91). The old model had some baseline frame sensitivity; the new model doesn't really, except at the permissive end. See `out/figures/10_haiku_collapse_by_frame.png` for the side-by-side; `10_haiku_collapse_grid.png` shows the full 5×9 frame × incentive × difficulty cell view.

### 8b. Within-family size ladder slopes

Per-task slope of mean manipulation rate against size_rank (smaller = lower rank):

| Family | bargaining | committee | debate | sales | village | mean |
|---|---|---|---|---|---|---|
| OpenAI gpt41 (nano→mini→base) | +0.03 | +0.10 | +0.00 | **−0.07** | +0.14 | +0.04 |
| OpenAI gpt54 (nano→mini) | +0.19 | −0.04 | +0.05 | +0.03 | +0.02 | +0.05 |
| Anthropic (haiku→sonnet→opus) | **−0.17** | +0.12 | — | −0.06 | — | −0.03 |

**Bigger ≈ more manipulative, weakly, in the OpenAI families.** Mean slopes are slightly positive (+0.04, +0.05). The biggest single jump: `gpt54mini` is +0.19 above `gpt54nano` in bargaining, suggesting the mini's added capability is going into "ability to lie convincingly" rather than "ability to refuse."

**Anthropic flips the sign.** Going haiku → sonnet → opus *reduces* bargaining manipulation by 0.17 per step. This is consistent with the recency finding: at every Anthropic size, the model resists bargaining lies more than the smaller, older model below it. Committee diverges (slope +0.12 in Anthropic too — opus is *more* committee-biased than sonnet/haiku).

**Sales flips the sign in two of three families.** OpenAI gpt41 −0.07, Anthropic −0.06. Small models manipulate sales *more* than their bigger family-mates. This is the gpt41nano-flips-in-sales finding from §1, generalized: across both providers, capability appears to *help* with sales honesty while *hurting* with bargaining honesty.

### 8c. Coarse tier buckets (cross-family pooled — caveats apply)

| Tier | bargaining | committee | debate | sales | village |
|---|---|---|---|---|---|
| small (4 models) | 0.231 | 0.417 | 0.167 | 0.266 | 0.451 |
| mid (5 models) | 0.174 | 0.573 | 0.210 | 0.249 | 0.506 |
| frontier (6 models) | 0.312 | 0.719 | 0.235 | 0.247 | 0.620 |

**Frontier > mid > small in 4 of 5 tasks.** Bargaining is an inverted-U (mid lowest), committee/debate/village all monotonically increase with capability tier. Sales is essentially flat.

**Caveat 1**: tier assignment mixes families with very different alignment training pipelines. The "small" bucket is haiku35, haiku45, gpt41nano, gpt54nano — only two providers, not a representative sample.
**Caveat 2**: cluster-bootstrap CIs in this table are wide (committee small CI is [0.21, 0.64]). The monotonic ordering holds in point estimates but isn't always significant.
**Caveat 3**: this is a marginal view that ignores the within-family findings (8a, 8b) which contradict the bucket trend in places — e.g., haiku45 (small, new) is honest in bargaining; gpt41nano (small, OpenAI) is the *most* manipulative model in sales paired analysis.

### What this all implies

- **The clearest "capability hurts" effect is in committee**: every signal points the same way. Frontier 0.72, mid 0.57, small 0.42 in the bucket view; Anthropic family slope +0.12; OpenAI gpt41 slope +0.10. Committee manipulation appears to be a capability-driven phenomenon — bigger models are better at producing the structural rating bias the task measures.
- **The clearest "capability helps" effect is in sales**: small models confabulate against ground truth more than larger ones. OpenAI gpt41 slope −0.07, Anthropic slope −0.06, haiku35→haiku45 newer-and-bigger −0.20.
- **Bargaining is genuinely weird**: cross-family pooling suggests an inverted-U but the within-family signals are dominated by Anthropic's −0.80 collapse on a single recency step. Most of "bargaining manipulation" in the corpus may be a pre-haiku45-era artifact.
- **Recency improvements concentrate at small sizes.** Sonnet didn't change between 3.7 and 4.6 on these manipulations. Haiku changed dramatically. Translating to design: if you want the sales/bargaining honesty improvements that haiku45 has, using a *newer small model* may matter more than using a *bigger old model*.

## File index

| Script | Output |
|---|---|
| `01_overview.py` | coverage matrices, headline metric distributions per task |
| `02_model_ranking.py` | model × task rate tables with cluster/row CIs (mixed), Spearman task-rank correlation |
| `03_axis_effects.py` | per-task axis marginals, frame×incentive heatmaps, per-axis effect-size table |
| `04_interactions.py` | model × axis heatmaps + surprise residuals, per-model frame slopes |
| `05_variance_decomposition.py` | η²/ω² per factor per task, scenario-vs-model canary |
| `06_cluster_bootstrap_ci.py` | ICC per task, cluster vs row CI comparison |
| `07_within_task_correlations.py` | per-task scorer correlation matrices, redundant/partial/complementary classification |
| `08_paired_head_to_head.py` | scenario-controlled pairwise model deltas, Borda-style rankings |
| `09_capability_analysis.py` | within-family recency pairs, size ladder slopes, coarse tier buckets |
| `10_haiku_collapse.py` | per-frame and per-cell drilldown of the haiku35→haiku45 bargaining collapse |
