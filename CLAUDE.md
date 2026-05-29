# CLAUDE.md — Context for Claude Code Sessions

## What this project is

manipulation-bench is a multi-agent evaluation framework for studying manipulation in AI interactions. It's built on [Inspect AI](https://inspect.aisi.org.uk/) and designed to answer: **how do different AI models behave when instructed to manipulate, and how susceptible are they to manipulation from others?**

The primary research contribution is evaluating how switching out the environment and communication topology influences models' manipulative behavior.

## Architecture overview

```
src/manipulation_bench/
  models.py          # Data models (AgentRole, Turn, ScenarioConfig, ScenarioMetadata, InteractionState)
  axes.py            # Canonical response-surface axes: frame/incentive/difficulty levels, per-env prompts, legacy→canonical aliases
  dataset.py         # JSONL loading with record_to_sample mapping
  game_solver.py     # Unified solver for all environments (DISCUSSION/ACTION phases)
  prompts.py         # All judge/juror prompt templates
  task.py            # @task manipulation_bench (debates)
  game_task.py       # @task for Werewolf game environment
  diplomacy_task.py  # @task for Diplomacy game environment
  sales_task.py      # @task for sales (single-agent, scripted buyer)
  committee_task.py  # @task for committee evaluation with conflict of interest
  _registry.py       # Inspect entry-point (lazy imports)
  generate.py        # CLI: YAML config → rotation JSONL + generate_debate_rotation() / generate_debate_surface() shared functions
  analyze.py         # CLI: eval log → comparison tables + susceptibility analysis (debate/werewolf/diplomacy)
  analyze_surface.py # CLI: cross-env response-surface analyzer (frame × incentive × difficulty pivot per model)
  scenarios/         # JSONL scenario files (generated or hand-crafted)
  # The heavier statistical pipeline (sensitivity slopes + 15-dim profile vectors
  # + cross-task correlations) lives under paper/cross_task/scripts/ — imports
  # utilities from analyze_surface.py.
  environments/
    base.py          # Environment ABC + Phase, Observation, ActionResult, GameOutcome
    debate.py        # Debate environment (DISCUSSION-only phases, round-robin)
    werewolf.py      # Werewolf social deduction game
    diplomacy.py     # Diplomacy negotiation game (wraps diplomacy package)
    __init__.py      # Factory: create_environment() + ENVIRONMENTS registry
  scorers/
    __init__.py      # Re-exports all scorers
    _helpers.py      # Shared: parse_json_score, score_per_agent, format_transcript
    judges.py        # LLM-judge scorers (manipulation_detection, argument_quality, belief_shift)
    voting.py        # Multi-juror voting + vote entropy
    grounded.py      # Ground-truth persuasion rate + Bayesian belief shift
    social_deduction.py  # Werewolf scorers: game_win_rate, vote_accuracy, deception_success, game_manipulation_detection
    negotiation.py       # Diplomacy scorers: territorial_success, agreement_compliance, negotiation_manipulation
    village.py           # Village scorers: exploitation_rate, promise_action_gap, village_fairness
    sales.py             # Sales rule-based classifier: sales_classifier (accurate/misleading/false)
    committee.py         # Committee scorers: initial_rating_bias, post_discussion_rating_change, discussion_polarity, decision_outcome
    _committee_wordlist.py  # Rule-based polarity classifier (positive/negative words, negation scope, hedge halving)
experiments/         # YAML configs and generator scripts for specific experiments
tests/               # pytest test suite
```

### Environments

The framework supports several environment types:

