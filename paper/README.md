# Paper artifacts

All artifacts directly supporting the NeurIPS 2026 E&D Track submission on the Manipulation Response Surface. Materials under `paper/` are the authoritative record for the paper; pre-PREREG exploratory work lives elsewhere in the repo ([../FINDINGS.md](../FINDINGS.md), `analysis/` at the repo root).

## Structure

```
paper/
  paper.tex                              # The paper
  README.md                              # This file

  task<N>_<env>/                         # One folder per task (T1-T5 + held-out T6)
    prereg.md                            # Pre-registration + amendments
    results.md                           # Official results against P1–P7
    pipeline_log.md                      # Production-run log (where applicable)
    eval_log.eval                        # Combined eval log (LFS), 6 frontier models
    eval_log_small_model_sweep.eval      # Small-model sweep log (LFS), 9 sweep models (T1-T5 only)
    scripts/                             # Per-task scripts (generator, prereg, visuals, exploratory)
    analysis/                            # Per-task analysis outputs (JSON + .md)
    figures/                             # Per-task figures (fig1..fig10)


  cross_task/
    SUMMARY.md                           # Paper-level cross-task patterns
    EXPLORATORY_FINDINGS.md              # Post-PREREG analyses
    REANALYSIS_NOTES.md                  # v2 statistical reanalysis methods + survival check
    results.csv                          # Per-rollout tidy CSV across all 5 tasks (the new aggregate)
    scripts/                             # Cross-task scripts (see scripts/README.md for the map)
    analysis/                            # Cross-task outputs (JSON + .md)
    figures/                             # Cross-task figures
```

The combined eval logs (`eval_log.eval`, `eval_log_small_model_sweep.eval`) are committed via Git LFS. Clone with `git lfs install && git lfs pull` to fetch them.

## Task status

T1–T5 have **complete full sweeps + Amendments A1–A5 applied** and form the pre-registered manipulator-response surface. T6 is a pre-registered held-out test of the cluster-split taxonomy derived from T1–T5 and is reported separately. The combined eval logs at `paper/task<N>/eval_log.eval` reflect the post-amendment state (GPT-5.5 + DeepSeek V4 Pro).

| Task | PREREG | Combined log | Results | Outstanding |
|---|---|---|---|---|
| Task 1 Bargaining | [task1_bargaining/prereg.md](task1_bargaining/prereg.md) (A1, A2, A3) | `task1_bargaining/eval_log.eval` (5,400 / 5,400) | [task1_bargaining/results.md](task1_bargaining/results.md) | None |
| Task 2 Debate | [task2_debate/prereg.md](task2_debate/prereg.md) (A1, A2) | `task2_debate/eval_log.eval` (4,140 / 4,140) | [task2_debate/results.md](task2_debate/results.md) | None |
| Task 3 Village | [task3_village/prereg.md](task3_village/prereg.md) (A1, A2, A3, A4) | `task3_village/eval_log.eval` (532 / 540, 1.5% errors) | [task3_village/results.md](task3_village/results.md) | None |
| Task 4 Sales | [task4_sales/prereg.md](task4_sales/prereg.md) (A1, A2) | `task4_sales/eval_log.eval` (1,350 / 1,350) | [task4_sales/results.md](task4_sales/results.md) | None — P7 hand-validation PASSED (100% agreement, 30/30) |
| Task 5 Committee | [task5_committee/prereg.md](task5_committee/prereg.md) (A1, A2, A3, A4, A5) | `task5_committee/eval_log.eval` (1,049 / 1,080, 0.2% errors) | [task5_committee/results.md](task5_committee/results.md) | Polarity scorer hand-validation FAILED (76.9% < 85% gate) → `discussion_polarity` dropped per Amendment A5; P1–P6 unaffected |
| Task 6 Inbox (held-out) | [task6_inbox/prereg.md](task6_inbox/prereg.md) | `task6_inbox/eval_log.eval` (1,080 / 1,080) | [task6_inbox/results.md](task6_inbox/results.md) | P-T6.7 hand-validation deferred to camera-ready; cluster-split predictions P-T6.4/.5/.6 PASS |

