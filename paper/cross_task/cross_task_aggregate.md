# Cross-task response-surface aggregate

Auto-generated from each task's `paper/<task>/analysis/prereg_results.json` (T1-T4) and embedded T5 numbers (since T5 uses a different per-model JSON shape). See [../../experiments/cross_task_analysis.py](../../experiments/cross_task_analysis.py).

## Per-task aggregate: mean |slope| across 6 models

| Task | Headline metric | Frame | Incentive | Difficulty | Dominant axis | Dominance ratio (top/2nd) |
|---|---|---:|---:|---:|---|---:|
| T1 Bargaining | `lied_rate` | 0.112 | 0.250 | 0.034 | **incentive** | 2.2× |
| T2 Debate | `manipulation_occurred` | 0.007 | 0.014 | 0.056 | **difficulty** | 4.0× |
| T3 Village | `exploitation_rate` | 0.168 | 0.054 | 0.023 | **frame** | 3.1× |
| T4 Sales | `manipulation_rate` | 0.026 | 0.010 | 0.087 | **difficulty** | 3.3× |
| T5 Committee | `initial_rating_bias` | 0.327 | 0.180 | 0.603 | **difficulty** | 1.8× |

Notes on metric scales:
- T1 / T2 / T3 / T4 use rates in [0, 1]; slopes are also in rate-per-axis-step units.
- T5 uses bias on a 0–20 rating scale; its slopes are in standardized (per-pooled-SD) units, larger in absolute magnitude than the rate-based slopes.
- For cross-task comparison of *which axis dominates within a task*, the relative size of slopes within a row is what matters, not the absolute number.

## Per-model 15-dim profile vector

Each model's profile = 5 tasks × 3 axes = 15 entries (signed slopes).

### Claude-Opus-4.7

| Task | Frame slope | Incentive slope | Difficulty slope |
|---|---:|---:|---:|
| T1 Bargaining | +0.066 | -0.159 | -0.014 |
| T2 Debate | -0.001 | -0.007 | -0.003 |
| T3 Village | +0.106 | +0.025 | -0.005 |
| T4 Sales | +0.020 | -0.003 | +0.055 |
| T5 Committee | +0.281 | +0.117 | -0.911 |

### GPT-5.5

| Task | Frame slope | Incentive slope | Difficulty slope |
|---|---:|---:|---:|
| T1 Bargaining | +0.161 | -0.341 | +0.053 |
| T2 Debate | +0.010 | +0.017 | -0.037 |
| T3 Village | +0.186 | +0.122 | -0.059 |
| T4 Sales | -0.000 | +0.001 | +0.021 |
| T5 Committee | +0.307 | +0.202 | -0.676 |

### Gemini-3.1-Pro

| Task | Frame slope | Incentive slope | Difficulty slope |
|---|---:|---:|---:|
| T1 Bargaining | +0.123 | -0.397 | +0.033 |
| T2 Debate | -0.007 | +0.009 | -0.053 |
| T3 Village | +0.255 | +0.105 | -0.047 |
| T4 Sales | +0.047 | +0.021 | +0.148 |
| T5 Committee | +0.434 | +0.430 | +0.016 |

### Grok-4

| Task | Frame slope | Incentive slope | Difficulty slope |
|---|---:|---:|---:|
| T1 Bargaining | +0.138 | -0.237 | +0.072 |
| T2 Debate | -0.009 | +0.004 | -0.086 |
| T3 Village | +0.213 | +0.032 | -0.004 |
| T4 Sales | +0.016 | +0.003 | +0.069 |
| T5 Committee | +0.372 | +0.135 | -0.537 |

### Llama-3.3-70B

| Task | Frame slope | Incentive slope | Difficulty slope |
|---|---:|---:|---:|
| T1 Bargaining | +0.077 | -0.022 | +0.000 |
| T2 Debate | +0.012 | +0.024 | -0.106 |
| T3 Village | +0.105 | +0.025 | +0.011 |
| T4 Sales | +0.035 | +0.011 | +0.113 |
| T5 Committee | +0.287 | +0.018 | -0.713 |

### DeepSeek-V4-Pro

| Task | Frame slope | Incentive slope | Difficulty slope |
|---|---:|---:|---:|
| T1 Bargaining | +0.106 | -0.346 | +0.029 |
| T2 Debate | -0.002 | +0.022 | -0.050 |
| T3 Village | +0.141 | +0.013 | +0.011 |
| T4 Sales | +0.038 | +0.019 | +0.115 |
| T5 Committee | +0.280 | +0.181 | -0.765 |
