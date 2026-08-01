# Reduced-protocol retrospective

Does a staged reduced design recover the conclusions of the complete sweep? This filters the
frozen six-model results to the cells a staged protocol would have run, recomputes the published
quantities on that subset, and compares. **No model calls** — filtering and reanalysis only.

Reproduce: `python paper/cross_task/scripts/reduced_protocol_retrospective.py`

---

## Pre-specified recovery criteria

*Written into the script before any subset quantity was computed.*

> **C1 Dominant axis.** The reduced design assigns the SAME dominant axis as the full design in
> all 6 environments. Dominant axis = argmax over axes of the mean absolute per-model slope, the
> aggregation `cross_task_analysis.py` uses. Slopes are recomputed on reduced cells with the
> published per-task estimator. On endpoint-reduced axes the slope becomes a two-point
> difference, rescaled by the original index span so it stays in per-step units.
>
> **C2 Directional partition.** The environment-level Δ_D sign pattern matches the full design's
> 3 positive / 3 negative, where
> Δ_D = mean|difficulty slope| − max(mean|frame slope|, mean|incentive slope|).
>
> **C3 Rank instability.** Mean off-diagonal Spearman ρ on the reduced design stays within ±0.15
> of the full-design value of +0.055 (i.e. still nowhere near a stable trait), AND the most
> negative pair remains strongly negative.
>
> **C4 Cost.** Report the exact fraction of the full design used, in cells and in
> model-trajectory evaluations, overall and per environment.
>
> A criterion that fails is reported plainly, with the cells that carried the lost information
> identified. A failed recovery is a finding about the protocol.

## Protocol and cell arithmetic (confirmed against the design)

The design is 5 frames × 3 incentives × 3 difficulties = **45 cells**, so the posted arithmetic
is correct:

| Arm | Cells | Of 45 | Environments |
|---|---|---:|---|
| Commissive — all 5 frames × incentive endpoints × difficulty endpoints | 5×2×2 = **20** | 44.4% | T1 Bargaining, T3 Village, T6 Inbox |
| Assertive — all 3 difficulties × frame endpoints × incentive endpoints | 3×2×2 = **12** | 26.7% | T2 Debate, T4 Sales, T5 Committee |

