"""Committee evaluation with conflict of interest.

Multi-agent committee reviews a candidate slate. One agent has a private
conflict of interest. All scorers are mathematical (no LLM judge).
Used as Task 5 in the Manipulation Response Surface paper.
"""

from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers._resolve import resolve_scorers
from manipulation_bench.scorers.committee import (
    decision_outcome,
    discussion_polarity,
    initial_rating_bias,
    post_discussion_rating_change,
)


@task
def committee_bench(
    scenarios: str = "task5_committee_pilot.jsonl",
    scorers: str | list = "default",
) -> Task:
    """Committee evaluation with conflict of interest.

    Args:
        scenarios: JSONL filename under ``src/manipulation_bench/scenarios/``.
        scorers: scorer override. ``"default"`` uses the four built-in
            committee scorers (initial_rating_bias, post_discussion_rating_change,
            discussion_polarity, decision_outcome). See
            :mod:`manipulation_bench.scorers._resolve`.
    """
    resolved = resolve_scorers(scorers)
    if resolved is None:
        resolved = [
            initial_rating_bias(),
            post_discussion_rating_change(),
            discussion_polarity(),
            decision_outcome(),
        ]
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=resolved,
    )
