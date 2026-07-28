# Table 3 (v2) — Per-task variance decomposition

Replaces the v1 mean-|slope| aggregate. η² = SS_term / SS_total from
Type II ANOVA on `y ~ C(model) + C(frame) + C(incentive) + C(difficulty)`.
Cluster-robust SEs where item structure exists (T2/T4/T5).

| Task | n | SE | η²(model) | η²(frame) | η²(incentive) | η²(difficulty) | residual | dominant axis |
|---|---:|---|---:|---:|---:|---:|---:|---|
| T1 Bargaining | 5399 | HC3 | 0.0763 | 0.1653 | **0.2641** | 0.0042 | 0.4900 | incentive |
| T2 Debate | 4140 | cluster_on_claim_id | 0.0046 | 0.0013 | 0.0016 | **0.0017** | 0.9908 | difficulty |
| T3 Village | 529 | HC3 | 0.1583 | **0.5869** | 0.0132 | 0.0015 | 0.2401 | frame |
| T4 Sales | 1350 | cluster_on_scenario_id | 0.0129 | 0.0073 | 0.0077 | **0.0189** | 0.9532 | difficulty |
| T5 Committee | 1075 | cluster_on_slate_id | 0.2097 | **0.1685** | 0.0375 | 0.0366 | 0.5477 | frame |

**Note**: T2 Debate has 99% residual variance — no axis explains
more than 0.2% of variance. The 'dominant axis' designation for T2
is between three nearly-tied near-zero numbers and should not be
interpreted as a real signal. v1 reported T2 as 'difficulty-dominant'
based on the 0.061 mean |slope|, which this v2 view does not support.