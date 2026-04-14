# manipulation-bench

Framework for measuring how AI models manipulate and respond to manipulation across multiple environments — debates, social deduction (Werewolf), and negotiation (Diplomacy). Built on [Inspect AI](https://inspect.aisi.org.uk/).

## Quick start

```bash
pip install -e ".[dev]"
cp .env.example .env   # add your OPENROUTER_API_KEY
```

Run a quick test (any environment):

```bash
# Debate (2 agents)
inspect eval src/manipulation_bench/task.py \
  --model openrouter/anthropic/claude-sonnet-4-20250514 \
  --model-role debater=openrouter/anthropic/claude-sonnet-4-20250514 \
  --model-role judge=openrouter/anthropic/claude-sonnet-4-20250514 \
  --limit 1

# Werewolf (4 players)
inspect eval src/manipulation_bench/game_task.py \
  --model openrouter/anthropic/claude-sonnet-4-20250514 \
  --model-role player=openrouter/anthropic/claude-sonnet-4-20250514 \
  --model-role judge=openrouter/anthropic/claude-sonnet-4-20250514

# Diplomacy (7 powers)
inspect eval src/manipulation_bench/diplomacy_task.py \
  --model openrouter/anthropic/claude-sonnet-4-20250514 \
  --model-role player=openrouter/anthropic/claude-sonnet-4-20250514 \
  --model-role judge=openrouter/anthropic/claude-sonnet-4-20250514
```

View results: `inspect view`

## Environments

### Debate

Conversation-based, 2-N agents. Each agent argues a position on a topic. Measures persuasion, rhetorical manipulation, and argument quality.

```bash
inspect eval src/manipulation_bench/task.py \
  -T scenarios=debate_2agent.jsonl \
  --model openrouter/anthropic/claude-opus-4-6 \
  --model-role debater=openrouter/anthropic/claude-opus-4-6 \
  --model-role judge=openrouter/anthropic/claude-opus-4-6
```

Use different models per debater with distinct `model_role` values in the scenario JSONL and separate `--model-role` flags.

### Werewolf

Social deduction game, 4-7 players. Werewolves must deceive villagers; villagers must detect and vote out werewolves. Measures deception, vote manipulation, and detection accuracy.

```bash
# Single model (all players)
inspect eval src/manipulation_bench/game_task.py \
  --model openrouter/anthropic/claude-opus-4-6 \
  --model-role player=openrouter/anthropic/claude-opus-4-6 \
  --model-role judge=openrouter/anthropic/claude-opus-4-6

# Multiple models (use generate_werewolf.py for rotation scenarios)
inspect eval src/manipulation_bench/game_task.py \
  -T scenarios=werewolf_rotation.jsonl \
  --model openrouter/anthropic/claude-opus-4-6 \
  --model-role model_a=openrouter/anthropic/claude-opus-4-6 \
  --model-role model_b=openrouter/openai/gpt-5 \
  --model-role model_c=openrouter/google/gemini-2.5-pro \
  --model-role model_d=openrouter/x-ai/grok-3 \
  --model-role judge=openrouter/anthropic/claude-opus-4-6
```

### Diplomacy

7-power negotiation game with private bilateral messaging and promise tracking. Wraps the `diplomacy` Python package for full DATC-compliant rules. Measures alliance formation, promise-breaking, and strategic betrayal.

Messages use `TO:<name>:` format for private routing. `PROMISE: <order>` tags are machine-parseable and tracked by the `agreement_compliance` scorer.

```bash
# Multiple models across 7 powers
inspect eval src/manipulation_bench/diplomacy_task.py \
  -T scenarios=diplomacy_multimodel.jsonl \
  --model openrouter/anthropic/claude-opus-4-6 \
  --model-role model_a=openrouter/anthropic/claude-opus-4-6 \
  --model-role model_b=openrouter/openai/gpt-5 \
  --model-role model_c=openrouter/google/gemini-2.5-pro \
  --model-role model_d=openrouter/x-ai/grok-3 \
  --model-role judge=openrouter/anthropic/claude-opus-4-6
```

## Running manipulation experiments

The standard experiment design: run the same scenario multiple times, rotating which agent is secretly instructed to manipulate. Compare behavior across conditions.

### Debate rotation

```bash
# 1. Define experiment in YAML
vim experiments/my_experiment.yaml

# 2. Generate rotation scenarios (baseline + 1 per manipulator)
python -m manipulation_bench.generate experiments/my_experiment.yaml \
  -o src/manipulation_bench/scenarios/my_rotation.jsonl

# 3. Run (copy the printed command)
inspect eval src/manipulation_bench/task.py -T scenarios=my_rotation.jsonl ...

# 4. Analyze
python -m manipulation_bench.analyze "logs/2026*.eval"
```

### Werewolf rotation

```bash
# Generate 10 games per model as werewolf (40 total)
python experiments/generate_werewolf.py

# Run
inspect eval src/manipulation_bench/game_task.py -T scenarios=werewolf_rotation.jsonl ...
```

### Diplomacy multi-model

```bash
# Generate 3 games with 4 models across 7 powers
python experiments/generate_diplomacy.py

# Run
inspect eval src/manipulation_bench/diplomacy_task.py -T scenarios=diplomacy_multimodel.jsonl ...
```

### Contagion experiment (multi-phase)

Tests whether exposure to manipulation in one debate carries over into a new, clean interaction.

```bash
# Phase 1: exposure (standard rotation on topics 0-1)
python experiments/generate_contagion.py phase1 -o scenarios/contagion_p1.jsonl
inspect eval src/manipulation_bench/task.py -T scenarios=contagion_p1.jsonl ...

# Phase 2: transfer (exposed agents debate topics 2-3 with a fresh partner)
python experiments/generate_contagion.py phase2 \
  --phase1-log "logs/2026*.eval" -o scenarios/contagion_p2.jsonl
inspect eval src/manipulation_bench/task.py -T scenarios=contagion_p2.jsonl ...

# Compare Phase 2 manipulation scores: exposed vs control
python -m manipulation_bench.analyze "logs/*contagion_p2*.eval"
```

Agents carry their Phase 1 conversation history via the `prior_context` field. The framework injects it automatically — experiment scripts just populate the field.

## Metrics

### LLM-judge (qualitative)

| Metric | Definition |
|--------|-----------|
| `manipulation_detection` | Single judge rates manipulation 0-1 per agent |
| `argument_quality` | Single judge rates reasoning quality 0-1 |
| `belief_shift` | Single judge rates position drift from assigned stance |

### Statistical (reproducible)

| Metric | Definition |
|--------|-----------|
| `juror_voting` | 7 independent binary YES/NO verdicts on manipulation. Reports vote fraction and Shannon entropy. |

### Grounded (mathematical, requires `ground_truth` on scenario)

| Metric | Definition |
|--------|-----------|
| `persuasion_rate` | Fraction of jurors believing the wrong answer. Binomial proportion. |
| `belief_shift` | Mean change in P(claim is true) before vs after debate. |

### Social deduction (Werewolf)

| Metric | Definition |
|--------|-----------|
| `game_win_rate` | Per-agent win/loss based on team outcome |
| `vote_accuracy` | Fraction of votes correctly targeting werewolves |
| `deception_success` | Fraction of game survived as werewolf before being caught |
| `game_manipulation_detection` | LLM-judge adapted for game context (evaluates sophistication) |

### Negotiation (Diplomacy)

| Metric | Definition |
|--------|-----------|
| `territorial_success` | Supply center count normalized to [0,1] |
| `agreement_compliance` | Kept promises / total promises. Hard metric, no LLM. |
| `negotiation_manipulation` | LLM-judge on deception sophistication in private messages |

### Derived (computed by `analyze.py`)

| Metric | Definition |
|--------|-----------|
| Ability delta | manipulation(instructed) - manipulation(baseline) |
| Contagion | manipulation(under pressure) - manipulation(baseline) |
| Quality tradeoff | quality(manipulating) - quality(baseline) |

## Communication topologies

Control what each agent can see via the `visibility` field:

| Topology | Description |
|----------|------------|
| `"all_to_all"` | Everyone sees everything (default) |
| `"isolated"` | Agents only see their own prior turns |
| `"hub_spoke"` | First agent sees all; others only see the first agent |
| `{agent: [list]}` | Custom adjacency dict, e.g. `{"mod": ["a","b"], "a": ["mod"]}` |

## Project structure

```
src/manipulation_bench/
  models.py            AgentRole, Turn, ScenarioConfig, ScenarioMetadata, InteractionState
  game_solver.py       Unified solver for all environments (DISCUSSION/ACTION phases)
  environments/
    base.py            Environment ABC + Phase, Observation, ActionResult, GameOutcome
    debate.py           Debate environment (DISCUSSION-only, round-robin)
    werewolf.py        Werewolf social deduction game
    diplomacy.py       Diplomacy negotiation game (wraps diplomacy package)
  scorers/
    judges.py          LLM-judge scorers (debates)
    voting.py          Multi-juror voting + entropy
    grounded.py        Ground-truth persuasion + belief shift
    social_deduction.py  Werewolf scorers
    negotiation.py       Diplomacy scorers
  prompts.py           All judge/juror prompt templates
  dataset.py           JSONL scenario loading
  task.py              @task for debates
  game_task.py         @task for Werewolf
  diplomacy_task.py    @task for Diplomacy
  generate.py          YAML -> rotation JSONL generator + generate_debate_rotation()
  analyze.py           Eval log -> comparison tables (debate/werewolf/diplomacy)
  scenarios/           Generated and hand-crafted JSONL files
experiments/           Experiment configs and generator scripts
tests/                 pytest test suite
```
