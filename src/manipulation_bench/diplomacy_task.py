from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers import (
    agreement_compliance,
    negotiation_manipulation,
    territorial_success,
)
from manipulation_bench.mitigations._resolve import resolve_mitigations
from manipulation_bench.scorers._resolve import resolve_scorers


@task
def diplomacy_bench(
    scenarios: str = "diplomacy_7player.jsonl",
    scorers: str | list = "default",
    mitigations: str | list = "default",
) -> Task:
    """Diplomacy 7-power negotiation: private bilateral messaging + promise tracking.

    Wraps the ``diplomacy`` Python package for DATC-compliant rules. DISCUSSION
    phases expose ``send_message`` and ``make_promise`` tools (tool_choice=auto);
    ACTION phases force ``submit_orders``. Promise compliance is computed
    deterministically from tool calls — no LLM judge.

    Args:
        scenarios: JSONL filename under ``src/manipulation_bench/scenarios/``.
        scorers: scorer override. ``"default"`` runs territorial_success,
            agreement_compliance, and negotiation_manipulation. See
            :mod:`manipulation_bench.scorers._resolve`.
    """
    resolved = resolve_scorers(scorers)
    if resolved is None:
        resolved = [
            territorial_success(),
            agreement_compliance(),
            negotiation_manipulation(),
        ]
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(mitigations=resolve_mitigations(mitigations)),
        scorer=resolved,
    )
