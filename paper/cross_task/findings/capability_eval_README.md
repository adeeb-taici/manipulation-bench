# Capability evaluation

Parallel analysis layered on top of the main paper artifacts. Adds a model-capability axis (LMArena ELO + tier + generation) to the cross-task results without modifying the existing pipeline.

This is **not pre-registered** — analyses here belong in `paper/cross_task/findings/exploratory.md`, not `prereg.md`.

## Capability metadata

`paper/cross_task/data/model_capability.csv` — frozen LMArena snapshot keyed on the model strings used in `results.csv`.

Columns:
- `elo` — Arena Score from `arena.ai/leaderboard/text` (or OpenLM mirror) on `elo_date`.
- `generation` — `current` (latest 2026 release cycle) or `prev`.
- `tier` — `flagship` / `average` / `small`. Family-relative: e.g., haiku45 is `small` even though it's `current`.
- `family` — anthropic / openai / google / xai / meta / deepseek.

## Scripts

All scripts read `paper/cross_task/data/results.csv` and `paper/cross_task/data/model_capability.csv` via the shared loader in `_capability_io.py`. Outputs go to `analysis/` and `figures/` in this directory.

| Script | What it does |
|---|---|
| `capability_analysis.py` | Spearman ELO-vs-rate per task, tier × frame heatmap, generation deltas (no controls). |
| `capability_regression.py` | OLS `manipulation_rate ~ ELO + frame + incentive + difficulty` per task and pooled (with task FE + ELO×task interaction). HC3 robust SEs. |
| `capability_anova.py` | Two-way ANOVA: tier × {frame, incentive, difficulty} per task and pooled. Type II SS. |
| `capability_response_surface.py` | The paper's 5-frame × 3-incentive heatmap, faceted by capability tier instead of by model. Also frame × difficulty version. |
| `capability_frontier_lift.py` | Within-family generation-pair deltas, paired by axis cell, bootstrapped 95% CIs. |
| `capability_clustering.py` | K-means on per-(task, frame) manipulation-rate profiles, projected to 2D PCA, colored by tier and generation. |

## Reproduce

```bash
cd paper/cross_task/scripts/capability
python3 capability_analysis.py
python3 capability_regression.py
python3 capability_anova.py
python3 capability_response_surface.py
python3 capability_frontier_lift.py
python3 capability_clustering.py
```

## Caveats

- LMArena ELO is a noisy proxy for "capability" — it measures human-rated chat quality, not manipulation propensity.
- Family confounds tier (e.g., 3 of 5 small-tier models are Anthropic). Within-family generation deltas are cleaner evidence than cross-family tier averages.
- Capability cells are sparse: 15 models split across 3 tiers means averaging 3–7 models per tier. Cross-tabulating tier × frame × incentive × difficulty (135 cells) yields many empty cells per task; the response-surface heatmap collapses across one of those axes.
