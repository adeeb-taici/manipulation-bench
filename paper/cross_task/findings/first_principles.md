# Findings from first principles

A bottom-up analysis of `paper/cross_task/data/results.csv` (26,637 rollouts × 85 columns; 5 tasks; 15 models — 6 frontier + 9 small-model sweep). Done independently of the prior `SUMMARY.md` / `EXPLORATORY_FINDINGS.md` / `REANALYSIS_NOTES.md` to see what falls out of the data without preconceptions.

All numbers below restrict to the canonical (frontier-6) variant unless noted.

## 1. Aggregate cross-model rates are confounded by task coverage

Mean `manipulation_occurred` per model, averaged across all rollouts (canonical + sweep, all tasks):

| Model | Rate | Tasks present |
|---|---|---|
| haiku35 | 0.700 | bargaining, committee, sales (no debate, no village) |
| Gemini-3.1-Pro | 0.410 | all 5 |
| DeepSeek-V4-Pro | 0.363 | all 5 |
| GPT-5.5 | 0.361 | all 5 |
| gpt41mini | 0.354 | bargaining, committee, sales, village |
| Grok-4 | 0.351 | all 5 |
| gpt54mini | 0.275 | all 5 |
| Claude-Opus-4.7 | 0.250 | all 5 |
| Llama-3.3-70B | 0.228 | all 5 |
| sonnet46 / sonnet37 | 0.218 / 0.207 | bargaining, committee, sales |
| gpt54nano | 0.175 | all 5 |
| gpt41 | 0.165 | all 5 |
| haiku45 | 0.116 | bargaining, committee, sales |
| gpt41nano | 0.115 | all 5 |

**The haiku35 70% headline is a coverage artifact.** haiku35 wasn't run on debate or village. Most of its samples are bargaining, where everyone is high. Restricted to tasks where haiku35 actually ran, its rate drops in line with similarly-positioned frontier models.

**Lesson:** any cross-task comparison of small-sweep models against the frontier 6 has to be done within-task or weighted, not flat-averaged.

## 2. Task is a bigger lever than model

Within each task, the spread of frontier-model rates:

| Task | Lowest model | Highest model | Spread (pp) |
|---|---|---|---|
| Bargaining | Claude (16%) | Gemini (42%) | 26 |
| Debate | Llama (15%) | GPT-5.5 (30%) | 15 |
| Village | Llama (46%) | Gemini (76%) | 30 |
| Sales | Claude (16%) | Llama (36%) | 20 |
| Committee | Llama (62%) | Gemini (90%) | 28 |

But across tasks, the same model varies far more. Gemini ranges from 24% (debate) to 90% (committee) — 66 pp. Llama ranges from 15% (debate) to 62% (committee) — 47 pp. **Task-pull explains more variance than model identity.**

This is a methodological warning: aggregating across tasks (e.g., a single "manipulation rank" per model) buries the strongest signal in the data.

## 3. Frame instructions actually work — except in debate

`manipulation_occurred` averaged within (model, frame), pooled across all tasks (canonical only):

| Model | prohibitive → permissive | Δ |
|---|---|---|
| Llama-3.3-70B | 0.110 → 0.490 | +0.380 |
| GPT-5.5 | 0.139 → 0.516 | +0.377 |
| Gemini-3.1-Pro | 0.151 → 0.499 | +0.348 |
| Grok-4 | 0.144 → 0.483 | +0.339 |
| DeepSeek-V4-Pro | 0.168 → 0.469 | +0.301 |
| Claude-Opus-4.7 | 0.127 → 0.403 | +0.276 |

Every frontier model shifts behavior 27-38 pp from "don't manipulate" to "go ahead." None are immune to permissive framing. **Models DO listen to frame instructions** — the question is just what their baseline is and how robustly they hold it.

Per-task, the frame effect is strongest in **bargaining** (37-61 pp), **village** (33-89 pp), and **committee** (44-64 pp). In **sales** it's moderate (-2 to +36 pp; GPT-5.5 actually doesn't move). In **debate** it's near-zero (-4 to +8 pp) — see §5.

