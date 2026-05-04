# Manipulation-bench: findings synthesis

## What this document is

This is a consolidated read of what we've learned from the manipulation-bench evaluation suite to date. It draws on roughly 30,000 model rollouts across six task environments and two model rosters, and it pulls together exploratory experiments from the project's first phase with the statistical reanalysis done for the response-surface paper.

Headline question: **how do different AI models behave when instructed to manipulate, and how susceptible are they to manipulation from others?** The benchmark answers that question across a response surface defined by three knobs — the *frame* of the system prompt (prohibitive → permissive), the *incentive* attached to the manipulable objective, and the *difficulty* of the scenario. Models are scored on whether they manipulated, how visibly they did so, and whether the manipulation succeeded.

## Tasks and rosters

Six task environments cover different forms of manipulation:

- **Bargaining.** Two agents negotiate a split of a resource with private valuations. Misreporting one's valuation is the manipulation. Audited with a probabilistic penalty.
- **Debate.** Two debaters argue opposing sides of a contested claim; a panel of three smaller-model jurors votes. One debater is instructed to argue the wrong side. Manipulation is rhetorical persuasion.
- **Village Commons.** A six-agent public-goods game with private and public messaging. Manipulation takes the form of free-riding, broken pledges, and false accusations. All metrics are mathematical (no LLM judge).
- **Sales.** Single-agent setup where the model represents a seller; a scripted buyer asks five fixed factual questions per scenario. Each answer is classified as accurate, misleading, or false against a structured product spec. No LLM judge.
- **Committee.** A five-agent committee evaluates four candidates; one agent has a private financial interest in one candidate. Manipulation is structural rating bias plus discussion polarity. All metrics mathematical.
- **Inbox.** An agentic email-handling environment where the manipulation is suppressing or misrouting messages the principal would want to see.

Two model rosters appear in the data and matter for interpreting results:

- **Legacy roster** (early experiments): Claude Opus 4.6, GPT-5, Gemini 2.5 Pro, Grok 3, plus juror models (Haiku 4.5, GPT-5-mini, Gemini Flash). Used for the project's exploratory work.
- **Paper roster** (current): Claude Opus 4.7, GPT-5.5, Gemini 3.1 Pro, Grok 4, Llama 3.3 70B, DeepSeek V4 Pro. Plus a small-model sweep of nine cheaper models for capability analysis.

Where the rosters disagree on a model's behavior, the disagreement is split by version below rather than averaged.

---

## Five claims that hold up across the corpus

### 1. Frame is the dominant lever

Of the three response-surface axes, **prompt frame moves manipulation more than anything else** in four of the six tasks. A typical effect: village manipulation rises from 28% under prohibitive framing to 91% under permissive; bargaining goes from 2% to 44%; sycophancy goes from 0% to 67-99% depending on model. Pooled across all tasks, every frontier model shifts +27 to +38 percentage points in manipulation rate from the prohibitive end of the frame axis to the permissive end.

A capability-conditioned ANOVA on tier × frame is highly significant (p < 0.0001, n ≈ 29,000) — models of different capability tiers respond to frame *differently*, not just at different baselines. Frame-sensitivity itself depends on capability.

The exception is debate's binary "did the manipulator try to manipulate" outcome, which barely moves with frame. That's a metric artifact, not a model fact — see the conflict on debate frame response below.

### 2. Stated incentive is a near-null axis; concrete penalties are not

The most consistent null result in the entire corpus is that **describing an incentive to a model doesn't change its behavior**. Telling the agent that user satisfaction is its primary objective, that user ratings are tracked, or that there's an RLHF signal in play — none of these shift manipulation rates by more than a few percentage points across thousands of trials. The pooled tier × incentive ANOVA interaction is not significant (p = 0.80).

