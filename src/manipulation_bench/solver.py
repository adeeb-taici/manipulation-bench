from __future__ import annotations

from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    GenerateConfig,
    get_model,
)
from inspect_ai.solver import Generate, Solver, TaskState, solver

from manipulation_bench.models import AgentRole, InteractionState, ScenarioConfig, Turn
from manipulation_bench.protocols import get_protocol


@solver
def multi_agent_interaction() -> Solver:
    """Orchestrate a multi-agent interaction defined by the scenario in sample metadata."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        scenario = ScenarioConfig(**state.metadata["scenario"])
        interaction = state.store_as(InteractionState)
        interaction.scenario = scenario
        interaction.agent_names = [a.name for a in scenario.agents]

        agents_by_name = {a.name: a for a in scenario.agents}
        protocol = get_protocol(scenario.protocol)
        turn_index = 0

        for round_num in range(scenario.num_rounds):
            interaction.current_round = round_num

            while True:
                speaker_name = protocol.next_speaker(interaction)
                if speaker_name is None:
                    break

                agent_config = agents_by_name[speaker_name]
                model = get_model(role=agent_config.model_role)
                messages = _build_agent_messages(
                    agent_config, interaction, round_num, scenario,
                )

                output = await model.generate(
                    messages,
                    config=GenerateConfig(max_tokens=scenario.max_tokens),
                )
                content = output.completion or ""

                turn = Turn(
                    speaker=speaker_name,
                    content=content,
                    round=round_num,
                    turn_index=turn_index,
                )
                interaction.turns = [*interaction.turns, turn]
                turn_index += 1

        # Write transcript into state.messages for Inspect's log viewer
        state.messages = _build_transcript_messages(interaction)

        return state

    return solve


def _build_agent_messages(
    agent: AgentRole,
    interaction: InteractionState,
    round_num: int,
    scenario: ScenarioConfig,
) -> list[ChatMessageSystem | ChatMessageUser | ChatMessageAssistant]:
    """Build the message list an agent sees when it's their turn to speak."""
    messages: list[ChatMessageSystem | ChatMessageUser | ChatMessageAssistant] = []

    messages.append(ChatMessageSystem(content=agent.system_prompt))

    context = f"Debate topic: {scenario.topic}"
    if agent.position:
        context += f"\nYour position: {agent.position}"
    context += f"\nRound {round_num + 1} of {scenario.num_rounds}."
    messages.append(ChatMessageUser(content=context))

    visible_turns = interaction.turns_visible_to(agent.name, scenario.visibility)
    for turn in visible_turns:
        if turn.speaker == agent.name:
            messages.append(ChatMessageAssistant(content=turn.content))
        else:
            messages.append(
                ChatMessageUser(content=f"[{turn.speaker}]: {turn.content}")
            )

    if not any(t.speaker == agent.name for t in interaction.turns):
        messages.append(ChatMessageUser(content="Present your opening argument."))
    else:
        messages.append(ChatMessageUser(content="Respond to the debate so far."))

    return messages


def _build_transcript_messages(
    interaction: InteractionState,
) -> list[ChatMessageUser | ChatMessageAssistant]:
    """Format the full transcript for Inspect's log viewer."""
    messages: list[ChatMessageUser | ChatMessageAssistant] = []
    assert interaction.scenario is not None
    messages.append(ChatMessageUser(content=f"Debate topic: {interaction.scenario.topic}"))
    for turn in interaction.turns:
        messages.append(
            ChatMessageAssistant(
                content=f"[{turn.speaker}, round {turn.round + 1}]: {turn.content}"
            )
        )
    return messages
