# Adding a new environment

This directory is a copy-pasteable starting point for a new
`Environment` subclass. The example is a 2-agent "guess my number"
game with two DISCUSSION rounds — works with any model including
`mockllm/model` (no tool-call support required).

## Files

- [`my_env.py`](my_env.py) — the `Environment` subclass. Implements
  every abstract method on `manipulation_bench.environments.base.Environment`
  in ~150 lines, with comments on each method's contract.
- [`my_env_task.py`](my_env_task.py) — the `@task` wrapper that
  `inspect eval` invokes. Shows how to register the environment
  with the global `ENVIRONMENTS` factory and includes a tiny
  scorer inline so the file is self-contained.
- [`my_env_scenarios.jsonl`](my_env_scenarios.jsonl) — two minimal
  scenarios. The format is the same as production scenarios under
  `src/manipulation_bench/scenarios/`.

## Run it

```bash
# Smoke test with the local mock model (no API key)
inspect eval examples/new_environment/my_env_task.py \
  --model mockllm/model \
  --model-role player=mockllm/model \
  --model-role judge=mockllm/model \
  --limit 1

# Real run with a real model (defaults the player + judge roles to it)
inspect eval examples/new_environment/my_env_task.py \
  --model openrouter/anthropic/claude-opus-4.7 \
  --model-role player=openrouter/anthropic/claude-opus-4.7 \
  --model-role judge=openrouter/anthropic/claude-opus-4.7
```

If you want this env wired into the `mb` CLI, add an entry to
`ENVS` in [`src/manipulation_bench/cli.py`](../../src/manipulation_bench/cli.py)
— the docstring at the top of `cli.py` shows the shape.

## Five-step checklist for your own environment

1. **Subclass `Environment`** in `src/manipulation_bench/environments/your_env.py`.
   Implement the 7 abstract methods. Read [`base.py`](../../src/manipulation_bench/environments/base.py)
   first — every method has a 1-line docstring describing the contract.

2. **Register it** in `src/manipulation_bench/environments/__init__.py`
   by adding to the `ENVIRONMENTS` dict so the factory can construct
   it from scenario metadata.

3. **Write a `@task` wrapper** in `src/manipulation_bench/your_env_task.py`.
   Pick scorers (`from manipulation_bench.scorers import …`) — see
   [`examples/new_scorer/`](../new_scorer/) for writing your own.

4. **Add to the registry** in `src/manipulation_bench/_registry.py`
   so `inspect eval -T task=your_env_bench` discovers it. Optional:
   add to [`src/manipulation_bench/cli.py`](../../src/manipulation_bench/cli.py)
   `ENVS` so `mb run your_env --model …` works.

5. **Write at least one scenario JSONL** under
   `src/manipulation_bench/scenarios/`. Each line must have:
   `id`, `agents` (list with `name`/`model_role`/`system_prompt`/`position`),
   `metadata.environment.type`, and any environment-specific config in
   `metadata.environment`.

## Common contract gotchas

- `setup()` is called once at the start with the agent name list. Save
  the names; you'll need them in `get_observation()`.
- `get_observation()` is called for **each acting agent** in **each
  phase**. Return information asymmetry here (the observer agent only
  sees what they should know).
- `apply_action()` must be idempotent on bad input: return
  `ActionResult(valid=False, error=…)` rather than raising. The solver
  retries up to a limit.
- `get_game_state_for_scoring()` is the bridge to scorers — include
  every field a scorer might want, even if it feels redundant.
- ACTION-phase tools must declare every property they accept under
  `required` (a few providers including OpenAI's strict mode and
  Azure-deployed GPT-5 reject the call otherwise).
