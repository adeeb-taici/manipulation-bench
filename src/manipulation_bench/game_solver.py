"""Game-aware solver that interleaves discussion and action phases."""
from __future__ import annotations

from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageUser,
    GenerateConfig,
    get_model,
)
from inspect_ai.solver import Generate, Solver, TaskState, solver

from manipulation_bench.environments import PhaseType, create_environment
from manipulation_bench.models import AgentRole, InteractionState, ScenarioConfig, Turn


@solver
def game_interaction(max_action_retries: int = 2) -> Solver:
    """Orchestrate a game environment interaction."""

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        scenario = ScenarioConfig(**state.metadata["scenario"])
        interaction = state.store_as(InteractionState)
        interaction.scenario = scenario
        interaction.agent_names = [a.name for a in scenario.agents]

        env_config = scenario.metadata.get("environment", {})
        env = create_environment(env_config)
        env.setup(interaction.agent_names)

        agents_by_name = {a.name: a for a in scenario.agents}
        turn_index = 0

        while not env.is_terminal():
            phase = env.get_current_phase()

            for actor_name in phase.acting_agents:
                if env.is_terminal():
                    break

                agent_config = agents_by_name[actor_name]
                model = get_model(role=agent_config.model_role)
                obs = env.get_observation(actor_name)
                messages = _build_game_messages(agent_config, obs, interaction, scenario)

                if phase.phase_type == PhaseType.DISCUSSION:
                    output = await model.generate(
                        messages,
                        config=GenerateConfig(max_tokens=scenario.max_tokens),
                    )
                    content = output.completion or ""
                    env.process_discussion(actor_name, content, phase)
                    turn = Turn(
                        speaker=actor_name, content=content,
                        round=phase.round, turn_index=turn_index,
                        metadata={"phase": phase.name, "phase_type": "discussion"},
                    )
                    interaction.turns = [*interaction.turns, turn]
                    turn_index += 1

                elif phase.phase_type == PhaseType.ACTION:
                    action = None
                    raw_content = ""
                    for attempt in range(max_action_retries + 1):
                        output = await model.generate(
                            messages,
                            config=GenerateConfig(max_tokens=scenario.max_tokens),
                        )
                        raw_content = output.completion or ""
                        try:
                            action = env.parse_action(actor_name, raw_content)
                            break
                        except ValueError as e:
                            if attempt < max_action_retries:
                                messages.append(ChatMessageAssistant(content=raw_content))
                                messages.append(ChatMessageUser(
                                    content=f"Invalid action: {e}. Try again."
                                ))
                            else:
                                action = (
                                    obs.valid_actions[0] if obs.valid_actions else "pass:none"
                                )

                    result = env.apply_action(actor_name, action)
                    turn = Turn(
                        speaker=actor_name, content=raw_content,
                        round=phase.round, turn_index=turn_index,
                        metadata={
                            "phase": phase.name, "phase_type": "action",
                            "action": action, "action_valid": result.valid,
                            "action_narrative": result.narrative,
                        },
                    )
                    interaction.turns = [*interaction.turns, turn]
                    turn_index += 1

            env.advance_phase()

        # Store game outcome for scorers
        outcome = env.get_outcome()
        game_state = env.get_game_state_for_scoring()
        interaction.scenario = ScenarioConfig(
            **interaction.scenario.model_dump()
            | {"metadata": {
                **interaction.scenario.metadata,
                "game_outcome": outcome.model_dump(),
                "game_state": game_state,
            }}
        )

        state.messages = _build_game_transcript(interaction)
        return state

    return solve


def _build_game_messages(
    agent: AgentRole,
    obs: "Observation",
    interaction: InteractionState,
    scenario: ScenarioConfig,
) -> list[ChatMessageSystem | ChatMessageUser | ChatMessageAssistant]:
    """Build the message list for an agent in a game context."""
    from manipulation_bench.environments import Observation  # noqa: F811

    messages: list[ChatMessageSystem | ChatMessageUser | ChatMessageAssistant] = []

    messages.append(ChatMessageSystem(content=agent.system_prompt))

    # Game context
    context_parts = [obs.public_info]
    if obs.private_info:
        context_parts.append(f"[PRIVATE] {obs.private_info}")
    if obs.history_summary:
        context_parts.append(f"Game history:\n{obs.history_summary}")
    messages.append(ChatMessageUser(content="\n\n".join(context_parts)))

    # Prior discussion turns (visible per topology)
    visible_turns = interaction.turns_visible_to(agent.name, scenario.visibility)
    discussion_turns = [
        t for t in visible_turns if t.metadata.get("phase_type") == "discussion"
    ]
    for turn in discussion_turns:
        if turn.speaker == agent.name:
            messages.append(ChatMessageAssistant(content=turn.content))
        else:
            messages.append(ChatMessageUser(content=f"[{turn.speaker}]: {turn.content}"))

    # Action events (narrated)
    action_turns = [
        t for t in visible_turns
        if t.metadata.get("phase_type") == "action" and t.metadata.get("action_narrative")
    ]
    if action_turns:
        events = "\n".join(t.metadata["action_narrative"] for t in action_turns)
        messages.append(ChatMessageUser(content=f"[Game Events]:\n{events}"))

    # Phase-specific prompt
    if obs.phase.phase_type == PhaseType.DISCUSSION:
        messages.append(ChatMessageUser(content="Discuss with the other players."))
    elif obs.phase.phase_type == PhaseType.ACTION:
        messages.append(ChatMessageUser(
            content=f"{obs.action_prompt}\nValid actions: {', '.join(obs.valid_actions)}"
        ))

    return messages


def _build_game_transcript(
    interaction: InteractionState,
) -> list[ChatMessageUser | ChatMessageAssistant]:
    """Format game transcript for Inspect's log viewer."""
    messages: list[ChatMessageUser | ChatMessageAssistant] = []
    assert interaction.scenario is not None
    messages.append(ChatMessageUser(content=f"Game: {interaction.scenario.topic}"))

    for turn in interaction.turns:
        phase = turn.metadata.get("phase", "")
        phase_type = turn.metadata.get("phase_type", "")
        if phase_type == "action":
            action = turn.metadata.get("action", "")
            narrative = turn.metadata.get("action_narrative", "")
            label = f"[{turn.speaker}, {phase}, action={action}]"
            content = f"{label}: {narrative}" if narrative else f"{label}: {turn.content}"
        else:
            content = f"[{turn.speaker}, {phase}]: {turn.content}"
        messages.append(ChatMessageAssistant(content=content))

    return messages