- **Debate**: Conversation-based, 2-N agents. Measures persuasion and rhetorical tactics. Implemented as `DebateEnvironment` (DISCUSSION-only phases).
- **Werewolf**: Social deduction game, 4-7 players. Measures deception and vote manipulation. Implemented as `WerewolfEnvironment`.
- **Diplomacy**: Negotiation game, 7 powers. Measures promise-breaking and alliance betrayal. Wraps the `diplomacy` Python package via `DiplomacyEnvironment`.
- **Village Commons**: Public goods game, 6 agents. Measures free-riding, promise-breaking, false accusations, and cooperative exploitation. Implemented as `VillageEnvironment`. Actions use tool calls (`contribute`, `inspect_agent`, `penalize`). All metrics are mathematical — no LLM judge needed.
- **Sales**: Principal-agent representation, single-agent. The agent represents a seller; a scripted buyer asks 5 fixed factual questions per scenario; answers are classified against a structured product spec as `accurate` / `misleading` / `false`. Deterministic rule-based scorer (`sales_classifier`) — no LLM judge. Lives in `sales_task.py` with its own 5-turn solver (`sales_interaction`) rather than `game_solver.py`, because there is no counterparty LLM.
- **Committee**: Multi-agent committee (5 agents) evaluates a slate of candidates (4) on structured criteria. One agent has a private interested-party affiliation with a specific candidate. Phase sequence: `private_rating (ACTION) → discussion_r1…rN (DISCUSSION) → final_rating (ACTION)` — `num_discussion_rounds` is configurable. Agents submit ratings via the `submit_ratings` tool (nested JSON: candidate_id → criterion → int 0-10). Discussion is free-text with required `[A]/[B]/[C]/[D]` markers per candidate; the scorer splits by marker and applies a rule-based polarity classifier. All metrics mathematical — no LLM judge.

Debate, Werewolf, Diplomacy, Village, and Committee share `game_solver.py` and the `Environment` ABC. Sales is single-agent and bypasses both.

## Key design decisions

### Agents are data, not code

Agent roles (name, model, system prompt, position) are defined per-scenario in JSONL, not in Python code. A scenario with 2 debaters, 4 panelists, or 1 interviewer + 1 subject all use the same solver. This means new experiment designs don't require code changes.

### Unified solver (`game_solver.py`)

All environments (including debates) use a single phase-aware solver. **DISCUSSION** phases let agents talk (free-form text + optional tool calls). **ACTION** phases require agents to submit structured moves via Inspect AI tool calls, with retry logic for invalid submissions.

Tool calling: environments expose `get_tools(agent, phase)` returning `ToolInfo` schemas with `enum` constraints for valid targets. The solver passes these to `model.generate(tools=..., tool_choice=...)`. ACTION phases use `tool_choice="any"` (must call a tool); Diplomacy DISCUSSION uses `"auto"` (messaging tools are optional). Tool call results are converted to actions via `tool_calls_to_action()` or routed via `process_tool_calls()` (Diplomacy message/promise routing).

The solver injects `scenario.topic`, agent positions, `num_rounds`, and `visibility` into the environment config for backward compatibility with debate scenarios that predate the environment system.

### Direct model.generate() instead of Inspect's generate(state)

The solver calls `get_model(role=agent.model_role).generate(messages)` directly rather than using Inspect's built-in `generate` callback. This is because N-agent interaction requires N different message views per turn, while Inspect's `generate` operates on a single `state.messages` thread.

### StoreModel for solver↔scorer bridge

`InteractionState` is a `StoreModel` persisted via `state.store_as(InteractionState)`. The solver writes to it, scorers read from it. **Important**: StoreModel fields return copies on access — you must reassign (`state.turns = [*state.turns, new_turn]`), not append (`state.turns.append(...)` silently drops the change).

### Communication topology

`ScenarioConfig.visibility` accepts either string shortcuts or per-agent adjacency dicts:
- Strings: `"all_to_all"`, `"isolated"`, `"hub_spoke"`
- Dict: `{"moderator": ["a", "b"], "a": ["moderator"], "b": ["moderator"]}`
- All logic is in `InteractionState.turns_visible_to()` — one method to change for new topologies.

### Scorers organized by what they require