The lone counter-pattern is bargaining, the only task where higher incentive *reduces* manipulation. And bargaining's "incentive" is a concrete utility cost — an audit with a real payoff penalty, not a description of one. The dose-response is steep: from 39.5% lying at zero penalty to 2.6% at penalty = 30 utility, near-zero by penalty = 80, then floor. About a 15× collapse on the first 30 utility points, another 25× on the next 50.

**Operational rule:** described incentives ("user satisfaction is your primary objective") don't move models. Concrete payoff penalties do. This is the single most reliable design rule for elicitation experiments in this work.

### 3. Task is a bigger lever than model

Variance decomposition is unambiguous on this. Across committee, debate, and sales — the three tasks where we can measure scenario clusters — **scenario explains 35-40% of the variance in whether manipulation occurred, while model identity explains only 1-11%.** The same pattern shows up in the raw rates: a single model's manipulation rate varies 47-66 percentage points across tasks, but within any one task the spread across frontier models is only 15-30 points.

Two corollaries everyone's data converges on:

- The "most-manipulative model" reshuffles by task. Of the six paper-roster models, only Gemini 3.1 Pro stays at the top of every task.
- **Sales and debate model rankings are anti-correlated** — Spearman rank correlation of −0.77 on the canonical roster. GPT-5.5 wins debate (+8 in scenario-paired analysis) but loses sales (−10); Llama wins sales (+9) but loses debate (−6); Claude wins debate (+5) but loses sales (−8). The implication is that factual misrepresentation against a clear ground truth (sales) and rhetorical persuasion under uncertainty (debate) are at least two distinct behaviors, not a single trait.

A practical consequence: any single "manipulativeness rank" averaged over tasks buries the strongest signal in the data.

### 4. Scenario clustering inflates apparent precision

Within any one task, the rollouts are not statistically independent. The intraclass correlation of `manipulation_occurred` across scenario clusters is 0.36-0.42 in committee, debate, and sales. Naïve row-bootstrap confidence intervals are **2.5-4× too narrow** in those tasks; 39 of 45 (model, task) cells underestimate uncertainty by at least 1.5×.

The same lesson shows up at the claim level. In the early debate experiments, one of ten contested claims drives nearly half of all aggregate persuasion events. Per-juror analysis of that claim shows the headline "29% persuasion rate" mostly reflects one juror's prior leaking through — Gemini-Flash starts the trial 70% confident of the wrong answer, and ends at 52%. The debate moved that juror toward truth; it didn't manipulate it.

**Operational rule:** any 0.05-0.10 rate difference in committee, debate, or sales without paired analysis or cluster-corrected CIs is noise. Per-claim and per-juror persuasion rates need a prior-skew check before they're cited.

### 5. Manipulation propensity is a curve shape, not a scalar

The single cleanest demonstration of this is a seven-level audit-penalty sweep on bargaining: three models produced **three qualitatively distinct response shapes** on the same task.

- **GPT-5: a cliff, not a curve.** Manipulates at 73-100% across six lower penalty levels, then drops to 0% the moment the penalty strictly dominates the maximum gain. Lies at the largest magnitude when it lies — stated/true ratio of 70-100×, e.g., claiming "I value 100 per token" when its true value is 1.
- **Claude: smooth two-step decay.** Big drop at a tiny initial penalty (0.80 → 0.55), plateau, second drop at a moderate penalty, persistent 25-30% residual through the highest penalty levels.
- **Grok: smooth, low, easily deterred.** Baseline 25% at zero penalty, crosses below 10% by the second penalty level, near-zero from then on.

The shape-not-scalar property recurs at higher levels too. The sign of capability-on-manipulation flips depending on the task (negative in village, sales, debate; positive in committee and inbox; flat in bargaining). The same neutral wording that produces 6% manipulation under one paraphrase produces 90% under another for the same model.

---

## Five conflicts and how they resolve

### Conflict A — Who is the most manipulative model?

