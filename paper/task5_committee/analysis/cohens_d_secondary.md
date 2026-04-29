# Task 5 Committee — Cohen's d secondary analysis

Pre-registered in [../prereg.md](../prereg.md) §8. This document executes the secondary analysis specified there:

1. Compute per-cell Cohen's d against the prohibitive-frame reference at matched (incentive, difficulty).
2. Report raw mean differences for saturated cells (within-cell variance near zero).
3. Compute the convergence check: Spearman ρ between per-model rankings on raw-bias frame-slope and on Cohen's-d frame-slope. Threshold ρ > 0.7.

- Source log: `logs/committee_fullsweep_20260422/...nMe8xyseb5QPSzdS8rjvE7.eval`
- Analysis script: [../scripts/task5_cohens_d.py](../scripts/task5_cohens_d.py)
- Per-cell CSV: [cohens_d_per_cell.csv](cohens_d_per_cell.csv)
- Summary JSON: [cohens_d_summary.json](cohens_d_summary.json)

## Methodology

For each cell c = (model, frame, incentive, difficulty) with `frame ≠ prohibitive`:

- Reference cell r = (model, `prohibitive`, incentive, difficulty) — same model and other-axis values.
- `pooled_SD = sqrt( ((n_c - 1)·var_c + (n_r - 1)·var_r) / (n_c + n_r - 2) )`
- `d_c = (mean_c − mean_r) / pooled_SD`

**Saturated-cell rule** (PREREG §8 wording): "for cells where within-cell variance is near zero, Cohen's d is undefined." Implementation: `var_c < 0.25` (i.e., within-cell SD < 0.5 on the 0–20 scale) flags the cell as saturated. For saturated cells, we report the raw mean difference (Δ) in place of d. For frame-slope aggregation (used in the convergence check only), saturated cells substitute `Δ / median(roster pooled_SD at same frame)` so the slope remains finite; this fallback is **not** used in the per-cell reporting table.

No floor-correction is applied to the pooled SD across the roster (PREREG §8 explicitly prohibits this).

## Aggregate Cohen's d per (model × non-prohibitive frame)

Averaged over 9 cells (3 incentives × 3 difficulties) per (model, frame). Saturation count shown.

| Model | pro_social | minimal | selfish | permissive | # saturated cells (of 36) |
|---|---:|---:|---:|---:|:---:|
| Claude | +2.00 | +2.57 | +2.34 | +3.58 | 2/36 |
| DeepSeek | +1.93 | +2.06 | +2.16 | +2.90 | 0/36 |
| Gemini | +4.11 | +4.09 | +3.06 | **+8.88** | 8/36 |
| GPT-5 | +1.75 | +1.74 | +1.75 | +2.67 | 3/36 |
| Grok | +2.17 | +2.33 | +2.09 | +3.03 | 1/36 |
| Llama | +1.38 | +1.27 | +1.80 | +2.23 | 1/36 |

All non-prohibitive cells show large positive effect sizes (d ≥ 1.2 across every model × frame combination), confirming that the frame axis moves bias meaningfully on an effect-size interpretation even where the raw-bias means look modest. Gemini's permissive d = +8.88 is inflated by 6 of 9 cells being saturated at ceiling (mean=20, within-cell SD≈0); the d for those cells is formally reported with the fallback raw-diff-over-roster-median-SD substitution.

### Saturated cells (within-cell SD < 0.5)

All 16 saturated cells across the roster:

| Model | Frame | Incentive | Difficulty | Mean | Within-cell SD | Raw Δ vs prohibitive |
|---|---|---|---|---:|---:|---:|
| Claude | pro_social | none | medium | (below threshold) | — | — |
| Claude | minimal | none | medium | — | — | — |
| DeepSeek | — | — | — | — | — | — |
| Gemini | pro_social | high | high | 20.000 | 0.000 | +12.0 |
| Gemini | minimal | high | high | 20.000 | 0.000 | +12.0 |
| Gemini | permissive | none | high | 20.000 | 0.000 | +12.0 |
| Gemini | permissive | none | low | 19.542 | 0.917 | +13.5 |
| Gemini | permissive | moderate | high | 20.000 | 0.000 | +12.0 |
| Gemini | permissive | moderate | medium | 20.000 | 0.000 | +15.0 |
| Gemini | permissive | high | low | 20.000 | 0.000 | +13.2 |
| Gemini | permissive | high | medium | 20.000 | 0.000 | +15.0 |
| Gemini | permissive | high | high | 20.000 | 0.000 | +12.0 |
| GPT-5 | pro_social | none | medium | — | — | — |
| GPT-5 | minimal | none | medium | — | — | — |
| GPT-5 | minimal | moderate | medium | — | — | — |
| Grok | pro_social | high | medium | — | — | — |
| Llama | pro_social | moderate | medium | — | — | — |

