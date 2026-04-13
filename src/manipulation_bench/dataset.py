from __future__ import annotations

from pathlib import Path
from typing import Any

from inspect_ai.dataset import Dataset, Sample, json_dataset

_SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def record_to_sample(record: dict[str, Any]) -> Sample:
    """Map a scenario JSONL record to an Inspect Sample.

    The full scenario config goes into metadata. The solver reads it from there
    and uses it to configure agents, protocol, and interaction parameters.
    Sample.input is just the topic (used as the seed for the interaction).
    """
    return Sample(
        input=record["topic"],
        target=record.get("judge_prompt", ""),
        id=record.get("id"),
        metadata={"scenario": record},
    )


def load_scenarios(path: str) -> Dataset:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = _SCENARIOS_DIR / path
    return json_dataset(str(resolved), sample_fields=record_to_sample)
