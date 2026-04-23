# Paper artifacts

All artifacts directly supporting the NeurIPS 2026 E&D Track submission on the Manipulation Response Surface. Materials under `paper/` are the authoritative record for the paper; exploratory work lives elsewhere in the repo ([../FINDINGS.md](../FINDINGS.md), `analysis/` at the repo root for pre-PREREG experiments).

## Structure

One folder per task. Each task folder contains its pre-registration, its pre-registered results, a supporting `analysis/` sub-folder, and (where applicable) a production-run `pipeline_log.md`.

```
paper/
  task5_committee/
    prereg.md                            # Pre-registration (committed; amendments A1, A2)
    results.md                           # Official results against P1–P6
    analysis/
      prereg_outcomes_per_model.md       # Per-model × per-prediction pass/fail breakdown
      cohens_d_secondary.md              # Pre-registered Cohen's d analysis + convergence check
      cohens_d_per_cell.csv              # Machine-readable d-per-cell table
      cohens_d_summary.json              # Machine-readable slopes + convergence rho
      minimal_selfish_inversion.md       # Deep-dive on the cross-model "selfish paradox"
      high_difficulty_cold_panel.md      # Per-slate cold-panel baselines for Methods/Appendix
      sensitivity_by_difficulty.md       # Post-hoc: frame dominates at each difficulty tier
  task1_bargaining/
    prereg.md                            # Pre-registration (locked 2026-04-22; amendment A1)
    pipeline_log.md                      # Production-run log (stalls, retries, recoveries)
    results_summary.md                   # DRAFT — pipeline-complete summary; Grok placeholders pending
    analysis/
      deepseek_config_audit.md           # Confirm DS reasoning-off applied to all Task 1 samples
      frame_per_model.md                 # Frame × model table + minimal-selfish inversion check
  task2_debate/
    prereg.md                            # DRAFT — author decisions A1–A7 pending
    claim_pool_revalidation.md           # Juror re-validation result (9 survive; 7 after flags)
```

## Task status

| Task | PREREG | Full sweep | Results | Blockers |
|---|---|---|---|---|
| Task 5 Committee | [task5_committee/prereg.md](task5_committee/prereg.md) committed | Complete (1,049 / 1,080 scored) | [task5_committee/results.md](task5_committee/results.md) | **Polarity scorer hand-validation pending** (author-only task; 30 stratified segments to label; gates `discussion_polarity` reporting only, does **not** gate P1–P6) |
| Task 1 Bargaining | [task1_bargaining/prereg.md](task1_bargaining/prereg.md) locked | 5 of 6 models complete (4,501 scored); Grok-4 in progress | — | Grok-4 completion; do not finalize until landed |
| Task 2 Debate | [task2_debate/prereg.md](task2_debate/prereg.md) — **ready for author timestamp** | Not launched | — | Juror re-validation complete ([task2_debate/claim_pool_revalidation.md](task2_debate/claim_pool_revalidation.md)); 18-claim pool locked (7 rounds, 113 candidates tested); A1–A5, A7 resolved in-line; awaits author A6 (bootstrap seed) + timestamp + pre-sweep smoke |
| Task 3 Village Commons | — | — | — | Not started |
| Task 4 Sales | — | — | — | Not started |

## Outstanding items

- **Task 5 polarity hand-validation** (not a Claude Code task). Author labels 30 stratified segments; verify rule-based `discussion_polarity` classifier agrees at ≥85% per PREREG §6. No LLM-judge fallback permitted. Validation template at [../task5_validation.md](../task5_validation.md). Gates the `discussion_polarity` secondary metric only; pre-registered P1–P6 verdicts in `results.md` do not depend on this.
- **Grok-4 Task 1 completion**. Running at `--max-connections 3` (low-concurrency path chosen after the Grok-reasoning stall diagnosed in [task1_bargaining/pipeline_log.md](task1_bargaining/pipeline_log.md)). Bargaining analysis is **not** finalized until Grok's 899 scenarios score. Current progress: ~30%.

## Where things live that are *not* under paper/

- **Pre-PREREG exploratory analysis**: `analysis/committee_pilot_3lab/`, `analysis/committee_prohibitive_cheap/`, `analysis/committee_sweep/`, `analysis/smoke_response_surface/`, `analysis/smoke_response_surface_multi/` — superseded by the pre-registered full sweep.
- **Ad-hoc findings and running notes**: [../FINDINGS.md](../FINDINGS.md)
- **Cold-panel slate validation raw data**: `logs/cold_panel_20260422/`
- **Full-sweep eval logs + figures**: `logs/committee_fullsweep_20260422/`, `logs/task1_fullsweep_20260422*/`
- **Scenario JSONLs**: `src/manipulation_bench/scenarios/`
- **Analysis scripts**: `experiments/task5_prereg_analysis.py`, `experiments/task5_cohens_d.py`, `experiments/task5_visuals.py`, `experiments/task1_visuals.py`, `experiments/task1_smoke_pilot_v61.py`
