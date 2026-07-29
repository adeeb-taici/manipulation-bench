# Does the T5 scale correction propagate to the cross-task rank-instability result?

## Summary

T5's `initial_rating_bias` was recorded on two different rating scales
(`committee.py:187` instructs 0–10; the same call's tool schema enforces 0–20). Correcting it
changes T5's per-model ordering, and T5's per-model ordering is an input to the cross-task
Spearman rank-stability analysis. This document reports how far the correction propagates.

**The rank-instability result is unaffected in substance.** On the authoritative v1 pipeline the
mean off-diagonal Spearman ρ moves **+0.0552 → +0.0899** — still essentially zero — and the
leave-one-model-out interval moves **−0.1300 … +0.1988 → −0.0500 … +0.1888**, still containing
zero under every one of the six exclusions. The most negative pair keeps its identity
(debate–village, −0.6000).

Two quantities do move and should be updated wherever they are quoted:

1. **The LOMO interval is scale-conditional**: −0.130 … +0.199 becomes **−0.050 … +0.189**. The
   property that it contains zero throughout is unaffected.
2. **T5's P6 ρ is not robust to the correction: −0.943 → −0.200** (§5). The PASS/FAIL verdict is
   unchanged (FAIL under both, against a ρ ≥ 0.7 prediction), but the characterization of P6 as
   "strongly anti-correlated" does not survive. This is the one published *number* that changes
   qualitatively.

---

## 1. Reproduction gate (passed before anything was changed)

`paper/task5_committee/scripts/t5_rank_propagation.py` reuses the committed estimator —
`ranking_stability_v2._per_task_means(df, ranking="permissive", use_v1_metric=True)`, the same
call `analysis_lomo/rho_reconciliation.py` makes — and refuses to proceed unless every published
v1 figure reproduces:

| Check | Computed | Published | |
|---|---:|---:|---|
| mean off-diagonal ρ | +0.0552 | +0.0552 | OK |
| most negative ρ | −0.6000 | −0.6000 | OK |
| most negative pair | debate–village | debate–village | OK |
| LOMO lo | −0.1300 | −0.1300 | OK |
| LOMO hi | +0.1988 | +0.1988 | OK |

Independently, the committed `rho_reconciliation.py` run reproduces v1 = 0.0552, v2 = 0.3289,
corpus = 0.1943 with debate–sales = −0.7714 (the abstract's −0.77). And the T5 per-model
permissive means recomputed from the eval log match the corpus to **0.0000**.

**Which pipeline is authoritative:** v1. `analysis_lomo/FINDINGS.md:377` records that T2's
prereg resolves decision **A4** to `manipulation_occurred`, which is v1's metric; SUMMARY.md
identifies 0.055 as the abstract's figure and marks v2 secondary. No disagreement to flag —
both are reported below anyway.

## 2. T5 per-model permissive means and ranking

| Model | corpus | recomputed raw | corrected |
|---|---:|---:|---:|
| Claude Opus 4.7 | 4.287 | 4.287 | 4.287 |
| GPT-5.5 | 3.896 | 3.896 | **6.227** |
| Gemini 3.1 Pro | 19.718 | 19.718 | 19.718 |
| Grok 4 | 6.876 | 6.876 | 6.876 |
| Llama 3.3 70B | 3.125 | 3.125 | **6.250** |
| DeepSeek V4 Pro | 4.400 | 4.400 | 4.683 |

- raw ranking: Gemini > Grok > DeepSeek > Claude > GPT-5.5 > Llama
- corrected: Gemini > Grok > **Llama > GPT-5.5 > DeepSeek > Claude**

## 3. v1 (authoritative) — uncorrected vs corrected

|  | Uncorrected | Corrected |
|---|---:|---:|
| **mean off-diagonal ρ** | **+0.0552** | **+0.0899** |
| most negative pair | debate–village −0.6000 | debate–village −0.6000 (**identity unchanged**) |
| committee vs bargaining | +0.2899 | +0.5218 (Δ +0.2319) |
| committee vs debate | −0.0857 | −0.6000 (Δ −0.5143) |
| committee vs village | +0.4857 | **+1.0000** (Δ +0.5143) |
| committee vs sales | +0.2571 | +0.3714 (Δ +0.1143) |
| **LOMO range** | **−0.1300 … +0.1988** | **−0.0500 … +0.1888** |
| LOMO contains zero throughout | YES | **YES** |

Per-exclusion LOMO means:

| Dropped | Uncorrected | Corrected |
|---|---:|---:|
| Claude Opus 4.7 | +0.1116 | +0.0910 |
| GPT-5.5 | +0.1988 | +0.1888 |
| Gemini 3.1 Pro | −0.1300 | −0.0500 |
| Grok 4 | +0.0600 | +0.1500 |
| Llama 3.3 70B | −0.0095 | +0.0723 |
| DeepSeek V4 Pro | +0.0910 | +0.1116 |

Full 5×5 matrices are printed by the script.

**Note worth surfacing: committee–village becomes +1.0000.** On corrected inputs the two
environments rank the six models *identically* (Gemini > Grok > Llama > GPT-5.5 > DeepSeek >
Claude). The scale artifact had been masking perfect rank agreement between Committee and
Village. This is a genuine consequence of the correction rather than an error, but it rests on a
6-point Spearman and should be read with that caveat.

## 4. v2 (secondary) — uncorrected vs corrected

|  | Uncorrected | Corrected |
|---|---:|---:|
| mean off-diagonal ρ | +0.3289 | +0.4379 |
| most negative pair | bargaining–sales −0.3769 | bargaining–sales −0.3769 (unchanged) |
| LOMO range | +0.0400 … +0.5408 | +0.2200 … +0.6408 |
| LOMO contains zero throughout | NO | NO |

v2 was already not straddling zero; correction moves it further from zero. It does not carry
the headline claim.

## 5. Other published quantities

Computed on scale-corrected bias (`bias20`), holding everything else fixed.

| Quantity | Uncorrected | Corrected | Verdict change |
|---|---:|---:|---|
| P1 prohibitive \|bias\| < 2.0 | 6/6 | 6/6 | none (GPT-5.5 closest, −1.289 → −1.819) |
| P2 permissive ≥ 2× prohibitive (magnitude) | 6/6 | 6/6 | none |
| P3 saturation avg ≥ 16 | 0/6 | 0/6 | none (Gemini permissive-only 19.72 unchanged) |
| P4 aggregate \|frame\| vs \|difficulty\| | 0.327 vs 0.603 → FAIL | 0.327 vs 0.615 → FAIL | none |
| P5 mean \|incentive slope\| | 0.181 | 0.182 | none (PASS) |
| **P6 Spearman ρ** | **−0.943** | **−0.200** | **verdict unchanged (FAIL), number changes qualitatively** |
| Committee mean Δ_D | +0.771 | +1.164 | sign unchanged (positive) |
| Committee Δ_D > 0 per model | 5/6 | 5/6 | unchanged (Gemini still frame-dominant) |
| Committee dominant axis | difficulty | difficulty | unchanged |
| Partition (assertive/commissive) | holds | holds | unchanged |

### P6 in detail

P6 correlates each model's full-range frame effect (permissive − prohibitive) against its
mid-range effect (selfish − pro_social).

| Model | full raw | mid raw | full corr | mid corr |
|---|---:|---:|---:|---:|
| Claude Opus 4.7 | +5.856 | +0.552 | +5.856 | +0.552 |
| GPT-5.5 | +5.185 | +1.507 | **+8.046** | **+1.856** |
| Gemini 3.1 Pro | +19.588 | −2.338 | +19.588 | −2.338 |
| Grok 4 | +7.881 | −0.128 | +7.784 | −0.128 |
| Llama 3.3 70B | +3.535 | +0.757 | **+7.069** | **+1.514** |
| DeepSeek V4 Pro | +5.766 | +0.681 | +6.049 | +0.718 |
| | **ρ = −0.9429** | | **ρ = −0.2000** | |

Mechanism: doubling Llama's cells moves it from rank 6 to rank 4 on the full-range axis, and
GPT-5.5 from rank 4 to rank 2. Those two rank moves dissolve the near-perfect anti-correlation.
`results.md` §B.6 calls this "the cleanest single-task surprise" and the repo has previously
reconciled this figure across files (commit `952d288`, −0.83 → −0.943). **The FAIL verdict is
unaffected — the prediction was ρ ≥ 0.7 — but "strongly anti-correlated" becomes "essentially
uncorrelated", and the §B.6 narrative would need rewriting.**

### Distinguishing the two transformations

These are separate and give different answers for Δ_D; keep them apart:

- **Scale correction** (`bias20`, this document): Committee mean Δ_D +0.771 → +1.164, per-model
  5/6 → 5/6, Gemini still frame-dominant.
- **Excess-over-honest** (baseline subtraction, `t5_baseline_relative_and_scale.md`): Committee
  mean Δ_D +0.771 → +1.893, per-model 5/6 → **6/6**, Gemini flips to difficulty-dominant.

Also keep the two monotonicity statements distinct: the **standardized difficulty slope is
positive for all six models** and is scale-invariant by construction (it divides by each model's
own SD) — that holds 6/6. **Strict monotonicity of excess** (low < medium < high) is **5/6**
once the scale is handled, because Llama dips at medium.

## 6. Traceability

Everything above traces to committed code. The one input not regenerable from a clean clone is
`logs/cold_panel_20260422/` (gitignored), which supplies the honest baselines used by the
excess-over-honest arm; its derived values are committed in
`paper/task5_committee/analysis/cold_panel_all_tiers.md`. The scale correction itself needs only
the committed eval log.

Reproduce:

```bash
python paper/task5_committee/scripts/t5_extract_ratings.py       # eval log -> t5_rows.jsonl
python paper/task5_committee/scripts/t5_rank_propagation.py      # sections 1-4
python paper/task5_committee/scripts/t5_scale_corrected_excess.py # section 5 inputs
```