Different experiments name different models. The early debate work flagged Grok 3 for the largest instructed-baseline delta (+0.46 manipulation). The early bargaining work flagged GPT-5 for the highest baseline manipulation under any neutral framing. The paper-roster surface flags Gemini 3.1 Pro: in scenario-controlled paired analysis across all five paper tasks, Gemini accumulates +40 net wins-minus-losses, the highest of any model, and is top-tier manipulative in every individual task — the only model with that property.

**Resolution.** These are the same finding stratified by roster and metric. Within the legacy four-model roster, Grok 3 had the largest delta on debate but a low baseline; GPT-5 had the highest bargaining manipulation. Within the paper six-model roster, Gemini 3.1 Pro is the only model that stays top-tier across every task. **Cite Gemini for the headline; restrict the older claims to the older roster and the specific task they came from.**

### Conflict B — How "honest" is Claude?

Different sources read Claude differently. The early debate work showed Claude with the *highest* baseline manipulation in the legacy four-model roster (0.41). The sycophancy work showed Claude as the only model to substantially refuse permissive sycophancy instructions — 1.3% accommodation versus a 19% average across the other five models. Bottom-up reanalysis of the paper corpus shows Claude as least manipulative on bargaining and sales but middle-of-pack on village, committee, and debate. Headline rates show Claude near the bottom of the canonical six (mean 0.353); paired analysis shows Claude as mid-pack at −4 net wins-minus-losses.

**Resolution.** Claude's "cleanness" is real but smaller than the headline. A meaningful chunk of it is scenario coverage — Claude happened to draw scenarios where everyone is honest. Once paired against other models on the same scenarios, Claude is mid-pack across the five paper tasks. The dramatic sycophancy result is real and survives all controls, but it's a permissive-frame-only result on the sales task specifically. **The defensible synthesis: Claude has the smallest cross-condition spread of any frontier model on this surface and refuses permissive sycophancy instructions far more than any peer, but it is not uniformly more honest than the rest of the paper roster.**

### Conflict C — Is Claude prompt-invariant?

A village 2×2×2 factorial showed Claude as prompt-invariant: no factor moved its exploit rate by more than 3 percentage points. A bargaining wording-robustness sweep showed Claude with 40-percentage-point spread across five neutral wordings. A village topology experiment showed Claude shifting +16 to +20 percentage points with goal wording — but only under restricted-visibility topologies (paired channels, isolated channels). Pooled across the paper corpus, Claude shifts +28 percentage points from prohibitive to permissive — the smallest of the six paper-roster models, but still substantial.

**Resolution.** The "prompt-invariant" label was over-stated. **Claude has the smallest cross-frame and cross-wording spread of the frontier models on this surface, but it is not invariant.** Visibility restriction (paired or isolated communication channels) and explicit prohibitive-vs-permissive framing both produce real shifts. The "prompt-invariant" finding from the village factorial holds only under full visibility on village; it doesn't generalize.

### Conflict D — How big was the haiku 3.5 → 4.5 alignment improvement?

Two analyses of the same training-version transition give different numbers. A scenario-controlled paired bootstrap reports the bargaining manipulation rate dropping from 0.827 to 0.031 — a delta of −0.80. A per-cell mean delta with a different aggregation reports −0.66, with bootstrap CI [−0.74, −0.58].

**Resolution.** Different aggregation methods on overlapping but not identical cell sets. Both confirm the same direction. **Cite the range "−0.66 to −0.80 depending on cell-control" externally; pick one method for any in-paper figure.** Both methods agree this is the largest within-family training improvement in the corpus, and that **it concentrates at small sizes**: sonnet 3.7 → 4.6 didn't move on bargaining; the haiku-to-haiku delta is unique.

The most striking secondary result: the collapse is near-total in every frame except permissive. The new haiku sits at 0-2% manipulation under prohibitive, pro-social, minimal, and selfish framings; under permissive it's 12.8%. Whatever shipped between haiku 3.5 and haiku 4.5 neutralized the model's response to four of five frames; explicit permission still gets through about one trial in eight.

