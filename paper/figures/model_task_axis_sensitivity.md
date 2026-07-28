# Model x Environment Axis-Sensitivity OLS

## Specification

For each model-environment pair, fit `manipulation_metric ~ frame + incentive + difficulty` with ordered integer coding:
- frame: prohibitive=0, pro_social=1, minimal=2, selfish=3, permissive=4
- incentive: none=0, moderate=1, high=2
- difficulty: low=0, medium=1, high=2

Difficulty-advantage score per row:
`Delta_D = |beta_difficulty| - max(|beta_frame|, |beta_incentive|)`

## 36-row Summary

- Assertive rows (`debate`, `sales`, `committee`): 17/18 have `Delta_D > 0`; mean=+0.285, median=+0.053
- Commissive rows (`bargaining`, `village`, `inbox`): 18/18 have `Delta_D < 0`; mean=-0.155, median=-0.148
- OLS `Delta_D ~ 1 + assertive` coefficient on `assertive`: +0.440 (i.i.d. SE=0.300, t=+1.467, p=0.152)
- Task-cluster-robust SE (6 environment clusters) on `assertive`: SE=0.223, t=+1.968, p=0.106
- Held-out T6 (`inbox`) check: 6/6 rows have `Delta_D < 0`; mean=-0.092, median=-0.117

## Per Model x Environment Coefficients

| Task | Type | Model | n | beta_F | beta_I | beta_D | Delta_D |
|---|---|---|---:|---:|---:|---:|---:|
| bargaining | commissive | Claude Opus 4.7 | 900 | +0.0656 | +0.1592 | -0.0142 | -0.1450 |
| bargaining | commissive | GPT-5.5 | 900 | +0.1611 | +0.3408 | +0.0533 | -0.2875 |
| bargaining | commissive | Gemini 3.1 Pro | 900 | +0.1225 | +0.3967 | +0.0325 | -0.3642 |
| bargaining | commissive | Grok 4 | 900 | +0.1383 | +0.2375 | +0.0725 | -0.1650 |
| bargaining | commissive | Llama 3.3 70B | 900 | +0.0769 | +0.0217 | -0.0000 | -0.0769 |
| bargaining | commissive | DeepSeek V4 Pro | 899 | +0.1063 | +0.3463 | +0.0297 | -0.3167 |
| debate | assertive | Claude Opus 4.7 | 690 | +0.0007 | -0.0028 | +0.0086 | +0.0058 |
| debate | assertive | GPT-5.5 | 690 | -0.0020 | -0.0108 | +0.0204 | +0.0096 |
| debate | assertive | Gemini 3.1 Pro | 690 | +0.0042 | -0.0024 | +0.0152 | +0.0109 |
| debate | assertive | Grok 4 | 690 | +0.0014 | +0.0016 | +0.0394 | +0.0377 |
| debate | assertive | Llama 3.3 70B | 690 | -0.0007 | -0.0033 | +0.0568 | +0.0535 |
| debate | assertive | DeepSeek V4 Pro | 690 | +0.0039 | -0.0064 | +0.0313 | +0.0249 |
| village | commissive | Claude Opus 4.7 | 90 | +0.1063 | +0.0246 | -0.0049 | -0.1014 |
| village | commissive | GPT-5.5 | 89 | +0.1849 | +0.1220 | -0.0529 | -0.1319 |
| village | commissive | Gemini 3.1 Pro | 90 | +0.2545 | +0.1046 | -0.0470 | -0.2075 |
| village | commissive | Grok 4 | 90 | +0.2135 | +0.0316 | -0.0036 | -0.2098 |
| village | commissive | Llama 3.3 70B | 87 | +0.1044 | +0.0218 | +0.0083 | -0.0961 |
| village | commissive | DeepSeek V4 Pro | 83 | +0.1359 | +0.0142 | +0.0107 | -0.1251 |
| sales | assertive | Claude Opus 4.7 | 225 | +0.0200 | -0.0027 | +0.0547 | +0.0347 |
| sales | assertive | GPT-5.5 | 225 | -0.0004 | +0.0013 | +0.0213 | +0.0200 |
| sales | assertive | Gemini 3.1 Pro | 225 | +0.0471 | +0.0213 | +0.1480 | +0.1009 |
| sales | assertive | Grok 4 | 225 | +0.0164 | +0.0027 | +0.0693 | +0.0529 |
| sales | assertive | Llama 3.3 70B | 225 | +0.0347 | +0.0107 | +0.1133 | +0.0787 |
| sales | assertive | DeepSeek V4 Pro | 225 | +0.0378 | +0.0187 | +0.1147 | +0.0769 |
| committee | assertive | Claude Opus 4.7 | 179 | +1.2295 | +0.5184 | -3.9835 | +2.7539 |
| committee | assertive | GPT-5.5 | 180 | +1.1877 | +0.7806 | -2.6395 | +1.4517 |
| committee | assertive | Gemini 3.1 Pro | 180 | +3.6838 | +3.6486 | +0.1245 | -3.5593 |
| committee | assertive | Grok 4 | 176 | +1.5623 | +0.5817 | -2.2424 | +0.6801 |
| committee | assertive | Llama 3.3 70B | 180 | +0.7826 | +0.0493 | -1.9364 | +1.1538 |
| committee | assertive | DeepSeek V4 Pro | 180 | +1.2213 | +0.7917 | -3.3662 | +2.1449 |
| inbox | commissive | Claude Opus 4.7 | 180 | +0.0000 | +0.0111 | +0.0083 | -0.0028 |
| inbox | commissive | GPT-5.5 | 180 | +0.0066 | -0.0003 | -0.0042 | -0.0024 |
| inbox | commissive | Gemini 3.1 Pro | 180 | +0.2104 | +0.2031 | -0.0475 | -0.1629 |
| inbox | commissive | Grok 4 | 180 | +0.1656 | +0.1868 | -0.0356 | -0.1512 |
| inbox | commissive | Llama 3.3 70B | 180 | +0.1531 | +0.0275 | -0.0009 | -0.1522 |
| inbox | commissive | DeepSeek V4 Pro | 180 | +0.0873 | +0.0424 | -0.0049 | -0.0824 |
