# T6 Permutation Test — Extended Cohort

Re-runs the §4.3 partition permutation test on the expanded T6 model set: the 6 paper-cohort frontier models plus 9 smaller models from the OpenAI and Anthropic sweeps (GPT-4.1 family, GPT-5.4 mini/nano, Sonnet 3.7 / 4.6, Haiku 3.5 / 4.5). Methodology is identical to `paper/figures/t6_permutation_test.md`: within-row axis-label permutation, three pre-registered conditions (frame/difficulty ≥ 2× aggregate, frame > difficulty in ≥ ⌈2n/3⌉ models individually, mean |incentive| < 0.10), 100,000 permutations, seed 42.

## Paper cohort (n=6, original test)

### Paper cohort (n=6 models)

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
- # models with |frame|>|difficulty| = 5/6 (need ≥4 for cond2)
- cond1: True; cond2: True; cond3: True

**Permutation test:**
- N=100,000, joint p = **0.08777**
- marginals — cond1: 0.11687, cond2: 0.34315, cond3: 0.93783

**Bootstrap (per-cell rollout resampling):**
- N=10,000, joint robustness fraction = 0.95110
- marginals — cond1: 0.99060, cond2: 0.99490, cond3: 0.96430

## Extended cohort (n=15, paper + small-model sweep)

### Extended cohort (n=15 models)

| Model | |Frame| | |Incentive| | |Difficulty| |
|---|---:|---:|---:|
| Claude Opus 4.7 | 0.000 | 0.011 | 0.008 |
| GPT-5.5 | 0.007 | 0.000 | 0.004 |
| Gemini 3.1 Pro | 0.210 | 0.203 | 0.047 |
| Grok 4 | 0.166 | 0.187 | 0.036 |
| Llama 3.3 70B | 0.153 | 0.028 | 0.001 |
| DeepSeek V4 Pro | 0.087 | 0.042 | 0.005 |
| GPT-4.1 | 0.205 | 0.083 | 0.010 |
| GPT-4.1 mini | 0.150 | 0.050 | 0.260 |
| GPT-4.1 nano | 0.004 | 0.021 | 0.119 |
| GPT-5.4 mini | 0.004 | 0.000 | 0.046 |
| GPT-5.4 nano | 0.004 | 0.005 | 0.126 |
| Sonnet 4.6 | 0.058 | 0.012 | 0.013 |
| Sonnet 3.7 | 0.102 | 0.034 | 0.029 |
| Haiku 4.5 | 0.099 | 0.049 | 0.025 |
| Haiku 3.5 | 0.100 | 0.035 | 0.054 |

- mean(|frame|)      = 0.0899
- mean(|incentive|)  = 0.0507
- mean(|difficulty|) = 0.0523
- frame/difficulty ratio = 1.720
- # models with |frame|>|difficulty| = 10/15 (need ≥10 for cond2)
- cond1: False; cond2: True; cond3: True

**Permutation test:**
- N=100,000, joint p = **0.02741**
- marginals — cond1: 0.03301, cond2: 0.15143, cond3: 0.99739

**Bootstrap (per-cell rollout resampling):**
- N=10,000, joint robustness fraction = 0.00580
- marginals — cond1: 0.00730, cond2: 0.48250, cond3: 1.00000

## Caveats

- The cond2 threshold is generalized from "≥4 of 6" to "≥⌈2n/3⌉" so the per-model majority condition has the same intent (clear majority of models) at both cohort sizes.
- Small-model sweeps may have different per-cell sample counts than the paper cohort (180 samples/model). The slope estimator is the same linear regression over level means regardless of cell n; bootstrap accounts for sampling variability per cell.
- Extending the cohort post-hoc is itself a researcher-degree-of-freedom decision. The paper-cohort number remains the canonical pre-registered test; the extended-cohort number is reported as a sensitivity analysis.

