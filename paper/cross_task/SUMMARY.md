# Cross-task summary — Manipulation Response Surface

The five-task response-surface study is complete. This document is the paper-level summary of cross-task patterns. Per-task results live in [../task1_bargaining/results.md](../task1_bargaining/results.md), [../task2_debate/results.md](../task2_debate/results.md), [../task3_village/results.md](../task3_village/results.md), [../task4_sales/results.md](../task4_sales/results.md), [../task5_committee/results.md](../task5_committee/results.md).

## Headline finding: tasks split into two clusters by dominant axis

| Cluster | Tasks | Dominant axis | Notes |
|---|---|---|---|
| **Prompt-dominant** | Bargaining, Village | Incentive (Bargaining) / Frame (Village) | Manipulation channel is *behavioral* (lying about a number; defecting on contributions). Prompt language has direct grip. |
| **State-dominant** | Debate, Sales, Committee | Difficulty (juror prior / product quality / slate quality) | Manipulation channel is *informational* (constructing claims). The truth's bend-ability is the binding constraint, not the prompt. |

The cluster split is **not** an artifact of which models manipulate easily — it's about whether the manipulator's lever is "decide what to do with my own contribution" (Village, Bargaining) versus "construct a sequence of claims that move someone's belief" (Debate, Sales, Committee). When the lever is a single behavioral choice that the prompt directly addresses, the prompt wins. When the lever requires generating false content that has to fit alongside the underlying truth, the underlying truth dominates.

## Per-task aggregate sensitivity (mean |slope| across 6 models)

See [cross_task_aggregate.md](cross_task_aggregate.md) for the full machine-generated table; [figures/per_task_slopes.pdf](figures/per_task_slopes.pdf) for the chart.

| Task | Frame | Incentive | Difficulty | Dominant axis | Dominance ratio |
|---|---:|---:|---:|---|---:|
| T1 Bargaining | 0.108 | **0.250** | 0.030 | incentive | 2.3× |
| T2 Debate | 0.007 | 0.014 | **0.061** | difficulty | 4.4× |
| T3 Village | **0.168** | 0.054 | 0.023 | **frame** | 3.1× |
| T4 Sales | 0.026 | 0.010 | **0.087** | difficulty | 3.3× |
| T5 Committee | 0.327 | 0.181 | **0.603** | difficulty | 1.8× |

