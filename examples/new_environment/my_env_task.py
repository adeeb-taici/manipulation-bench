"""@task wrapper for MyEnvironment.

The wrapper is what `inspect eval` and `mb run` invoke. It loads
scenarios from a JSONL, picks a solver (the unified game_solver
handles every Environment subclass), and lists scorers.

To run this example:

    inspect eval examples/new_environment/my_env_task.py \\
        -T scenarios=examples/new_environment/my_env_scenarios.jsonl \\
        --model mockllm/model \\
        --model-role player=mockllm/model \\
        --model-role judge=mockllm/model \\
        --limit 1

Adding to the mb registry (optional but nice):
    Edit src/manipulation_bench/cli.py and add to ``ENVS``:
        "my_env": EnvSpec(
            name="my_env",
            task_module="examples/new_environment/my_env_task.py",
            task_function="my_env_bench",
            default_scenario="examples/new_environment/my_env_scenarios.jsonl",
            description="Two-agent guess-my-number toy environment.",
        ),
"""

from __future__ import annotations

import sys
from pathlib import Path

# Inspect loads @task files via importlib without examples/ on sys.path.
# This is the standard pattern in experiments/ scripts that import siblings.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from inspect_ai import Task, task
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer, stderr
from inspect_ai.solver import TaskState

from examples.new_environment.my_env import MyEnvironment
from manipulation_bench.dataset import load_scenarios
from manipulation_bench.environments import ENVIRONMENTS
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.models import InteractionState

# Register MyEnvironment with the global factory. Production envs
# would do this once in src/manipulation_bench/environments/__init__.py
# instead.
ENVIRONMENTS.setdefault("my_env", MyEnvironment)


# We inline a tiny scorer here for a fully self-contained example.
# A richer reference (LLM-judge + dict-valued shape) is in
# examples/new_scorer/my_scorer.py.
@scorer(metrics=[mean(), stderr()])
def guess_accuracy() -> Scorer:
    """1.0 if the guesser hit the secret, 0.0 otherwise."""

    async def score(state: TaskState, target: Target) -> Score:
        interaction = state.store_as(InteractionState)
        gs = interaction.scenario.metadata.game_state if interaction.scenario else None
        if not gs:
            return Score(value=0.0, explanation="no game_state recorded")
        won = bool(gs.get("won"))
        return Score(
            value=1.0 if won else 0.0,
            explanation=(
                f"guess={gs.get('guess')!r} secret={gs.get('secret')!r} "
                f"({'hit' if won else 'miss'})"
            ),
            metadata=gs,
        )

    return score


_DEFAULT_SCENARIO = str(Path(__file__).resolve().parent / "my_env_scenarios.jsonl")


@task
def my_env_bench(scenarios: str = _DEFAULT_SCENARIO) -> Task:
    """Run the guess-my-number game from a scenario JSONL.

    ``scenarios`` accepts: an absolute path, a CWD-relative path, or a
    bare filename (resolved against ``src/manipulation_bench/scenarios/``).
    """
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=[guess_accuracy()],
    )
