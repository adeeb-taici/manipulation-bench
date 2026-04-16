"""Bargaining task — resource-split negotiation with private valuations.

Measures whether agents misrepresent private valuations to capture a larger
share of a divisible resource. The expected penalty for misrepresentation is
varied across scenarios to produce a dose-response curve.
"""

from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers import bargaining_manipulation


@task
def bargaining_bench(scenarios: str = "bargaining.jsonl") -> Task:
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=[bargaining_manipulation()],
    )
