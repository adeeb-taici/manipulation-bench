from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers.village import (
    exploitation_rate,
    promise_action_gap,
    village_fairness,
)


@task
def village_bench(
    scenarios: str = "village_6player.jsonl",
) -> Task:
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=[
            exploitation_rate(),
            promise_action_gap(),
            village_fairness(),
        ],
    )
