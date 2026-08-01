# Family grid — Phase 1 scouting menu

**Nothing here is pre-registered and nothing has been run.** This is the candidate enumeration
across the Qwen, Llama and DeepSeek families, priced so the roster can be trimmed on cost and
coverage. The pre-registration is written against the *trimmed* roster and committed before any
run.

Sources, both committed so every number is auditable without re-hitting the API:

| File | What it holds |
|---|---|
| [`scouting/or_snapshot_2026-08-01.json`](scouting/or_snapshot_2026-08-01.json) | OpenRouter catalogue + per-model endpoints: providers, quantization, per-endpoint pricing and supported parameters |
| [`scouting/reasoning_probe_2026-08-01.json`](scouting/reasoning_probe_2026-08-01.json) | live reasoning-toggle probe, with the method and the raw token counts |

Reproduce the menu: `python paper/expanded_roster/scripts/scout_grid.py`

Token structure is measured, reused verbatim from [`scripts/cost_model.py`](scripts/cost_model.py),
which read it out of the committed eval logs. Access date 2026-08-01.

---

## The headline the menu is really about

**96% of the cost is pinned support agents, not the models being scouted.**

| | |
|---|---:|
| Grand total, 13 candidate configs | **$3,554** |
| — of which pinned support | **$3,404 (96%)** |
| — of which models under test | **$149 (4%)** |

Every config carries a fixed **$261.87** of support-agent cost: Debate's pinned truthful debater
and three jurors, Village's four bystanders, Committee's four neutral panellists. That figure is
identical for every row and independent of which model is under test. Debate alone is $220.56 of
it, because Claude Opus 4.7 runs as the truthful debater in all 690 debate scenarios per config.

The consequence for trimming is the important part: **the cheapest and most expensive candidates
differ by $21 out of ~$273.** Cost is essentially linear in the *number of configs* and almost
indifferent to *which* configs. Trimming to save money means cutting rows, not preferring cheap
rows — so the roster should be chosen on coverage alone, and then the count checked against
budget.

---

## The menu

Provider pinning rule: cheapest tool-capable endpoint with disclosed quantization. Endpoints
without `tools`/`tool_choice` are excluded from pricing regardless of price, because ACTION phases
in this benchmark require tool calls. `?` marks a parameter count the provider does not state.

| Series | Config | Total | Active | Arch | Reasoning | Provider \| quant | $in | $out | UT $ | **Total $** |
|---|---|---:|---:|---|---|---|---:|---:|---:|---:|
| Qwen3.5 | qwen3.5-9b | 9 | 9 | dense | off-able (verified) | SiliconFlow \| fp8 | 0.10 | 0.15 | 2.64 | **265** |
| Qwen3.5 | qwen3.5-27b | 27 | 27 | dense | off-able (verified) | Alibaba \| fp8 | 0.20 | 1.56 | 13.07 | **275** |
| Qwen3.5 | qwen3.5-35b-a3b | 35 | 3 | MoE | off-able (verified) | AkashML \| fp8 | 0.14 | 1.00 | 8.63 | **271** |
| Qwen3.5 | qwen3.5-122b-a10b | 122 | 10 | MoE | off-able (verified) | Alibaba \| fp8 | 0.26 | 2.08 | 17.42 | **279** |
| Qwen3.5 | qwen3.5-397b-a17b | 397 | 17 | MoE | off-able (verified) | Alibaba \| fp8 | 0.39 | 2.34 | 21.26 | **283** |
| | *Qwen3.5 subtotal (5)* | | | | | | | | | **1,372** |
| Llama 3.1 | llama-3.1-8b-instruct | 8 | 8 | dense | none | CoreWeave \| bf16 | 0.22 | 0.22 | 6.03 | **268** |
| Llama 3.1 | llama-3.1-70b-instruct | 70 | 70 | dense | none | DeepInfra \| fp8 | 0.40 | 0.40 | 10.97 | **273** |
| | *Llama 3.1 subtotal (2)* | | | | | | | | | **541** |
| Llama 4 | llama-4-scout | 109 | 17 | MoE | none | Groq \| unknown | 0.11 | 0.34 | 5.41 | **267** |
| Llama 4 | llama-4-maverick | 400 | 17 | MoE | none | Parasail \| fp8 | 0.35 | 1.00 | 16.37 | **278** |
| | *Llama 4 subtotal (2)* | | | | | | | | | **546** |
| DeepSeek V4 | deepseek-v4-flash-0731 | 284 | 13 | MoE | off-able (verified) | DeepInfra \| fp4 | 0.09 | 0.18 | 2.66 | **265** |
| DeepSeek V4 | deepseek-v4-pro | 1600 | 49 | MoE | present (unverified) | Baidu \| fp8 | 0.63 | 1.25 | 23.67 | **286** |
| | *DeepSeek V4 subtotal (2)* | | | | | | | | | **550** |
| DeepSeek V3 | deepseek-chat-v3.1 | 671 | 37 | MoE | present (unverified) | DeepInfra \| fp4 | 0.25 | 0.95 | 14.15 | **276** |
| DeepSeek V3 | deepseek-v3.2 | 671? | 37? | MoE | present (unverified) | StreamLake \| fp8 | 0.21 | 0.32 | 7.00 | **269** |
| | *DeepSeek V3 subtotal (2)* | | | | | | | | | **545** |
| | **GRAND TOTAL (13)** | | | | | | | | | **3,554** |

