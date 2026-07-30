# T5 — baseline-relative slopes, partition propagation, and the rating-scale confound

Three follow-ups to [cold_panel_all_tiers.md](cold_panel_all_tiers.md). **No model calls** —
all of this is recomputation over `paper/task5_committee/eval_log.eval` (1,078 executed
samples, 2 errors, matching `results.md`) and the committed Δ_D table.

Reproduce:

```bash
python paper/task5_committee/scripts/t5_extract_ratings.py      # eval log -> t5_rows.jsonl
python paper/task5_committee/scripts/t5_scale_and_baseline.py   # Q1 + Q2
python paper/task5_committee/scripts/t5_partition_propagation.py # Q3
```

**Validation.** Both recomputations reproduce the committed numbers exactly on the raw metric
before anything is changed: the P4 standardized slopes match `results.md` §B.4 to three
decimals (Claude +0.281 / −0.911; aggregate |frame| 0.327, |difficulty| 0.603), and the
multivariate betas match `paper/figures/model_task_axis_sensitivity.md` to four
(Claude Δ_D +2.7539; Gemini −3.5593; assertive 17/18, mean +0.2851; §4.3 coef +0.4396,
cluster-SE 0.2234, t +1.968, p 0.106).

---

## 1. The rating-scale confound is real and large

`committee.py:187` tells the agent, in the `private_rating` phase, to rate *"from 0 (worst) to
10 (best)"*. The same call's tool description and validator enforce **0–20**
(`:205, :232, :241, :303`, clamped `:304`). Models split on which instruction they followed.

Interested party's own initial rating values, pooled across all its samples:

| Model | n values | % > 10 | max | mean | % samples with any value > 10 | followed |
|---|---:|---:|---:|---:|---:|---|
| Claude Opus 4.7 | 2864 | 80.5% | 20 | 13.26 | 100.0% | schema (0–20) |
| Grok 4 | 2816 | 73.9% | 20 | 13.49 | 99.4% | schema (0–20) |
| DeepSeek V4 Pro | 2880 | 63.3% | 20 | 12.00 | 90.6% | schema (0–20) |
| Gemini 3.1 Pro | 2880 | 47.1% | 20 | 9.61 | 100.0% | mixed |
| GPT-5.5 | 2880 | 16.2% | 20 | 8.08 | 21.7% | mostly prose (0–10) |
| **Llama 3.3 70B** | 2880 | **0.0%** | **10** | 6.64 | **0.0%** | **prose (0–10), exclusively** |
| *neutral panel (pooled)* | 64624 | 61.4% | — | 12.08 | — | schema (0–20) |

**Llama never once exceeded 10, across 2,880 rating values.** Its achievable `initial_bias`
range is therefore roughly half every other model's. GPT-5.5 is partly affected; the other
four are effectively on 0–20.

This is a genuine cross-model comparability problem for T5 absolute levels, and it is
correctable — see §1a.

### 1a. Scale correction and corrected figures

**Identification.** Per-sample max rating is perfectly bimodal across the entire sweep: every
sample tops out either ≤ 10 or ≥ 15, and **no sample in any model has a max in 11–14**. Each
sample's scale is therefore unambiguous. The ≤ 10 samples are spread uniformly over difficulty
and frame — for GPT-5.5 they are *most* common at **low** difficulty (82%), where candidates
are strong and a genuine 0–20 rater would certainly exceed 10 — so `max ≤ 10` reflects a scale
choice, not honest low rating. Under its assigned scale each model uses a similar share of its
range (Llama 0.664, Claude 0.663, Grok 0.675), supporting a linear ×2 mapping.

**Correction.** A sample with `max ≤ 10` is on the 0–10 scale; its bias is multiplied by 2 to
express it in 0–20-equivalent units. Samples reaching ≥ 15 pass through unchanged.

| Model | samples on 0–10 | correction applied |
|---|---:|---|
| Claude Opus 4.7 | 0 / 179 | none |
| Gemini 3.1 Pro | 0 / 180 | none |
| Grok 4 | 1 / 176 (0.6%) | negligible |
| DeepSeek V4 Pro | 17 / 180 (9.4%) | minor |
| **GPT-5.5** | **141 / 180 (78.3%)** | **substantial** |
| **Llama 3.3 70B** | **180 / 180 (100%)** | **full ×2** |

**Corrected excess-over-honest** (0–20-equivalent units, per-slate baselines, computed from
the eval log). Only GPT-5.5 and Llama move materially:

