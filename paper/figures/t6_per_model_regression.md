# T6 Per-Model Regression — §4.3 Partition Claim

## Methodology

For each of the 6 paper-cohort models, suppression_rate is regressed on z-scored level codes for each axis:

    suppression_rate ~ intercept + frame_z + incentive_z + difficulty_z

Levels are coded by canonical ordering (frame: prohibitive=0 ... permissive=4; incentive: none=0 .. high=2; difficulty: low=0 .. high=2), then z-scored across each model's sample (so coefficients are in units of 'SD of axis level' → suppression rate). OLS with classical SEs (no clustering — sample-level, not cell-level, so within-cell correlation is mild but not zero; treat SEs as approximate at the per-model level). The cross-model partition test uses the resulting 6-vector of coefficients per axis.

**Cross-model contrasts:**
- (A) `β_frame > β_difficulty` (signed): paired Wilcoxon signed-rank, one-sided.
- (B) `|β_frame| > |β_difficulty|` (magnitude): paired Wilcoxon signed-rank, one-sided. This is the one that maps to the partition claim — direction is unconstrained per model.
- (C) `β_incentive ≈ 0`: one-sample t-test against zero, two-sided.
- (S) Sign test on `|β_frame| > |β_difficulty|`: binomial against p=0.5, one-sided.

Paired t-test companions are reported alongside the Wilcoxon tests.

## Per-Model Coefficients (z-scored predictors)

| Model | n | β_frame (SE) | β_incent (SE) | β_diff (SE) | R² |
|---|---:|---:|---:|---:|---:|
| Claude Opus 4.7 | 180 | -0.0000 (0.0058) | +0.0091 (0.0058) | +0.0068 (0.0058) | 0.021 |
| GPT-5.5 | 180 | +0.0093 (0.0087) | -0.0003 (0.0087) | -0.0034 (0.0087) | 0.007 |
| Gemini 3.1 Pro | 180 | +0.2975 (0.0252) | +0.1659 (0.0252) | -0.0387 (0.0252) | 0.513 |
| Grok 4 | 180 | +0.2342 (0.0241) | +0.1525 (0.0241) | -0.0291 (0.0241) | 0.436 |
| Llama 3.3 70B | 180 | +0.2166 (0.0193) | +0.0225 (0.0193) | -0.0008 (0.0193) | 0.419 |
| DeepSeek V4 Pro | 180 | +0.1235 (0.0199) | +0.0346 (0.0199) | -0.0040 (0.0199) | 0.190 |

Cross-model means (raw signed slopes):
- mean β_frame      = +0.1468 (SE 0.0504)
- mean β_incentive  = +0.0640 (SE 0.0305)
- mean β_difficulty = -0.0115 (SE 0.0074)

## Cross-Model Partition Tests

**(A) Signed: β_frame > β_difficulty (paired across 6 models)**
- Wilcoxon signed-rank (one-sided): W = 20.00, p = 0.0312
- Paired t-test (one-sided): t = 2.806, p = 0.0189

**(B) Magnitude: |β_frame| > |β_difficulty| (paired)**
- Wilcoxon signed-rank (one-sided): W = 19.00, p = 0.0469
- Paired t-test (one-sided): t = 2.886, p = 0.0172

**(C) Incentive slope = 0 (one-sample t, two-sided)**
- t = 2.098, p = 0.0900

**(S) Sign test on |β_frame| > |β_difficulty|**
- 5/6 models satisfy; binomial one-sided p = 0.1094

## Notes & Caveats

- Per-rollout SEs in the OLS step ignore within-cell clustering (5 frame × 3 incentive × 3 difficulty = 45 cells per model, ~4 reps/cell). For more conservative SEs at the per-model level use cluster-robust SEs by cell; the cross-model meta-analysis uses only the point estimates and is unaffected by per-model SE choice.
- All three axes are coded with equal-spacing on level index. If the underlying construct is non-linear (e.g., frame jumps from prohibitive→pro_social are larger than minimal→selfish), the slope estimates compress true effects toward the linear best-fit. This affects all axes equally.
- n=6 models is small for nonparametric paired tests. Wilcoxon at n=6 has minimum achievable one-sided p of 0.0156 (when all 6 differences agree in sign). Paired t-test is more powerful when normality holds approximately; we report both.
- This analysis uses signed slopes, so a strongly *negative* frame slope and a small positive difficulty slope would show as 'frame > difficulty' on |β| but not on signed β. For the §4.3 partition claim the magnitude contrast (B) is the relevant one.