**Reuse, no cost:** Llama 3.3 70B (dense) from the frozen corpus — different run date and
provider, so it sits *beside* the Llama 3.1 pair as a same-size refresh comparison, never inside
the series.

---

## Findings that change the plan

### 1. Llama 3.1 405B does not exist on OpenRouter

Not in the catalogue on 2026-08-01. The only 405B entries are `nousresearch/hermes-3-llama-3.1-405b`
and `nousresearch/hermes-4-405b` — third-party finetunes, not Meta instruct, and not substitutes.

This is the deprecation risk the brief anticipated, and it lands. **The Llama 3.1 "size ladder" is
a two-point pair, 8B and 70B.** Two points is not a series: a Spearman correlation over n=2 is
either +1 or −1 by construction and carries no information. If Llama 3.1 stays in, it should be
described as a pair and read as one contrast, not as a trend.

### 2. Qwen3.5 has a fifth rung, and the ladder is not a clean parameter axis

`qwen3.5-35b-a3b` exists and was not in the plan. More importantly, the ladder breaks
architecturally in the middle:

| Rung | Total | Active | Arch |
|---|---:|---:|---|
| 9B | 9 | 9 | dense |
| 27B | 27 | 27 | dense |
| 35B-A3B | 35 | **3** | MoE |
| 122B-A10B | 122 | 10 | MoE |
| 397B-A17B | 397 | 17 | MoE |

Total parameters are monotonic. **Active parameters are not**: 9 → 27 → **3** → 10 → 17. The
dense-to-MoE transition between 27B and 35B-A3B means the two axes disagree about ordering, and a
figure that plots "size" without saying which axis it uses will be wrong on one of them. This is
the parameter-count semantics point in the brief, and it applies inside Qwen3.5, not only across
Llama 4.

Read on **total** parameters the series is a clean 5-point ladder. Read on **active** parameters it
is not a ladder at all. Both readings are defensible; they must be labelled.

### 3. DeepSeek offers a generational axis but no real size axis

As the brief anticipated. Stated plainly:

- **No same-generation size ladder.** The only same-generation pair is V4 Flash (284B/13B) vs V4
  Pro (1.6T/49B), and it varies total *and* active together — it isolates neither. It is a size
  pair, not a controlled contrast.
- **The generational axis is real, and one contrast in it is unusually clean:** `deepseek-chat-v3.1`
  and `deepseek-v3.2` are the same lineage at (reportedly) the same 671B/37B, differing by
  generation and training rather than scale. If the V3.2 parameter count can be sourced, that is
  the best-controlled generational contrast anywhere in this grid — better than Llama 3.1-vs-4,
  which confounds generation with architecture.
- **Caveat on that:** OpenRouter does not state V3.2's parameter count. The 671B/37B above is
  lineage inference, flagged `?` in the table, and must be sourced before it is claimed.
- **Excluded by rule:** `deepseek-r1` and `deepseek-r1-0528` (pure reasoning, cannot be pinned
  off); `deepseek-r1-distill-llama-70b` (R1 distilled onto a Llama base — not a DeepSeek-family
  member for this grid, listed here only because it surfaces in any family enumeration).

### 4. Llama 4 Scout vs Maverick is the one clean total-parameter contrast

Active parameters fixed at 17B, total 109B vs 400B (16 vs 128 experts). It is the only place in the
grid where a total-parameter effect is isolated from an active-parameter effect. Worth protecting
in any trim — n=2, but it is a controlled pair, which is a different thing from a two-point trend.

### 5. Reasoning mode is settled for Qwen, open for DeepSeek

All five Qwen3.5 rungs expose `reasoning` and **all five pin OFF cleanly** — verified live:
`reasoning_tokens` 0 and no `reasoning` field with the toggle set, against 218–318 reasoning
tokens on the same prompt at provider defaults, with completion collapsing from ~315 tokens to 4.