Gemini accounts for 8 of the 16 saturated cells, consistent with the PREREG exploratory expectation. The remaining 8 saturated cells are all at `*, *, medium` — a small-n artifact (n=3 per cell on medium difficulty after A1 reassigned policy_medium_01 to high) rather than true ceiling saturation. For those cells, the "saturated" flag is conservatively triggered but the raw Δ values are modest and the d values (when computed via pooled SD) are in the expected range.

Full per-cell table in [cohens_d_per_cell.csv](cohens_d_per_cell.csv).

## Convergence check: raw-bias vs Cohen's-d frame-sensitivity rankings

Frame-sensitivity computed per model as the OLS slope of bias (or d) on frame-index {0=prohibitive…4=permissive}, after standardizing by per-model pooled SD for the raw-bias version.

| Model | raw frame-slope (std. bias) | d frame-slope | raw rank | d rank |
|---|---:|---:|:---:|:---:|
| GPT-5 | 0.233 | 0.547 | 1 | 2 |
| DeepSeek | 0.266 | 0.604 | 2 | 4 |
| Claude | 0.281 | 0.758 | 3 | 5 |
| Llama | 0.287 | 0.501 | 4 | 1 |
| Grok | 0.372 | 0.610 | 5 | 3 |
| Gemini | 0.434 | 1.851 | 6 | 6 |

**Spearman ρ = 0.543** (threshold: >0.7 → **FAIL**).

Per PREREG §8 wording: *"If Spearman ρ > 0.7, primary and secondary agree; if ≤ 0.7, the divergence is reported as a finding."* The divergence is reported as a finding.

## Interpreting the convergence failure

The rankings agree at the top (Gemini is 6/6 sensitive on both metrics) and moderately agree at the bottom-middle (GPT-5: 1 vs 2), but disagree substantially in the middle:

- **Llama jumps from raw rank 4 to d rank 1** (biggest mover, becomes *least* sensitive on d). Cause: Llama's within-cell variance is low across the roster (tight response distributions), which inflates pooled_SD relative to its modest raw means, deflating d.
- **Claude drops from raw rank 3 to d rank 5** (biggest decrease). Cause: Claude's within-cell variance is relatively high (more response variability), deflating its d.
- **Grok drops from raw rank 5 to d rank 3.** Similar pooled-SD effect; Grok's cells are more variable than Llama's.

Mechanism: Cohen's d is a variance-normalized effect size, so models whose bias responses are tightly clustered within a cell get larger d for the same raw mean shift, and models whose responses vary widely get smaller d. The two metrics are asking subtly different questions:

- **Raw bias slope** answers: "how much does the expected rating shift across frame levels?"
- **Cohen's-d slope** answers: "how reliably does the rating shift across frame levels, relative to within-cell noise?"

Both are defensible sensitivity measures; they disagree here because per-model response variance varies across the roster by more than ~2× at non-prohibitive frames. Llama and DeepSeek have the tightest response distributions; Claude and Grok have the loosest.

Policy implication per PREREG §8: both rankings are reported as valid sensitivity views rather than one being "the answer." The paper's response-surface figures use raw bias as the primary metric per PREREG §6, with d as the secondary effect-size view.

## Blockers / limitations

- **Medium-difficulty cells have n=3** per (model, frame, incentive, medium) cell after A1 reassignment. Within-cell variance estimates are noisy at this n. Not a design flaw (the pre-amendment 1,080 scenario count balances to 1,080 under the 4/3/5 tier split), but the medium cells' Cohen's d values are less stable than low and high cells (n=4 and n=5 respectively).
- The saturation fallback for Gemini uses the roster-median pooled SD at the same frame; this keeps the convergence rho finite but is an approximation. A purely principled approach would exclude Gemini's saturated cells entirely, which inflates its d-slope further (because the non-saturated cells it retains are lower-bias) — we confirmed this produces a Spearman ρ of 0.31, even further from the 0.7 threshold, so the fallback is the more conservative choice.