In addition, each T1–T5 task has a `eval_log_small_model_sweep.eval` containing the small-model sweep arm (9 additional models: GPT-4.1, GPT-4.1-mini, GPT-4.1-nano, GPT-5.4-mini, GPT-5.4-nano, Claude Haiku 3.5, Claude Haiku 4.5, Claude Sonnet 3.7, Claude Sonnet 4.6). T2 has only OpenAI sweep models (no Claude sweep on debate). T6 has no small-model sweep.

## Cross-task

Paper-level findings: [cross_task/SUMMARY.md](cross_task/SUMMARY.md). Past-PREREG exploratory analyses (clustering, ranking-stability, frontier-lift, surprise-residuals, etc.): [cross_task/EXPLORATORY_FINDINGS.md](cross_task/EXPLORATORY_FINDINGS.md). v2 statistical reanalysis (regression, ranking-stability bootstrap, variance decomposition): [cross_task/REANALYSIS_NOTES.md](cross_task/REANALYSIS_NOTES.md).

The trajectory-level tidy CSV is at [cross_task/results.csv](cross_task/results.csv) (~26k rows × 85 cols, both canonical and small_model_sweep variants). Most cross-task analysis scripts now read this CSV via [cross_task/scripts/load.py](cross_task/scripts/load.py)'s `load_corpus()` function (~0.13s vs the multi-minute eval-log walk).

## Model cohort

Six **frontier models**, locked at PREREG time and updated via Amendments A2 (GPT-5 → GPT-5.5) and A3 (DeepSeek-v3.2 → DeepSeek-V4-Pro):

| Slot | Model | Provider |
|---|---|---|
| `model_a` | Claude Opus 4.7 | OpenRouter (Anthropic) |
| `model_b` | GPT-5.5 | OpenRouter (OpenAI), `reasoning_enabled=true` |
| `model_c` | Gemini 3.1 Pro | OpenRouter (Google), `reasoning_enabled=true` |
| `model_d` | Grok 4 | OpenRouter (xAI), `reasoning_enabled=true` |
| `model_e` | Llama 3.3 70B | OpenRouter (Meta) |
| `model_f` | DeepSeek V4 Pro | DeepSeek official API; `tool_choice_strategy=auto` workaround for reasoning-mode rejection of `tool_choice="any"` |

Plus **9 small-model sweep arms** (post-PREREG, recorded in `eval_log_small_model_sweep.eval`): GPT-4.1, GPT-4.1-mini, GPT-4.1-nano, GPT-5.4-mini, GPT-5.4-nano, Claude Haiku 3.5, Claude Haiku 4.5, Claude Sonnet 3.7, Claude Sonnet 4.6.

## Reproducing analysis

```bash
# Re-build per-task PREREG verdicts (P1–P6/P7) + figures
python task1_bargaining/scripts/task1_prereg_analysis.py
python task2_debate/scripts/task2_prereg_analysis.py
python task3_village/scripts/task3_prereg_analysis.py
python task4_sales/scripts/task4_prereg_analysis.py
python task5_committee/scripts/task5_prereg_analysis.py
python task6_inbox/scripts/task6_prereg_analysis.py     # held-out cluster-split test
python task1_bargaining/scripts/task1_visuals.py
python task2_debate/scripts/task2_visuals.py
python task3_village/scripts/task3_visuals.py
python task4_sales/scripts/task4_visuals.py
python task5_committee/scripts/task5_visuals.py
python task6_inbox/scripts/task6_visuals.py

# Refresh the cross-task CSV (only needed when eval logs change)
python cross_task/scripts/eval_logs_to_csv.py

# v1 cross-task analyses (read results.csv via load_corpus)
python cross_task/scripts/bootstrap_cis.py
python cross_task/scripts/cohens_d.py
python cross_task/scripts/response_surface.py
python cross_task/scripts/aggregate.py
python cross_task/scripts/clustering.py
python cross_task/scripts/ranking_stability_v1.py
python cross_task/scripts/explore.py
python cross_task/scripts/surprise_residuals.py
python cross_task/scripts/sample_distributions.py
python cross_task/scripts/frontier_lift.py    # walks pre-amendment split logs

# v2 statistical reanalysis (regression, ranking-stability bootstrap, variance decomposition)
python cross_task/scripts/regression.py
python cross_task/scripts/ranking_stability_v2.py
python cross_task/scripts/variance_decomposition.py
python cross_task/scripts/v2_figures.py

# Per-task exploratory pivots
python task1_bargaining/scripts/t1_lie_magnitude.py
python task2_debate/scripts/t2_per_claim.py
python task3_village/scripts/t3_promise_gap.py
python task4_sales/scripts/t4_per_question_type.py
```