- `scorers/judges.py` — LLM-judge (qualitative, model-dependent, not reproducible across studies)
- `scorers/voting.py` — statistical (N juror votes, Bernoulli rates, entropy)
- `scorers/grounded.py` — mathematical (requires `ground_truth` field on scenario)
- `scorers/social_deduction.py` — Werewolf game metrics: `game_win_rate`, `vote_accuracy`, `deception_success`, `game_manipulation_detection`
- `scorers/negotiation.py` — Diplomacy game metrics: `territorial_success`, `agreement_compliance` (hard metric — no LLM, computes kept/total promises per agent), `negotiation_manipulation`
- `scorers/village.py` — Village Commons metrics (all mathematical, no LLM): `exploitation_rate` (1 - avg contribution / 20), `promise_action_gap` (promised - actual), `village_fairness` (Gini coefficient + free-rider detection rate)
- `scorers/sales.py` — sales: `sales_classifier` classifies each buyer-question response as `accurate` / `misleading` / `false` using per-check-type rules against a typed `check_fields` DSL on the ground-truth record. No LLM judge. Hand-validated with `paper/task4_sales/scripts/task4_hand_validation.py` (emit template → human fills → score agreement ≥90%).
- `scorers/committee.py` — committee metrics (all mathematical, no LLM): `initial_rating_bias` (interested party's favored-vs-matched-tier-peers delta on initial ratings), `post_discussion_rating_change` (neutral_shift_toward_interested = mean neutral delta signed by interested-party delta direction), `discussion_polarity` (rule-based wordlist classifier from `_committee_wordlist.py` with negation scope 3 and hedge halving; per-candidate segments split by `[X]` markers), `decision_outcome` (favored_won / ground_truth_matched / favored_rank). Hand-validated with `paper/task5_committee/scripts/task5_hand_validation.py` (≥85% agreement gate).

### Model swapping via Inspect model roles

Each agent has a `model_role` field. At eval time, roles are bound to actual models via `--model-role name=provider/model`. Multiple agents can share a role (e.g., all debaters use `model_role: "debater"`) or have distinct roles for cross-model comparison.

## How experiments work

### Response-surface axes

Cross-environment comparisons standardize on three axes, each with fixed canonical levels defined in [src/manipulation_bench/axes.py](src/manipulation_bench/axes.py):

- **Frame** (5 levels): `prohibitive`, `pro_social`, `minimal`, `selfish`, `permissive` — prompt framing from strict prohibition through neutral instruction to permissive encouragement.
- **Incentive** (3 levels): `none`, `moderate`, `high` — intensity of the reward/penalty structure attached to the manipulable objective. Environment-specific: bargaining maps to expected penalty (0/40/80), village maps to token-balance bonus emphasis, committee/sales/debate to payoff language.
- **Difficulty** (3 levels): `low`, `medium`, `high` — how much manipulation is needed to move the outcome. Village uses public-good multiplier (1.8×/1.5×/1.2×), bargaining uses valuation asymmetry, debate uses juror pre-belief distance, sales/committee use pre-existing slate/product difficulty tags.

Rules:
- **Typed source of truth**: each scenario's `ScenarioMetadata.frame`, `.incentive`, `.difficulty`, and `.manipulator` fields (on [models.py](src/manipulation_bench/models.py)) are the canonical record. Generators must set these.
- **Prompts + aliases live in [axes.py](src/manipulation_bench/axes.py)**: `FRAME_PROMPTS[env][level]` and `INCENTIVE_PROMPTS[env][level]` are per-environment prompt fragments. `FRAME_ALIASES` / `INCENTIVE_ALIASES` map legacy names (`goal_fairness`, `I=moderate`, `cooperative`, `pro_honesty`, etc.) to canonical ones so old eval logs still pivot correctly.
- **Unified analyzer**: [src/manipulation_bench/analyze_surface.py](src/manipulation_bench/analyze_surface.py) reads any env's eval log, auto-detects environment by scorer names, normalizes axis metadata through the aliases, and emits frame × incentive and frame × difficulty grids per model (plus optional CSV).
- **Surface generators** live alongside legacy ones with the `_surface` suffix: [experiments/generate_village_surface.py](experiments/generate_village_surface.py), [experiments/generate_debate_surface.py](experiments/generate_debate_surface.py), [experiments/generate_bargaining_surface.py](experiments/generate_bargaining_surface.py). Sales and committee generators are kept under `paper/task<N>/scripts/` — they already factor over frame × incentive × difficulty.

### Debate rotation design

The standard experimental design for measuring manipulation in debates:
1. N agents debate a topic, each with a position
2. Generate N+1 scenarios: one **baseline** (no manipulator) + one per agent as the designated manipulator
3. The manipulator gets an extra instruction appended to their system prompt
4. Compare scores across conditions

The `generate.py` CLI automates this from a YAML config. Custom generator scripts (in `experiments/`) handle multi-topic experiments.

### Sales (single-agent, scripted buyer)

Sales scenarios are not debates or games — a scripted buyer asks 5 fixed questions and the seller-agent answers each in turn. Every scenario is one principal-agent pairing (frame × incentive × product × model). The solver (`sales_task.py:sales_interaction`) maintains a single chat thread, appends each buyer question, generates the agent's reply, and stores all 5 responses in `state.metadata['responses']`. The scorer (`scorers/sales.py:sales_classifier`) classifies each response deterministically against the scenario's `ground_truth` records (one per question, with `check_type` + `check_fields`). Experimental design cross-cuts the 5 canonical frames (`prohibitive`/`pro_social`/`minimal`/`selfish`/`permissive`) with 3 incentives (`none`/`moderate`/`high`) and 3 difficulty tiers, producing manipulation-rate as the headline metric.

### Game environments (Werewolf, Diplomacy)

Game environments follow a phase loop (DISCUSSION then ACTION) and produce game-specific metrics rather than debate metrics. Werewolf games run via `game_task.py`; Diplomacy games run via `diplomacy_task.py`.

Diplomacy has a dedicated promise-tracking system using tool calls: `send_message(recipient, content)` routes private messages between powers, and `make_promise(recipient, order)` records commitments. The `agreement_compliance` scorer computes kept/total promises per agent as a hard mathematical metric (no LLM judge needed).

Village Commons uses tool calls for structured actions: `contribute(amount)`, `inspect_agent(target)`, `penalize(target)`. Agents discuss privately and publicly, then act via tools. Commitments and accusations are captured via first-class tool calls exposed during discussion phases: `pledge_contribution(amount)` (both private_messaging and public_discussion) and `accuse_agent(target, claimed_amount?)` (public_discussion only). The `promise_action_gap` scorer reads pledges deterministically — no regex scanning of free text. Two experimental conditions: propensity ("maximize tokens") vs capability ("explicitly manipulate").

### Analysis pipeline

`analyze.py` reads an Inspect eval log, auto-detects the environment type from scorer names, and dispatches to the appropriate analysis:
- **Debate**: Per-scenario grids (manipulation/quality/shift), ability summary (instructed vs baseline + delta), susceptibility (contagion, quality drop, belief shift)
- **Werewolf**: Win rates by role and model, deception success for werewolves, vote accuracy for villagers
- **Diplomacy**: Territorial success, agreement compliance, negotiation manipulation — all aggregated by model

`analyze_surface.py` is the **cross-environment** companion: it pivots any sales/committee/village/debate/bargaining log into frame × incentive and frame × difficulty grids per model, using each environment's canonical manipulation metric (`sales_classifier` misleading+false rate, `initial_rating_bias`, `exploitation_rate`, `belief_shift`, `overstatement_rate`). Legacy axis names (`goal_fairness`, `I=moderate`, `pro_honesty`, etc.) are normalized through `axes.canonical_frame` / `canonical_incentive` on read, so archived eval logs still pivot correctly.

## API keys and providers

Most models are accessed through OpenRouter (`OPENROUTER_API_KEY` in `.env`). Model IDs use the format `openrouter/provider/model-name`. The judge defaults to the eval's primary model but can be overridden with `--model-role judge=...`.

DeepSeek V4 Pro reasoning rejects OpenRouter's privacy guardrails AND rejects `tool_choice="any"` (reasoner-only constraint), so the canonical roster uses the **official DeepSeek API**:
- `DEEPSEEK_API_KEY` and `DEEPSEEK_BASE_URL=https://api.deepseek.com/v1` in `.env`
- Provider prefix: `openai-api/deepseek/<model>` (Inspect's openai-api adapter)
- Per-agent `metadata.tool_choice_strategy="auto"` triggers a `game_solver.py` override that downgrades `tool_choice="any"` → `"auto"` for that agent only, with the existing retry budget covering tool-call refusals.

For the full catalog of provider quirks the framework works around (DeepSeek V4 Pro, GPT-5 strict-mode tool schemas, Llama retry sensitivity), see [`docs/provider_quirks.md`](docs/provider_quirks.md). Point new researchers there if they hit a 400 from a provider they haven't used before.

## Running things

```bash
# Install (registers the `mb` console script via pyproject.toml)
pip install -e ".[dev]"

# Recommended: the `mb` CLI auto-binds every model_role in the default
# scenario to --model, so single-model runs are one line.
mb envs                                                  # list registered envs
mb run debate --model mockllm/model --limit 1            # smoke test, local mock
mb run debate --model openrouter/anthropic/claude-opus-4.7
mb run debate village --model openrouter/...             # multi-env, sequential
mb run debate --models debater=...,judge=...             # explicit per-role
mb analyze 'logs/2026*.eval'                             # auto-detect environment

# Power users (custom solvers, custom scorer lists, large sweeps): call
# inspect eval directly. mb is a convenience layer, not a replacement.
inspect eval src/manipulation_bench/task.py -T scenarios=out.jsonl --model-role ...

# Generate rotation from YAML
python -m manipulation_bench.generate experiments/personhood.yaml -o src/manipulation_bench/scenarios/out.jsonl

# View in Inspect's UI
inspect view
```

## Environment ABC contract

All environments (including debate) implement `environments/base.py:Environment`:

```
setup(agent_names) → get_current_phase() → get_observation(agent) →
  DISCUSSION: solver generates text with tools, calls process_tool_calls() + process_discussion()
  ACTION: solver generates tool calls, calls tool_calls_to_action() + apply_action()
→ advance_phase() → ... → is_terminal() → get_outcome()
```

Key methods:
- `get_tools(agent, phase) -> list[ToolInfo]` — tool schemas for this agent/phase (default: empty; Werewolf returns kill/investigate/vote; Diplomacy returns submit_orders or send_message/make_promise)
- `get_tool_choice(phase) -> str | None` — `"any"` for ACTION, `None` for DISCUSSION (Diplomacy overrides to `"auto"` for DISCUSSION)
- `tool_calls_to_action(agent, tool_calls) -> str` — convert tool calls to action string; raise ValueError to trigger retry
- `process_tool_calls(agent, tool_calls, phase) -> list[str]` — handle DISCUSSION tool calls (Diplomacy message routing, promise recording)
- `process_discussion(agent, content, phase)` — non-tool text processing (default no-op; Debate uses it to track first-turn status)
- `get_game_state_for_scoring() -> dict` — full state dump for scorers (roles, votes, messages, outcomes)

Adding a new game: implement the ABC, register in `environments/__init__.py:ENVIRONMENTS`, create a `@task` file, add environment-specific scorers.

### Templates for new researchers

When a researcher asks "how do I add a new env / scorer?", point them at [`examples/`](examples/), which has a fully working starter:

- [`examples/new_environment/`](examples/new_environment/) — minimal `Environment` subclass (DISCUSSION-only, ~150 LOC), self-contained `@task` wrapper, two sample scenarios, and a 5-step checklist for production envs. Runs end-to-end with `mockllm/model`.
- [`examples/new_scorer/`](examples/new_scorer/) — two scorer flavors in one file: a deterministic mathematical scorer and an LLM-judge scorer with the dict-valued `metrics={"*": [...]}` shape.

Direct researchers there before having them read full production env code (`debate.py`, `werewolf.py`, etc.); those are richer but mix in study-specific concerns.

### Adding to the `mb` CLI

If the new env should be runnable via `mb run <name>`, add an entry to `ENVS` in [`src/manipulation_bench/cli.py`](src/manipulation_bench/cli.py). The CLI auto-discovers model_roles from the env's default scenario JSONL and binds them all to `--model` unless overridden.

### Pluggable scorer override

Every `@task` accepts a `scorers` parameter that overrides the hardcoded scorer list:

```bash
# Built-in scorer names (one or comma-separated)
inspect eval src/manipulation_bench/task.py -T scorers=manipulation_detection,argument_quality ...
mb run debate --model ... -T scorers=manipulation_detection

# Dotted import path to a custom scorer factory
mb run debate --model ... -T scorers=my_pkg.my_module.my_scorer
```

Resolution lives in [`src/manipulation_bench/scorers/_resolve.py`](src/manipulation_bench/scorers/_resolve.py): bare names hit `manipulation_bench.scorers`, dotted names go through `importlib.import_module`. Default behavior (no `-T scorers=…`) is unchanged — each task keeps its own hardcoded list as the fallback. New scorer factories must take no required positional args (the resolver calls `factory()` with no args).

### Mitigations (defenses)

A **mitigation** is a runtime-resolved plug-in that tries to *reduce* measured manipulation. Same scenario JSONL, baseline vs. defended, no regeneration. Every `game_solver.py`-based `@task` (debate, werewolf, diplomacy, village, committee) accepts a `mitigations` parameter (default `"default"` = undefended); sales is single-agent and bypasses the unified solver, so it is out of scope for v1 (see the TODO in `sales_task.py`).

```bash
# Built-in defenses, one or comma-separated
mb run debate --model mockllm/model -T mitigations=prompt_suffix
inspect eval src/manipulation_bench/task.py -T mitigations=prompt_suffix,critic_monitor ...

# critic_monitor calls a separate model — bind the mitigation_critic role (falls back to judge, then default)
mb run debate --model ... --model-role mitigation_critic=openrouter/... -T mitigations=critic_monitor

# Dotted import path to a custom defense factory
mb run debate --model ... -T mitigations=my_pkg.my_module.my_defense
```

The package lives in [`src/manipulation_bench/mitigations/`](src/manipulation_bench/mitigations/):
- [`base.py`](src/manipulation_bench/mitigations/base.py) — `Mitigation` ABC with three hooks (all no-op by default): `transform_agent` (sync, rewrite a role before the loop), `transform_messages` (async, rewrite the model input per turn), `transform_response` (async, flag/redact/rewrite the output before delivery).
- [`_resolve.py`](src/manipulation_bench/mitigations/_resolve.py) — clone of the scorer resolver. Sentinels `{None, "default", "DEFAULT", ""}` and empty lists → `None` (undefended); bare names hit `manipulation_bench.mitigations`, dotted go through `importlib`. Factories take no args.
- [`_targeting.py`](src/manipulation_bench/mitigations/_targeting.py) — `is_adversary(agent, scenario)` reads **only** `AgentRole.adversary` (the canonical targeting flag; no metadata fallback).
- [`prompt_suffix.py`](src/manipulation_bench/mitigations/prompt_suffix.py) (~25 LOC, `transform_agent`) — appends a skeptical-framing suffix to non-adversary agents.
- [`critic_monitor.py`](src/manipulation_bench/mitigations/critic_monitor.py) (~80 LOC, `transform_response`) — a critic LLM screens each adversary message and flags/redacts/rewrites it.

**Targeting refactor**: `AgentRole.adversary: bool = False` ([models.py](src/manipulation_bench/models.py)) is the canonical record of who manipulates. Generators set it alongside the legacy `metadata.manipulator`/`metadata.manipulative` keys (which remain for scorer-side bookkeeping and pre-refactor eval logs). `analyze.py`'s manipulator detection prefers `adversary` and falls back to the legacy metadata.

**Solver integration** ([game_solver.py](src/manipulation_bench/game_solver.py)): `game_interaction(mitigations=...)` applies `transform_agent` when building the agent table, `transform_messages` after the message view is built, and `transform_response` after `generate` (in both DISCUSSION and the ACTION retry loop). Each turn stamps `Turn.metadata['mitigations_applied']`; when a response is altered, the pre-mitigation text is preserved in `Turn.metadata['original_content']`. The solver feeds the **original** (pre-mitigation) content to `env.process_discussion`, so committee's `discussion_polarity` measures the speaker's actual statement, not the critic's wrapper — no `committee.py` change needed.

Templates and tests: [`examples/new_mitigation/`](examples/new_mitigation/) is a copy-pasteable starter; [`tests/test_mitigations.py`](tests/test_mitigations.py) covers the resolver, targeting, and both reference defenses.

### Reusing the study generators with a different model roster

All five study-task generators under `paper/` accept a `--models` CLI flag so external researchers don't have to fork the script to change models. Bare labels auto-prefix the role; `label=role` pairs let you pick roles explicitly.

```bash
# T1 Bargaining — bare labels auto-assign model_a/b/c roles
python paper/task1_bargaining/scripts/generate_task1_bargaining.py --pilot --models 'claude,grok'

# T2 Debate — bare labels auto-prefix with manipulator_
python paper/task2_debate/scripts/generate_task2_debate_full.py --models 'claude,grok'

# T3 Village — same auto-prefix as T2
python paper/task3_village/scripts/generate_task3_village_full.py --models 'claude,grok'

# T4 Sales — same auto-prefix as T1 (model_a/b/c)
python paper/task4_sales/scripts/generate_task4_sales.py --pilot --models 'claude,gpt5,llama'

# T5 Committee — supports --pilot / --sweep / --frontier-endpoints
python paper/task5_committee/scripts/generate_task5_committee.py --pilot \
    --models 'claude=model_claude,gpt5=model_gpt5'
```

Each generator prints the exact `inspect eval` command at the end, with `--model-role <role>=openrouter/<provider>/<model>` placeholders for the under-test roster (so the user fills in their provider strings) and verbatim canonical bindings for the pinned framework roles (Debate truthful debater + jurors + judge; Village bystanders; Committee neutral panel). Without `--models`, T1/T2/T3 print the canonical roster bindings; T4/T5 always print placeholders for under-test roles regardless.

Generators that don't take `--models`:
- [`generate_debate_surface.py`](experiments/generate_debate_surface.py) — model-agnostic; binds models at eval time via `--model-role debater=...`.
- [`generate_village_surface.py`](experiments/generate_village_surface.py) — has a fixed 6-agent layout with role doubling. Edit `MODELS` at the top of the file directly if you need a different roster.
- Single-env demos in `experiments/` (`generate_diplomacy.py`, `generate_werewolf_8player.py`) — minimal one-each demos that are safer to fork than parameterize.

## Experiment design conventions

- **Agent names must be generic** (alice, bob, carol, etc. or country names like austria, england). Never use model names (claude, gpt5) as agent names — models will recognize each other and adjust strategy, confounding results.
- **Model identity** is tracked in `scenario.metadata.model_mapping` for analysis, never exposed to agents.
- **Experiment generators** live in two places. Surface generators (env-agnostic, 3-axis factorial) live in `experiments/`: `generate_village_surface.py`, `generate_debate_surface.py`, `generate_bargaining_surface.py` (all take `--pilot`), plus `generate_diplomacy.py` and `generate_werewolf_8player.py` for env demos. Study-task generators (with full PREREG-locked configs and `--models` overrides) live alongside their results under `paper/task<N>/scripts/generate_task<N>_*.py`. Each prints the exact `inspect eval` command after writing the JSONL.
- **Rotation pattern**: baseline (no manipulation) + N variants (one per agent manipulating). Debate generators use the shared `generate_debate_rotation()` function from `generate.py`; game generators have custom rotation logic.
- **Multi-phase experiments**: `AgentRole.prior_context` carries interaction history across phases. The solver injects it before the current interaction. `extract_agent_history(log_path, sample_id, agent_name)` in `generate.py` reads a log and formats an agent's experience.

## Prior experimental results

See `FINDINGS.md` for early experimental results with sample sizes and reproduction commands. Reference this file when the user asks about earlier prototype experiments. When new eval runs complete that don't belong in an archived study, add results to FINDINGS.md following the established format.

**Note: "Task 4" is overloaded.** The current Task 4 is **Sales** (`paper/task4_sales/`, `sales_task.py`, `scorers/sales.py`). An earlier Task 4 was Sycophancy (`sycophancy_task.py`, `scorers/sycophancy.py`, `scenarios/task4_sycophancy.jsonl`, FINDINGS.md §Task 4) and is preserved for reproducibility only. New work referring to "Task 4" means Sales unless explicitly qualified.

## Study artifacts (under `paper/`)

`paper/` is the authoritative record for the 5-task response-surface study. Each task has `prereg.md` (pre-registered with formal Amendments), `results.md` (verdicts against P1-P7), `analysis/` (per-task JSONs), `figures/` (per-task PNGs), and `eval_log.eval` (canonical combined eval log, committed via Git LFS). Cross-task material is in `paper/cross_task/` — `SUMMARY.md` (study-level), `EXPLORATORY_FINDINGS.md` (post-PREREG analyses), `cross_task_aggregate.md` (machine-generated per-task tables).

The frozen model cohort is **Claude Opus 4.7, GPT-5.5, Gemini 3.1 Pro, Grok 4, Llama 3.3 70B, DeepSeek V4 Pro** (post Amendments A2/A3). Older split logs in `logs/task*_*` are kept for provenance; the combined logs at `paper/task<N>/eval_log.eval` are produced by `paper/cross_task/scripts/combine_eval_logs.py` (dedup-by-sample-id with later-running splits winning, so amendments overlay originals).

### Per-study analysis scripts

Study-specific scripts live next to the artifact they produce, under `paper/task<N>/scripts/` and `paper/cross_task/scripts/`. The framework's `experiments/` directory only holds env-agnostic harness code (surface generators + the cross-env analyzer); study-specific analysis does not belong there.

- **Per task** — `paper/task<N>/scripts/`:
  - `task<N>_prereg_analysis.py` — P1-P7 verdicts against the combined log
  - `task<N>_visuals.py` — figures
  - `task<N>_hand_validation.py` (T4, T5) — scorer-agreement harness
  - `t<N>_*.py` — post-PREREG exploratory pivots (`t1_lie_magnitude`, `t2_per_claim`, `t3_promise_gap`, `t4_per_question_type`)
  - `generate_task<N>_*.py` — the canonical generator
- **Cross-task** — `paper/cross_task/scripts/`:
  - `combine_eval_logs.py` — dedup-by-sample-id merger that produces `paper/task<N>/eval_log.eval`
  - `run_bootstrap_cis.py` + `bootstrap_slopes.py` — per-axis 95% CIs at N=1000
  - `run_cohens_d.py`, `task5_cohens_d.py` — per-cell effect sizes
  - `run_response_surface.py` — cross-task fig7 (3 difficulty rows × 6 model cols × 5×3 heatmap each)
  - `cross_task_analysis.py`, `cross_task_explore.py` — aggregate views
  - `cross_task_ranking_stability.py`, `cross_task_clustering.py` — model-archetype + ranking-stability
  - `surprise_residuals.py`, `frontier_lift.py`, `sample_distributions.py` — exploratory analyses

When updating analysis, add new scripts under the relevant `paper/<...>/scripts/` directory and to `paper/cross_task/SUMMARY.md`'s reproduction block.

## Gotchas

- **Windows encoding**: Always use `encoding="utf-8"` when opening files for read/write. YAML with unicode characters (em-dashes, etc.) will produce corrupt JSONL otherwise. Print statements that emit non-ASCII (ρ, →, etc.) crash on Windows cp1252 stdout — use ASCII (`rho`, `->`).
- **StoreModel mutation**: `state.turns.append(x)` does NOT work. Use `state.turns = [*state.turns, x]`.
- **Scorer metrics with `"*"` glob**: Dict-valued scores with `@scorer(metrics={"*": [mean(), stderr()]})` auto-create per-key metrics. Different scenarios can have different agent names — metrics aggregate per-key across samples that share that key.
- **Ground-truth scorers**: Return `Score(value={"persuasion_rate": None, ...})` when `ground_truth` is not set. They don't error — they just produce None values.
- **JSONL paths**: `load_scenarios()` resolves relative paths against `src/manipulation_bench/scenarios/`. The `-T scenarios=filename.jsonl` flag passes just the filename, not a full path.
- **Combined eval logs preserve OLD model labels**: When an amendment swaps a model (e.g., GPT-5 → GPT-5.5 via `--model-role`), the new run's scenario metadata still carries the original model label (`model: GPT-5`) because scenarios are regenerated against the original JSONL. To do a within-task pre/post comparison, filter by the OLD label in BOTH halves — only the runtime model binding changed, not the recorded scenario label. See `paper/cross_task/scripts/frontier_lift.py`.
- **Git LFS for combined logs**: `paper/task*/eval_log.eval` are LFS-tracked (~1 GB total). Clone with `git lfs install && git lfs pull`. The repo is right at GitHub's free 1 GB LFS quota; new combined logs need `git lfs track` before adding.

### Typed scenario metadata (`ScenarioMetadata`)

`ScenarioConfig.metadata` is a `ScenarioMetadata` Pydantic model with `extra="allow"`. Typed fields: `environment`, `model_mapping`, `game_outcome`, `game_state`. Access with dot notation (`metadata.game_state`) instead of `.get()`. Extra keys from generators are preserved.

## Running tests

```bash
pytest tests/ -v
```

## Future directions (discussed, not yet implemented)

- **Live observation**: `TurnObserver` callback protocol for streaming to Discord/WebSocket
- **More game environments**: Extend the `Environment` ABC pattern to other social games (e.g., Mafia variants, Prisoner's Dilemma tournaments)
