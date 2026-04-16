"""@task definitions for consensus game levels 1-5."""

from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers import (
    influence_asymmetry,
    mean_opinion,
    opinion_change_rate,
    opinion_spread,
    persona_consistency,
    sycophancy_rate,
    time_to_consensus,
)


@task
def binary_coordination_bench(
    scenarios: str = "binary_coordination.jsonl",
) -> Task:
    """Level 1: Binary Coordination -- two agents pick A or B."""
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=[
            time_to_consensus(),
        ],
    )


@task
def naming_game_bench(
    scenarios: str = "naming_game.jsonl",
) -> Task:
    """Level 2: Naming Game -- vocabulary convergence through pairwise encounters."""
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=[
            time_to_consensus(),
        ],
    )


@task
def continuous_convergence_bench(
    scenarios: str = "continuous_convergence.jsonl",
) -> Task:
    """Level 3: Continuous Convergence -- numeric opinion convergence."""
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=[
            time_to_consensus(),
            opinion_change_rate(),
            mean_opinion(),
            opinion_spread(),
            sycophancy_rate(),
        ],
    )


@task
def deliberative_consensus_bench(
    scenarios: str = "deliberative_consensus.jsonl",
) -> Task:
    """Level 4: Deliberative Consensus -- jury deliberation with voting."""
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=[
            time_to_consensus(),
            opinion_change_rate(),
            mean_opinion(),
            opinion_spread(),
            influence_asymmetry(),
        ],
    )


@task
def biased_deliberation_bench(
    scenarios: str = "biased_deliberation.jsonl",
) -> Task:
    """Level 5: Biased Deliberation -- persona-driven opinion dynamics."""
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=[
            opinion_change_rate(),
            mean_opinion(),
            opinion_spread(),
            influence_asymmetry(),
            persona_consistency(),
            sycophancy_rate(),
        ],
    )
