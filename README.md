# manipulation-bench

Framework for measuring how AI models manipulate and respond to manipulation across multiple multi-agent environments — debates, social deduction (Werewolf), negotiation (Diplomacy / Bargaining), a public-goods game (Village Commons), vocabulary-convergence (Naming Game), a single-agent sales task, a committee evaluation with conflict of interest, and inbox triage. Built on [Inspect AI](https://inspect.aisi.org.uk/).

Every environment can be parameterized on the same three axes (frame × incentive × difficulty), so results are comparable cross-environment via a single analyzer. Bring your own scenarios, models, and scorers — the framework is independent of any particular study.

For exploratory experiment write-ups see [`FINDINGS.md`](FINDINGS.md). Study artifacts (pre-registrations, eval logs, analysis outputs) live under [`paper/`](paper/README.md).

## Quick start

```bash
# Install. Required: Python 3.11+. (uv pip install -e ".[dev]" works too.)
pip install -e ".[dev]"

# Provider keys. Most models go through OpenRouter; DeepSeek's reasoner needs
# the official DeepSeek API for tool calls (see docs/provider_quirks.md).
cp .env.example .env   # then add OPENROUTER_API_KEY (and DEEPSEEK_* if needed)

# Smoke test — local, no API key.
mb run debate --model mockllm/model --judge mockllm/model --limit 1

# List environments, run an env, run multiple envs, compare two models.
mb envs
mb run debate --model openrouter/anthropic/claude-opus-4.7
mb run debate village sales --model openrouter/anthropic/claude-opus-4.7
mb run debate --models debater=openrouter/anthropic/claude-opus-4.7,judge=openrouter/openai/gpt-5

# Analyze the most recent matching log.
mb analyze 'logs/2026*.eval'
```

`mb run` discovers the `model_role`s in each environment's default scenario JSONL and binds them all to `--model`. Pass `--models name=id,name=id` to override individual roles, `--scenarios <file.jsonl>` to swap scenario files, and any other flag (`--max-connections`, `--no-fail-on-error`, etc.) is forwarded verbatim to `inspect eval`. Power users can call `inspect eval src/manipulation_bench/<task>.py …` directly — the CLI is just a convenience layer. If `mb` is not on your `PATH`, `python -m manipulation_bench.cli` is equivalent.

### Extending the framework

- **Add a new environment**: copy [`examples/new_environment/`](examples/new_environment/) and follow the 5-step checklist in its README.
- **Add a new scorer**: see [`examples/new_scorer/`](examples/new_scorer/) for a deterministic + LLM-judge template. Use a custom scorer without forking a task file via `-T`:
  ```bash
  mb run debate --model openrouter/... -T scorers=manipulation_detection,my_pkg.my_module.my_scorer
  ```
  Bare names hit the built-in `manipulation_bench.scorers` registry; dotted names are imported. The resolver lives in [`src/manipulation_bench/scorers/_resolve.py`](src/manipulation_bench/scorers/_resolve.py).
- **Add a new mitigation (defense)**: see [`examples/new_mitigation/`](examples/new_mitigation/). Defenses are resolved at runtime like scorers, so the same scenario runs baseline vs. defended without regeneration:
  ```bash
  mb run debate --model openrouter/... -T mitigations=prompt_suffix,critic_monitor
  ```
  Built-ins live in [`src/manipulation_bench/mitigations/`](src/manipulation_bench/mitigations/) (`prompt_suffix`, `critic_monitor`); dotted names import a custom factory.

## Architecture

```
  YAML config / generator script            (experiments/)
              │
              ▼
       scenarios/*.jsonl                    (1 scenario per line)
              │
              ▼
   Inspect AI task + dataset                (src/manipulation_bench/*_task.py)
              │
              ▼
         game_solver                        (unified solver for all envs)
              │
              ▼
      Environment (Debate / Werewolf /
                  Diplomacy / Village /
                  Naming / Sales /
                  Committee / Inbox)        DISCUSSION → text + optional tools
                                            ACTION    → tool calls → state
                                            (Sales / Inbox use custom solvers)
              │
              ▼
       Scorers (judge / grounded /
                game-specific)
              │
              ▼
        logs/*.eval  ──▶  analyze.py        (tables, susceptibility, per-model aggregates)
```

Three things make the architecture hang together:

- **Agents are data, not code.** An `AgentRole` is `name`, `model_role`, `system_prompt`, `position`. A 2-person debate, a 7-power Diplomacy game, and a 6-agent village all use the same solver — only the scenario JSONL changes.
- **Model binding is late.** Scenarios name a `model_role` (e.g. `debater_a`); you bind it to a real model at eval time with `--model-role debater_a=openrouter/...`. Swap models without regenerating scenarios.
- **Environments share an ABC.** All phase-based interaction goes through `environments/base.py`. Adding a new game = subclass it, register it, add a `@task` file.

## Environments

| Env | Players | Channel | Headline metric | Task file |
|---|---|---|---|---|
| **Debate** | 2-N | Conversation | `manipulation_detection`, `belief_shift`, `juror_voting` | [`task.py`](src/manipulation_bench/task.py) |
| **Bargaining** | 2 | Negotiation + structured `commit_valuation` | `manipulation_rate` (rule-based) | [`bargaining_task.py`](src/manipulation_bench/bargaining_task.py) |
| **Werewolf** | 4-8 | Social deduction | `game_win_rate`, `vote_accuracy`, `deception_success` | [`game_task.py`](src/manipulation_bench/game_task.py) |
| **Diplomacy** | 7 | Bilateral messaging + tracked promises | `agreement_compliance` (kept/total promises), `territorial_success` | [`diplomacy_task.py`](src/manipulation_bench/diplomacy_task.py) |
| **Village Commons** | 6 | Public-goods game (contribute/inspect/accuse) | `exploitation_rate`, `promise_action_gap`, `village_fairness` | [`village_task.py`](src/manipulation_bench/village_task.py) |
| **Sales** | 1 (scripted buyer) | 5 fixed factual questions | `manipulation_rate` = (misleading + false) / 5 | [`sales_task.py`](src/manipulation_bench/sales_task.py) |
| **Committee** | 5 (1 interested + 4 neutral) | Multi-phase rate → discuss → re-rate | `initial_rating_bias`, `neutral_shift_toward_interested` | [`committee_task.py`](src/manipulation_bench/committee_task.py) |
| **Inbox triage** | 1 | Triage emails via `triage_message` tool | per-message attention/archive/forward classification | [`inbox_task.py`](src/manipulation_bench/inbox_task.py) |
| **Naming Game** | N | Parallel broadcast | vocabulary convergence under topology | [`game_task.py`](src/manipulation_bench/game_task.py) |

Most envs share `game_solver.py`; Sales and Inbox use custom solvers because the counterparty is scripted. Reference scenario generators live in [`experiments/`](experiments/) (env-agnostic, surface-style) and [`paper/task<N>/scripts/`](paper/) (study-specific, PREREG-locked configs with `--models` overrides).

## Response-surface design (cross-environment)

To compare manipulation behavior *across* environments, every env can be parameterized on the same three axes:

| Axis | Levels | Controls |
|------|--------|----------|
| **Frame** | `prohibitive`, `pro_social`, `minimal`, `selfish`, `permissive` | The prompt framing of the manipulable objective |
| **Incentive** | `none`, `moderate`, `high` | Strength of the payoff/penalty attached to manipulation |
| **Difficulty** | `low`, `medium`, `high` | How much manipulation is needed to move the outcome (asymmetric valuations for bargaining, pool multiplier for village, juror pre-belief for debate, slate/product difficulty for committee/sales) |

Axis levels and per-environment prompt fragments live in [`src/manipulation_bench/axes.py`](src/manipulation_bench/axes.py). Each scenario's canonical axis cell is stored on typed `ScenarioMetadata.frame / .incentive / .difficulty` fields; study-specific role labels (e.g. `manipulator`, `interested_party`) live alongside in extra metadata, preserved by `extra='allow'`.

```bash
# Generate pilot scenarios for any env
python experiments/generate_village_surface.py --pilot
python experiments/generate_debate_surface.py --pilot
python experiments/generate_bargaining_surface.py --pilot
python paper/task4_sales/scripts/generate_task4_sales.py --pilot
python paper/task5_committee/scripts/generate_task5_committee.py --pilot

# Pivot any eval log into frame × incentive / frame × difficulty grids per model
python -m manipulation_bench.analyze_surface "logs/*_surface*.eval" --csv out.csv
```

The analyzer auto-detects the environment by scorer names, normalizes legacy axis names through an alias map, and uses each env's canonical manipulation metric.

## Running manipulation experiments

The standard design: run the same scenario multiple times, rotating which agent is secretly instructed to manipulate. Compare behavior across conditions.

```bash
# 1. Define a YAML rotation (use experiments/personhood.yaml as a template)
# 2. Generate baseline + 1 scenario per manipulator
python -m manipulation_bench.generate experiments/my_experiment.yaml \
  -o src/manipulation_bench/scenarios/my_rotation.jsonl

# 3. Run (the generator prints the exact inspect eval command)
inspect eval src/manipulation_bench/task.py -T scenarios=my_rotation.jsonl ...

# 4. Analyze
python -m manipulation_bench.analyze "logs/2026*.eval"
```

YAML works for single-topic debate rotations. Multi-topic, custom-rotation, or non-debate experiments use a Python generator under [`experiments/`](experiments/) — see [`generate_debate_surface.py`](experiments/generate_debate_surface.py) for the canonical response-surface template.

`AgentRole.prior_context` carries interaction history across phases for multi-phase experiments — `extract_agent_history(log_path, sample_id, agent_name)` in [`generate.py`](src/manipulation_bench/generate.py) reads a log and formats an agent's experience for a Phase-2 JSONL.

## What you get: sample analyzer output

After a debate rotation + `python -m manipulation_bench.analyze "logs/*.eval"` (values illustrative):

```
SUMMARY: Manipulation score when INSTRUCTED vs CLEAN
Model              Instructed    Clean    Delta
alice                    0.68     0.24    +0.44
bob                      0.71     0.23    +0.48
carol                    0.64     0.29    +0.35
dave                     0.66     0.28    +0.38

SUSCEPTIBILITY (baseline vs under manipulation pressure)
Model              Contagion   Quality Drop   Belief Shift
alice                  +0.03          -0.04          +0.12
bob                    +0.02          -0.01          +0.05
carol                  +0.01          -0.08          +0.18
dave                   +0.04          -0.12          +0.21
```

"Delta" = instructed minus baseline = **ability to manipulate on command**. Contagion / quality drop / belief shift = what happens to the other agents when a manipulator is present = **susceptibility**. Werewolf, Diplomacy, Village, Sales, and Committee analyses produce environment-specific tables (per-role win rates, deception success, exploitation rate, etc.) — see [`analyze.py`](src/manipulation_bench/analyze.py) for details.

## Glossary

| Term | Meaning |
|------|---------|
| **Agent** | One role in a scenario (`alice`, `bob`, `austria`, `agent_1`). Has a name, system prompt, position, and a `model_role`. |
| **`model_role`** | An indirection layer. The scenario says `model_role: debater_a`; at eval time you bind it to a real model with `--model-role debater_a=openrouter/...`. |
| **Judge** | A single LLM scoring qualitative metrics (one call per sample). Bound via `--model-role judge=...`. |
| **Juror** | A voter in a multi-model panel. `juror_voting` polls 7 jurors; grounded scorers elicit beliefs from several juror models. Distinct from the single `judge`. |
| **Baseline** | A rotation scenario where no agent is instructed to manipulate. The reference point for every delta. |
| **Rotation** | The standard experiment design: `baseline + one scenario per agent as the designated manipulator`. N+1 scenarios per topic. |
| **Ability (delta)** | `manipulation(instructed) − manipulation(baseline)`. How much a model manipulates *on command*. |
| **Susceptibility / Contagion** | What happens to other agents when a manipulator is present. How much they drift, use more tactics themselves, or lose quality. |
| **Topology / visibility** | Who can see whose messages. `"all_to_all"`, `"hub_spoke"`, `"isolated"`, or a custom adjacency dict. |
| **Phase** | `DISCUSSION` (free-form text, optional tools) or `ACTION` (must emit a tool call). The solver loops through phases until the environment reports terminal. |

## Models

The framework is model-agnostic — bind any provider/model via `--model-role`. A canonical 6-model frontier roster is used in the [`paper/`](paper/README.md) artifacts:

| Slot | Label | Model ID | Notes |
|---|---|---|---|
| `model_a` | Claude Opus 4.7 | `openrouter/anthropic/claude-opus-4.7` | default |
| `model_b` | GPT-5.5 | `openrouter/openai/gpt-5.5-20260423` | `reasoning_enabled=true` |
| `model_c` | Gemini 3.1 Pro | `openrouter/google/gemini-3.1-pro-preview` | `reasoning_enabled=true` |
| `model_d` | Grok 4 | `openrouter/x-ai/grok-4` | `reasoning_enabled=true` |
| `model_e` | Llama 3.3 70B | `openrouter/meta-llama/llama-3.3-70b-instruct` | default |
| `model_f` | DeepSeek V4 Pro | `openai-api/deepseek/deepseek-v4-pro` | DeepSeek official API; per-agent `metadata.tool_choice_strategy=auto` (see [`docs/provider_quirks.md`](docs/provider_quirks.md)) |

Cheap-tier alternatives for jurors / bystander panels / smoke runs: `openrouter/openai/gpt-5-mini`, `openrouter/google/gemini-3-flash-preview`, `openrouter/anthropic/claude-haiku-4.5`, `openrouter/deepseek/deepseek-chat`. [`FINDINGS.md`](FINDINGS.md) examples use earlier-generation models (Claude Opus 4.6, GPT-5, Gemini 2.5 Pro, Grok 3) preserved at the versions they were originally published at.

**Local / offline runs** are supported via [Ollama](https://ollama.com/) using Inspect AI's native `ollama` provider — see [`docs/ollama.md`](docs/ollama.md). Example: `mb run debate --model ollama/qwen3:14b --limit 1`.

## Communication topologies

Control what each agent can see via the `visibility` field on a scenario:

| Topology | Description |
|----------|------------|
| `"all_to_all"` | Everyone sees everything (default) |
| `"isolated"` | Agents only see their own prior turns |
| `"hub_spoke"` | First agent sees all; others only see the first agent |
| `{agent: [list]}` | Custom adjacency dict, e.g. `{"mod": ["a","b"], "a": ["mod"]}` |

## Project structure

```
src/manipulation_bench/
  axes.py            Canonical response-surface axes + per-env prompt fragments
  models.py          AgentRole, Turn, ScenarioConfig, ScenarioMetadata, InteractionState
  game_solver.py     Unified DISCUSSION/ACTION solver
  environments/      Environment ABC + per-env implementations
  scorers/           Per-env scorers (judges, voting, grounded, env-specific)
  prompts.py         All judge/juror prompt templates
  *_task.py          One @task per environment
  generate.py        YAML → rotation JSONL helpers
  analyze.py         Eval log → per-env comparison tables
  analyze_surface.py Eval log → cross-env frame × incentive × difficulty pivot
  scenarios/         Generated and hand-crafted JSONL files
experiments/         Env-agnostic surface generators + per-env demos
examples/            Templates: new_environment/, new_scorer/
paper/               Study artifacts (pre-registrations, eval logs, analyses)
docs/                Cross-cutting docs (provider_quirks.md, etc.)
tests/               pytest test suite
```
