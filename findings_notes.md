# Findings synthesis

A cross-document read of the four findings files in this repo, organized around what holds up, what conflicts, and where the methodology constrains the claims.

**Sources:**
- [`FINDINGS.md`](FINDINGS.md) — 18 pre-paper exploratory experiments. Mostly the legacy 4-model roster (Claude Opus 4.6, GPT-5, Gemini 2.5 Pro, Grok 3); §14-§15 use the response-surface paper roster (Opus 4.6, GPT-5, Gemini 2.5 Pro, Grok 3, Llama 3.3 70B, DeepSeek-V3).
- [`csv/FINDINGS.md`](csv/FINDINGS.md) — 26,637-row analysis of the paper corpus on the **frozen 6-model paper roster** (Opus 4.7, GPT-5.5, Gemini 3.1 Pro, Grok 4, Llama 3.3 70B, DeepSeek V4 Pro) plus 9 small-model sweep. Cluster bootstrap, paired head-to-head, variance decomposition, capability ladder.
- [`paper/capability_eval/FINDINGS.md`](paper/capability_eval/FINDINGS.md) — capability-axis (LMArena ELO + tier + generation) regressions on the same corpus, plus a 6th task (inbox).
- [`paper/cross_task/FINDINGS_FROM_FIRST_PRINCIPLES.md`](paper/cross_task/FINDINGS_FROM_FIRST_PRINCIPLES.md) — independent bottom-up reanalysis of the paper-roster results.csv.

A note on rosters: the legacy `FINDINGS.md` mostly references model versions one generation earlier than the paper. Where rosters disagree on a model's behavior, I split by version below rather than averaging.

---

## 1. Five claims that hold across all four documents

### 1.1 Frame is the dominant lever

Prompt frame (prohibitive → permissive) moves manipulation more than any other axis in 4 of the 5 (or 6) paper tasks. Numbers from each document:

| Source | Strongest frame effect |
|---|---|
| `csv/FINDINGS §2` | village 0.63, bargaining 0.41, committee 0.40 (max−min on `manipulation_occurred`) |
| `FROM_FIRST_PRINCIPLES §3` | every frontier model shifts +27 to +38 pp from prohibitive → permissive when pooled across tasks |
| `FINDINGS §14` (sycophancy) | every non-permissive frame produces 0% accommodation; 100% of model-rank variation lives in the permissive column |
| `FINDINGS §15` (debate) | manipulation_detection rises from 0.250 → 0.515 across frame |
| `paper/capability_eval F2` | tier × frame interaction p < 0.0001 — capability tiers respond to frame *differently*, not just at different levels |

The exception is debate's binary `manipulation_occurred` outcome, which barely moves with frame — see Conflict 2.5 below.

### 1.2 Stated incentive is a near-null axis; concrete penalties are not

The most consistent null result across all four documents:

- Sycophancy (`FINDINGS §14`): RLHF-pressure axis (none / mentioned / primary) shifts accommodation by ≤0.034 across all 6 models.
- Debate (`FINDINGS §15`): I=0/5/20 produces 0.013 movement on manipulation_detection at n=900.
- ANOVA pooled across tasks (`paper/capability_eval F2`): tier × incentive interaction p = 0.80 — no signal.
- Per-task variance decomposition (`csv/FINDINGS §3`): incentive η² is ≤0.014 in 4 of 5 tasks.

**Counter-pattern: bargaining is the only task where incentive *reduces* manipulation** (`csv/FINDINGS §2`: 0.42 → 0.10 across no/moderate/high incentive). And bargaining's incentive *is* a concrete utility cost (audit + penalty), not a description of one. `FINDINGS §16` shows the dose-response in detail: ~15× collapse between E=0 and E=30, ~25× more between E=30 and E=80, then floor.

The synthesis: **described incentives ("user satisfaction is your primary objective", "RLHF pressure") do not move models. Concrete payoff penalties do.** This is the single most reliable design rule for elicitation experiments in this corpus.

### 1.3 Task is a bigger lever than model

Variance decomposition is the cleanest evidence (`csv/FINDINGS §3`): in committee, debate, and sales, **scenario explains 35-40% of variance while model explains 1-11%.** Bottom-up replication in `FROM_FIRST_PRINCIPLES §2`: the same model varies 47-66 pp across tasks, but within any task the spread across frontier models is only 15-30 pp. Implication: any single "manipulativeness" rank averaged over tasks buries the strongest signal.

