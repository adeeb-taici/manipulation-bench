# Agent Activation Schedule — Design

**Date:** 2026-04-16
**Status:** Proposed (follow-up to naming-game PR)
**Repo:** `manipulation-bench`

## Problem

`game_solver.py` iterates `phase.acting_agents` in a fixed serial loop and calls `env.get_observation(agent)` → `model.generate(...)` → `env.process_discussion(...)` for each agent one at a time. This hardcodes a single activation policy (sequential, fixed order) into the framework.

Real MAS research distinguishes several activation schedules, and the choice materially changes the system's dynamics — the Baronchelli naming game, for example, is defined with synchronous or random-asynchronous updates, not sequential ones. Debates want round-robin, Werewolf wants a fixed action order, Diplomacy wants concurrent private messaging.

Today the naming-game environment works around the serial loop by keeping a staging buffer (`_pending_proposals`) so that mid-round observations don't leak one agent's current-round proposal to another. This is correct but costly: N sequential LLM calls per round (~N× wall-clock) and it conflates *semantics* (observations see the same pre-round state) with *execution order* (which agent runs first).

## Goals

1. Make the activation schedule a first-class, configurable property of a `Phase`.
2. Preserve current behaviour for all existing environments (debate, werewolf, diplomacy, village) by defaulting to `sequential_fixed`.
3. Let the naming-game environment declare `synchronous` activation and drop its staging buffer.
4. Run synchronous agents concurrently (`asyncio.gather`) so N LLM calls take ~1× wall-clock, not N×.
5. Keep scenario-level override possible (`metadata.environment.schedule: ...`).

## Non-goals

- Do not redesign `Environment`'s ABC. Schedules live on `Phase`; environments opt in per phase.
- Do not implement `event_driven` in this PR. It's listed for future completeness but is not needed by any current environment.
- Do not change `network.py` or the topology system. Schedule (when) is orthogonal to topology (who sees whom).

## Schedules

| Schedule | Each agent sees | Execution | Primary use case |
|---|---|---|---|
| `synchronous` | Identical pre-round state | Concurrent (`asyncio.gather`) | Cellular automata, Baronchelli naming game, simultaneous voting |
| `sequential_fixed` | All prior actions this round (incl. earlier agents') | Serial, order from `acting_agents` | Debate round-robin, Werewolf action order (current default) |
| `sequential_random` | Same as `sequential_fixed` | Serial, order reshuffled per call via `env.rng` | Deliberation studies that want to remove position bias |
| `random_asynchronous` | All prior actions so far (no "round" boundary) | One agent per solver tick; env drives who by returning a 1-element `acting_agents` | Classical async Baronchelli; event-like dynamics |

## Changes

### `environments/base.py`

```python
from typing import Literal

Schedule = Literal[
    "synchronous",
    "sequential_fixed",
    "sequential_random",
    "random_asynchronous",
]

class Phase(BaseModel, frozen=True):
    name: str
    phase_type: PhaseType
    round: int
    acting_agents: list[str]
    description: str = ""
    schedule: Schedule = "sequential_fixed"
```

The existing `parallel: bool = False` field is removed. `schedule == "synchronous"` replaces it.

### `game_solver.py`

The per-phase block becomes:

```python
phase = env.get_current_phase()

if phase.schedule == "synchronous":
    # All observations built BEFORE any generation — everyone sees the same pre-round state.
    obs_by_agent = {a: env.get_observation(a) for a in phase.acting_agents}
    msg_sets = {a: _build_game_messages(agents_by_name[a], obs_by_agent[a], interaction, scenario)
                for a in phase.acting_agents}

    # Concurrent generation
    outputs = await asyncio.gather(*[
        get_model(role=agents_by_name[a].model_role).generate(
            msg_sets[a], tools=env.get_tools(a, phase), tool_choice=env.get_tool_choice(phase),
            config=GenerateConfig(max_tokens=scenario.max_tokens),
        )
        for a in phase.acting_agents
    ])

    # Apply all results after
    for a, output in zip(phase.acting_agents, outputs):
        content = output.completion or ""
        if output.message.tool_calls:
            env.process_tool_calls(a, output.message.tool_calls, phase)
        env.process_discussion(a, content, phase)
        interaction.turns = [*interaction.turns, Turn(
            speaker=a, content=content, round=phase.round, turn_index=turn_index,
            metadata={"phase": phase.name, "phase_type": "discussion"},
        )]
        turn_index += 1

elif phase.schedule in ("sequential_fixed", "sequential_random"):
    agents_order = list(phase.acting_agents)
    if phase.schedule == "sequential_random":
        env.rng.shuffle(agents_order)  # env owns the RNG for reproducibility
    for a in agents_order:
        # ... existing per-agent body (observation → generate → process) ...

elif phase.schedule == "random_asynchronous":
    # Same as sequential_fixed; env is responsible for returning a 1-element
    # acting_agents list on each advance_phase() and for its own convergence check.
    for a in phase.acting_agents:
        # ... existing body ...
```

`ACTION`-phase handling stays in the serial branch. Synchronous ACTION phases are possible in principle but no current env needs them; defer until a consumer asks.

### Environments (no changes required by default)

Every existing environment's `get_current_phase()` omits `schedule`, so the Pydantic default `"sequential_fixed"` fires — identical to today's behaviour. No debate/werewolf/diplomacy/village code touches change.

### `environments/naming_game.py` (simplification)

- Set `schedule="synchronous"` in the Phase returned by `get_current_phase()`.
- **Delete** `_pending_proposals` and all references.
- `process_discussion` writes directly to `self._round_proposals[self._round][agent_name] = name`.
- `advance_phase` no longer promotes a buffer — only runs convergence check + round bump.

Net effect: the env shrinks by ~15 lines and runs ~N× faster per round.

### Scenario-level override

`scenario.metadata.environment.schedule` flows through `create_environment(config)` the same way `topology` does. Environments that honor it pass it to the Phase constructor. Naming game defaults to `synchronous` when no override is present.

### Tests

- `tests/test_solver_schedule.py` (new): verifies `synchronous` runs observations before any generation, `sequential_random` uses a seeded shuffle, and the default path is unchanged for debate.
- `tests/test_naming_game.py`: remove the staging-buffer tests (invariant is now enforced by the solver, not the env). Add an integration test that mocks the model and asserts all 4 agents' observations are built before any of their generations complete.

## Risk / rollback

- **Concurrent LLM calls may hit rate limits.** OpenRouter already serializes per-key; and N≤10 in any realistic scenario. If it becomes a problem, add a `max_concurrency` scenario key and wrap `asyncio.gather` in a semaphore.
- **Observation-before-generation breaks environments that mutate state in `get_observation`.** Audit: today no environment does. Lint/type check won't catch this — add a note to the `Environment` ABC docstring that `get_observation` must be pure.
- **Rollback:** revert the solver + base.py + naming_game.py commits; the scenario config key `schedule` becomes a harmless unused dict entry. No data migration needed.

## Scope boundary

This spec covers the framework change and the naming-game retrofit only. Separate follow-ups (not in this spec):

- Promote scheduling to an experimental axis: run the same naming-game scenario under `synchronous` vs `sequential_fixed` vs `random_asynchronous` and compare convergence curves.
- Apply `sequential_random` to debate to measure position-bias in persuasion metrics.
- Design `event_driven` once a concrete need surfaces (e.g., a Diplomacy negotiation phase where messages trigger responses outside the round structure).
