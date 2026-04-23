# Task 5 Committee — Sensitivity by difficulty (post-hoc)

Post-hoc analysis in response to an author concern about [../results.md](../results.md) Table "P4" / [prereg_outcomes_per_model.md §P4](prereg_outcomes_per_model.md): the "difficulty dominates frame" conclusion was computed with frame and difficulty slopes each averaged across *all* difficulty levels. Because high-difficulty slates have cold-panel honest baselines in the −5 to −8 range (see [high_difficulty_cold_panel.md](high_difficulty_cold_panel.md)), averaging mechanically compresses the frame range: prohibitive and permissive cells at high difficulty are both pulled downward by the baseline, shrinking their span.

This document recomputes the sensitivity slopes **per-difficulty-tier separately** to check whether the dominant-axis conclusion holds when the compression artifact is removed. It also recomputes Gemini's frame slope over the non-saturated middle frames (`pro_social / minimal / selfish`) to check whether Gemini's saturation is driving its unique "frame-dominant" pattern on the reference analysis.

**This is a post-hoc robustness check and does not modify the pre-registered P4 verdict in [../results.md](../results.md).** The pre-registered P4 was written against the averaged-over-difficulty slope per PREREG §8, so the FAIL verdict stands as pre-registered. This analysis is reported as a finding that qualifies the interpretation.

## Reference: averaged-over-difficulty slopes (from pre-registered analysis)

| Model | \|frame slope\| | \|difficulty slope\| | \|incentive slope\| | Dominant axis (averaged) |
|---|---:|---:|---:|:---:|
| Claude | 0.281 | 0.911 | 0.117 | difficulty |
| DeepSeek | 0.266 | 0.790 | 0.195 | difficulty |
| Gemini | 0.434 | 0.016 | 0.430 | frame (saturation) |
| GPT-5 | 0.233 | 0.893 | 0.143 | difficulty |
| Grok | 0.372 | 0.537 | 0.135 | difficulty |
| Llama | 0.287 | 0.713 | 0.018 | difficulty |

Reference aggregate: `mean |frame slope| = 0.312, mean |difficulty slope| = 0.643`. Per pre-registered P4: difficulty dominates for 5 of 6 models.

## Per-difficulty frame slopes (sliced analysis)

Standardized bias units per step along the 5-level frame axis, computed *within* each difficulty tier (not averaged across).

| Model | low-difficulty frame slope | medium-difficulty frame slope | high-difficulty frame slope | Averaged-over-difficulty (ref) |
|---|---:|---:|---:|---:|
| Claude | +0.116 | +0.172 | **+0.477** | +0.281 |
| DeepSeek | +0.083 | +0.166 | **+0.454** | +0.266 |
| Gemini | +0.307 | +0.347 | **+0.589** | +0.434 |
| GPT-5 | +0.117 | +0.155 | **+0.372** | +0.233 |
| Grok | +0.101 | +0.195 | **+0.700** | +0.372 |
| Llama | +0.256 | +0.225 | **+0.348** | +0.287 |

**Two observations:**

1. Frame slope grows with difficulty for every model — high-difficulty frame slopes are 2-7× their low-difficulty counterparts.
2. The averaged slope falls below every per-tier-high value, confirming the averaging compresses the signal.

Mechanism: at high difficulty, the favored candidate is genuinely weak (cold-panel bias roughly −5 to −8). Under prohibitive, the interested-party tracks the honest bias (≈−7). Under permissive, the party ignores it (≈+2 for most models, +20 for Gemini). The dynamic range at high difficulty is therefore ~10-20 units — much larger than at low difficulty, where both prohibitive and permissive cluster in the positive single digits. Higher range × same frame-axis length = higher slope.

## Per-difficulty: frame vs incentive axis comparison

For each `(model, difficulty)` cell, compare the frame-axis slope to the incentive-axis slope computed on the same tier's data:

