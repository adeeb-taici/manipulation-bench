from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers import (
    agreement_compliance,
    negotiation_manipulation,
    territorial_success,
)
from manipulation_bench.scorers._resolve import resolve_scorers


@task
def diplomacy_bench(
    scenarios: str = "diplomacy_7player.jsonl",
    scorers: str | list = "default",
) -> Task:
    resolved = resolve_scorers(scorers)
    if resolved is None:
        resolved = [
            territorial_success(),
            agreement_compliance(),
            negotiation_manipulation(),
        ]
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=resolved,
    )
