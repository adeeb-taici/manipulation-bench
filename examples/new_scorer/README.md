# Adding a new scorer

A scorer is an `inspect_ai.scorer.Scorer` that reads `TaskState` and
returns a numeric or dict-valued `Score`. This directory shows the
two most common shapes in a single file: a deterministic
mathematical scorer and an LLM-judge scorer.

## Files

- [`my_scorer.py`](my_scorer.py) — two scorers, ~100 LOC total.
  - `guess_accuracy()` — mathematical, no LLM call. Reads game state
    from `InteractionState.instance` and returns 1.0/0.0.
  - `response_clarity()` — LLM-judge, dict-valued per agent.

## Use it

Two ways to wire a custom scorer in. First, hardcoded in a task file:

```python
# In your task file, import and add to the scorer list:
from examples.new_scorer.my_scorer import guess_accuracy, response_clarity

@task
def my_task() -> Task:
    return Task(
        ...,
        scorer=[guess_accuracy(), response_clarity()],
    )
```

Second, pluggable via the `-T scorers=...` flag (no fork needed):

```bash
mb run debate --model openrouter/... \
  -T scorers=examples.new_scorer.my_scorer.guess_accuracy
```

Bare names (e.g. `manipulation_detection`) hit the built-in `manipulation_bench.scorers` registry; dotted paths are imported. Comma-separated lists work. The resolver lives in [`src/manipulation_bench/scorers/_resolve.py`](../../src/manipulation_bench/scorers/_resolve.py).

## Three-step checklist for your own scorer

1. **Pick a flavor**:
   - **Mathematical**: read `state.store_as(InteractionState)` or your
     environment's `get_game_state_for_scoring()`. Return a `Score`.
     Add `@scorer(metrics=[mean(), stderr()])` for a single value or
     `@scorer(metrics={"*": [mean(), stderr()]})` for a dict-valued
     score (Inspect auto-creates per-key metrics).
   - **LLM-judge**: call `get_model(role="judge").generate([…])` per
     agent or per scenario. Parse the output defensively — judges
     can return malformed text.
   - **Multi-juror**: like LLM-judge but with N independent calls and
     a Bernoulli rate. See `src/manipulation_bench/scorers/voting.py`.

2. **File location**:
   - One scorer that's tightly coupled to a specific environment goes
     in `src/manipulation_bench/scorers/<env_name>.py`.
   - A general-purpose scorer goes in `judges.py` / `voting.py` /
     `grounded.py` based on flavor.
   - Standalone "I'm sharing this with collaborators" scorers can
     live in their own file like this example.

3. **Register**:
   - Add the import to `src/manipulation_bench/scorers/__init__.py`
     and to `__all__`.
   - Either add to the relevant task file's `scorer=[…]` list, or
     pass via `-T scorers=…` at eval time (see "Use it" above).

## Common gotchas

- **Dict-valued scores aggregate per key**: if scenarios have
  different agent names, Inspect groups per key across samples that
  share that key. This is good for cross-scenario aggregation.
- **`Score(value=None)` is acceptable**: ground-truth scorers return
  `value=None` when ground truth isn't set on the scenario. They
  don't error.
- **Judge model defaults**: `get_model(role="judge")` falls back to
  the eval's primary model if `--model-role judge=…` isn't bound.
  Document this if your scorer is sensitive to judge identity.
- **`StoreModel` access returns copies**: `state.turns.append(...)`
  silently drops the change. Use `state.turns = [*state.turns, x]`
  if you write back state. (You usually don't from a scorer.)