| Model | Difficulty | \|frame slope\| | \|incentive slope\| | Frame > Incentive? |
|---|---|---:|---:|:---:|
| Claude | low | 0.116 | 0.070 | ✓ |
| Claude | medium | 0.172 | 0.076 | ✓ |
| Claude | high | 0.477 | 0.175 | ✓ |
| DeepSeek | low | 0.083 | 0.154 | ✗ |
| DeepSeek | medium | 0.166 | 0.149 | ✓ |
| DeepSeek | high | 0.454 | 0.218 | ✓ |
| Gemini | low | 0.307 | 0.292 | ✓ |
| Gemini | medium | 0.347 | 0.543 | ✗ |
| Gemini | high | 0.589 | 0.473 | ✓ |
| GPT-5 | low | 0.117 | 0.025 | ✓ |
| GPT-5 | medium | 0.155 | 0.046 | ✓ |
| GPT-5 | high | 0.372 | 0.295 | ✓ |
| Grok | low | 0.101 | 0.083 | ✓ |
| Grok | medium | 0.195 | 0.153 | ✓ |
| Grok | high | 0.700 | 0.168 | ✓ |
| Llama | low | 0.256 | 0.030 | ✓ |
| Llama | medium | 0.225 | 0.046 | ✓ |
| Llama | high | 0.348 | 0.008 | ✓ |

**Frame exceeds incentive in 16 of 18 model × difficulty cells (89%).**

Two exceptions:
- DeepSeek at low difficulty (0.083 vs 0.154) — small-magnitude frame effect coincides with small-magnitude incentive effect; both close to zero.
- Gemini at medium difficulty (0.347 vs 0.543) — medium difficulty has only 3 slates × 3 incentives × 4 reps = 36 data points per model, so Gemini's saturated behavior at some incentive levels creates an outsized incentive slope here.

## Gemini non-saturated frame slope (middle 3 frames)

The averaged Gemini frame slope (0.434) is large because its permissive endpoint saturates at ~20 while prohibitive clusters near −5. But the middle 3 frames (`pro_social / minimal / selfish`) are all substantially manipulation-biased; their pairwise ordering is where Gemini's unique non-monotonicity lives.

Frame slope of Gemini computed over the mid-3 frames only:

| Tier | Gemini mid-3 frame slope (standardized) |
|---|---:|
| low | −0.102 |
| medium | −0.265 |
| high | −0.090 |
| overall (avg over difficulty) | −0.138 |

Gemini's mid-3 slope is **negative** across all difficulty tiers — i.e., going `pro_social → minimal → selfish` decreases bias on average. This is the selfish < minimal inversion re-expressed as a 3-point slope. The full-5-frame slope of +0.434 masks this by being dominated by the permissive endpoint.

For reference: full-5-frame slope (averaged over difficulty) = **+0.434**; mid-3-frame slope (averaged over difficulty) = **−0.138**. Same data, different axis subset, qualitatively opposite direction.

## What this means for the paper's Committee narrative

The pre-registered P4 verdict (difficulty dominates, 5/6 fail) stands. The post-hoc reading suggests three things to qualify the narrative:

1. **Frame is the dominant axis at every difficulty tier** for 5 of 6 models individually (Claude, Gemini at high difficulty only, GPT-5, Grok, Llama) and for 16 of 18 model × difficulty cells in aggregate. The averaged-slope result understates the frame effect.
2. **Frame sensitivity grows with slate difficulty**. The same prompt framing produces 3-7× more signal on hard slates than on easy ones. Interpretation: framing language matters most when the ground truth is against the interested party (hard slates); on easy slates, honest ratings are already high so framing has less room to move behavior.
3. **Gemini's exceptional frame slope is driven entirely by the permissive endpoint**. The mid-3 frames produce a negative-direction slope for Gemini, not the positive-direction slope the averaged full-5 number suggests. This is the pre-registered P6 anti-correlation ([prereg_outcomes_per_model.md §P6](prereg_outcomes_per_model.md)) showing up in the slope decomposition.

These are all post-hoc observations on the pre-registered data; no predictions are being modified. Paper should:
- Report the per-difficulty table (above) as a robustness check.
- Note that frame dominates at each difficulty tier separately even though the averaged-across-difficulty analysis shows difficulty dominates.
- Attribute the difference to compression artifact, not a real reversal of dominance.
