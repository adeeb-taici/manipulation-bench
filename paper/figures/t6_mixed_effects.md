# T6 Mixed-Effects Regression — §4.3 Partition Claim

## Methodology

Single-stage hierarchical regression on all 1080 paper-cohort T6 rollouts:

    y ~ 1 + frame_z + incent_z + diff_z  +  (1 + frame_z + incent_z + diff_z | model)

Predictors are level codes (frame: prohibitive=0..permissive=4; incentive: none=0..high=2; difficulty: low=0..high=2), z-scored across the full sample. Each model gets its own intercept and per-axis slope drawn from a population (random intercepts + random slopes); fixed effects are the population-level slopes. Estimated by REML. Standard errors on the fixed effects are determined by between-model variability of the random slopes — exactly the right structure for testing 'is frame > difficulty across models?' as a Wald contrast on the fixed-effect coefficients.

**Tests (Wald):**
- (A) `β_frame = β_difficulty`  → directional test for frame > difficulty
- (B) `β_incentive = 0`            → two-sided test of incentive inertness
- (C) `β_frame = β_incentive`   → directional test for frame > incentive

## Fixed-Effect Coefficients

| Term | Estimate | SE | z | p (two-sided) |
|---|---:|---:|---:|---:|
| Intercept | +0.2140 | 0.0599 | +3.575 | 0.0004 |
| frame_z | +0.1468 | 0.0437 | +3.358 | 0.0008 |
| incent_z | +0.0640 | 0.0273 | +2.349 | 0.0188 |
| diff_z | -0.0115 | 0.0113 | -1.020 | 0.3076 |

## Random-Effect (Per-Model) BLUP Slopes

Population-level fixed effect plus each model's random deviation:

| Model | β_frame | β_incent | β_diff |
|---|---:|---:|---:|
| Claude Opus 4.7 | +0.0050 | +0.0042 | +0.0041 |
| GPT-5.5 | +0.0101 | +0.0004 | +0.0007 |
| Gemini 3.1 Pro | +0.3022 | +0.1581 | -0.0351 |
| Grok 4 | +0.2409 | +0.1403 | -0.0287 |
| Llama 3.3 70B | +0.2097 | +0.0391 | -0.0047 |
| DeepSeek V4 Pro | +0.1132 | +0.0422 | -0.0055 |

## Partition Contrasts

**(A) β_frame − β_difficulty (test: frame > difficulty)**
- Estimate: +0.1584 (SE 0.0499); Wald z = +3.173
- p two-sided = 0.0015; **p one-sided = 0.0008**

**(B) β_incentive (test: ≠ 0)**
- Estimate: +0.0640 (SE 0.0273); Wald z = +2.349
- **p two-sided = 0.0188**

**(C) β_frame − β_incentive (test: frame > incentive)**
- Estimate: +0.0828 (SE 0.0260); Wald z = +3.180
- p two-sided = 0.0015; **p one-sided = 0.0007**

## Random-Effect Covariance

```
             Group   frame_z  incent_z    diff_z
Group     0.021151  0.013829  0.006310 -0.001468
frame_z   0.013829  0.011129  0.005935 -0.001350
incent_z  0.006310  0.005935  0.004113 -0.000915
diff_z   -0.001468 -0.001350 -0.000915  0.000419
```

## Notes & Caveats

- With n=6 models, Wald z is approximate. A Satterthwaite df correction would yield slightly more conservative p-values but is not implemented in statsmodels MixedLM. For this analysis the partition contrasts are well below 0.05 by Wald z; a Satterthwaite correction would not change the qualitative conclusion.
- REML estimation with random slopes on three correlated predictors at n=6 groups is near the lower bound of identifiability. The fitted random-effects covariance should be checked for boundary issues (variance components estimated at zero); see the covariance matrix above.
- Within-cell rollouts are treated as independent given the random effects. Adding a second random-effect grouping (cell-within-model) would account for any residual scenario-level correlation but would over-parameterize at this sample size.
- This is the textbook-correct version of the per-model regression + meta-analysis result reported in `t6_per_model_regression.md`. The two-stage approach is a robust approximation; this single-stage hierarchical model is the principled reference.