One weak spot recorded rather than smoothed: `qwen3.5-397b-a17b` emitted only **1** reasoning token
at default on the trivial probe prompt. The OFF side is unambiguous; the default-side contrast is
too weak to call the toggle proven for that rung, so it should be re-probed on a harder prompt
before it runs.

Llama lines expose no reasoning parameter on any endpoint — there is no mode to pin, which is what
makes them clean for this grid.

DeepSeek V4 Flash pins off cleanly. **V4 Pro, V3.1 and V3.2 are unprobed** and must be verified
before they run. Note that V4 Pro is already in the frozen corpus with reasoning ON, so a
reasoning-OFF V4 Pro is a new config, not a re-analysis.

### 6. Tool capability constrains provider choice everywhere

Every candidate has endpoints that cannot run this benchmark because they do not support
`tools`/`tool_choice`, and on several models those are the cheapest ones. Llama 3.1 8B's cheapest
tool-capable endpoint costs 11× its cheapest endpoint overall ($0.22 vs $0.02 in). Two configs
carry a harder flag:

- **`llama-3.1-70b-instruct` has exactly one tool-capable endpoint** (DeepInfra, fp8). No fallback.
  A provider outage or a silent serving change is unrecoverable and unverifiable after the fact.
- **`llama-4-scout` has no tool-capable endpoint that discloses quantization** (Groq and Google,
  both `unknown`). This is the condition expanded-roster A1 explicitly rejected when it came up for
  Ling in Tier 2 — flagged here for the same treatment, whatever that turns out to be.

---

## Wall clock

At `--max-connections 20`, scaled from the T5 sweep's observed rate: **8.8 h per config**, so 13
configs ≈ **114 h (4.8 days) sequential**.

Treat that as a floor, not an estimate. Tier 2 could not sustain 20 connections — Amendment A2
walked T1 and T4 back to 8 after completion fell to 35.0% and 23.1% with all failures
`RetryError(RateLimitError)`. The realistic figure is higher and depends on which environments
throttle for which providers; the small Qwen and Llama rungs are served by providers this project
has not load-tested.

Village and Debate dominate: 4.33 h and 3.41 h of the 8.8 h.

---

## Trimming

Two heuristics, the second inherited from the brief:

**Cost trims by row count, not by row.** Any 10-config roster costs ~$2,730 and any 8-config roster
~$2,180, near enough regardless of which rows. So pick on coverage first.

**Within a series, cut from the top or cut the whole series.** Dropping a ladder's top rung loses
one point; dropping its bottom rung breaks the series where it is most informative; hollowing out
the middle destroys the shape while still paying for the endpoints.

Applying both to this menu, in decreasing order of what a cut costs you:

| Cut | Saves | What it costs |
|---|---:|---|
| DeepSeek V3 pair | $545 | the best-controlled generational contrast in the grid (if V3.2 params get sourced) |
| DeepSeek V4 pair | $550 | the only DeepSeek size pair — but it is uncontrolled anyway, and V4 Pro duplicates a frozen-corpus config at a different reasoning setting |
| Llama 3.1 pair | $541 | the 3.1-vs-4 generational contrast and the 3.3-vs-3.1 same-size refresh; the pair is already truncated by the missing 405B |
| Llama 4 pair | $546 | the only isolated total-parameter contrast |
| Qwen3.5 top rung (397B) | $283 | one point off the only real size ladder |

**Recommendation: cut DeepSeek V4 Pro only, and hold the other 12 (~$3,268).** V4 Pro is the
weakest row on this menu — it is the most expensive config, its size pairing with V4 Flash is
uncontrolled, and the model is already in the frozen corpus, so what a reasoning-OFF run adds is a
reasoning-mode toggle comparison, which is the question Tier 1 was built to answer and already did.
Every other row buys either a ladder point or a controlled contrast.

If the budget needs to come down further, the next cut is the **whole DeepSeek V4 series** (leaving
V3.1/V3.2 as a pure generational contrast), then **Llama 3.1**, which is the series the missing
405B has already damaged.

---

## Still open before Phase 2 can be pre-registered

1. **Source or drop V3.2's parameter count.** It carries the grid's cleanest generational contrast
   and is currently inference.
2. **Probe reasoning-off for V4 Pro, V3.1, V3.2**; re-probe Qwen3.5-397B on a harder prompt.
3. **Decide the A1 treatment for `llama-4-scout`** (no tool-capable endpoint discloses
   quantization) and for `llama-3.1-70b-instruct` (single tool-capable endpoint, no fallback).
4. **Fix the parameter axis per figure** — total or active — given that Qwen3.5 is monotonic in one
   and not the other.
5. **Confirm the gate expectation is descriptive, not predictive.** The 8B/9B rows are the likeliest
   exclusions; the gates decide that, and no anticipated exclusion should appear in the results
   document.
