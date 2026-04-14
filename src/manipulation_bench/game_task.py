from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction


@task
def werewolf_bench(
    scenarios: str = "werewolf_5player.jsonl",
) -> Task:
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=[],  # scorers added in commit 4
    )
