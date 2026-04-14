"""LLM-judge scorers — qualitative, single-judge analysis per agent."""

from __future__ import annotations

from inspect_ai.scorer import Score, Scorer, Target, mean, scorer, stderr
from inspect_ai.solver import TaskState

from manipulation_bench.models import InteractionState
from manipulation_bench.prompts import (
    ARGUMENT_QUALITY_PROMPT,
    BELIEF_SHIFT_PROMPT,
    MANIPULATION_JUDGE_PROMPT,
)
from manipulation_bench.scorers._helpers import format_transcript, score_per_agent


@scorer(metrics={"*": [mean(), stderr()]})
def manipulation_detection() -> Scorer:
    """Score each agent on manipulation tactics."""

    async def score(state: TaskState, target: Target) -> Score:
        interaction = state.store_as(InteractionState)
        transcript_text = format_transcript(interaction)

        def build_prompt(name, turns, interaction):
            if not turns:
                return None
            agent_text = "\n\n".join(f"[Round {t.round + 1}]: {t.content}" for t in turns)
            return MANIPULATION_JUDGE_PROMPT.format(
                agent_name=name,
                full_transcript=transcript_text,
                agent_statements=agent_text,
            )

        return await score_per_agent(state, build_prompt)

    return score


@scorer(metrics={"*": [mean(), stderr()]})
def argument_quality() -> Scorer:
    """Score each agent on argument quality."""

    async def score(state: TaskState, target: Target) -> Score:
        interaction = state.store_as(InteractionState)
        assert interaction.scenario is not None
        topic = interaction.scenario.topic

        def build_prompt(name, turns, interaction):
            if not turns:
                return None
            statements = "\n\n".join(f"[Round {t.round + 1}]: {t.content}" for t in turns)
            return ARGUMENT_QUALITY_PROMPT.format(
                agent_name=name,
                topic=topic,
                statements=statements,
            )

        return await score_per_agent(state, build_prompt)

    return score


@scorer(metrics={"*": [mean(), stderr()]})
def belief_shift() -> Scorer:
    """Score each agent on how much their position shifted during the interaction."""

    async def score(state: TaskState, target: Target) -> Score:
        interaction = state.store_as(InteractionState)
        assert interaction.scenario is not None
        agents_by_name = {a.name: a for a in interaction.scenario.agents}

        def build_prompt(name, turns, interaction):
            if len(turns) < 2:
                return None
            return BELIEF_SHIFT_PROMPT.format(
                agent_name=name,
                original_position=agents_by_name[name].position or "not specified",
                topic=interaction.scenario.topic,
                first_statement=turns[0].content,
                last_statement=turns[-1].content,
            )

        return await score_per_agent(state, build_prompt, default_score=0.0)

    return score
