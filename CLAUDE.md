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
  prompts.py         # All judge/juror prompt templates
  task.py            # @task manipulation_bench — wires dataset + solver + scorers
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
experiments/         # YAML configs and generator scripts for specific experiments
```

## Key design decisions

### Agents are data, not code

Agent roles (name, model, system prompt, position) are defined per-scenario in JSONL, not in Python code. A scenario with 2 debaters, 4 panelists, or 1 interviewer + 1 subject all use the same solver. This means new experiment designs don't require code changes.

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

Future game environments add their own scorer files (e.g., `scorers/social_deduction.py`).

### Model swapping via Inspect model roles

Each agent has a `model_role` field. At eval time, roles are bound to actual models via `--model-role name=provider/model`. Multiple agents can share a role (e.g., all debaters use `model_role: "debater"`) or have distinct roles for cross-model comparison.

## How experiments work

### Rotation design

The standard experimental design for measuring manipulation:
1. N agents debate a topic, each with a position
2. Generate N+1 scenarios: one **baseline** (no manipulator) + one per agent as the designated manipulator
3. The manipulator gets an extra instruction appended to their system prompt
4. Compare scores across conditions

The `generate.py` CLI automates this from a YAML config. Custom generator scripts (in `experiments/`) handle multi-topic experiments.

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

## Gotchas

- **Windows encoding**: Always use `encoding="utf-8"` when opening files for read/write. YAML with unicode characters (em-dashes, etc.) will produce corrupt JSONL otherwise.
- **StoreModel mutation**: `state.turns.append(x)` does NOT work. Use `state.turns = [*state.turns, x]`.
- **Scorer metrics with `"*"` glob**: Dict-valued scores with `@scorer(metrics={"*": [mean(), stderr()]})` auto-create per-key metrics. Different scenarios can have different agent names — metrics aggregate per-key across samples that share that key.
- **Ground-truth scorers**: Return `Score(value={"persuasion_rate": None, ...})` when `ground_truth` is not set. They don't error — they just produce None values.
- **JSONL paths**: `load_scenarios()` resolves relative paths against `src/manipulation_bench/scenarios/`. The `-T scenarios=filename.jsonl` flag passes just the filename, not a full path.

## Future directions (discussed, not yet implemented)

- **Communication topology experiments**: Test how hub-spoke vs all-to-all vs bilateral pairs change manipulation dynamics
- **Live observation**: `TurnObserver` callback protocol for streaming to Discord/WebSocket
- **Game environments**: `Environment` ABC with `get_observation()`/`apply_action()`/`is_terminal()` for social deduction, negotiation, etc.
- **Game-specific metrics**: Conditional probabilities from social deduction outcomes, agreement compliance rates from negotiation
- **More protocols**: Moderated (designated agent controls turn order), sequential, free-form
