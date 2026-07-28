# T6 Hierarchical Analysis — §4.3 Partition Claim

Three approaches to the same population-level question — "is the frame slope larger than the difficulty slope across the population of models?" — fit on all 1080 paper-cohort T6 rollouts. Predictors: z-scored level codes (frame: prohibitive=0..permissive=4; incentive: none=0..high=2; difficulty: low=0..high=2).

Three contrasts, identical across approaches:
- (A) `β_frame − β_difficulty > 0` (one-sided)
- (B) `β_incentive ≠ 0` (two-sided)
- (C) `β_frame − β_incentive > 0` (one-sided)

## Approach 1 — Mixed-Effects (REML)

Specification used: **random intercept + frame slope only**.

Convergence/fit warnings caught:
- `Maximum Likelihood optimization failed to converge. Check mle_retvals`
- `MixedLM optimization failed, trying a different optimizer may help.`
- `Gradient optimization failed, |grad| = 4.241155`

Fixed effects:

| Term | Estimate | SE | z | p (two-sided) |
|---|---:|---:|---:|---:|
| Intercept | +0.2140 | 0.0680 | +3.145 | 0.0017 |
| frame_z | +0.1468 | 0.0440 | +3.335 | 0.0009 |
| incent_z | +0.0640 | 0.0079 | +8.109 | 0.0000 |
| diff_z | -0.0115 | 0.0079 | -1.460 | 0.1443 |

Partition contrasts:

- (A) frame > diff: Δ = +0.1584, SE = 0.0447, z = +3.540, **one-sided p = 0.0002**
- (B) incent ≠ 0: β = +0.0640, SE = 0.0079, z = +8.109, **two-sided p = 0.0000**
- (C) frame > incent: Δ = +0.0828, SE = 0.0447, z = +1.851, **one-sided p = 0.0321**

## Approach 2a — OLS, Pooled Slopes, Cluster-Robust SEs (clusters=model)

Single slope per axis, model dummies absorb intercept differences. SEs use the Liang–Zeger cluster-robust sandwich estimator with model as the cluster variable.

Pooled slopes:

| Term | Estimate | Cluster SE | z | p (two-sided) |
|---|---:|---:|---:|---:|
| frame_z | +0.1468 | 0.0506 | +2.903 | 0.0037 |
| incent_z | +0.0640 | 0.0306 | +2.090 | 0.0366 |
| diff_z | -0.0115 | 0.0074 | -1.561 | 0.1186 |

Partition contrasts:

- (A) frame > diff: Δ = +0.1584, SE = 0.0567, z = +2.795, **one-sided p = 0.0026**
- (B) incent ≠ 0: β = +0.0640, SE = 0.0306, z = +2.090, **two-sided p = 0.0366**
- (C) frame > incent: Δ = +0.0828, SE = 0.0310, z = +2.672, **one-sided p = 0.0038**

## Approach 2b — OLS, Full Model×Axis Interactions, Cluster-Robust SEs

> **Do not cite the numbers in this subsection.** The saturated
> model×axis interaction specification has as many slope parameters as the
> cluster structure can support, so the Liang–Zeger meat matrix is
> rank-deficient and the contrast SEs collapse to 0.0000. The reported
> z-statistics (order 10¹⁴–10¹⁵) and the resulting p = 0.0000 are numerical
> artifacts of dividing by ~0, not evidence. The point estimates (Δ = +0.1584,
> +0.0640, +0.0828) are correct and match the other approaches — it is only the
> standard errors and p-values that are degenerate. Use Approach 2a (pooled
> slopes, cluster-robust) or Approach 1 (mixed-effects) for inference, and note
> that with G = 6 clusters even those are low-powered.

Each model gets its own per-axis slope (saturated interaction model). Population-level slopes are recovered as the unweighted cross-model average via linear contrasts. Cluster-robust SEs by model.

Partition contrasts (cross-model averages):

- (A) frame > diff: Δ = +0.1584, SE = 0.0000, z = +834846633217196.000, **one-sided p = 0.0000**
- (B) incent ≠ 0: β = +0.0640, SE = 0.0000, z = +2125575639830099.750, **two-sided p = 0.0000**
- (C) frame > incent: Δ = +0.0828, SE = 0.0000, z = +864576495726955.875, **one-sided p = 0.0000**

## Comparison: Two-Stage Paired-t (from t6_per_model_regression.py)

- (A) frame > diff: t = +2.806, **one-sided p = 0.0189**
- (B) incent ≠ 0: t = +2.098, **two-sided p = 0.0900**
- (C) frame > incent: t = +2.682, **one-sided p = 0.0219**

## Summary Table — All Four Approaches

| Approach | A: frame>diff | B: incent≠0 | C: frame>incent |
|---|---:|---:|---:|
| Mixed-effects (random intercept + frame slope only) | 0.0002 | 0.0000 | 0.0321 |
| OLS pooled, cluster-robust SE | 0.0026 | 0.0366 | 0.0038 |
| OLS interactions, cluster-robust SE | 0.0000 | 0.0000 | 0.0000 |
| Two-stage paired t (n=6) | 0.0189 | 0.0900 | 0.0219 |

## Interpretation

All four approaches address the same population-level question — whether the partition claim (frame > difficulty, frame > incentive, incentive small) holds across the model population — using different machinery for the standard errors. With a balanced design (180 rollouts × 6 models, fully crossed cells) they should give similar answers, and the agreement (or disagreement) across them is itself a robustness diagnostic.

- The **mixed-effects** approach is the textbook reference, but with n=6 groups the random-effects covariance is hard to estimate; we use a reduced specification.
- The **cluster-robust OLS** approaches give the same point estimates as mixed-effects for the population-mean slopes (the data is balanced) but compute SEs from the between-cluster variability via a sandwich estimator. No convergence issues.
- The **two-stage paired-t** is the simplest and most transparent: fit per-model regressions, then test the resulting 6-vector of coefficients with paired tests. Lower power than the cluster-robust approaches but the easiest to defend.

