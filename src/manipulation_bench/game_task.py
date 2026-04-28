from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers import (
    deception_success,
    game_manipulation_detection,
    game_win_rate,
    vote_accuracy,
)
from manipulation_bench.scorers._resolve import resolve_scorers


@task
def werewolf_bench(
    scenarios: str = "werewolf_5player.jsonl",
    scorers: str | list = "default",
) -> Task:
    resolved = resolve_scorers(scorers)
    if resolved is None:
        resolved = [
            game_win_rate(),
            vote_accuracy(),
            deception_success(),
            game_manipulation_detection(),
        ]
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=resolved,
    )
