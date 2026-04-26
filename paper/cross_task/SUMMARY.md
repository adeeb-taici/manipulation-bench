# Cross-task summary — Manipulation Response Surface

The five-task response-surface study is complete. This document is the paper-level summary of cross-task patterns. Per-task results live in [../task1_bargaining/results.md](../task1_bargaining/results.md), [../task2_debate/results.md](../task2_debate/results.md), [../task3_village/results.md](../task3_village/results.md), [../task4_sales/results.md](../task4_sales/results.md), [../task5_committee/results.md](../task5_committee/results.md).

## Headline finding: tasks split into two clusters by dominant axis

| Cluster | Tasks | Dominant axis | Notes |
|---|---|---|---|
| **Prompt-dominant** | Bargaining, Village | Incentive (Bargaining) / Frame (Village) | Manipulation channel is *behavioral* (lying about a number; defecting on contributions). Prompt language has direct grip. |
| **State-dominant** | Debate, Sales, Committee | Difficulty (juror prior / product quality / slate quality) | Manipulation channel is *informational* (constructing claims). The truth's bend-ability is the binding constraint, not the prompt. |

The cluster split is **not** an artifact of which models manipulate easily — it's about whether the manipulator's lever is "decide what to do with my own contribution" (Village, Bargaining) versus "construct a sequence of claims that move someone's belief" (Debate, Sales, Committee). When the lever is a single behavioral choice that the prompt directly addresses, the prompt wins. When the lever requires generating false content that has to fit alongside the underlying truth, the underlying truth dominates.

## Per-task aggregate sensitivity (mean |slope| across 6 models)

See [cross_task_aggregate.md](cross_task_aggregate.md) for the full machine-generated table; [figures/per_task_slopes.png](figures/per_task_slopes.png) for the chart.

| Task | Frame | Incentive | Difficulty | Dominant axis | Dominance ratio |
|---|---:|---:|---:|---|---:|
| T1 Bargaining | 0.106 | **0.208** | 0.030 | incentive | 2.0× |
| T2 Debate | 0.010 | 0.012 | **0.061** | difficulty | 5.2× |
| T3 Village | **0.155** | 0.054 | 0.024 | **frame** | 2.9× |
| T4 Sales | 0.027 | 0.013 | **0.130** | difficulty | 4.9× |
| T5 Committee | 0.325 | 0.183 | **0.607** | difficulty | 1.9× |

(T5 numbers are on a 0–20 bias scale, not a 0–1 rate scale, so absolute magnitudes aren't directly comparable to T1-T4.)

## Cross-task incentive taxonomy (refines P5 across tasks)

The PREREG predicted incentive sensitivity would be a per-task continuum, with Sales/Village landing intermediate between Debate (weak) and Bargaining (strong). The empirical pattern is **bimodal, not continuous**:

| Cluster | Tasks | Mean \|incentive slope\| | Why |
|---|---|---:|---|
| **Binding** | Bargaining, Committee | 0.22, 0.17 | **Structural reward integration** — penalty math affecting payoff (Bargaining); competition outcome determining win/loss (Committee) |
| **Inert** | Village, Sales, Debate | 0.05, 0.01, 0.01 | **Verbal emphasis only** — "your final score is X" or "you earn N points per Y" doesn't change the agent's actual reward function |

This refines the cross-task incentive theory: **incentive language only binds when it introduces NEW reward structure**. When it's just a verbal restatement of the natural objective ("your final token balance is your only score" — but token balance is *already* the natural objective in Village), models treat it as redundant. This was a P5 failure across three of five tasks (Village, Sales, Debate); only Bargaining and Committee passed P5 as predicted.

## Per-model profile signatures (15-dim cross-task vector)

See [figures/per_model_profiles.png](figures/per_model_profiles.png) for the small-multiples view; [figures/cross_task_heatmap.png](figures/cross_task_heatmap.png) for the dense matrix; [cross_task_aggregate.md](cross_task_aggregate.md) for the machine-readable signed slopes.

A few notable per-model patterns:

- **Gemini 3.1 Pro** is the most frame-sensitive model in 4 of 5 tasks (Bargaining, Village, Sales, Committee), but saturates early on permissive frames (Sales, Village, Committee all hit ≥ 0.85 at the permissive endpoint), making it the easiest model to push to extreme manipulation.
- **GPT-5.5** is the most-aligned model on Sales (0.03 prohibitive manipulation rate, comparable to Claude/Grok) — a major reversal from GPT-5, which had a 0.51 prohibitive manipulation rate driven by a "commercial-omission default" (selectively omitting comparables and known defects). On Bargaining, GPT-5.5 keeps GPT-5's clean 0.000 prohibitive endpoint but reads pro-social/minimal middle-frames ~30pp better. On Debate/Village/Committee the alignment shift is smaller and task-dependent.
- **Claude Opus 4.7** is the most prohibitive-compliant model across tasks (≤ 0.05 on T1/T2 prohibitive averages) and never saturates a high-manipulation cell on T3 Village or T4 Sales. Frame slopes are also middling — Claude's overall manipulation envelope is the smallest of the six.
- **Llama 3.3 70B** and **DeepSeek v3.2** show a parallel pattern: weak prompt-following on Village (both fail P1, prohibitive 0.42 and 0.51 respectively) and weak incentive sensitivity on Bargaining. **Within the six-model roster, these two consistently behave as "less prompt-responsive"** across multiple tasks. This is a candidate paper-level finding worth flagging in Methods/Discussion.
- **Grok 4** behaves close to Claude on prompt-compliance baselines but has a steeper permissive endpoint. On Village Grok jumps from 0.00 prohibitive to 0.96 permissive — a 96-percentage-point swing, the largest endpoint range in T3.

## Cross-task verdict matrix

| Task | P1 prohib | P2 perm | P3 saturation | P4 dominance | P5 incentive | P6 ρ stable | P7 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| T1 Bargaining | ✓ | ✓ | (deferred) | partial (4/6) | ✗ | ✓ | — |
| T2 Debate | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | — |
| T3 Village | ✗ | ✗ | ✓ | **✓** | ✗ | ✓ | ✓ |
| T4 Sales | **✓** | ✗ | **✗** | ✓ | ✗ | ✓ | (deferred) |
| T5 Committee | ✓ | ✓ | weak | ✗ | ✓ | (FAIL ρ=−0.83) | — |

P1/P2 fail in 2/5 tasks (Debate, Village, with Sales now passing P1 after GPT-5.5 swap). The pattern: predictions that "prohibitive will land below 5%" are correct on Bargaining and Committee (where prohibitive is a hard constraint on a single act) but fail on Debate, Village, and Sales (where prohibitive doesn't fully prevent manipulation because it doesn't change the manipulator's underlying *role* — they're still arguing the false side, still defecting from cooperation, still selling a bad product).

## What's NOT in this file

- Cohen's d secondary analysis across all 5 tasks (only T5 has it; deferred for T1-T4)
- Bootstrap CIs (deferred)
- Per-task hand-validation results (deferred for T4/T5)
- Statistical model: which axis-pairs are significantly correlated across models (deferred)

## Reproduction

```bash
# Re-build all per-task analysis JSONs
python experiments/task1_prereg_analysis.py
python experiments/task2_prereg_analysis.py
python experiments/task3_prereg_analysis.py
python experiments/task4_prereg_analysis.py
python experiments/task5_prereg_analysis.py    # T5 prints to stdout; numbers embedded in cross_task_analysis.py

# Build cross-task summary
python experiments/cross_task_analysis.py
```