See [cross_task/scripts/README.md](cross_task/scripts/README.md) for a map of what each cross-task script does.

## Reproducing the experiments on a new model roster

Each task's generator accepts a `--models` flag that overrides the paper roster while keeping the rest of the design (axes, reps per cell, scorer, analysis) fixed. The recipe is uniform across all five tasks:

```bash
# 1. Generate scenarios with your roster.
#    Bare labels auto-prefix the role; `label=role` pairs let you pick roles explicitly.
python task1_bargaining/scripts/generate_task1_bargaining.py --models 'opus47,haiku45,gpt55,grok4'
python task2_debate/scripts/generate_task2_debate_full.py    --models 'opus47,haiku45,gpt55,grok4'
python task3_village/scripts/generate_task3_village_full.py  --models 'opus47,haiku45,gpt55,grok4'
python task4_sales/scripts/generate_task4_sales.py           --models 'opus47,haiku45,gpt55,grok4'
python task5_committee/scripts/generate_task5_committee.py   --models 'opus47,haiku45,gpt55,grok4' --sweep
python task6_inbox/scripts/generate_task6_inbox.py           --models 'opus47,haiku45,gpt55,grok4'

# 2. Each generator prints the exact `inspect eval ...` command, with each
#    `--model-role <role>=openrouter/<provider>/<model>` left as a placeholder.
#    Copy-paste it and substitute your provider strings into each role.

# 3. Score against the same pre-registered analysis used in the paper.
python task1_bargaining/scripts/task1_prereg_analysis.py
python task2_debate/scripts/task2_prereg_analysis.py
python task3_village/scripts/task3_prereg_analysis.py
python task4_sales/scripts/task4_prereg_analysis.py
python task5_committee/scripts/task5_prereg_analysis.py
python task6_inbox/scripts/task6_prereg_analysis.py
python cross_task/scripts/eval_logs_to_csv.py
python cross_task/scripts/bootstrap_cis.py
python cross_task/scripts/cohens_d.py
```

Notes:
- Pinned framework roles (Debate's `truthful_debater`/jurors/judge, Village's `bystander_*`, Committee's `model_neutral_*`) keep their canonical bindings in the printed command — only the under-test roster changes.
- Without `--models`, the generators print the canonical paper-roster command, which is what produced the eval logs under this directory.
- Pilot variants are available via `--pilot` (T1, T4, T5) — useful for sanity-checking your new roster before paying for the full sweep.

## Where things live that are *not* under paper/

- **Pre-PREREG exploratory analysis**: `analysis/` at the repo root.
- **Ad-hoc findings and running notes**: [../FINDINGS.md](../FINDINGS.md).
- **Original split eval logs**: `logs/task<N>_*`, `logs/task<N>_dsv4`, `logs/task<N>_gpt55`. The combined logs at `paper/task<N>/eval_log.eval` dedup these by sample id (later-running splits win, so amendments overlay originals). `cross_task/scripts/frontier_lift.py` reads these splits directly to do GPT-5 vs GPT-5.5 within-scenario contrasts.
- **Small-model sweep raw logs**: `logs/openai_sweep/*_t<N>/`, `logs/claude_sweep/*_t<N>/`. Consolidated into each task's `eval_log_small_model_sweep.eval`.
- **Sweep launch scripts**: `experiments/sweeps/run_{openai,claude,gemini}_sweep.sh`.
- **Scenario JSONLs**: `src/manipulation_bench/scenarios/`.
- **Framework code (envs, scorers, solver)**: `src/manipulation_bench/`.
