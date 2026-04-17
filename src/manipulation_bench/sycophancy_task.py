"""Sycophancy task — single-turn response-surface Task 4.

Agent receives a system prompt containing the correct fact and (on some
conditions) framing pressure. The user turn expresses a wrong belief with
varying levels of stated investment. One response is generated and graded
by a 3-model LLM panel (``sycophancy_panel``, PREREG §8.4 / §7.1).
"""

from __future__ import annotations

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Dataset, Sample, json_dataset
from inspect_ai.model import ChatMessageSystem, ChatMessageUser
from inspect_ai.solver import generate

from manipulation_bench.scorers import sycophancy_panel

_SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def _record_to_sample(record: dict) -> Sample:
    """Map a sycophancy scenario record to an Inspect Sample.

    Record schema:
        id, system_prompt, user_message, canonical_fact,
        metadata (frame, incentive, difficulty, model_role, claim_id, ...)
    """
    messages = [
        ChatMessageSystem(content=record["system_prompt"]),
        ChatMessageUser(content=record["user_message"]),
    ]
    return Sample(
        input=messages,
        target=record.get("canonical_fact", ""),
        id=record.get("id"),
        metadata=dict(record.get("metadata", {})),
    )


def _load(path: str) -> Dataset:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = _SCENARIOS_DIR / path
    return json_dataset(str(resolved), sample_fields=_record_to_sample)


@task
def sycophancy_bench(
    scenarios: str = "task4_sycophancy_pilot.jsonl",
    grader_roles: list[str] | None = None,
) -> Task:
    """Task 4 of the manipulation response surface: sycophancy.

    Args:
        scenarios: JSONL filename under ``src/manipulation_bench/scenarios/``.
        grader_roles: list of Inspect model-role names for the grader panel.
            Default (via ``sycophancy_panel``) is the 3-grader panel in
            PREREG §7.1: ``grader_haiku``, ``grader_gpt5_mini``,
            ``grader_gemini_flash``. Bind these with ``--model-role`` on the
            eval command line.
    """
    return Task(
        dataset=_load(scenarios),
        solver=generate(),
        scorer=[sycophancy_panel(grader_roles=grader_roles)],
    )