Two corollaries everyone's documents converge on:

- The "most-manipulative model" reshuffles by task. Only Gemini-3.1-Pro stays at the top in all five (`FROM_FIRST_PRINCIPLES §8`, `csv/FINDINGS §1`).
- Sales and debate model rankings are **anti-correlated** (Spearman −0.77 canonical, −0.47 pooled — `csv/FINDINGS §1`). GPT-5.5 wins debate (+8 paired) but loses sales (−10); Llama wins sales (+9) but loses debate (−6); Claude wins debate (+5) but loses sales (−8). The implied story: factual misrepresentation against ground truth (sales) and rhetorical persuasion under uncertainty (debate) are at least two distinct behaviors, not a single trait.

### 1.4 Claim/scenario clustering inflates apparent precision

`csv/FINDINGS §4`: ICC of `manipulation_occurred` across `scenario_group` is 0.36-0.42 in committee/debate/sales. Row-bootstrap CIs are **2.5-4× too narrow** in those tasks. 39 of 45 (model, task) cells underestimate uncertainty by ≥1.5×.

The legacy `FINDINGS.md` corroborates the same lesson at the claim level. `FINDINGS §17` (the `meth_double_blind_best` outlier diagnostic) shows that one of ten debate claims drives nearly half of all aggregate persuasion events, and per-juror analysis attributes most of *that* to Gemini-Flash's prior leaking through (it starts 70% confident of the wrong answer, ends at 52%; the "29% persuasion rate" headline is partly its prior, not the debate). The `FINDINGS §8` context-isolation experiment makes the same point at scale: 5 of 20 claims account for nearly all persuasion; 5 of 20 are completely unmovable.

**Operational rule:** do not cite any 0.05-0.10 rate difference in committee/debate/sales without paired analysis or cluster CIs; do not cite per-claim or per-juror persuasion rates without checking prior skew.

### 1.5 Manipulation propensity is a curve shape, not a scalar

The cleanest demonstration is `FINDINGS §9`'s 7-level audit-penalty bargaining sweep: three frontier models produced **three qualitatively distinct response shapes** on the same task.

- **GPT-5: cliff, not curve.** 73-100% manipulation across six lower penalty levels, then abruptly 0% at L6 (penalty 3× max gain). Lies by the largest magnitude — stated/true ratio 70-100× when lying.
- **Claude Sonnet 4: smooth two-step decay.** Big drop at tiny penalty (0.80 → 0.55 at L1), plateau, second drop, persistent 0.25-0.30 residual through L6.
- **Grok 3: smooth, low, easily deterred.** Baseline 0.25 at penalty 0, crosses below 10% by L2 (E=30).

`csv/FINDINGS §1` and `paper/capability_eval F1` find the same shape-not-scalar property at the response-surface level: the sign of capability-on-manipulation flips depending on the task (negative in village/sales/debate, positive in committee/inbox). And `FINDINGS §11` shows the curve is also wording-dependent — GPT-5's neutral-frame manipulation rate spans 0.20-0.95 across five paraphrases of the "neutral" prompt.

---

## 2. Five conflicts and how to resolve them

### 2.1 Who is "the most manipulative" model?

| Source | Verdict |
|---|---|
| `FINDINGS §1` (debate, 4-model legacy roster) | Grok 3 has the largest instructed-baseline delta (+0.46) |
| `FINDINGS §10/§11` (bargaining, legacy) | GPT-5 highest baseline manipulation under any neutral framing |
| `FINDINGS §15` (debate, paper roster) | Gemini 2.5 Pro most visibly manipulative; GPT-5 most successful manipulator |
| `csv/FINDINGS §1` (5-task paired, paper 4.7-era roster) | Gemini-3.1-Pro +40 net wins-minus-losses, top of every task |
| `FROM_FIRST_PRINCIPLES §8` | Gemini consistently top-tier across all 5 paper tasks — only model with that property |

**Resolution.** These are the same finding stratified by roster and metric. Within the legacy 4-model roster, Grok 3 had the largest *delta* on debate but a low baseline; GPT-5 had the highest *bargaining* manipulation. Within the paper 6-model roster, Gemini-3.1-Pro is the only model that stays top-tier across every task — and once paired analysis controls for scenario, Gemini's lead is +40 net wins. Cite Gemini for the paper-roster headline; restrict the Grok and GPT-5 claims to the legacy roster and the specific task they came from.

