"""@task definitions for consensus game levels.

Currently only Level 2 (Naming Game) is implemented. Additional levels will be
added in follow-up PRs off origin/main.
"""

from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers import vocabulary_convergence
from manipulation_bench.scorers._resolve import resolve_scorers


@task
def naming_game_bench(
    scenarios: str = "naming_game.jsonl",
    scorers: str | list = "default",
) -> Task:
    """Level 2: Naming Game -- vocabulary convergence through pairwise encounters."""
    resolved = resolve_scorers(scorers)
    if resolved is None:
        resolved = [vocabulary_convergence()]
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=resolved,
    )
