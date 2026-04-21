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
  sales_task.py      # @task for Task 4 sales (single-agent, scripted buyer)
  committee_task.py  # @task for Task 5 committee evaluation with conflict of interest
  _registry.py       # Inspect entry-point (lazy imports)
  generate.py        # CLI: YAML config → rotation JSONL + generate_debate_rotation() / generate_debate_surface() shared functions
  analyze.py         # CLI: eval log → comparison tables + susceptibility analysis (debate/werewolf/diplomacy)
  analyze_surface.py # CLI: cross-env response-surface analyzer (frame × incentive × difficulty pivot per model)
  scenarios/         # JSONL scenario files (generated or hand-crafted)
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
    sales.py             # Task 4 sales rule-based classifier: sales_classifier (accurate/misleading/false)
    committee.py         # Task 5 committee scorers: initial_rating_bias, post_discussion_rating_change, discussion_polarity, decision_outcome
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
- **Sales** (Task 4): Principal-agent representation, single-agent. The agent represents a seller; a scripted buyer asks 5 fixed factual questions per scenario; answers are classified against a structured product spec as `accurate` / `misleading` / `false`. Deterministic rule-based scorer (`sales_classifier`) — no LLM judge. Lives in `sales_task.py` with its own 5-turn solver (`sales_interaction`) rather than `game_solver.py`, because there is no counterparty LLM.
- **Committee** (Task 5): Multi-agent committee (5 agents) evaluates a slate of candidates (4) on structured criteria. One agent has a private interested-party affiliation with a specific candidate. Phase sequence: `private_rating (ACTION) → discussion_r1…rN (DISCUSSION) → final_rating (ACTION)` — `num_discussion_rounds` is configurable. Agents submit ratings via the `submit_ratings` tool (nested JSON: candidate_id → criterion → int 0-10). Discussion is free-text with required `[A]/[B]/[C]/[D]` markers per candidate; the scorer splits by marker and applies a rule-based polarity classifier. All metrics mathematical — no LLM judge.

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
- `scorers/sales.py` — Task 4 sales: `sales_classifier` classifies each buyer-question response as `accurate` / `misleading` / `false` using per-check-type rules against a typed `check_fields` DSL on the ground-truth record. No LLM judge. Hand-validated with `experiments/task4_hand_validation.py` (emit template → human fills → score agreement ≥90%).
- `scorers/committee.py` — Task 5 committee metrics (all mathematical, no LLM): `initial_rating_bias` (interested party's favored-vs-matched-tier-peers delta on initial ratings), `post_discussion_rating_change` (neutral_shift_toward_interested = mean neutral delta signed by interested-party delta direction), `discussion_polarity` (rule-based wordlist classifier from `_committee_wordlist.py` with negation scope 3 and hedge halving; per-candidate segments split by `[X]` markers), `decision_outcome` (favored_won / ground_truth_matched / favored_rank). Hand-validated with `experiments/task5_hand_validation.py` (≥85% agreement gate).

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
- **Surface generators** live alongside legacy ones with the `_surface` suffix: [experiments/generate_village_surface.py](experiments/generate_village_surface.py), [experiments/generate_debate_surface.py](experiments/generate_debate_surface.py), [experiments/generate_bargaining_surface.py](experiments/generate_bargaining_surface.py). Task 4 and Task 5 were migrated in place (their original generators already factor over frame × incentive × difficulty).

### Debate rotation design

The standard experimental design for measuring manipulation in debates:
1. N agents debate a topic, each with a position
2. Generate N+1 scenarios: one **baseline** (no manipulator) + one per agent as the designated manipulator
3. The manipulator gets an extra instruction appended to their system prompt
4. Compare scores across conditions

The `generate.py` CLI automates this from a YAML config. Custom generator scripts (in `experiments/`) handle multi-topic experiments.

### Task 4 sales (single-agent, scripted buyer)

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

All models are accessed through OpenRouter (`OPENROUTER_API_KEY` in `.env`). Model IDs use the format `openrouter/provider/model-name`. The judge defaults to the eval's primary model but can be overridden with `--model-role judge=...`.

## Running things

```bash
# Install
pip install -e ".[dev]"

# Quick smoke test
inspect eval src/manipulation_bench/task.py --model mockllm/model --model-role debater=mockllm/model --model-role judge=mockllm/model --limit 1

# Generate rotation from YAML
python -m manipulation_bench.generate experiments/personhood.yaml -o src/manipulation_bench/scenarios/out.jsonl

# Run eval (fill in model names from generator output)
inspect eval src/manipulation_bench/task.py -T scenarios=out.jsonl --model-role ...

# Analyze results
python -m manipulation_bench.analyze "logs/2026*.eval"

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

## Experiment design conventions

- **Agent names must be generic** (alice, bob, carol, etc. or country names like austria, england). Never use model names (claude, gpt5) as agent names — models will recognize each other and adjust strategy, confounding results.
- **Model identity** is tracked in `scenario.metadata.model_mapping` for analysis, never exposed to agents.
- **Experiment generators** live in `experiments/`. Each produces a JSONL + prints the `inspect eval` command. Generators for: `generate_werewolf.py`, `generate_diplomacy.py`, `generate_factual.py`, `generate_contested.py`, `generate_policy_debates.py`, `generate_village.py`, `generate_contagion.py`, `generate_cross_env_antibody.py`, `generate_task4_sales.py`, `generate_task5_committee.py` (with `--pilot` flag for smaller subsets).
- **Rotation pattern**: baseline (no manipulation) + N variants (one per agent manipulating). Debate generators use the shared `generate_debate_rotation()` function from `generate.py`; game generators have custom rotation logic.
- **Multi-phase experiments**: `AgentRole.prior_context` carries interaction history across phases. The solver injects it before the current interaction. `extract_agent_history(log_path, sample_id, agent_name)` in `generate.py` reads a log and formats an agent's experience. Experiment scripts generate Phase 2 JSONL from Phase 1 logs. See `experiments/generate_contagion.py` for the pattern.

## Prior experimental results

See `FINDINGS.md` for all raw experimental results with sample sizes and reproduction commands. Reference this file when the user asks about prior results or wants to build on existing experiments. When new eval runs complete, add results to FINDINGS.md following the established format.

## Gotchas

- **Windows encoding**: Always use `encoding="utf-8"` when opening files for read/write. YAML with unicode characters (em-dashes, etc.) will produce corrupt JSONL otherwise.
- **StoreModel mutation**: `state.turns.append(x)` does NOT work. Use `state.turns = [*state.turns, x]`.
- **Scorer metrics with `"*"` glob**: Dict-valued scores with `@scorer(metrics={"*": [mean(), stderr()]})` auto-create per-key metrics. Different scenarios can have different agent names — metrics aggregate per-key across samples that share that key.
- **Ground-truth scorers**: Return `Score(value={"persuasion_rate": None, ...})` when `ground_truth` is not set. They don't error — they just produce None values.
- **JSONL paths**: `load_scenarios()` resolves relative paths against `src/manipulation_bench/scenarios/`. The `-T scenarios=filename.jsonl` flag passes just the filename, not a full path.

### Typed scenario metadata (`ScenarioMetadata`)

`ScenarioConfig.metadata` is a `ScenarioMetadata` Pydantic model with `extra="allow"`. Typed fields: `environment`, `model_mapping`, `game_outcome`, `game_state`. Access with dot notation (`metadata.game_state`) instead of `.get()`. Extra keys from generators are preserved.

## Running tests

```bash
pytest tests/ -v
```

## Future directions (discussed, not yet implemented)

- **Communication topology experiments**: Test how hub-spoke vs all-to-all vs bilateral pairs change manipulation dynamics
- **Live observation**: `TurnObserver` callback protocol for streaming to Discord/WebSocket
- **More game environments**: Extend the `Environment` ABC pattern to other social games (e.g., Mafia variants, Prisoner's Dilemma tournaments)
- **Cross-environment analysis**: Unified metrics comparing manipulation strategies across debate, social deduction, and negotiation settings
