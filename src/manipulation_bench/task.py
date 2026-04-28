from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers import (
    argument_quality,
    belief_shift,
    ground_truth_persuasion,
    juror_voting,
    manipulation_detection,
)
from manipulation_bench.scorers._resolve import resolve_scorers


@task
def manipulation_bench(
    scenarios: str = "debate_2agent.jsonl",
    juror_roles: str | list[str] = "",
    scorers: str | list = "default",
) -> Task:
    if isinstance(juror_roles, list):
        juror_list = juror_roles or None
    else:
        juror_list = [r.strip() for r in juror_roles.split(",") if r.strip()] or None
    resolved = resolve_scorers(scorers)
    if resolved is None:
        resolved = [
            manipulation_detection(),
            argument_quality(),
            belief_shift(),
            juror_voting(),
            ground_truth_persuasion(juror_roles=juror_list),
        ]
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=resolved,
    )
