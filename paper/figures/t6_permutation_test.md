# T6 Inbox Triage — Permutation Test for the Assertive/Commissive Partition

## Methodology

The paper's §4.3 partition (assertive vs. commissive manipulation) was constructed by inspecting T1–T5 outcomes; T6 was pre-registered as a held-out test. The original joint-probability calculation (~0.016, or 0.011 with T6) treated the partition as if it were specified ex ante and is therefore methodologically problematic. This note replaces that calculation with a permutation-based p-value computed *over T6 alone*.

**Test statistics (pre-registered conditions, evaluated on the absolute slopes from Table 5):**
- `cond1`: aggregate frame dominance over difficulty — `mean(|frame|) / mean(|difficulty|) >= 2`
- `cond2`: per-model frame dominance — at least 4 of 6 models have `|frame| > |difficulty|`
- `cond3`: incentive inertness — `mean(|incentive|) < 0.10`

**Null model.** For each of N permutations, axis labels {frame, incentive, difficulty} are permuted *independently within each model row* of the absolute-slope table; the same three conditions are then evaluated. The empirical p-value is the fraction of permutations satisfying all three jointly. Random seed: `np.random.default_rng(42)`.

**Bootstrap variant.** Where the eval log is available, we additionally resample scenarios with replacement within each (model, axis, level) cell, recompute per-axis slopes, and re-evaluate the same three conditions. This addresses sampling variability in the slope estimates themselves rather than only label assignment.

## Observed Test Statistics (real data)

| Model | |Frame| | |Incentive| | |Difficulty| |
|---|---:|---:|---:|
| Claude Opus 4.7 | 0.000 | 0.011 | 0.008 |
| GPT-5.5 | 0.007 | 0.000 | 0.004 |
| Gemini 3.1 Pro | 0.210 | 0.203 | 0.047 |
| Grok 4 | 0.166 | 0.187 | 0.036 |
| Llama 3.3 70B | 0.153 | 0.028 | 0.001 |
| DeepSeek V4 Pro | 0.087 | 0.042 | 0.005 |

- mean(|frame|)      = 0.1038
- mean(|incentive|)  = 0.0785
- mean(|difficulty|) = 0.0169
- frame/difficulty ratio = 6.145
- # models with |frame| > |difficulty| = 5/6
- cond1 satisfied: True; cond2 satisfied: True; cond3 satisfied: True

## Permutation P-Values

- N = 100,000 permutations, seed = 42
- **Joint p-value (cond1 ∧ cond2 ∧ cond3): 0.08777**
- Marginal p(cond1, frame/difficulty ≥ 2×): 0.11687
- Marginal p(cond2, ≥4/6 models |frame|>|diff|): 0.34315
- Marginal p(cond3, mean |incentive| < 0.10): 0.93783

## Bootstrap P-Values (per-cell rollout resampling)

- N = 10,000 bootstrap iterations, seed = 42
- Joint p-value: 0.94900
- Marginal p(cond1): 0.99070
- Marginal p(cond2): 0.99470
- Marginal p(cond3): 0.96260

Note: the bootstrap is *not* a null-hypothesis test — it characterizes the sampling distribution of the test statistics under the observed data. A small bootstrap 'p' here reflects that the partition holds robustly under resampling, not that it is unlikely under chance. The permutation p-value above is the inferential quantity.

## Caveats

- The within-row permutation null assumes the three axes are exchangeable for a given model. This is a reasonable null for 'is the assertive/commissive partition predicted by T6?' but does not test whether the *direction* of frame > difficulty is exogenously meaningful.
- The slopes are linear-regression coefficients over ordered levels (5 frame levels, 3 incentive, 3 difficulty); permuting cells within a row is sensible only because we compare *absolute* slopes.
- The conditions were specified before looking at T6 outcomes (they restate the assertive/commissive partition derived from T1–T5). Within T6 itself this is a single pre-registered three-part test; no multiple-comparisons correction is needed.

