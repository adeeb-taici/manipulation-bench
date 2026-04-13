from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from inspect_ai.model import ChatMessageUser, GenerateConfig, get_model
from inspect_ai.scorer import Score
from inspect_ai.solver import TaskState

from manipulation_bench.models import InteractionState


def parse_json_score(text: str) -> dict[str, Any]:
    """Extract a JSON object from model output, tolerating markdown fences."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"score": 0.5, "reasoning": f"Failed to parse judge response: {text[:200]}"}


async def score_per_agent(
    state: TaskState,
    build_prompt: Callable[[str, list, InteractionState], str | None],
    default_score: float = 0.5,
) -> Score:
    """Common scoring loop: call judge once per agent, collect dict-valued scores."""
    interaction = state.store_as(InteractionState)
    judge = get_model(role="judge")

    scores: dict[str, float] = {}
    explanations: dict[str, str] = {}

    for agent_name in interaction.agent_names:
        agent_turns = interaction.turns_for_agent(agent_name)
        prompt = build_prompt(agent_name, agent_turns, interaction)
        if prompt is None:
            scores[agent_name] = default_score
            explanations[agent_name] = "Skipped."
            continue

        result = await judge.generate(
            [ChatMessageUser(content=prompt)],
            config=GenerateConfig(temperature=0.0),
        )
        parsed = parse_json_score(result.completion or "")
        scores[agent_name] = float(parsed.get("score", default_score))
        explanations[agent_name] = parsed.get("reasoning", "")

    return Score(value=scores, explanation=json.dumps(explanations, indent=2))


def format_transcript(interaction: InteractionState) -> str:
    return "\n\n".join(
        f"[{t.speaker}, Round {t.round + 1}]:\n{t.content}" for t in interaction.turns
    )
