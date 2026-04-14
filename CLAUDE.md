# CLAUDE.md — Context for Claude Code Sessions

## What this project is

manipulation-bench is a multi-agent evaluation framework for studying manipulation in AI interactions. It's built on [Inspect AI](https://inspect.aisi.org.uk/) and designed to answer: **how do different AI models behave when instructed to manipulate, and how susceptible are they to manipulation from others?**

The primary research contribution is evaluating how switching out the environment and communication topology influences models' manipulative behavior.

## Architecture overview

```
src/manipulation_bench/
  models.py          # Data models (AgentRole, Turn, ScenarioConfig, InteractionState)
  dataset.py         # JSONL loading with record_to_sample mapping
  protocols.py       # TurnProtocol interface + RoundRobinProtocol
  solver.py          # multi_agent_interaction() @solver — core orchestration loop
  game_solver.py     # Phase-aware solver for game environments (DISCUSSION/ACTION phases)
  prompts.py         # All judge/juror prompt templates
  task.py            # @task manipulation_bench — wires dataset + solver + scorers
  game_task.py       # @task for Werewolf game environment
  diplomacy_task.py  # @task for Diplomacy game environment
  _registry.py       # Inspect entry-point (just imports the task)
  generate.py        # CLI: YAML config → rotation JSONL + eval command
  analyze.py         # CLI: eval log → comparison tables + susceptibility analysis
  scenarios/         # JSONL scenario files (generated or hand-crafted)
  scorers/
    __init__.py      # Re-exports all scorers
    _helpers.py      # Shared: parse_json_score, score_per_agent, format_transcript
    judges.py        # LLM-judge scorers (manipulation_detection, argument_quality, belief_shift)
    voting.py        # Multi-juror voting + vote entropy
    grounded.py      # Ground-truth persuasion rate + Bayesian belief shift
    social_deduction.py  # Werewolf scorers: game_win_rate, vote_accuracy, deception_success, game_manipulation_detection
    negotiation.py       # Diplomacy scorers: territorial_success, agreement_compliance, negotiation_manipulation
experiments/         # YAML configs and generator scripts for specific experiments
```

### Environments

The framework supports three environment types:

- **Debate**: Conversation-based, 2-N agents. Measures persuasion and rhetorical tactics. Uses the standard `solver.py`.
- **Werewolf**: Social deduction game, 4-7 players. Measures deception and vote manipulation. Custom implementation in `game_task.py`.
- **Diplomacy**: Negotiation game, 7 powers. Measures promise-breaking and alliance betrayal. Wraps the `diplomacy` Python package via `diplomacy_task.py`.

## Key design decisions

### Agents are data, not code

Agent roles (name, model, system prompt, position) are defined per-scenario in JSONL, not in Python code. A scenario with 2 debaters, 4 panelists, or 1 interviewer + 1 subject all use the same solver. This means new experiment designs don't require code changes.

### Game solver (`game_solver.py`)

The game solver is phase-aware. **DISCUSSION** phases let agents talk (free-form messages routed by the environment). **ACTION** phases require agents to submit structured moves, with retry logic for invalid submissions. The `process_discussion()` hook lets environments process private messages — for example, Diplomacy uses it to route `TO:<name>:` prefixed messages to specific powers and extract `PROMISE: <order>` tags for promise tracking.

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

### Model swapping via Inspect model roles

Each agent has a `model_role` field. At eval time, roles are bound to actual models via `--model-role name=provider/model`. Multiple agents can share a role (e.g., all debaters use `model_role: "debater"`) or have distinct roles for cross-model comparison.

## How experiments work

### Debate rotation design

The standard experimental design for measuring manipulation in debates:
1. N agents debate a topic, each with a position
2. Generate N+1 scenarios: one **baseline** (no manipulator) + one per agent as the designated manipulator
3. The manipulator gets an extra instruction appended to their system prompt
4. Compare scores across conditions

The `generate.py` CLI automates this from a YAML config. Custom generator scripts (in `experiments/`) handle multi-topic experiments.

