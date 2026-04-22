# Paper artifacts

All artifacts directly supporting the NeurIPS 2026 E&D Track submission on the Manipulation Response Surface. Materials under `paper/` are the authoritative record for the paper; exploratory work lives elsewhere in the repo ([../FINDINGS.md](../FINDINGS.md), `analysis/` at the repo root for pre-PREREG experiments).

## Structure

One folder per task. Each task folder contains its pre-registration, its pre-registered results, and a supporting `analysis/` sub-folder.

```
paper/
  task5_committee/
    prereg.md                          # Pre-registration (committed 2026-04-21; amendments A1, A2)
    results.md                         # Official results against P1–P6
    analysis/
      prereg_outcomes_per_model.md     # Per-model × per-prediction pass/fail breakdown
      cohens_d_secondary.md            # Pre-registered Cohen's d analysis + convergence check
      cohens_d_per_cell.csv            # Machine-readable d-per-cell table
      cohens_d_summary.json            # Machine-readable slopes + convergence rho
      minimal_selfish_inversion.md     # Deep-dive on the cross-model "selfish paradox"
      high_difficulty_cold_panel.md    # Per-slate cold-panel baselines for Methods/Appendix
  task1_bargaining/
    prereg.md                          # Draft — author decisions A2–A5 + timestamp pending
```

## Task status

| Task | PREREG | Full sweep | Results | Blockers |
|---|---|---|---|---|
| Task 5 Committee | [task5_committee/prereg.md](task5_committee/prereg.md) — committed | Complete (1,078/1,080 scored) | [task5_committee/results.md](task5_committee/results.md) | Polarity scorer hand-validation pending (gates discussion-polarity reporting only; does not gate P1–P6) |
| Task 1 Bargaining | [task1_bargaining/prereg.md](task1_bargaining/prereg.md) — draft | Not launched | — | Author resolution of decisions A2–A5 + timestamp + commit |
| Task 2 Debate | — | — | — | Not started |
| Task 3 Village Commons | — | — | — | Not started |
| Task 4 Sales | — | — | — | Not started |

## Where things live that are *not* under paper/

- **Pre-PREREG exploratory analysis**: `analysis/committee_pilot_3lab/`, `analysis/committee_prohibitive_cheap/`, `analysis/committee_sweep/`, `analysis/smoke_response_surface/`, `analysis/smoke_response_surface_multi/` — superseded by the pre-registered full sweep.
- **Ad-hoc findings and running notes**: [../FINDINGS.md](../FINDINGS.md)
- **Cold-panel slate validation raw data**: `logs/cold_panel_20260422/`
- **Full-sweep eval log and figures**: `logs/committee_fullsweep_20260422/`
- **Scenario JSONLs**: `src/manipulation_bench/scenarios/`
- **Analysis scripts**: `experiments/task5_prereg_analysis.py`, `experiments/task5_cohens_d.py`, `experiments/task5_visuals.py`