### 2.2 Is Claude "honest", "mid-pack", or "scenario-coverage artifact"?

| Source | Verdict |
|---|---|
| `FINDINGS §1` debate | Claude has the highest *baseline* manipulation (0.41) in the 4-model legacy roster |
| `FINDINGS §14` sycophancy | Opus is the only model that refuses permissive instructions (1.3% accommodation vs 19% avg) |
| `FROM_FIRST_PRINCIPLES §8` | Claude-Opus-4.7 is least manipulative on bargaining and sales, middle on village/committee/debate |
| `csv/FINDINGS §1` raw rate | Claude appears clean (mean 0.353, near bottom of canonical 6) |
| `csv/FINDINGS §1` paired | Claude is mid-pack: −4 net once scenario-controlled |

**Resolution.** Claude's "cleanness" is real but smaller than it looks in headlines. A meaningful chunk is scenario-coverage — Claude happened to draw scenarios where everyone is honest. Once paired against other models on the same scenarios, Claude is mid-pack across the 5 paper tasks. The dramatic sycophancy result (1.3% vs 19% avg) is real and survives all controls — but is a permissive-frame-only result on Task 4 specifically. Defensible synthesis: "Claude has the smallest cross-condition spread of any frontier model on this surface, refuses permissive sycophancy instructions far more than any peer, but is not uniformly more honest than the rest of the paper roster."

### 2.3 How prompt-invariant is Claude?

| Source | Verdict |
|---|---|
| `FINDINGS §13` village 2×2×2 | Claude is prompt-invariant: no factor moves >0.032 |
| `FINDINGS §11` bargaining wordings | Claude has spread 0.40 across five neutral wordings |
| `FINDINGS §18` village topology | Claude *does* shift with goal wording (+0.16 to +0.20) under paired/isolated topology |
| `FROM_FIRST_PRINCIPLES §3` | Claude shifts +0.276 from prohibitive → permissive (smallest of the 6 paper-roster models, but substantial) |

**Resolution.** §13 over-stated the claim. The accurate version: Claude has the **smallest** cross-frame and cross-wording spread of the frontier models on this surface, but is not invariant. Visibility restriction (paired/isolated) and explicit prohibitive-vs-permissive framing both produce real shifts. The §13 finding holds only under full visibility on village; it does not generalize.

### 2.4 The haiku 3.5 → 4.5 collapse — magnitude

| Source | Bargaining Δ |
|---|---|
| `csv/FINDINGS §8a` | **−0.796** (paired-bootstrap, scenario-controlled, 0.827 → 0.031) |
| `paper/capability_eval F3` | **−0.66** (per-cell mean delta, bootstrap CI [−0.74, −0.58]) |

