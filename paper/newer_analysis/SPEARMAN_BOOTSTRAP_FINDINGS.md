# Bootstrap of the rank-instability claim

The paper's headline rank-instability claim is **mean off-diagonal Spearman ρ = 0.055** across the 10 T1–T5 task-pairs on the canonical-6 roster. That number is computed as a correlation between two 6-element rank vectors, repeated 10 times and averaged. With n=6 models per ranking, the per-pair ρ has high sampling variance even at fixed rates. Two questions worth answering with raw-row resampling:

1. How tight is the bootstrap CI around 0.055?
2. Is 0.055 distinguishable from the permutation null where model labels are shuffled within each task?

Source script: [`scripts/05_spearman_bootstrap.py`](scripts/05_spearman_bootstrap.py). B = 2000, cluster-resample where `cluster_id` is populated (committee/debate/sales), row-resample on bargaining/village.

---

## Headline numbers

| Quantity | Point | Bootstrap mean | 95% CI |
|---|---|---|---|
| **All-rows pooled** mean off-diag ρ | **+0.194** | +0.231 | **[+0.067, +0.440]** |
| **Permissive-frame only** mean off-diag ρ | −0.225 | −0.122 | [−0.279, +0.105] |
| **Permutation null** mean off-diag ρ | — | +0.004 | [−0.200, +0.349] |

**Two-sided permutation p (|null| ≥ |observed +0.194|): p = 0.144.**

## What this changes

### The 0.055 headline doesn't reproduce on all-rows pooled.

I read the paper's 0.055 figure as constructed on the **permissive-frame** rate (the figure caption says "the permissive-frame manipulation rate"). On all-rows pooled (averaging over all frames, incentives, difficulties), the same statistic is **+0.194**, not 0.055 — substantially positive, with a bootstrap CI that excludes zero ([+0.067, +0.440]). The paper's framing "rank correlations average ρ = 0.055" is metric-specific; on a more conventional all-rows mean, the rankings show real positive correlation.

### The permissive-frame number reproduces but is unstable.

On permissive-frame only, the point estimate is **−0.225**, not the paper's 0.055. The discrepancy comes from how the missing pairs are handled: at permissive frame, **village saturates at 1.000 across all six models**, making four of the ten task-pair ρ values undefined (constant rank vector). The paper's 0.055 may include those nan pairs as zero or use a different aggregation. My implementation drops them; the four valid pairs average to −0.225.

The bootstrap CI on permissive-only is **[−0.279, +0.105]** — doesn't exclude zero. So the permissive-frame rank instability is consistent with no signal, but is not significantly *negative* either.

### The all-rows ρ is not significantly different from the permutation null.

The two-sided p-value from the permutation test is **p = 0.144**. The null distribution of the mean off-diag ρ has 95% CI [−0.200, +0.349], which fully contains the observed +0.194. So while +0.194 is descriptively positive, it is **not statistically distinguishable from random model-label assignment within each task** at conventional thresholds.

This is the cleanest summary: with only 6 models per ranking and 10 task-pairs, the mean off-diag ρ statistic has so much sampling variance that even a correlation as large as +0.194 is consistent with chance.

## Per-pair detail

Several individual pairs *do* have CIs excluding zero, even though the mean across all 10 doesn't:

| Pair | ρ | 95% CI | Excludes 0? |
|---|---|---|---|
| bargaining vs village | **+0.771** | [+0.314, +1.000] | ✓ |
| village vs committee | **+0.657** | [+0.086, +0.943] | ✓ |
| bargaining vs committee | **+0.600** | [+0.314, +0.943] | ✓ |
| debate vs sales | −0.771 | [−0.943, +0.143] | (close, includes 0) |
| debate vs village | +0.486 | [−0.143, +0.829] | no |
| bargaining vs debate | +0.143 | [−0.257, +0.771] | no |
| sales vs committee | +0.086 | [−0.116, +0.771] | no |
| bargaining vs sales | +0.200 | [−0.257, +0.600] | no |
| village vs sales | −0.257 | [−0.486, +0.429] | no |
| debate vs committee | +0.029 | [−0.600, +0.429] | no |

So model rankings on bargaining, village, and committee correlate strongly (ρ around +0.6 to +0.8, CIs robustly positive). Debate and sales pull the average back down — the often-cited debate-vs-sales ρ = −0.77 is real as a point estimate but its CI just barely includes zero.

## Interpretation

The paper's "rank instability" claim is doing work it can't quite support at the strength it's stated. Three more accurate framings:

1. **"Model rankings are weakly positively correlated across tasks (mean ρ ≈ +0.19, CI excluding zero on raw rates) but the correlation is not distinguishable from chance under a permutation null (p = 0.14)."** This is the most honest summary.

2. **"Three pairs of tasks (bargaining/village, village/committee, bargaining/committee) show robust positive rank correlation; the other seven are noisy."** This identifies where signal exists.

3. **"The mean off-diagonal ρ is small relative to its sampling variance with n=6 models per ranking, regardless of the actual underlying correlation."** This is a small-sample point — the descriptive statistic is unstable even when the underlying truth might be either zero or moderately positive.

The task × model interaction F-test (paper's stronger inferential claim, F ≈ 24, p ≈ 2.4e-109) is not at risk from this. The interaction *is* large; rankings differ across tasks in ways that aren't explained by additive main effects. But "rankings are essentially uncorrelated" overstates the descriptive ρ. Rankings are *weakly* correlated, and the noise in the descriptive statistic is large enough that a permutation test doesn't reject the null.

## Output files

- [`out/05_spearman_bootstrap.csv`](out/05_spearman_bootstrap.csv) — per-pair ρ + bootstrap CI.
- [`out/05_spearman_bootstrap_summary.txt`](out/05_spearman_bootstrap_summary.txt) — headline numbers.

## Caveats

- Cluster bootstrap on committee/debate/sales; row bootstrap on bargaining/village (no cluster_id populated). The CIs for bargaining/village pairs are slightly tighter than they would be under a properly clustered scheme — but bargaining/village have no scenario_group at all, so this is the best available.
- Permutation null shuffles model labels within each task. This preserves each task's marginal rate distribution (so the null retains task-difficulty heterogeneity) but breaks any cross-task model-identity signal. Standard test for the question "is the cross-task correlation real or chance?"
- B = 2000 throughout. Doubling to 5000 didn't move the CIs more than a couple percentage points in spot checks.