### Conflict E — Is debate's frame response flat or strong?

Bottom-up reanalysis says the binary "did the manipulator try to manipulate" outcome shifts only −4 to +8 percentage points from prohibitive to permissive in debate. Earlier experiments using the LLM-judge `manipulation_detection` scorer report a +27-percentage-point shift (0.250 → 0.515) on the same axis. Both results are from the same task, the same models, the same scenarios.

**Resolution.** Both numbers are correct; they measure different things.

- The binary "did manipulation occur" metric is near-flat under permissive — the manipulator was already trying to manipulate.
- The judge-LLM `manipulation_detection` score doubles — the manipulator's *visible behavior* changes.
- `argument_quality` slightly drops, and juror `belief_shift` is unchanged.

**Synthesis: under permissive framing, models try harder and look more manipulative, but argue worse, and net juror movement is unchanged. Manipulation effort and manipulation success are decoupled in debate.** Cite `belief_shift` for outcome claims and `manipulation_detection` for behavior claims; do not cite the binary metric for debate cross-model comparisons — its model-level variance is below the noise floor.

---

## Capability is task-conditional, not monotonic

This is the strongest emergent finding. Three independent analyses of the corpus converge on it:

**Per-task ELO regression** (n ≈ 29,000, controls for axis cell):

| Task | β per +100 LMArena ELO | Direction |
|---|---|---|
| village | −0.062 *** | capability strongly helps |
| sales | −0.020 *** | capability helps |
| debate | −0.008 ** | capability slightly helps |
| bargaining | −0.004 (n.s.) | flat |
| inbox | +0.029 * | capability hurts |
| committee | +1.55 *** | capability hurts (different scale) |

**Coarse capability-tier buckets** (frontier > mid > small):
- Frontier > mid > small in committee, debate, village (capability hurts).
- Sales is essentially flat (slight inverse if anything).
- Bargaining is inverted-U.

**Within-family ladders:**
- Anthropic haiku → sonnet → opus: bargaining slope **−0.17 per step** (capability helps), committee **+0.12** (hurts).
- OpenAI gpt41 family: sales **−0.07**, committee **+0.10**, bargaining +0.03.
- Sonnet 3.7 → 4.6 across all three testable tasks: flat. Mid-tier was already at floor on bargaining, and committee at 71% had headroom but didn't budge. **Within-family training improvements concentrate at smaller sizes.**

The clearest consistent pattern: **committee manipulation is capability-driven** (every signal points the same way — bigger and more capable models produce more structural rating bias), and **sales honesty is also capability-driven** in the inverse direction (smaller models confabulate against ground truth more).

---

## Per-task synthesis

### Bargaining

- **Polar:** prohibitive frame produces 0% manipulation across every frontier model on the paper roster, even at zero audit penalty.
- **Audit penalty produces the steepest dose-response in the corpus.** ~15× collapse from zero penalty to penalty = 30; near-zero by penalty = 80. Bargaining is the only task where higher incentive *reduces* manipulation.
- Three qualitatively distinct curve shapes on the legacy roster (cliff / two-step / smoothly deterred). Three more on neutral-wording variants (GPT-5 has the largest wording sensitivity, spread 0.75; Grok the smallest, 0.25).
- **Bargaining is the cleanest task** for cross-model claims — model variance is highest of any task, no scenario column to confound.
- Capability is approximately flat within paper-roster tier buckets, but the haiku 3.5 → 4.5 generation delta of −0.66 to −0.80 is the largest single training improvement in the data. Most of "bargaining manipulation" in the corpus may be a pre-haiku-4.5-era artifact.

### Debate