(T5 numbers are on a 0–20 bias scale, not a 0–1 rate scale, so absolute magnitudes aren't directly comparable to T1-T4.)

## Cross-task incentive taxonomy (refines P5 across tasks)

The PREREG predicted incentive sensitivity would be a per-task continuum, with Sales/Village landing intermediate between Debate (weak) and Bargaining (strong). The empirical pattern is **bimodal, not continuous**:

| Cluster | Tasks | Mean \|incentive slope\| | Why |
|---|---|---:|---|
| **Binding** | Bargaining, Committee | 0.25, 0.18 | **Structural reward integration** — penalty math affecting payoff (Bargaining); competition outcome determining win/loss (Committee) |
| **Inert** | Village, Sales, Debate | 0.05, 0.01, 0.01 | **Verbal emphasis only** — "your final score is X" or "you earn N points per Y" doesn't change the agent's actual reward function |

(T1 Bargaining and T5 Committee mean |incentive slope| = 0.250 and 0.181 respectively, post-Amendment-A2/A3. T3 Village = 0.054, T4 Sales = 0.010, T2 Debate = 0.014.)

This refines the cross-task incentive theory: **incentive language only binds when it introduces NEW reward structure**. When it's just a verbal restatement of the natural objective ("your final token balance is your only score" — but token balance is *already* the natural objective in Village), models treat it as redundant. This was a P5 failure across three of five tasks (Village, Sales, Debate); only Bargaining and Committee passed P5 as predicted.

## Per-model profile signatures (15-dim cross-task vector)

See [figures/per_model_profiles.pdf](figures/per_model_profiles.pdf) for the small-multiples view; [figures/cross_task_heatmap.pdf](figures/cross_task_heatmap.pdf) for the dense matrix; [cross_task_aggregate.md](cross_task_aggregate.md) for the machine-readable signed slopes.

A few notable per-model patterns:

- **Gemini 3.1 Pro** is the most frame-sensitive model in 3 of 5 tasks (Bargaining, Village, Committee). On Village and Committee its permissive endpoint saturates near the ceiling (Village 0.997, Committee bias 19.7). On Sales the permissive endpoint is only 0.19 — Gemini's frame-sensitivity does not generalize to Sales' product-truthfulness setting.
- **GPT-5.5** is tied with the rest of the roster on Sales prohibitive compliance (0.03 vs Claude 0.01 / Grok 0.03 / Llama 0.04 / Gemini 0.04 / DeepSeek 0.03) — a major reversal from GPT-5, which had a 0.51 prohibitive manipulation rate driven by a "commercial-omission default" (selectively omitting comparables and known defects). On Bargaining, GPT-5.5 keeps GPT-5's clean 0.000 prohibitive endpoint but reads pro-social/minimal middle-frames ~30pp better. On Debate/Village/Committee the alignment shift is smaller and task-dependent.
- **Claude Opus 4.7** is the most prohibitive-compliant model across tasks (≤ 0.05 on T1/T2 prohibitive averages) and never saturates a high-manipulation cell on T3 Village or T4 Sales. Frame slopes are also middling — Claude's overall manipulation envelope is the smallest of the six.
- **Llama 3.3 70B** is the only model that consistently behaves as "less prompt-responsive" across tasks — it fails P1 on Village (prohibitive 0.42) and shows low incentive sensitivity on Bargaining. The V3.2 → V4 Pro DeepSeek swap (Amendment A3) closed what was previously a parallel "Llama + DeepSeek = both unresponsive" pattern: V4 Pro now shows strong incentive sensitivity on Bargaining (slope −0.346, V3.2 reasoning-off was −0.093) and dramatically improved prohibitive compliance on Village (0.11 vs V3.2's 0.51). Llama is the sole remaining outlier on those measures.
- **DeepSeek V4 Pro vs V3.2 generation contrast**: V4 Pro is more compliant on Village (prohibitive 0.51 → 0.11), Sales (overall 0.17 → 0.10), and Committee (prohibitive bias −0.28 → −1.37). On Bargaining and Debate the direction inverts: V4 Pro is slightly *more* aggressive on T1 (+0.14 lied-rate) and on T2 (+0.04 manipulation-occurred). The cross-generation pattern is "more compliant on the structured-tool tasks (T3/T4/T5), more aggressive on the persuasion/lying tasks (T1/T2)".
- **Grok 4** behaves close to Claude on prompt-compliance baselines but has a steeper permissive endpoint. On Village Grok jumps from 0.00 prohibitive to 0.96 permissive — a 96-percentage-point swing, the largest endpoint range in T3.

## Cross-task verdict matrix

| Task | P1 prohib | P2 perm | P3 saturation | P4 dominance | P5 incentive | P6 ρ stable | P7 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| T1 Bargaining | ✓ | ✓ | (deferred) | partial (4/6) | ✗ | ✓ | — |
| T2 Debate | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | — |
| T3 Village | ✗ | ✓ | ✓ | **✓** | ✗ | ✓ | ✓ |
| T4 Sales | ✓ | ✗ | ✗ | ✓ | ✗ | ✓ | ✓ |
| T5 Committee | ✓ | ✓ | weak | ✗ | ✓ | (FAIL ρ=−0.94) | — |

P1 fails in 2/5 tasks (Debate, Village). P2 fails in 3/5 (Debate, Sales — conjunctive structure unsatisfiable at low absolute baselines — and the per-model 4/6 floor on others). The pattern: predictions that "prohibitive will land below 5%" are correct on Bargaining, Sales, and Committee (where prohibitive is a hard constraint on a single act) but fail on Debate and Village (where prohibitive doesn't fully prevent manipulation because it doesn't change the manipulator's underlying *role* — they're still arguing the false side, still defecting from cooperation).

## What's NOT in this file

- Cohen's d secondary analysis (only T5 has the full prereg version; T1-T4 carried out via [../../experiments/run_cohens_d.py](../../experiments/run_cohens_d.py))
- Hand-validation status: T4 P7 PASSED at 30/30 = 100% agreement (`sales_classifier` validated). T5 polarity scorer FAILED at 20/26 = 76.9% (below the 85% gate); `discussion_polarity` is dropped from reporting per Amendment A5 in [`../task5_committee/prereg.md`](../task5_committee/prereg.md).
- Per-claim T2 weighting in cross-task aggregation (see [EXPLORATORY_FINDINGS.md §4](EXPLORATORY_FINDINGS.md))

## Exploratory follow-ups (post-PREREG)

Past-PREREG analyses live in [EXPLORATORY_FINDINGS.md](EXPLORATORY_FINDINGS.md). Highlights:

- **Cross-task model rankings barely correlate** (mean Spearman ρ = 0.055 across the 10 task-pairs) — manipulation propensity is task-dependent, not a stable model trait. See [ranking_stability.json](ranking_stability.json) and [figures/fig_ranking_stability.pdf](figures/fig_ranking_stability.pdf).
- **Frontier-generation lift is non-uniform**: GPT-5 → GPT-5.5 reduces manipulation on 4/5 tasks (T4 Sales 56% → 3%). DeepSeek V3.2 → V4 Pro is more compliant on T3 Village (-0.37) and T4 Sales (-0.08), slightly more aggressive on T1 Bargaining (+0.14) and T2 Debate (+0.04), and roughly tied on T5 Committee. See [frontier_lift.json](frontier_lift.json) and [figures/fig_frontier_lift.pdf](figures/fig_frontier_lift.pdf).
- **T1 lie magnitude**: when models lie, Gemini 100% / GPT-5.5 97% / DeepSeek 76% / Grok 79% lie *extremely* (>200pt overstatements); Claude 6%, Llama 1%. See [../task1_bargaining/analysis/lie_magnitude.json](../task1_bargaining/analysis/lie_magnitude.json).
- **T5 dominates non-additive interactions**: per-(task, model) residuals from an additive linear fit; the top-10 most-surprising cells are all T5 (`prohibitive × high-difficulty` flips sign). See [residuals.json](residuals.json) and [figures/fig_residual_t<N>.pdf](figures/).
- **Model archetypes** (15-dim profile clustering): Claude/Llama/DeepSeek vs GPT-5.5/Grok vs Gemini outlier. See [clusters.json](clusters.json) and [figures/fig_dendrogram.pdf](figures/fig_dendrogram.pdf).

## Reproduction

```bash
# Re-build all per-task PREREG analysis JSONs
python experiments/task1_prereg_analysis.py
python experiments/task2_prereg_analysis.py
python experiments/task3_prereg_analysis.py
python experiments/task4_prereg_analysis.py
python experiments/task5_prereg_analysis.py

# Cross-task summary + bootstrap CIs + Cohen's d
python experiments/cross_task_analysis.py
python experiments/run_bootstrap_cis.py
python experiments/run_cohens_d.py
python experiments/run_response_surface.py     # per-task fig7 (3×6 grid: difficulty × model)

# Exploratory analyses (sec 1-9 of EXPLORATORY_FINDINGS.md)
python experiments/cross_task_ranking_stability.py
python experiments/cross_task_clustering.py
python experiments/surprise_residuals.py
python experiments/frontier_lift.py
python experiments/sample_distributions.py
python experiments/t1_lie_magnitude.py
python experiments/t2_per_claim.py
python experiments/t3_promise_gap.py
python experiments/t4_per_question_type.py
```