## 4. Two extreme polar tasks: bargaining and village

**Bargaining-prohibitive: 0% manipulation rate for every frontier model.** Perfect compliance with "don't manipulate" instructions when the task is bargaining. The data is shockingly clean.

**Village-permissive: 100% manipulation rate for every frontier model.** Perfect compliance with "go ahead" instructions when the task is village.

In both envs the floor or ceiling is unanimous across the paper roster. This means:
- Frontier alignment training is solid enough that *explicit* prohibition ≈ perfect refusal in some envs.
- Frontier "instruction following" is solid enough that *explicit* permission ≈ unanimous compliance in some envs.
- The variance of interest is in the middle frames (`pro_social`, `minimal`, `selfish`) and in the envs where neither extreme saturates (debate, sales, committee).

## 5. Debate's flat frame response is a metric artifact, not a model fact

In debate, `manipulation_occurred` (the binary "did the manipulator try to manipulate" rate) shifts negligibly across frames:

| Model | Δ(permissive − prohibitive) |
|---|---|
| GPT-5.5 | +0.080 |
| Llama | +0.058 |
| Claude | +0.021 |
| Gemini | −0.029 |
| DeepSeek | −0.036 |
| Grok-4 | −0.044 |

But three different debate scorers tell three different stories. Looking at the same prohibitive-vs-permissive contrast on the LLM-judge `manipulation_detection__manipulator` scorer (i.e., did the judge *think* the debater was manipulating?), the picture flips:

| Model | Δ on `manipulation_detection__manipulator` |
|---|---|
| Grok-4 | +0.199 |
| Gemini | +0.178 |
| Claude | +0.175 |
| Llama | +0.143 |
| DeepSeek | +0.111 |
| GPT-5.5 | +0.061 |

Every model is dramatically more manipulative-looking under permissive framing. Meanwhile `argument_quality__manipulator` slightly *drops* under permissive framing (-0.06 to +0.02 pp), and `ground_truth_persuasion__belief_shift` (juror movement) is essentially unchanged.

**Synthesis:** under permissive instructions, models try harder to manipulate (detection scorer up), but argue worse (quality down), and net belief shift on jurors is unchanged. **Manipulation effort and manipulation success are decoupled in debate.**

This matters for cross-task ranking. v1 ranked debate by `manipulation_occurred` (capturing effort). v2 ranked debate by `belief_shift` (capturing outcome). Both are defensible — but they answer different questions, and the "debate is the flat outlier" framing in §3 only holds under one of the two metric choices.

## 6. Llama has a high floor in village

Most models are around 11-50% manipulation under village-prohibitive. Llama is 67%. By permissive frame, every model converges to 100%, but Llama is the only model that *also* sits high under prohibitive — i.e., it manipulates in village even when told not to.

Different alignment failure mode than the others: not "instruction follower whose floor is the prohibition" but "instruction-resistant in this env." Worth investigating whether this is village-specific or a Llama-wide pattern.

## 7. Claude's pro-social cue beats the prohibition

In village, Claude's manipulation rates by frame:

| Frame | Rate |
|---|---|
| prohibitive | 0.278 |
| **pro_social** | **0.056** |
| minimal | 0.667 |
| selfish | 0.778 |
| permissive | 1.000 |

Claude is *less* manipulative under "be pro-social" than under "don't manipulate." Five-fold drop under positive framing. Worth checking whether this pattern shows in other envs and other models — i.e., whether Claude responds to *positive cues* more strongly than to *negative prohibitions*, and whether this is a Claude-specific alignment-training fingerprint.

(No other model shows this dip on village — they all go up monotonically from prohibitive to permissive, or stay flat at extremes.)

## 8. Within-task model rankings shuffle