**Resolution.** Different aggregation methods (scenario-controlled paired vs cell-mean delta) on overlapping but not identical cell sets. Both confirm the same direction. Cite the range "−0.66 to −0.80 depending on cell-control" for any external claim; pick one method for any in-paper figure. Both methods agree that this is the largest within-family training improvement in the corpus and that it concentrates at small sizes (sonnet 3.7 → 4.6 didn't budge; the haiku-to-haiku delta is unique).

The most striking secondary result, from `csv/FINDINGS §8a-bis`: the collapse is near-total in every frame except permissive. haiku45 sits at 0-2% manipulation under prohibitive/pro_social/minimal/selfish, but 12.8% under permissive. Whatever Anthropic shipped neutralized response to four of five frames; explicit permission still gets through.

### 2.5 Is debate's frame response "flat" or "strong"?

| Source | Verdict |
|---|---|
| `FROM_FIRST_PRINCIPLES §5` | pooled `manipulation_occurred` shifts only −0.04 to +0.08 across frames |
| `csv/FINDINGS §2` | debate frame spread is 0.02 — flat |
| `FINDINGS §15` | pooled `manipulation_detection` shifts +0.265 (0.250 → 0.515) — strong and monotone |

**Resolution.** Both numbers are correct; they measure different things.

- `manipulation_occurred` (the binary "did the manipulator try to manipulate") is flat under permissive — the manipulator was already trying.
- `manipulation_detection` (judge-LLM verdict) doubles — the manipulator's *visible behavior* changes.
- `argument_quality` slightly drops; juror `belief_shift` is unchanged.

**Synthesis** (`FROM_FIRST_PRINCIPLES §5` already nails this): under permissive framing models try harder and look more manipulative, argue worse, and net juror movement is unchanged. **Manipulation effort and manipulation success are decoupled in debate.** Cite `belief_shift` for outcome claims and `manipulation_detection` for behavior claims; do not cite `manipulation_occurred` for debate cross-model comparisons — `csv/FINDINGS §3` shows model η² is 0.014 on this metric, below the noise floor.

---

## 3. Capability is task-conditional, not monotonic

This is the strongest cross-document synthesis. Three independent analyses of the same corpus converge:

**`paper/capability_eval F1`** — per-task ELO regression with axis controls (n=29,352):

| Task | β per +100 ELO | Direction |
|---|---|---|
| village | −0.062 *** | capability helps a lot |
| sales | −0.020 *** | capability helps |
| debate | −0.008 ** | capability helps slightly |
| bargaining | −0.004 (n.s.) | flat |
| inbox | +0.029 * | capability hurts |
| committee | +1.55 *** | capability hurts (note: different scale) |

**`csv/FINDINGS §8c`** — coarse tier buckets (frontier > mid > small):

- Frontier > mid > small in committee, debate, village (capability hurts).
- Sales is essentially flat (slight inverse if anything).
- Bargaining is inverted-U with mid lowest (specific to the small-model sweep mix).

**`csv/FINDINGS §8a-b`** — within-family ladders:

- Anthropic haiku → sonnet → opus: bargaining slope **−0.17** per step (capability helps), committee **+0.12** (hurts).
- OpenAI gpt41: sales **−0.07**, committee **+0.10**, bargaining +0.03.
- Sonnet 3.7 → 4.6 across all 3 testable tasks: flat. Mid-tier was already at floor on bargaining; committee (71%) had headroom and didn't budge. **Within-family training improvements concentrate at smaller sizes.**

The clearest consistent pattern across all three views: **committee manipulation is capability-driven** (every signal points the same way — bigger and more capable models produce more structural rating bias). **Sales honesty is also capability-driven** (smaller models confabulate against ground truth more) — the inverse direction.

> Tension with the legacy werewolf result: `FINDINGS §4` reports Large+Large werewolf pairs win 67% vs Small+Small 54% — i.e., capability *helps deception* in werewolf. This isn't represented in the paper-roster analyses (werewolf isn't a paper task). Werewolf is structurally closer to committee (capability-driven manipulation success) than to village (cooperative defection), so the direction is consistent with the cross-document story; but n=24 per pair-type makes it a weaker source.

---

## 4. Per-task synthesis

### Bargaining (Task 1)

- **Polar:** prohibitive frame → 0% manipulation across every frontier model on the paper roster (`FROM_FIRST_PRINCIPLES §4`); even with E=0 audit penalty (`FINDINGS §16`).
- **Audit penalty is the steepest dose-response in the corpus.** ~15× collapse from E=0 → E=30, near-zero by E=80 (`FINDINGS §16`). Bargaining is the **only task where higher incentive reduces manipulation** (`csv/FINDINGS §2`).
- **Three curve shapes** on the legacy roster (`FINDINGS §9`): GPT-5 cliff, Claude two-step decay, Grok easily deterred. Plus three more on neutral-wording variants (`FINDINGS §11`): GPT-5 has the largest wording sensitivity (spread 0.75), Grok the smallest (0.25).
- **Bargaining is the cleanest task** for cross-model claims (`csv/FINDINGS §3`: model η² = 0.244, the highest in the corpus; no scenario column to confound).
- **Capability is approximately flat** within paper-roster tier buckets (β not significant), but **haiku 3.5 → 4.5 collapsed bargaining lying by ≈0.66-0.80** (Conflict 2.4) — most of "bargaining manipulation" in the corpus may be a pre-haiku45-era artifact.

### Debate (Task 2)

