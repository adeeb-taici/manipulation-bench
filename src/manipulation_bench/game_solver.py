"""Unified solver that interleaves discussion and action phases using tool calls."""

from __future__ import annotations

from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
    get_model,
)
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import ToolCallError, ToolFunction

from manipulation_bench.environments import Observation, PhaseType, create_environment
from manipulation_bench.mitigations.base import Mitigation
from manipulation_bench.models import AgentRole, InteractionState, ScenarioConfig, Turn


@solver
def game_interaction(
    max_action_retries: int = 2, mitigations: list[Mitigation] | None = None
) -> Solver:
    """Orchestrate a game environment interaction using tool calls.

    ``mitigations`` (optional) are defenses applied at three points each turn:
    ``transform_agent`` (rewrite the role before the loop), ``transform_messages``
    (rewrite the model input), and ``transform_response`` (flag/redact/rewrite the
    model output before it is delivered to other agents). See
    :mod:`manipulation_bench.mitigations`. A ``transform_response`` that drops
    ACTION tool calls counts as a missing-tool retry (handled below).
    """
    mits: list[Mitigation] = mitigations or []

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        scenario = ScenarioConfig(**state.metadata["scenario"])
        interaction = state.store_as(InteractionState)
        interaction.scenario = scenario
        interaction.agent_names = [a.name for a in scenario.agents]

        env_config = dict(scenario.metadata.environment)
        # Inject scenario-level context for environments that need it
        env_config.setdefault("topic", scenario.topic)
        env_config.setdefault("agent_positions", {a.name: a.position for a in scenario.agents})
        # Backward compat: debate scenarios store these at the top level
        env_config.setdefault("num_rounds", scenario.num_rounds)
        env_config.setdefault("visibility", scenario.visibility)
        env = create_environment(env_config)
        env.setup(interaction.agent_names)

        # Apply mitigation agent-rewrites (e.g. skeptical-framing suffix on
        # protected agents) once, before the interaction loop.
        agents_by_name = {}
        for a in scenario.agents:
            transformed = a
            for mit in mits:
                transformed = mit.transform_agent(transformed, scenario)
            agents_by_name[a.name] = transformed
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
                for mit in mits:
                    messages = await mit.transform_messages(agent_config, messages, scenario)

                tools = env.get_tools(actor_name, phase)
                tool_choice = env.get_tool_choice(phase) if tools else None

                # Per-agent tool_choice override for providers that reject the
                # default ``tool_choice="any"``. Set in the scenario's
                # ``agents[i].metadata.tool_choice_strategy``:
                #
                #   "specific_first_tool" — substitute
                #     ``ToolFunction(name=tools[0].name)``. Equivalent to "any"
                #     for single-tool ACTION phases; bypasses providers that
                #     reject "required" but accept named-tool selection.
                #
                #   "auto" — substitute "auto". Required for reasoning models
                #     like DeepSeek V4 Pro that only accept tool_choice in
                #     {"none", "auto"}. The existing max_action_retries budget
                #     covers the case where the model declines to call a tool
                #     on the first attempt.
                #
                # See docs/provider_quirks.md for the catalog of provider
                # constraints this addresses.
                strategy = agent_config.metadata.get("tool_choice_strategy")
                if tool_choice == "any" and tools and strategy:
                    if strategy == "specific_first_tool":
                        tool_choice = ToolFunction(name=tools[0].name)
                    elif strategy == "auto":
                        tool_choice = "auto"

                # Per-agent max_tokens override (e.g., DeepSeek-chat 64K context cap)
                agent_max_tokens = agent_config.metadata.get("max_tokens", scenario.max_tokens)

                if phase.phase_type == PhaseType.DISCUSSION:
                    output = await model.generate(
                        messages,
                        tools=tools,
                        tool_choice=tool_choice,
                        config=GenerateConfig(max_tokens=agent_max_tokens),
                    )
                    original_content = output.completion or ""
                    for mit in mits:
                        output = await mit.transform_response(
                            agent_config, messages, output, scenario
                        )
                    content = output.completion or ""

                    # Process tool calls (e.g., Diplomacy message routing)
                    if output.message.tool_calls:
                        env.process_tool_calls(actor_name, output.message.tool_calls, phase)

                    # Non-tool processing (e.g., Debate tracks first-speaker).
                    # Feed the *original* (pre-mitigation) text so text-based
                    # scorers (e.g. committee discussion_polarity) measure what
                    # the agent actually said, not a critic flag/redaction. Other
                    # agents still receive ``content`` (delivered text) via the
                    # transcript built from ``Turn.content``.
                    env.process_discussion(actor_name, original_content, phase)

                    turn_meta = {
                        "phase": phase.name,
                        "phase_type": "discussion",
                        "mitigations_applied": [m.name for m in mits],
                    }
                    if content != original_content:
                        turn_meta["original_content"] = original_content
                    turn = Turn(
                        speaker=actor_name,
                        content=content,
                        round=phase.round,
                        turn_index=turn_index,
                        metadata=turn_meta,
                    )
                    interaction.turns = [*interaction.turns, turn]
                    turn_index += 1

                elif phase.phase_type == PhaseType.ACTION:
                    action = None
                    raw_content = ""
                    original_raw = ""
                    result = None
                    for attempt in range(max_action_retries + 1):
                        output = await model.generate(
                            messages,
                            tools=tools,
                            tool_choice=tool_choice,
                            config=GenerateConfig(max_tokens=agent_max_tokens),
                        )
                        original_raw = output.completion or ""
                        # Mitigations run inside the retry loop so a critic that
                        # rewrites/redacts a turn still gets parsed by
                        # ``tool_calls_to_action`` below.
                        for mit in mits:
                            output = await mit.transform_response(
                                agent_config, messages, output, scenario
                            )
                        raw_content = output.completion or ""

                        if not output.message.tool_calls:
                            # Model didn't call a tool (shouldn't happen with
                            # tool_choice="any", but handle gracefully)
                            if attempt < max_action_retries:
                                messages.append(output.message)
                                messages.append(
                                    ChatMessageUser(
                                        content="You must use a tool to submit your action."
                                    )
                                )
                                continue
                            action = obs.valid_actions[0] if obs.valid_actions else "pass:none"
                        else:
                            try:
                                action = env.tool_calls_to_action(
                                    actor_name, output.message.tool_calls
                                )
                            except ValueError as e:
                                if attempt < max_action_retries:
                                    _append_tool_errors(messages, output.message, str(e))
                                    continue
                                action = obs.valid_actions[0] if obs.valid_actions else "pass:none"

                        result = env.apply_action(actor_name, action)
                        if result.valid or attempt == max_action_retries:
                            break
                        _append_tool_errors(messages, output.message, result.error)

                    turn_meta = {
                        "phase": phase.name,
                        "phase_type": "action",
                        "action": action,
                        "action_valid": result.valid,
                        "action_narrative": result.narrative,
                        "mitigations_applied": [m.name for m in mits],
                    }
                    if raw_content != original_raw:
                        turn_meta["original_content"] = original_raw
                    turn = Turn(
                        speaker=actor_name,
                        content=raw_content,
                        round=phase.round,
                        turn_index=turn_index,
                        metadata=turn_meta,
                    )
                    interaction.turns = [*interaction.turns, turn]
                    turn_index += 1

            env.advance_phase()

        # Store game outcome for scorers
        outcome = env.get_outcome()
        game_state = env.get_game_state_for_scoring()
        new_meta = interaction.scenario.metadata.model_copy(
            update={"game_outcome": outcome.model_dump(), "game_state": game_state}
        )
        interaction.scenario = interaction.scenario.model_copy(update={"metadata": new_meta})

        state.messages = _build_game_transcript(interaction)
        return state

    return solve