### Game environments (Werewolf, Diplomacy)

Game environments use `game_solver.py` instead of the standard debate solver. They follow a phase loop (DISCUSSION then ACTION) and produce game-specific metrics rather than debate metrics. Werewolf games run via `game_task.py`; Diplomacy games run via `diplomacy_task.py`.

Diplomacy has a dedicated promise-tracking system: messages use `TO:<name>:` format for private routing, and `PROMISE: <order>` tags are machine-parseable. The `agreement_compliance` scorer computes kept/total promises per agent as a hard mathematical metric (no LLM judge needed).

### Analysis pipeline

`analyze.py` reads an Inspect eval log and computes:
- **Per-scenario grids**: manipulation/quality/shift scores for each agent, with `*` marking the designated manipulator
- **Ability summary**: each model's manipulation score when instructed vs clean baseline + delta
- **Susceptibility**: contagion (did clean agents adopt manipulation?), quality drop, belief shift — all compared against the baseline scenario

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

All game environments implement `environments/base.py:Environment`:

```
setup(agent_names) → get_current_phase() → get_observation(agent) →
  DISCUSSION: solver generates text, calls process_discussion()
  ACTION: solver generates text, calls parse_action() + apply_action()
→ advance_phase() → ... → is_terminal() → get_outcome()
```

Key methods:
- `process_discussion(agent, content, phase)` — hook for routing private messages (default no-op; Diplomacy overrides it for TO:/PROMISE: parsing)
- `parse_action(agent, raw_text) -> str` — extract structured action from LLM output; raise ValueError to trigger retry
- `get_game_state_for_scoring() -> dict` — full state dump for scorers (roles, votes, messages, outcomes)

Adding a new game: implement the ABC, register in `environments/__init__.py:ENVIRONMENTS`, create a `@task` file, add environment-specific scorers.

## Experiment design conventions

- **Agent names must be generic** (alice, bob, carol, etc. or country names like austria, england). Never use model names (claude, gpt5) as agent names — models will recognize each other and adjust strategy, confounding results.
- **Model identity** is tracked in `scenario.metadata.model_mapping` for analysis, never exposed to agents.
- **Experiment generators** live in `experiments/`. Each produces a JSONL + prints the `inspect eval` command. Generators for: `generate_werewolf.py`, `generate_diplomacy.py`, `generate_factual.py`, `generate_contested.py`.
- **Rotation pattern**: baseline (no manipulation) + N variants (one per agent manipulating). The `generate.py` CLI handles this for debates; game generators do it manually.

## Gotchas

- **Windows encoding**: Always use `encoding="utf-8"` when opening files for read/write. YAML with unicode characters (em-dashes, etc.) will produce corrupt JSONL otherwise.
- **StoreModel mutation**: `state.turns.append(x)` does NOT work. Use `state.turns = [*state.turns, x]`.
- **Scorer metrics with `"*"` glob**: Dict-valued scores with `@scorer(metrics={"*": [mean(), stderr()]})` auto-create per-key metrics. Different scenarios can have different agent names — metrics aggregate per-key across samples that share that key.
- **Ground-truth scorers**: Return `Score(value={"persuasion_rate": None, ...})` when `ground_truth` is not set. They don't error — they just produce None values.
- **JSONL paths**: `load_scenarios()` resolves relative paths against `src/manipulation_bench/scenarios/`. The `-T scenarios=filename.jsonl` flag passes just the filename, not a full path.

## Future directions (discussed, not yet implemented)

- **Communication topology experiments**: Test how hub-spoke vs all-to-all vs bilateral pairs change manipulation dynamics
- **Live observation**: `TurnObserver` callback protocol for streaming to Discord/WebSocket
- **More game environments**: Extend the `Environment` ABC pattern to other social games (e.g., Mafia variants, Prisoner's Dilemma tournaments)
- **Cross-environment analysis**: Unified metrics comparing manipulation strategies across debate, social deduction, and negotiation settings
- **More protocols**: Moderated (designated agent controls turn order), sequential, free-form