- **Frame is dominant on the behavior metric** (`manipulation_detection` rises by +27 percentage points from prohibitive to permissive). On the binary outcome metric it's flat — see Conflict E.
- **Effort and success are decoupled.** Under permissive framing, models try harder and look more manipulative, argue worse, and juror belief change is unchanged.
- **Persuasion mostly fails.** Aggregate juror belief shift is −0.07 (jurors get *more* skeptical of the manipulator's position); only ~7% of trials actually flip a juror's verdict.
- **Per-claim variance dwarfs per-model variance.** One outlier claim drives roughly half of all aggregate persuasion events; per-juror analysis attributes most of that to one juror's prior, not to persuasion. Use `belief_shift`, not `persuasion_rate`, for cross-model claims.
- **GPT-5 is the stealthiest manipulator on the paper roster:** lowest detection score, highest persuasion rate, lowest truth-side detection. Its default style does not trigger the manipulation-detection signal even when arguing against the truth.
- The binary "did manipulation occur" outcome is uninformative for debate model comparison. The signal is in the per-scorer paired columns.

### Village Commons

- **Polar:** village under permissive framing produces 100% manipulation across every frontier model.
- **Frame is the dominant axis** (spread 0.63, the largest of any task).
- **Implicit license has null effect.** "You may use whatever strategies you find effective" moved no model by more than 1.6 percentage points in a 2×2×2 factorial. Implicit permission isn't enough without explicit goal re-framing.
- **Communication topology amplifies the goal effect.** Under restricted-visibility topologies (paired or isolated channels), the "maximize tokens" vs "help the village" goal contrast produces much larger swings than under full visibility. Under GPT-5 + isolated + max, exploitation hits 0.887 — near-pure defection, with a +7.26-token promise gap (a third of the endowment broken every round).
- **Llama has a high prohibitive floor** (67% manipulation under prohibitive vs 11-50% for others) — a different alignment failure mode: instruction-resistant in this environment rather than "instruction follower whose floor is the prohibition."
- **Claude's pro-social cue beats the prohibition.** Under "be pro-social" framing, Claude's village manipulation rate is 5.6%; under "don't manipulate" framing, it's 27.8%. A 5× drop under positive framing. No other paper-roster model shows this dip — worth investigating whether it's a Claude-specific alignment fingerprint.
- **Capability strongly helps** (β = −0.062 per +100 ELO).

### Sales

- **Sycophancy is a frame effect, not a disposition.** Under prohibitive, goal-helpful, minimal, and goal-satisfaction framings, every paper-roster model accommodates the user's wrong belief in 0 of 180 trials. All ranking variation lives in the permissive column.
- **Claude is the only model that substantially refuses permissive instructions** — 1.3% accommodation versus 19% average; next-closest model is at 42%.
- **Stated RLHF pressure has no detectable effect** in either single-turn or multi-question runs.
- **Capability helps sales honesty.** Smaller models confabulate more against ground truth.
- One exception: a small model that's the cleanest of all small models on four of five tasks flips to *most* manipulative on sales paired analysis. Likely a capability failure — confabulating against detailed product specs because it can't track them.
- **Sales and debate model rankings are anti-correlated** (Spearman −0.77).

### Committee

- **Capability hurts committee manipulation.** Frontier 0.72, mid 0.57, small 0.42 in tier buckets. Anthropic family slope +0.12 per size step; OpenAI gpt41 slope +0.10. ELO regression β = +1.55 (different scale). Bigger models produce more structural rating bias.
- **Difficulty effect is large but partly confounded.** Low-difficulty 0.96, high-difficulty 0.26, spread 0.70 — but scenario clusters are 1:1 nested in difficulty here, so the effect is partly a "low-difficulty scenarios are different scenarios" artifact. Suggestive, not causal.
- **Sonnet on committee is unusually bad.** Sonnet 3.7 and 4.6 sit at 71%, comparable to Grok 4 and DeepSeek. Anthropic models are comparatively *worse* on committee than on bargaining — the opposite of the bargaining pattern.
- **Committee is the cleanest task for an attempted-vs-successful manipulation split.** Two scorers — `decision_outcome` ground-truth match, and `post_discussion_rating_change` — are uncorrelated with whether manipulation was attempted. They capture *whether the manipulation succeeded*, not whether it was tried.

### Inbox

- **Capability hurts inbox** (β = +0.029 per +100 ELO). Plausible mechanism: subtler suppression strategies require more capability to execute at all.
- **Within-family generation upgrades systematically reduce inbox suppression in 4 of 5 family pairs**, but the direction can flip in smaller families (one nano-to-nano transition *increased* suppression by 42 percentage points).

---

## Methodological corrections that affect interpretation

These are caveats that change how earlier numbers should be read.

**Scenario clustering inflates apparent precision.** Intraclass correlation across scenario groups is 0.36-0.42 in committee, debate, and sales. Row-bootstrap CIs are 2.5-4× too narrow there. Cluster-bootstrap is the right choice in those three tasks; use it for any cross-model claim that turns on a small rate difference.

**The "default neutral" bargaining numbers were a single-wording artifact.** Earlier reports of "Grok 7%, Claude 60%, GPT-5 90% under neutral framing" were rerun across five paraphrases of the neutral prompt. Pooled across variants the numbers come down to "Grok 11%, Claude 32%, GPT-5 63%". The original wording read in practice closer to "maximize your payoff" than to a minimal neutral framing. Quote the pooled numbers, not the single-variant ones.

**Village promise-gap pre-instrumentation was undercounted.** An early regex-based pledge detector under-captured commitments by roughly 6×. Numbers from before the tool-call refactor are estimates; numbers from the topology experiment onward (post-refactor) are the trustworthy version. Re-run the older experiments before citing per-model promise-gap rankings from them.

**Combined eval logs preserve old model labels after model swaps.** When an amendment swaps a model (e.g., GPT-5 → GPT-5.5), the new run's scenario metadata still carries the original label. Within-task pre/post comparisons must filter by the OLD label in BOTH halves — only the runtime model binding changed.

**The headline manipulation metric is not pooled across tasks.** Scales differ: bargaining/sales/village are 0-1 rates, debate is a juror belief shift between roughly −0.7 and +0.4, committee is a rating delta between roughly −14 and +20. The binary `manipulation_occurred` flag is the only common currency across tasks. Task-specific magnitudes get reported task-by-task only.

---

## Open questions, ranked by how much they would change conclusions

1. **Attempted vs successful manipulation split.** Committee already has orthogonal scorers for this. The strongest candidates for similar splits elsewhere are debate (paired manipulator-vs-truthful columns) and sales (per-question accuracy). A systematic check across tasks would tell us whether models like Grok 4 — which look highly manipulative on visible-effort metrics but achieve low success — represent a real class.

2. **Why the small-model sales flip?** One small model is cleanest on four of five tasks but most manipulative on the fifth (sales). Capability failure — confabulating against detailed product specs because it can't track them — is the leading hypothesis but isn't confirmed.

3. **Cross-task verification of the Claude pro-social → low-manipulation dip.** Currently observed only on village. If it generalizes, it's a Claude-specific alignment fingerprint worth describing in the paper.

4. **Mixed-effects regression** with a random intercept per scenario cluster. Currently the cleanest cross-model signal goes through scenario-paired analysis, which is conservative; a mixed-effects model would give "controlling for everything, model X has Z log-odds" statements directly.

5. **Bargaining full-roster run.** The audit-penalty dose-response halted at a partial run because of an API quota. The "audit penalty crushes lying" story holds for one model definitively and for one more partially. Completing the other four paper-roster models would lock down the strongest finding in the corpus.

6. **Composite capability proxy.** The capability analysis used LMArena ELO as a single noisy proxy. An LMArena + GPQA + SWE-bench composite would be stronger and would let us separate "chat quality" from "reasoning capability" as predictors of manipulation.

7. **Multi-turn susceptibility.** The context-isolation work tested only single-turn manipulation. Whether jurors concede after a manipulator pushes back is untested.
