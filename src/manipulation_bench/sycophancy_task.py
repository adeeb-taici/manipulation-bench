"""Sycophancy task — single-turn response-surface Task 4.

Agent receives a system prompt containing the correct fact and (on some
conditions) framing pressure. The user turn expresses a wrong belief with
varying levels of stated investment. One response is generated. The
``sycophancy_classification`` scorer labels the response as
``corrects`` / ``hedges`` / ``accommodates`` via rule-based keyword
matching (no LLM judge for outcome extraction, per brief).
"""

from __future__ import annotations

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Dataset, Sample, json_dataset
from inspect_ai.model import ChatMessageSystem, ChatMessageUser
from inspect_ai.solver import generate

from manipulation_bench.scorers import sycophancy_classification

_SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def _record_to_sample(record: dict) -> Sample:
    """Map a sycophancy scenario record to an Inspect Sample.

    Record schema:
        id, system_prompt, user_message, correct_keywords (list), wrong_keywords (list),
        metadata (frame, incentive, difficulty, model_role, claim_id, ...)
    """
    messages = [
        ChatMessageSystem(content=record["system_prompt"]),
        ChatMessageUser(content=record["user_message"]),
    ]
    meta = dict(record.get("metadata", {}))
    meta["correct_keywords"] = record["correct_keywords"]
    meta["wrong_keywords"] = record["wrong_keywords"]
    return Sample(
        input=messages,
        target=record.get("canonical_fact", ""),
        id=record.get("id"),
        metadata=meta,
    )


def _load(path: str) -> Dataset:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = _SCENARIOS_DIR / path
    return json_dataset(str(resolved), sample_fields=_record_to_sample)


@task
def sycophancy_bench(scenarios: str = "task4_sycophancy_pilot.jsonl") -> Task:
    """Task 4 of the manipulation response surface: sycophancy."""
    return Task(
        dataset=_load(scenarios),
        solver=generate(),
        scorer=[sycophancy_classification()],
    )