| Model | low raw → corr | medium raw → corr | high raw → corr |
|---|---|---|---|
| Claude Opus 4.7 | +1.52 → **+1.52** | +2.01 → **+2.01** | +5.15 → **+5.15** |
| **GPT-5.5** | −0.82 → **+1.56** | +1.36 → **+2.42** | +5.53 → **+4.45** |
| Gemini 3.1 Pro | +6.65 → **+6.65** | +10.94 → **+10.94** | +18.49 → **+18.49** |
| Grok 4 | +1.47 → **+1.53** | +2.79 → **+2.79** | +8.60 → **+8.60** |
| **Llama 3.3 70B** | −0.63 → **+3.18** | +0.93 → **+2.45** | +7.05 → **+6.97** |
| DeepSeek V4 Pro | +1.21 → **+1.43** | +2.76 → **+2.92** | +6.10 → **+6.16** |

**Correction to the earlier claim.** Strict monotonicity (low < medium < high) held 6/6 on the
uncorrected numbers but holds **5/6** after correction — **Llama breaks it**, dipping at medium
(+3.18 → +2.45 → +6.97). The weaker directional claim is unaffected: Llama's low→high excess
slope is still clearly positive (+1.90 per step), and the *standardized* difficulty slope is
positive for all six models (§2a), which is scale-invariant by construction. So "excess rises
with difficulty" survives at 6/6; "rises monotonically" is 5/6.

**The cross-model ordering changes materially.** Permissive-frame endpoint, raw vs corrected:

| Rank | Raw | Corrected |
|---|---|---|
| 1 | Gemini 19.72 | Gemini 19.72 |
| 2 | Grok 6.88 | Grok 6.88 |
| 3 | DeepSeek 4.40 | **Llama 6.25** |
| 4 | Claude 4.29 | **GPT-5.5 6.23** |
| 5 | GPT-5.5 3.90 | DeepSeek 4.68 |
| 6 | **Llama 3.13** | **Claude 4.29** |

Llama moves from last to third and Claude becomes the roster minimum. Any statement that
"Llama manipulates least on Committee" is an artifact of the scale bug.

**Pre-registered verdicts are unaffected.** P1 (prohibitive |bias| < 2.0) stays 6/6 — GPT-5.5
moves −1.289 → −1.819, closest to the line but still passing. P2 under the magnitude reading
stays 6/6.

Note these "raw" figures are computed from the eval log with **per-slate** baselines, so they
differ slightly from the earlier per-tier figures applied to the transcribed §A.3 cells
(e.g. GPT-5.5 low, −0.82 here vs +0.95 there). The per-slate version supersedes.

---

## 2. Difficulty slope on excess-over-honest

`excess = initial_bias − cold_panel_honest[slate]`, using the 12 per-slate cold-panel values.

### 2a. P4-style standardized marginal slopes (the `results.md` §A.4 / §B.4 method)

| Model | frame raw | frame excess | **difficulty raw** | **difficulty excess** |
|---|---:|---:|---:|---:|
| Claude Opus 4.7 | +0.281 | +0.374 | **−0.911** | **+0.558** |
| GPT-5.5 | +0.307 | +0.281 | **−0.676** | **+0.750** |
| Gemini 3.1 Pro | +0.434 | +0.361 | +0.016 | **+0.581** |
| Grok 4 | +0.372 | +0.300 | **−0.537** | **+0.683** |
| Llama 3.3 70B | +0.287 | +0.179 | **−0.713** | **+0.876** |
| DeepSeek V4 Pro | +0.280 | +0.299 | **−0.765** | **+0.600** |
| **aggregate \|·\|** | **0.327** | **0.299** | **0.603** | **0.675** |

**The difficulty slope flips sign for all six models** — from −0.911…−0.537 to
+0.558…+0.876 — and its magnitude *grows*. These slopes are standardized by each model's own
pooled SD, so they are invariant to the 0–10 vs 0–20 scale split: the sign flip is not a
scale artifact.

**P4 is unaffected in verdict and gets worse in degree.** Raw: FAIL, 1/6 models with
|frame| > |difficulty|. Excess: FAIL, **0/6** — Gemini, the sole raw passer, was passing only
because its raw difficulty slope was flattened to ≈0 by saturation; on excess it becomes
+0.581 and joins the rest.

### 2b. Multivariate OLS betas and Δ_D (the Section 4.3 partition method)

| Model | β_D raw | β_D excess | Δ_D raw | Δ_D excess | dominant raw | dominant excess |
|---|---:|---:|---:|---:|---|---|
| Claude Opus 4.7 | −3.983 | +1.856 | +2.754 | +0.633 | difficulty | difficulty |
| GPT-5.5 | −2.639 | +3.202 | +1.452 | +2.014 | difficulty | difficulty |
| **Gemini 3.1 Pro** | +0.125 | +5.966 | **−3.559** | **+2.282** | **frame** | **difficulty** |
| Grok 4 | −2.242 | +3.635 | +0.680 | +2.056 | difficulty | difficulty |
| Llama 3.3 70B | −1.936 | +3.905 | +1.154 | +3.122 | difficulty | difficulty |
| DeepSeek V4 Pro | −3.366 | +2.475 | +2.145 | +1.254 | difficulty | difficulty |
| **Committee mean Δ_D** | | | **+0.771** | **+1.893** | | |

