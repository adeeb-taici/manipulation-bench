# Paper artifacts

All artifacts directly supporting the NeurIPS 2026 E&D Track submission on the Manipulation Response Surface. Materials under `paper/` are the authoritative record for the paper; pre-PREREG exploratory work lives elsewhere in the repo ([../FINDINGS.md](../FINDINGS.md), `analysis/` at the repo root).

## Structure

One folder per task. Each task folder contains its pre-registration, its pre-registered results, a supporting `analysis/` sub-folder, a `figures/` sub-folder, and (where applicable) a production-run `pipeline_log.md`. The combined eval log lives at `paper/task<N>/eval_log.eval` (Git LFS).

```
paper/
  task1_bargaining/
    prereg.md                 # Pre-registration + amendments A1, A2, A3
    results.md                # Official results against P1–P6
    pipeline_log.md           # Production-run log (stalls, retries, recoveries)
    eval_log.eval             # Combined eval log (LFS) — 5,400 samples
    analysis/                 # Per-task analysis outputs (JSON + .md)
    figures/                  # Per-task figures (fig1..fig10)
  task2_debate/  ... (4,140 samples)
  task3_village/ ... (532/540 samples; A1+A2+A3+A4)
  task4_sales/   ... (1,350 samples)
  task5_committee/ ... (1,049/1,080 samples; A1+A2)
  cross_task/
    SUMMARY.md                # Paper-level cross-task patterns
    EXPLORATORY_FINDINGS.md   # Post-PREREG analyses (cluster, ranking-stability, frontier-lift, …)
    cross_task_aggregate.md   # Machine-generated per-task aggregate slope tables
    cross_task_profiles.json  # 15-dim per-model profile vectors
    clusters.json             # Hierarchical clustering on profile vectors
    ranking_stability.json    # Spearman ρ between per-task model orderings
    frontier_lift.json        # GPT-5→5.5 / V3.2→V4-Pro within-scenario contrasts
    residuals.json            # Cells flagged by additive-model residual analysis
    figures/                  # All cross-task figures
  README.md                   # This file
```

## Task status

All five tasks have **complete full sweeps + Amendments A1-A4 applied**. The combined eval logs at `paper/task<N>/eval_log.eval` reflect the post-amendment state (GPT-5.5 + DeepSeek V4 Pro).

| Task | PREREG | Combined log | Results | Outstanding |
|---|---|---|---|---|
| Task 1 Bargaining | [task1_bargaining/prereg.md](task1_bargaining/prereg.md) (A1, A2, A3) | `task1_bargaining/eval_log.eval` (5,400 / 5,400) | [task1_bargaining/results.md](task1_bargaining/results.md) | None |
| Task 2 Debate | [task2_debate/prereg.md](task2_debate/prereg.md) (A1, A2) | `task2_debate/eval_log.eval` (4,140 / 4,140) | [task2_debate/results.md](task2_debate/results.md) | None |
| Task 3 Village | [task3_village/prereg.md](task3_village/prereg.md) (A1, A2, A3, A4) | `task3_village/eval_log.eval` (532 / 540, 1.5% errors) | [task3_village/results.md](task3_village/results.md) | None |
| Task 4 Sales | [task4_sales/prereg.md](task4_sales/prereg.md) (A1, A2) | `task4_sales/eval_log.eval` (1,350 / 1,350) | [task4_sales/results.md](task4_sales/results.md) | P7 hand-validation (author task; gates `manipulation_rate` reporting only) |
| Task 5 Committee | [task5_committee/prereg.md](task5_committee/prereg.md) (A1, A2, A3, A4) | `task5_committee/eval_log.eval` (1,049 / 1,080, 0.2% errors) | [task5_committee/results.md](task5_committee/results.md) | Polarity scorer hand-validation (gates `discussion_polarity` only; not P1-P6) |

## Cross-task

Paper-level findings: [cross_task/SUMMARY.md](cross_task/SUMMARY.md). Past-PREREG exploratory analyses (clustering, ranking-stability, frontier-lift, surprise-residuals, etc.): [cross_task/EXPLORATORY_FINDINGS.md](cross_task/EXPLORATORY_FINDINGS.md).

## Model cohort

Six models, locked at PREREG time and updated via Amendments A2 (GPT-5 → GPT-5.5) and A3 (DeepSeek-v3.2 → DeepSeek-V4-Pro):

| Slot | Model | Provider |
|---|---|---|
| `model_a` | Claude Opus 4.7 | OpenRouter (Anthropic) |
| `model_b` | GPT-5.5 | OpenRouter (OpenAI), `reasoning_enabled=true` |
| `model_c` | Gemini 3.1 Pro | OpenRouter (Google), `reasoning_enabled=true` |
| `model_d` | Grok 4 | OpenRouter (xAI), `reasoning_enabled=true` |
| `model_e` | Llama 3.3 70B | OpenRouter (Meta) |
| `model_f` | DeepSeek V4 Pro | DeepSeek official API (`DEEPSEEK_API_KEY` + `DEEPSEEK_BASE_URL`); `tool_choice_strategy=auto` workaround for reasoning-mode rejection of `tool_choice="any"` |

## Reproducing analysis

The combined eval logs (`paper/task<N>/eval_log.eval`) are committed via Git LFS — clone with `git lfs install && git lfs pull` to fetch them. Then:

```bash
# Re-build per-task PREREG verdicts (P1-P6/P7) + figures
for n in 1 2 3 4 5; do python experiments/task${n}_prereg_analysis.py; done

# Bootstrap CIs and Cohen's d (cross-task)
python experiments/run_bootstrap_cis.py
python experiments/run_cohens_d.py

# Per-task response-surface figure (3 difficulty rows × 6 model cols × 5×3 frame×incentive heatmap)
python experiments/run_response_surface.py

# Cross-task summary + exploratory analyses
python experiments/cross_task_analysis.py
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

Re-running an eval from scratch is documented per-task in `paper/task<N>/prereg.md` §11 and in [../FINDINGS.md](../FINDINGS.md).

## Where things live that are *not* under paper/

- **Pre-PREREG exploratory analysis**: `analysis/committee_pilot_3lab/`, `analysis/committee_prohibitive_cheap/`, `analysis/committee_sweep/`, `analysis/smoke_response_surface/`, `analysis/smoke_response_surface_multi/`.
- **Ad-hoc findings and running notes**: [../FINDINGS.md](../FINDINGS.md).
- **Cold-panel slate validation raw data**: `logs/cold_panel_20260422/`.
- **Original split eval logs**: `logs/task<N>_*` and `logs/task<N>_dsv4`, `logs/task<N>_gpt55`. The combined logs at `paper/task<N>/eval_log.eval` dedup these by sample id (later-running splits win, so amendments overlay originals).
- **Scenario JSONLs**: `src/manipulation_bench/scenarios/`.
- **Analysis scripts**: `experiments/`.