def _append_tool_errors(
    messages: list, output_message: ChatMessageAssistant, error_text: str
) -> None:
    """Append assistant message + tool error responses for retry."""
    messages.append(output_message)
    for tc in output_message.tool_calls:
        messages.append(
            ChatMessageTool(
                content=error_text,
                tool_call_id=tc.id,
                function=tc.function,
                error=ToolCallError(type="unknown", message=error_text),
            )
        )


def _build_game_messages(
    agent: AgentRole,
    obs: Observation,
    interaction: InteractionState,
    scenario: ScenarioConfig,
) -> list[ChatMessageSystem | ChatMessageUser | ChatMessageAssistant]:
    """Build the message list for an agent in a game context.

    If ``agent.metadata['input_char_budget']`` is set, the visible-turn
    portion of the context is truncated (oldest turns dropped first) so the
    total character count of message contents stays under that budget. Anchor
    messages (system prompt, prior_context, current game-state context, the
    final phase-specific prompt) are always retained. See paper PREREG
    amendment Task 3 A2 (Village) — added because cumulative Village
    transcripts can exceed bystander context windows on long games with
    verbose framing.
    """
    messages: list[ChatMessageSystem | ChatMessageUser | ChatMessageAssistant] = []

    messages.append(ChatMessageSystem(content=agent.system_prompt))

    if agent.prior_context:
        messages.append(ChatMessageUser(content=agent.prior_context))

    # Game context
    context_parts = [obs.public_info]
    if obs.private_info:
        context_parts.append(f"[PRIVATE] {obs.private_info}")
    if obs.history_summary:
        context_parts.append(f"Game history:\n{obs.history_summary}")
    messages.append(ChatMessageUser(content="\n\n".join(context_parts)))

    # Index marker: messages 0..n_anchors_pre−1 are pre-history anchors
    n_anchors_pre = len(messages)

    # Prior turns (visible per topology) — single pass
    visible_turns = interaction.turns_visible_to(agent.name, scenario.visibility)
    action_narratives: list[str] = []
    for turn in visible_turns:
        phase_type = turn.metadata.get("phase_type")
        if phase_type == "discussion":
            if turn.speaker == agent.name:
                messages.append(ChatMessageAssistant(content=turn.content))
            else:
                messages.append(ChatMessageUser(content=f"[{turn.speaker}]: {turn.content}"))
        elif phase_type == "action" and turn.metadata.get("action_narrative"):
            action_narratives.append(turn.metadata["action_narrative"])
    if action_narratives:
        events = "\n".join(action_narratives)
        messages.append(ChatMessageUser(content=f"[Game Events]:\n{events}"))

    # Phase-specific prompt
    if obs.phase.phase_type == PhaseType.DISCUSSION:
        prompt = obs.engagement_prompt or "Discuss with the other players."
        messages.append(ChatMessageUser(content=prompt))
    elif obs.phase.phase_type == PhaseType.ACTION:
        if obs.valid_actions:
            va_preview = ", ".join(obs.valid_actions[:30])
            suffix = (
                f"\n... and {len(obs.valid_actions) - 30} more."
                if len(obs.valid_actions) > 30
                else ""
            )
            messages.append(
                ChatMessageUser(
                    content=f"{obs.action_prompt}\nValid options include: {va_preview}{suffix}"
                )
            )
        elif obs.action_prompt:
            messages.append(ChatMessageUser(content=obs.action_prompt))
        elif obs.engagement_prompt:
            # Fall back to engagement_prompt so the conversation doesn't end on
            # an assistant message (Azure-routed Claude rejects this with
            # "This model does not support assistant message prefill"). Village
            # sets engagement for all phases; other envs set action_prompt.
            messages.append(ChatMessageUser(content=obs.engagement_prompt))

    # Per-agent input budget — drop oldest visible-turn messages if total
    # content size exceeds budget. Anchors (pre-history + final phase prompt)
    # are always kept.
    char_budget = agent.metadata.get("input_char_budget")
    if char_budget is not None:
        _truncate_to_char_budget(messages, char_budget, n_anchors_pre, n_anchors_tail=1)

    return messages


def _truncate_to_char_budget(
    messages: list[ChatMessageSystem | ChatMessageUser | ChatMessageAssistant],
    char_budget: int,
    n_anchors_pre: int,
    n_anchors_tail: int,
) -> None:
    """Drop oldest messages between the pre-anchors and tail-anchor regions
    until total content character count is under ``char_budget``. Mutates
    ``messages`` in place. If even the anchors alone exceed the budget,
    no truncation happens (caller should set a budget that's larger than
    fixed prompts).
    """

    def total_chars() -> int:
        return sum(len(m.text or "") for m in messages)

    if total_chars() <= char_budget:
        return

    # Index of first droppable message and last droppable message (exclusive)
    first = n_anchors_pre
    last = len(messages) - n_anchors_tail
    while total_chars() > char_budget and first < last:
        del messages[first]
        last -= 1


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