β_F and β_I are essentially unchanged (the honest baseline is a function of slate, hence of
difficulty, so subtracting it loads almost entirely onto β_D).

---

## 3. Propagation into the assertive/commissive partition

Committee's six rows replaced with the excess-based betas; the other five environments
untouched.

| Quantity | Raw (committed) | Excess | Change |
|---|---|---|---|
| Committee Δ_D, sign | positive | positive | **no sign change** |
| Committee mean Δ_D | +0.771 | +1.893 | ~2.5× larger |
| Assertive rows with Δ_D > 0 | 17/18 | **18/18** | strengthened |
| Commissive rows with Δ_D < 0 | 18/18 | 18/18 | unchanged |
| Committee dominant axis | difficulty (5/6 rows) | difficulty (**6/6** rows) | unchanged, now unanimous |
| Environment-level 2×2 | [[3,0],[0,3]] | [[3,0],[0,3]] | unchanged |
| Fisher one-sided p | 0.0500 | 0.0500 | unchanged (at its floor) |
| `Δ_D ~ assertive` coef | +0.4396 | +0.8138 | larger |
| `Δ_D ~ assertive` p (cluster) | 0.106 | **0.207** | **worse** |
| `Δ_rel ~ assertive` coef | +1.1998 | +1.2696 | larger |
| `Δ_rel ~ assertive` p (cluster) | 0.0005 | **0.00004** | **better** |

**Answers.**

- **Does Δ_D for Committee change sign?** No. It is positive under both, and the *environment*
  stays assertive-classified. One per-model row flips: Gemini, from −3.559 to +2.282, which is
  what takes assertive sign agreement from 17/18 to a clean 18/18.
- **Does the partition survive?** Yes, and on every scale-free measure it is stronger: 18/18
  vs 17/18 sign agreement, 6/6 vs 5/6 committee rows difficulty-dominant, and Δ_rel's t-statistic
  rising from +8.10 to +13.33.
- **Does T5's dominant axis change?** No — difficulty under both, and it becomes unanimous
  across models rather than 5/6.

**One caveat that cuts the other way.** The scale-sensitive pooled statistic gets *worse*:
`Δ_D ~ assertive` moves from p = 0.106 to p = 0.207, because Committee's Δ_D values grow in
both magnitude and spread, inflating the cluster-robust SE from 0.223 to 0.561. This is
exactly the metric-scale artifact
[`analysis_lomo/partition_scale_diagnostic.py`](../../../analysis_lomo/partition_scale_diagnostic.py)
identifies — Committee's Δ_D carries 0–20 rating units while the other five environments carry
rates in [0,1], so Committee dominates the between-cluster signal. Making Committee's
coefficients larger makes that domination worse. It is a further argument for reporting Δ_rel
as the headline rather than Δ_D; on Δ_rel the same substitution strengthens the result.

---

## 4. Is `post_discussion_rating_change` used in any headline result?

**No. Appendix/exploratory only.**

- **No verdict line uses it.** P1–P6 all use `initial_rating_bias`, stated explicitly in
  `prereg.md:230` and `results.md:271`. It is "retained" under Amendment A5 only in the sense
  that it was *not* dropped when `discussion_polarity` was (it does not depend on the failed
  wordlist classifier) — retention is not use.
- **It appears in no results table** in `results.md` §A or §B.
- Where it does appear: `paper/cross_task/findings/{consolidated,corpus,notes}.md` and
  `paper/notes.md` note it is *uncorrelated* with `manipulation_occurred` (ρ ≈ 0.02 / −0.08)
  and propose it as one half of a future **attempted-vs-successful** manipulation split; it is
  listed as a Committee metric in `README.md:94`; and its per-sample values appear in
  `paper/sample_traces/task5_committee_traces.md`.

**Consequence for the scale bug.** The §1 defect contaminates
`post_discussion_rating_change` structurally — it compares a **0–10-instructed** initial rating
against a **0–20-instructed** final rating, so a model that follows both prompts records a
positive shift with no change of opinion. Because no headline result uses that scorer, **no
published verdict is affected**. But the proposed attempted-vs-successful analysis would be
built directly on the contaminated quantity, so it should not proceed until the prompt is
fixed. Llama is the worst case: it followed the 0–10 prose in every one of its 2,880 initial
ratings, so its entire `interested_delta_favored` is measured across a scale change.
