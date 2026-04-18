"""Task 4 sales — principal-agent representation with a scripted buyer.

Each sample = one 5-turn conversation. System prompt holds the product
spec + frame + incentive; the scripted buyer asks 5 fixed questions one
per turn; the agent answers each turn conditioned on the growing history.
Answers are scored deterministically by ``sales_classifier``.
"""

from __future__ import annotations

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Dataset, Sample, json_dataset
from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    GenerateConfig,
    get_model,
)
from inspect_ai.solver import Generate, Solver, TaskState, solver

from manipulation_bench.scorers import sales_classifier

_SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def _record_to_sample(record: dict) -> Sample:
    """Each record = one sales conversation (scenario × frame × incentive × model).

    Record schema:
        id, system_prompt, questions [{q_id, text}], ground_truth [{...}],
        model_role, metadata (frame, incentive, difficulty, scenario_id, model, ...)
    """
    meta = dict(record.get("metadata", {}))
    meta["questions"] = record["questions"]
    meta["ground_truth"] = record["ground_truth"]
    meta["system_prompt"] = record["system_prompt"]
    meta["model_role"] = record.get("model_role")
    return Sample(
        input=record["system_prompt"],
        id=record.get("id"),
        metadata=meta,
    )


def _load(path: str) -> Dataset:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = _SCENARIOS_DIR / path
    return json_dataset(str(resolved), sample_fields=_record_to_sample)


@solver
def sales_interaction(temperature: float = 0.7, max_tokens: int = 400) -> Solver:
    """Walk through the scripted questions one by one, storing each response.

    The agent's system prompt, the 5 questions, and the model role are all on
    the sample metadata (set by ``_record_to_sample``). Responses are written
    back to ``state.metadata['responses']`` for the scorer.
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        meta = state.metadata or {}
        system_prompt: str = meta.get("system_prompt", "")
        questions: list[dict] = meta.get("questions", []) or []
        model_role: str | None = meta.get("model_role")

        model = get_model(role=model_role) if model_role else get_model()
        config = GenerateConfig(max_tokens=max_tokens, temperature=temperature)

        messages: list = [ChatMessageSystem(content=system_prompt)]
        responses: list[str] = []

        for q in questions:
            messages.append(ChatMessageUser(content=q["text"]))
            output = await model.generate(messages, config=config)
            content = output.completion or ""
            responses.append(content)
            messages.append(ChatMessageAssistant(content=content))

        # Store responses for the scorer.
        state.metadata["responses"] = responses
        # Also put transcript on state.messages so Inspect's log viewer shows it.
        state.messages = messages
        # state.output set to the last turn for consistency.
        if output is not None:
            state.output = output
        return state

    return solve


@task
def sales_bench(
    scenarios: str = "task4_sales_pilot.jsonl",
    temperature: float = 0.7,
    max_tokens: int = 400,
) -> Task:
    """Task 4 of the manipulation response surface: sales-agent representation.

    Args:
        scenarios: JSONL filename under ``src/manipulation_bench/scenarios/``.
        temperature: generation temperature for the agent (default 0.7).
        max_tokens: per-turn max tokens for the agent (default 400).
    """
    return Task(
        dataset=_load(scenarios),
        solver=sales_interaction(temperature=temperature, max_tokens=max_tokens),
        scorer=[sales_classifier()],
    )
