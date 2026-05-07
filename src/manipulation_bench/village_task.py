from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers._resolve import resolve_scorers
from manipulation_bench.scorers.village import (
    exploitation_rate,
    promise_action_gap,
    village_fairness,
)


@task
def village_bench(
    scenarios: str = "village_6player.jsonl",
    scorers: str | list = "default",
) -> Task:
    """Village Commons public-goods game (6 agents): contribute / inspect / accuse.

    Each round agents privately choose how much of 20 tokens to contribute to
    a common pool (multiplied by a difficulty-dependent multiplier and split
    equally). Agents can inspect another agent's contribution, publicly pledge,
    and accuse free-riders to trigger penalty votes. All scorers are
    mathematical — no LLM judge.

    Args:
        scenarios: JSONL filename under ``src/manipulation_bench/scenarios/``.
        scorers: scorer override. ``"default"`` runs exploitation_rate,
            promise_action_gap, and village_fairness. See
            :mod:`manipulation_bench.scorers._resolve`.
    """
    resolved = resolve_scorers(scorers)
    if resolved is None:
        resolved = [
            exploitation_rate(),
            promise_action_gap(),
            village_fairness(),
        ]
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=resolved,
    )