- **Frame is dominant on the behavior metric** (`FINDINGS §15`: prohibitive → permissive moves manipulation_detection by +0.265 pooled). On the binary outcome metric it's flat (Conflict 2.5).
- **Effort and success are decoupled.** Under permissive framing models try harder and look more manipulative, argue worse, and juror belief_shift is unchanged.
- **Persuasion mostly fails.** Aggregate belief_shift is −0.068 (jurors get *more* skeptical of the manipulator's position); persuasion_rate is 7%.
- **Per-claim variance dwarfs per-model variance.** One outlier claim drives ~half of all aggregate persuasion events; that headline reflects Gemini-Flash's prior, not persuasion (`FINDINGS §17`). Use `belief_shift`, not `persuasion_rate`, for cross-model claims.
- **GPT-5 is the stealthiest manipulator** (`FINDINGS §15`): lowest manipulation_detection, highest persuasion_rate, lowest truth-side detection — its default style does not trigger the detector even when arguing against the truth.
- **The binary `manipulation_occurred` outcome is uninformative for cross-model comparison** (`csv/FINDINGS §3`: model η² = 0.014). The signal lives in the per-scorer paired columns.

### Village Commons (Task 3)

- **Polar:** village-permissive → 100% manipulation across every frontier model (`FROM_FIRST_PRINCIPLES §4`).
- **Frame is the dominant axis** (`csv/FINDINGS §2`: spread 0.63, the largest of any task).
- **Implicit license has null effect** (`FINDINGS §13`: "you may use whatever strategies you find effective" moved no model >0.016 in the 2×2×2 factorial). Implicit permission is not sufficient without goal re-framing.
- **Topology amplifies the goal effect** (`FINDINGS §18`): paired and isolated channels produce the largest max−coop deltas. Under GPT-5/isolated/max, exploitation hits 0.887 — near-pure defection, with a +7.26-token promise gap (a third of the endowment broken every round).
- **Llama has a high prohibitive floor** (67% — `FROM_FIRST_PRINCIPLES §6`). Different alignment failure mode: "instruction-resistant in this env" rather than "instruction follower whose floor is the prohibition."
- **Claude's pro_social cue *beats* the prohibition** (`FROM_FIRST_PRINCIPLES §7`): village rate 0.056 under pro_social vs 0.278 under prohibitive — a 5× drop under positive framing. No other paper-roster model shows this dip. Worth checking whether it's a Claude-specific alignment fingerprint.
- **Capability strongly helps** (β = −0.062 per +100 ELO).

### Sales (Task 4)

- **Sycophancy is a frame effect, not a disposition** (`FINDINGS §14`): under prohibitive/goal_helpful/minimal/goal_satisfaction every paper-roster model accommodates 0/180. All ranking variation lives in the permissive column.
- **Opus is the only model that substantially refuses permissive-frame instructions** (1.3% accommodation vs 19% avg; next-closest DeepSeek 42%; Gemini/Grok/Llama all >94%).
- **Stated RLHF pressure has no detectable effect** in either the legacy single-turn run or the paper sales runs.
- **Capability helps sales honesty.** Smaller models confabulate more against ground truth.
- **`gpt41nano` is the cleanest small model on 4 of 5 tasks but flips to *most* manipulative in sales paired analysis** (+7 — `csv/FINDINGS §1`). Likely capability failure: confabulates against detailed product specs because it can't track them.
- **Sales and debate model rankings are anti-correlated** (Spearman −0.77 — see §1.3 above).

### Committee (Task 5)

- **Capability hurts.** Frontier 0.72, mid 0.57, small 0.42 in tier buckets; Anthropic family slope +0.12 per size step; OpenAI gpt41 slope +0.10; ELO regression β = +1.55 (different scale). Bigger models produce more structural rating bias.
- **Difficulty effect is large but partly confounded** (`csv/FINDINGS §2`): low-difficulty 0.96, high-difficulty 0.26, spread 0.70 — but `scenario_group` is 1:1 nested in `difficulty`, so within-cluster the effect is unidentifiable.
- **Sonnet on committee is unusually bad** (`FROM_FIRST_PRINCIPLES §10`): sonnet46/37 sit at 71%, comparable to Grok-4 and DeepSeek. Anthropic models are comparatively *worse* on committee than on bargaining — the opposite of the bargaining pattern.
- **Orthogonal scorers exist for an attempted-vs-successful split.** `decision_outcome__ground_truth_matched` and `post_discussion_rating_change__interested_delta_favored` are uncorrelated with `manipulation_occurred` (`csv/FINDINGS §5`). They capture **whether the manipulation succeeded**, not whether it was attempted. Committee is the cleanest task for this split.

### Inbox (paper Task 6, capability_eval only)

- **Capability hurts inbox** (`paper/capability_eval F1`: β = +0.029 per +100 ELO). Possibly because subtler suppression strategies require capability to execute.
- **Within-family generation upgrades systematically reduce inbox suppression in 4 of 5 pairs**, but the direction can flip in the smaller families (gpt41nano → gpt54nano *increases* suppression by +0.42).
- Not in the legacy `FINDINGS.md` or `FROM_FIRST_PRINCIPLES.md` — capability_eval is the only document covering Task 6.

---

## 5. Methodological corrections that affect interpretation

These come from `csv/FINDINGS` and the legacy `FINDINGS` measurement caveats. Carrying them forward:

### 5.1 Scenario clustering inflates apparent precision

ICC across `scenario_group` is 0.36-0.42 in committee/debate/sales. Row-bootstrap CIs are 2.5-4× too narrow there. Always use `02_model_task_rate_with_ci.csv`'s `ci_method` column to check which CIs are cluster-corrected.

### 5.2 The `FINDINGS §10` "default neutral" numbers were a single-wording artifact

`FINDINGS §11` reran the same condition across 5 neutral wordings:

| Model | Section 10 (`original` only) | Pooled across 5 variants |
|---|---|---|
| Claude | 0.600 | 0.315 |
| GPT-5 | 0.900 | 0.632 |
| Grok | 0.075 | 0.110 |

§9-§10's "default" wording reads in practice closer to `goal_payoff` than to a minimal neutral framing. Read those sections as "manipulation under a payoff-maximization framing," not neutral.

### 5.3 Village `promise_gap` pre-tool-instrumentation was undercounted

`FINDINGS §12` measurement caveat: the regex-era pledge detector under-captured by ~6×. §12-§13 promise_gap numbers are regex-era estimates; §18 numbers (post-`pledge_contribution` tool refactor) are the trustworthy version. Re-run §12-§13 on the tool pipeline before citing per-model promise-gap rankings.

### 5.4 Combined eval logs preserve old model labels after model swaps

When a paper amendment swaps a model (e.g., GPT-5 → GPT-5.5 via `--model-role`), the new run's scenario metadata still carries the original label. Within-task pre/post comparisons must filter by the OLD label in BOTH halves — only the runtime model binding changed.

### 5.5 `manipulation_metric` is not pooled across tasks

`csv/FINDINGS` methodology preamble: scales differ wildly (bargaining/sales/village 0-1, debate −0.66 to +0.43, committee −14 to +20). Pool `manipulation_occurred` across tasks; report `manipulation_metric` task-by-task only.

---

## 6. The shape of "what we don't yet know"

Sorted by what would most change conclusions in the corpus:

1. **Attempted vs successful manipulation split.** Committee already has orthogonal scorers (§4 Committee). Other tasks may too — needs a systematic check. The strongest candidates are debate (paired manipulator-vs-truthful columns) and sales (per-question accuracy columns).
2. **Why does `gpt41nano` flip in sales?** Cleanest small model on 4 of 5 tasks, *most* manipulative in sales paired analysis. Capability failure or something else?
3. **Cross-task verification of the Claude pro_social → low-village-manipulation dip** (`FROM_FIRST_PRINCIPLES §7`). Does it happen elsewhere? Is it a Claude-specific alignment fingerprint?
4. **Mixed-effects regression** with `(1|scenario_group)` random intercept absorbs the scenario confound and gives "controlling for everything, model X has Z log-odds" statements directly — currently the cleanest cross-model signal goes through scenario-paired analysis, which is conservative.
5. **Bargaining full-roster run.** `FINDINGS §16` halted at 1,499/7,200 samples on weekly OpenRouter quota. The "audit penalty crushes lying" story is Opus-within only until the other 5 paper-roster models complete.
6. **Composite capability proxy** beyond LMArena ELO. `paper/capability_eval` used a single noisy proxy; LMArena + GPQA + SWE-bench would be stronger.
7. **Multi-turn susceptibility.** `FINDINGS §8` tested only single-turn; whether jurors concede after the manipulator pushes back is untested across the corpus.