**Endpoint mapping** (a choice, and therefore part of the protocol's definition):

| Axis | Levels | Endpoints | Index span |
|---|---|---|---:|
| frame | prohibitive, pro_social, minimal, selfish, permissive | **prohibitive, permissive** | 4 |
| incentive | none, moderate, high | **none, high** | 2 |
| difficulty | low, medium, high | **low, high** | 2 |

### Two estimator points that materially affect the answer

**Index-span rescaling is required.** The published `slope()` regresses on *positions*
(`xs = list(range(n))`). Handing it a 2-element endpoint list returns a raw difference — 2×
too large for incentive/difficulty and **4× too large for frame** relative to the full-design
per-step slope. Uncorrected, this inflates exactly the axes the protocol reduced and biases the
dominant-axis test toward them. Each endpoint-reduced slope is therefore divided by its original
index span.

**Endpoint reduction is slope-preserving for 3-level axes, but not for frame.** For an evenly
spaced 3-level axis the full-design OLS slope is exactly `(y_high − y_none)/2` — it does not
depend on the middle level. So reducing incentive or difficulty to endpoints changes nothing in
estimator form; only the cell means shift, because fewer cells are averaged into each. Frame has
5 levels and its OLS slope weights all five
(`(−2y₀ − y₁ + y₃ + 2y₄)/10` vs the endpoint-only `(y₄ − y₀)/4`), so **frame reduction is the one
place this protocol genuinely discards slope information** — and it is the assertive arm that
reduces frame.

### Estimator reuse

The published per-task `model_sensitivity_slopes(rows)` is called **verbatim** for T1–T4 and T6,
with only the module-level level tuples restricted to the retained levels. T5 has no such function
and no `prereg_results.json` (`cross_task_analysis.py` carries a hardcoded map instead), so T5 uses
the estimator from `task5_prereg_analysis.py`, validated against the committed `T5_SLOPES` to
0.0005 in `model_distance_matrix.py`. C3 uses the committed v1 pipeline
(`ranking_stability_v2._per_task_means(..., use_v1_metric=True)`) on a filtered corpus, gated on
reproducing +0.0552.

**T5 scale correction applied.** The per-sample 0–10 vs 0–20 correction (max rating ≤ 10 ⇒ ×2) is
applied to Committee before any cross-model quantity, consistent with how T5 is now reported.

---

## Results

| Environment | Arm | Full dominant | Reduced dominant | Match | Reduced top:2nd | Expansion trigger | Evals used vs full |
|---|---|---|---|:---:|---:|:---:|---|
| T1 Bargaining | commissive | incentive | incentive | ✅ | 2.55 | no | 2,399 / 5,399 (44.4%) |
| T2 Debate | assertive | difficulty | difficulty | ✅ | 2.01 | no | 1,104 / 4,140 (26.7%) |
| T3 Village | commissive | frame | frame | ✅ | 3.00 | no | 235 / 529 (44.4%) |
| T4 Sales | assertive | difficulty | difficulty | ✅ | 4.00 | no | 360 / 1,350 (26.7%) |
| T5 Committee | assertive | difficulty | difficulty | ✅ | 1.85 | no | 288 / 1,075 (26.8%) |
| **T6 Inbox** | commissive | frame | frame | ✅ | **1.44** | **YES** | 480 / 1,080 (44.4%) |
| **TOTAL** | | | | **6/6** | | **1 of 6** | **4,866 / 13,573 (35.9%)** |

**C1 — dominant axis: PASS.** 6/6 environments recover the full-design dominant axis.

**C2 — directional partition: PASS.** 6/6 signs match; the 3-positive / 3-negative environment
pattern is preserved. Δ_D full → reduced: T1 −0.2168 → −0.2364 · T2 +0.0420 → +0.0237 ·
T3 −0.1448 → −0.1425 · T4 +0.0608 → +0.0675 · T5 +0.2881 → +0.2696 · T6 −0.0869 → −0.0903.

**C3 — rank instability: PASS, but marginally, and this is the weakest result here.** Mean
off-diagonal ρ moves **+0.0552 → +0.1950**, a delta of **+0.1398 against a pre-specified tolerance
of ±0.15** — inside the band by 0.0102. The most negative pair keeps its identity and strengthens
slightly (debate–village −0.600 → −0.638). The qualitative claim survives (ρ ≈ 0.195 is ~4% shared
rank variance, still nowhere near a stable trait), but **the point estimate nearly quadruples**, and
a marginally different tolerance would have failed this criterion. Anyone quoting the recovery
should quote this number, not just the pass.

**C4 — cost.** The reduced protocol uses **96 of 270 cells** and **4,866 of 13,573 model-trajectory
evaluations = 35.9%** of the full sweep. Realized evaluation fractions track the cell fractions
closely (44.4% commissive, 26.7% assertive) because reps per cell are near-uniform within each
environment.

---

## Exploratory (clearly separated; not pre-specified)

### Sensitivity to the endpoint definition

One alternative mapping only: incentive endpoints **none/moderate** instead of none/high,
everything else fixed.

| Environment | dom (none, high) | dom (none, moderate) | Same? | Ratio |
|---|---|---|:---:|---:|
| T1 Bargaining | incentive | incentive | ✅ | 1.82 |
| **T2 Debate** | difficulty | **incentive** | ❌ **FLIP** | **1.18** |
| T3 Village | frame | frame | ✅ | 4.04 |
| T4 Sales | difficulty | difficulty | ✅ | 3.61 |
| T5 Committee | difficulty | difficulty | ✅ | 1.84 |
| T6 Inbox | frame | frame | ✅ | 4.81 |

**5/6 unchanged; T2 Debate flips** from difficulty- to incentive-dominant. The endpoint choice is
therefore not cosmetic — dropping the high-incentive cell costs Debate its dominant axis. Two
things make this less alarming than it looks: the flip happens at a top-vs-second ratio of **1.18**,
which would itself have fired the expansion trigger, and none/high is the mapping that spans the
axis, which is the defensible default. But it does mean the endpoint mapping must be stated as part
of the protocol rather than left implicit.

### Would the expansion trigger have fired?

Operationalizing "the leading axes are close" as top-vs-second ratio < 1.5:

**Exactly one environment fires: T6 Inbox at 1.44×** — the expected candidate. A user running the
staged protocol would have been told to expand T6 to the full design, and would have run the other
five at reduced cost. Under the exploratory none/moderate mapping, T2 Debate would also have fired
(1.18×) — the same environment whose dominant axis flips, so the safety valve catches the one case
where the reduction misleads.

---

## Summary

**The staged protocol recovers the full-sweep conclusions at 35.9% of the cost.** All three
substantive criteria pass: dominant axis in 6/6 environments, the assertive/commissive partition
sign pattern 6/6, and rank instability still weak.

Two caveats belong with that headline. **C3 passes marginally** — ρ moves +0.055 → +0.195, using
up 93% of the pre-specified tolerance; the qualitative conclusion holds but the point estimate does
not, which is consistent with what the full-design leave-one-model-out range (−0.130 … +0.199)
already said about that statistic. And **the endpoint mapping is load-bearing**: switching incentive
endpoints to none/moderate flips T2 Debate's dominant axis.

The protocol's own safety valve behaves correctly. It would have flagged **T6 Inbox** (1.44×) for
expansion under the primary mapping, and **T2 Debate** (1.18×) under the alternative — in both
cases identifying the environment where the reduced design is least trustworthy, including the one
case where it would have given the wrong answer.
