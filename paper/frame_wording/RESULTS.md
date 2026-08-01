# Frame-wording check — results

Evaluated against [CRITERIA.md](CRITERIA.md), locked before any frame-wording model call.
Answers kcqH W4: could a paraphrase shift a slope enough to flip a dominance ranking in a
borderline environment?

Reproduce:

```bash
python paper/frame_wording/scripts/prepare_frame_wording.py    # cells + cost
python paper/frame_wording/scripts/generate_frame_wording.py   # scenarios
bash   paper/frame_wording/scripts/launch_frame_wording.sh inbox 12
bash   paper/frame_wording/scripts/launch_frame_wording.sh committee 12
python paper/frame_wording/scripts/analyze_frame_wording.py
```

## Provenance

| Field | Value |
|---|---|
| Roster | claude, gpt55, gemini, **grok43**, llama, deepseek |
| Slugs | `anthropic/claude-opus-4.7`, `openai/gpt-5.5-20260423`, `google/gemini-3.1-pro-preview`, `x-ai/grok-4.3`, `meta-llama/llama-3.3-70b-instruct`, `openai-api/deepseek/deepseek-v4-pro` |
| Provider | OpenRouter (DeepSeek via official API), access date 2026-07-31 |
| Grok | Grok 4 deprecated; **Grok 4.3 substituted with its own v1 arm**, so its within-model contrast is internally valid |
| Cells | Committee (incentive=none, difficulty=medium); Inbox (incentive=high, difficulty=medium) |
| Scenarios | Committee 270, Inbox 360 |
| Scoring | T5 per-sample scale correction applied before every cross-model quantity |

## Coverage and attrition

**Zero attrition in the final result.** Committee 270/270, Inbox 360/360, arms balanced
90/90/90 and 120/120/120.

One infrastructure failure occurred and was fixed rather than absorbed. On the first Committee
pass, **all 45 DeepSeek samples failed** — 15 per version — with
`BadRequestError: 'Thinking mode does not support this tool_choice'`, the documented DeepSeek
V4 Pro quirk: the generated scenarios lacked `metadata.tool_choice_strategy="auto"`, which
`game_solver.py:97` reads to downgrade `tool_choice="any"` → `"auto"`. The flag was added and
those 45 scenarios re-run; both halves live in the same log directory and are unioned by sample
id, with a usable sample always winning over an errored one.

Two points about that failure. It was **balanced across versions** (15/15/15), so even the
pre-fix 5-model result was an internally valid v1/v2/v3 contrast — the fix restored the sixth
model rather than rescuing the comparison. And it is **infrastructure, not competence and not a
wording effect**: the request was rejected by the provider before the model saw the prompt.

## C1 — Dominance stability (the registered question)

### T6 Inbox

| Version | Frame slope | Top-vs-second | Dominant axis | Matches published |
|---|---:|---:|---|:---:|
| v1 (original) | 0.1168 | 1.49 | frame | ✅ |
| v2 (formal imperative) | 0.1365 | 1.74 | frame | ✅ |
| v3 (conversational) | 0.1514 | 1.93 | frame | ✅ |

### T5 Committee

| Version | Frame slope | Top-vs-second | Dominant axis | Matches published |
|---|---:|---:|---|:---:|
| v1 (original) | 0.5456 | 1.13 | difficulty | ✅ |
| v2 (formal imperative) | 0.5288 | 1.16 | difficulty | ✅ |
| v3 (conversational) | 0.4676 | 1.32 | difficulty | ✅ |

**PASS in both environments, all three versions. No flips.**

Worth stating because it cuts against the concern rather than merely surviving it: **both margins
widen under paraphrase** — Inbox 1.49 → 1.93, Committee 1.13 → 1.32. The original production
wording is the *least* favourable of the three for the published dominance claim, not the most.
A wording-artifact story would predict the opposite.

## C2 — Slope stability (context for C1)

| Environment | Spread across versions | Appendix F band (~20%) |
|---|---:|---|
| Committee | **15.2%** | inside |
| Inbox | **25.6%** | **outside** |

Reported as measured. Inbox's frame slope does move more than the Appendix F precedent led us to
expect, and that is not smoothed over.

The negative control is what makes it interpretable. T6's `minimal` frame is the empty string in
the frozen design, so its three arms are byte-identical prompts run three times — a pure
run-to-run noise estimate:

| Version | `minimal` mean | n |
|---|---:|---:|
| v1 | +0.2292 | 24 |
| v2 | +0.2170 | 24 |
| v3 | +0.2205 | 24 |

That is a **5.5% spread on identical text**. Inbox's 25.6% is roughly 5× the noise floor, so the
wording genuinely moves the frame slope — it simply does not move it far enough to threaten the
ordering, which has 1.49× of headroom at its tightest.

## C3 — Flips

**None.** No flip to report in either environment under either variant.

## T5 scale adherence by version (prereg §4)

| Version | n | on 0–10 | % |
|---|---:|---:|---:|
| v1 | 90 | 31 | 34.4% |
| v2 | 90 | 30 | 33.3% |
| v3 | 90 | 25 | 27.8% |

Adherence drifts monotonically with rewording — reworded frames pull models slightly toward the
schema's 0–20 scale and away from the prose's 0–10. The effect is small (6.6 points across the
range) but it is a **finding, not noise**: prompt wording is one of the levers on prose-vs-schema
adherence, which is a mechanism the scale-bug analysis had not identified. All Committee numbers
above are computed after the per-sample scale correction, so the headline result does not depend
on it.

## Thread-ready paragraph (kcqH)

> We ran the wording check on both Committee and Inbox: two meaning-preserving paraphrases per
> frame level (formal-imperative and conversational) against the original, holding incentive text,
> difficulty substrates, scoring and models byte-identical, at the representative cell for each
> environment — 630 scenarios across six models, with Grok 4.3 substituting for the deprecated
> Grok 4 and running its own original-wording arm. **The dominant axis is unchanged in both
> environments under both paraphrases** — Inbox stays frame-dominant (1.49× → 1.93×) and Committee
> stays difficulty-dominant (1.13× → 1.32×), with both margins widening under rewording rather
> than narrowing, so the original wording is the least favourable case for the published claim
> rather than the most. Frame-slope magnitude moved 15.2% across versions on Committee and 25.6%
> on Inbox — the latter outside the ~20% band our earlier paraphrase analysis established, though
> Inbox's `minimal` frame is empty in the frozen design and its three byte-identical arms give a
> 5.5% run-to-run noise floor, so the movement is real but roughly 5× noise and well short of what
> a flip would require.