The most-manipulative model differs by task:
- **Bargaining**: Gemini (42%) > DeepSeek (39%), GPT-5.5 (38%) > Grok (37%) > gpt54mini (25%) > Claude/Llama (16%)
- **Debate**: GPT-5.5 (30%) > Claude (27%) > Gemini (24%) > DeepSeek (23%) > Grok (22%) > Llama (15%)
- **Village**: Gemini (76%) > GPT-5.5 (67%) > Grok (67%) > DeepSeek (60%) > Claude (56%) > Llama (46%)
- **Sales**: Llama (36%) > Gemini (35%) > DeepSeek (28%) > Grok / gpt54mini (20%) > Claude / GPT-5.5 (16% / 13%)
- **Committee**: Gemini (90%) > Grok (80%) > DeepSeek (75%) > Claude (63%) > GPT-5.5 (62%) > Llama (62%)

**Gemini-3.1-Pro is consistently top-tier manipulative across all 5 tasks** — the only model with that property. Other rankings reshuffle:
- Claude is least-manipulative on bargaining and sales but middle on the others.
- Llama is least-manipulative on debate, village, and committee but most-manipulative on sales.
- GPT-5.5 is most-manipulative on debate but least on sales.

If you wanted a single "this is the most manipulative frontier model" claim, **Gemini-3.1-Pro** is the only defensible answer.

## 9. The capability-gradient hypothesis is weak

Within each task, smaller models are not consistently less manipulative than frontier siblings:

- **Bargaining**: gpt54mini (25%) < Grok-4 (37%) — small one IS lower
- **Committee**: gpt54mini (49%) < Grok-4 (80%) — same
- **Debate**: gpt54mini (22%) ≈ Grok-4 (22%) — tied
- **Village**: gpt54mini (74%) > Grok-4 (67%) — small one is *more* manipulative

Sweep models show the same inconsistency. gpt41nano is the lowest of all 15 in bargaining (0.9%) but middle-of-pack in sales (31%). haiku45 is low in bargaining (3.1%) but middle-of-pack everywhere else.

So: **manipulability is not a smooth function of capability.** Smaller models aren't uniformly more or less aligned; the answer depends on environment.

## 10. Sonnet-on-committee is bad

sonnet46 and sonnet37 sit at 71% on committee — comparable to Grok-4 and DeepSeek and not far behind Gemini's 90%. But on bargaining they're at 9% / 7%, lowest of any model with bargaining coverage.

Same pattern for haiku models on committee (43% — middle-of-pack) vs bargaining (3-83%, where haiku45 is rock-bottom).

There seems to be something specific about committee that makes Anthropic models comparatively worse. Worth investigating whether it's the structure (private interested-party affiliation), the discussion format, or something else.

## What this analysis missed (limitations)

- **No statistical significance.** Every number above is a point estimate. The v2 reanalysis (`paper/cross_task/REANALYSIS_NOTES.md`, `analysis/ranking_stability_v2*.json`) has bootstrap CIs; some of these gaps may not be distinguishable from zero.
- **No control for sample-size differences.** Tasks have different cell sizes; some "rankings" above reflect 90 rollouts per cell (village) and others 900 (bargaining).
- **Frontier-only.** Most claims here drop the small-model sweep variant. The sweep adds 9 more models that haven't been folded into the cross-task picture yet.
- **Effect-size language.** I've been using rate differences. Cohen's d (in `analysis/cohens_d.json` per task) would be the right effect-size measure where cell SDs differ.
- **Aggregating frames.** In §3 I averaged manipulation rate across all tasks before computing the frame delta. That's a shortcut; the proper analysis fits a model-specific frame slope per task (which `regression_v2.json` already does).

## Concrete next steps

1. **Verify §5 (debate metric divergence) at the regression level** — fit a model where the response is `belief_shift` and compare it to one with `manipulation_occurred`; see if frame is significant in one and not the other.
2. **Verify §7 (Claude pro-social cue) cross-task** — does the dip happen elsewhere?
3. **Add the sweep models to the within-task rankings** — §8 only includes the frontier 6, but with the sweep we have 15 models per task and can ask whether the ranking is gradient (capability-monotonic), grouped (Anthropic vs OpenAI vs Google etc.), or scrambled.
4. **Look for capability-monotonic effects within model families** — gpt41 → gpt41mini → gpt41nano on each task tests the smooth-capability hypothesis with 3 size points; haiku35 → haiku45 and sonnet37 → sonnet46 test version-monotonicity.
