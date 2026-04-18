"""Task 5 — Committee Evaluation with Conflict of Interest.

Multi-agent committee reviews a candidate slate. One agent has a private
conflict of interest. All scorers are mathematical.
"""

from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers.committee import (
    decision_outcome,
    discussion_polarity,
    initial_rating_bias,
    post_discussion_rating_change,
)


@task
def committee_bench(
    scenarios: str = "task5_committee_pilot.jsonl",
) -> Task:
    """Task 5 committee evaluation with conflict of interest.

    Args:
        scenarios: JSONL filename under ``src/manipulation_bench/scenarios/``.
    """
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=[
            initial_rating_bias(),
            post_discussion_rating_change(),
            discussion_polarity(),
            decision_outcome(),
        ],
    )
