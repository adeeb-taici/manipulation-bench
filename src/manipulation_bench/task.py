from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.scorers import (
    argument_quality,
    belief_shift,
    ground_truth_persuasion,
    juror_voting,
    manipulation_detection,
)
from manipulation_bench.solver import multi_agent_interaction


@task
def manipulation_bench(
    scenarios: str = "debate_2agent.jsonl",
) -> Task:
    return Task(
        dataset=load_scenarios(scenarios),
        solver=multi_agent_interaction(),
        scorer=[
            manipulation_detection(),
            argument_quality(),
            belief_shift(),
            juror_voting(),
            ground_truth_persuasion(),
        ],
    )
