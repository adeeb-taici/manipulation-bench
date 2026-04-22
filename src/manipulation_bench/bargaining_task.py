"""Bargaining task — resource-split negotiation with private valuations.

Measures whether agents misrepresent private valuations to capture a larger
share of a divisible resource. The expected penalty for misrepresentation is
varied across scenarios to produce a dose-response curve.
"""

from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers import bargaining_commit, bargaining_manipulation


@task
def bargaining_bench(scenarios: str = "bargaining.jsonl") -> Task:
    """Legacy bargaining task — LLM-judge extracts stated valuation from free text.

    Kept for reproducibility of FINDINGS §9–11, whose scenarios predate the
    structured-commit environment. New experiments should use
    ``bargaining_commit_bench``.
    """
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=[bargaining_manipulation()],
    )


@task
def bargaining_commit_bench(
    scenarios: str = "task1_bargaining.jsonl",
    max_action_retries: int = 2,
) -> Task:
    """Bargaining with a structured ``commit_valuation`` ACTION phase.

    Requires scenarios built with ``metadata.environment.type = 'bargaining'``
    so the :class:`BargainingEnvironment` runs and emits committed valuations
    into ``game_state_for_scoring``. Outcome is computed deterministically
    from the tool call — no LLM judge for outcome extraction.

    Args:
        scenarios: JSONL filename under ``src/manipulation_bench/scenarios/``.
        max_action_retries: retry budget for ACTION-phase tool calls when a
            model returns empty content or a malformed tool call. Default 2
            (up to 3 attempts total). Bump for providers that intermittently
            drop tool calls under reasoning (e.g. DeepSeek-v3.2 with reasoning
            enabled, observed empirically in smoke diagnostics).
    """
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(max_action_retries=max_action_retries),
        scorer=[bargaining_commit()],
    )
