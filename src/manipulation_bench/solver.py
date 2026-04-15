"""Unified solver with parallel execution and infrastructure integration.

Enhanced version of the original ``game_solver`` that adds:

* Parallel agent execution via ``collect()`` when ``phase.parallel`` is True
* Network-aware message routing from ``scenario.topology``
* Persona injection into system prompts via ``PersonaCard.prompt_block()``
* Post-round hooks: ``env.update_network()``, network snapshotting
* Opinion/stance tracking after each agent response
* Optional ``ConversationStyle``, ``ContextStrategy``, and ``PlatformBridge``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from inspect_ai.model import (
    ChatMessageAssistant,
    ChatMessageSystem,
    ChatMessageTool,
    ChatMessageUser,
    GenerateConfig,
    get_model,
)
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import ToolCallError
from inspect_ai.util import collect

from manipulation_bench.agents import PersonaCard
from manipulation_bench.environments import PhaseType, create_environment
from manipulation_bench.models import (
    AgentRole,
    AgentSnapshot,
    InteractionState,
    NetworkSnapshot,
    ScenarioConfig,
    Turn,
)
from manipulation_bench.network import TOPOLOGIES, Network, broadcast

if TYPE_CHECKING:
    from manipulation_bench.environments.base import Observation, Phase
    from manipulation_bench.protocols import ContextStrategy, ConversationStyle, PlatformBridge


@solver
def game_interaction(
    max_action_retries: int = 2,
    conversation_style: ConversationStyle | None = None,
    context_strategy: ContextStrategy | None = None,
    bridge: PlatformBridge | None = None,
) -> Solver:
    """Orchestrate a game environment interaction using tool calls.

    Extends the original solver with parallel execution and new infrastructure:

    * *conversation_style* -- optional pacing / social-norm constraints
    * *context_strategy* -- optional memory / history management
    * *bridge* -- optional platform integration (e.g. Discord, console)

    When a phase has ``parallel=True``, all acting agents run concurrently
    via ``collect()``.  Otherwise they execute sequentially (original behavior).
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        scenario = ScenarioConfig(**state.metadata["scenario"])
        interaction = state.store_as(InteractionState)
        interaction.scenario = scenario
        interaction.agent_names = [a.name for a in scenario.agents]

        # ── Build environment ────────────────────────────────────────
        env_config = dict(scenario.metadata.environment)
        env_config.setdefault("topic", scenario.topic)
        env_config.setdefault(
            "agent_positions", {a.name: a.position for a in scenario.agents}
        )
        env_config.setdefault("num_rounds", scenario.num_rounds)
        env_config.setdefault("visibility", scenario.visibility)
        env = create_environment(env_config)

        # ── Build network from topology ──────────────────────────────
        personas = _build_personas(scenario.agents)
        topo_name = scenario.topology
        factory = TOPOLOGIES.get(topo_name, broadcast)
        network = factory(personas)

        # Let environment add its own channels
        env.setup_channels(network)

        # Pass network to environment setup
        env.setup(interaction.agent_names, network=network)

        # ── Initialize agent snapshots ───────────────────────────────
        agent_states: dict[str, AgentSnapshot] = {
            a.name: AgentSnapshot() for a in scenario.agents
        }
        interaction.agent_states = agent_states

        agents_by_name = {a.name: a for a in scenario.agents}
        turn_index = 0

        # ── Setup bridge if present ──────────────────────────────────
        if bridge:
            await bridge.setup(
                {ch_id: ch.name for ch_id, ch in network.channels.items()}
            )

        try:
            while not env.is_terminal():
                phase = env.get_current_phase()

                if phase.parallel:
                    # Parallel execution: run all acting agents concurrently
                    coros = [
                        _run_single_agent(
                            actor_name=actor_name,
                            phase=phase,
                            env=env,
                            agent_config=agents_by_name[actor_name],
                            interaction=interaction,
                            scenario=scenario,
                            network=network,
                            max_action_retries=max_action_retries,
                            conversation_style=conversation_style,
                            context_strategy=context_strategy,
                        )
                        for actor_name in phase.acting_agents
                    ]
                    results = await collect(*coros)
                    for turns in results:
                        for turn in turns:
                            turn = turn.model_copy(
                                update={"turn_index": turn_index}
                            )
                            interaction.turns = [*interaction.turns, turn]
                            turn_index += 1
                else:
                    # Sequential execution (original behavior)
                    for actor_name in phase.acting_agents:
                        if env.is_terminal():
                            break

                        turns = await _run_single_agent(
                            actor_name=actor_name,
                            phase=phase,
                            env=env,
                            agent_config=agents_by_name[actor_name],
                            interaction=interaction,
                            scenario=scenario,
                            network=network,
                            max_action_retries=max_action_retries,
                            conversation_style=conversation_style,
                            context_strategy=context_strategy,
                        )
                        for turn in turns:
                            turn = turn.model_copy(
                                update={"turn_index": turn_index}
                            )
                            interaction.turns = [*interaction.turns, turn]
                            turn_index += 1

                # ── Post-round hooks ─────────────────────────────────
                env.update_network(network, interaction)
                _snapshot_network(network, interaction, phase.round)

                if bridge:
                    await bridge.mark_round(phase.round)

                env.advance_phase()

        finally:
            if bridge:
                await bridge.teardown()

        # ── Store game outcome for scorers ───────────────────────────
        outcome = env.get_outcome()
        game_state = env.get_game_state_for_scoring()
        new_meta = interaction.scenario.metadata.model_copy(
            update={
                "game_outcome": outcome.model_dump(),
                "game_state": game_state,
            }
        )
        interaction.scenario = interaction.scenario.model_copy(
            update={"metadata": new_meta}
        )

        state.messages = _build_game_transcript(interaction)
        return state

    return solve


# ── Helpers ──────────────────────────────────────────────────────────


def _build_personas(agents: list[AgentRole]) -> list[PersonaCard]:
    """Build PersonaCard list from agent configs."""
    personas: list[PersonaCard] = []
    for a in agents:
        if a.persona and isinstance(a.persona, PersonaCard):
            personas.append(a.persona)
        elif a.persona and isinstance(a.persona, dict):
            personas.append(PersonaCard(**a.persona))
        else:
            personas.append(PersonaCard(name=a.name, role="agent"))
    return personas


async def _run_single_agent(
    actor_name: str,
    phase: Phase,
    env: object,
    agent_config: AgentRole,
    interaction: InteractionState,
    scenario: ScenarioConfig,
    network: Network,
    max_action_retries: int,
    conversation_style: ConversationStyle | None = None,
    context_strategy: ContextStrategy | None = None,
) -> list[Turn]:
    """Run one agent's turn. Returns a list of Turn objects (usually one).

    This is self-contained so it can safely run via ``collect()`` for
    parallel execution.  It does not mutate ``interaction.turns`` directly;
    the caller is responsible for appending returned turns and assigning
    ``turn_index`` values.
    """
    model = get_model(role=agent_config.model_role)
    obs = env.get_observation(actor_name)
    messages = _build_game_messages(
        agent_config,
        obs,
        interaction,
        scenario,
        network=network,
        conversation_style=conversation_style,
        context_strategy=context_strategy,
    )

    tools = env.get_tools(actor_name, phase)
    tool_choice = env.get_tool_choice(phase) if tools else None
    turns: list[Turn] = []

    if phase.phase_type == PhaseType.DISCUSSION:
        output = await model.generate(
            messages,
            tools=tools,
            tool_choice=tool_choice,
            config=GenerateConfig(max_tokens=scenario.max_tokens),
        )
        content = output.completion or ""

        # Process tool calls (e.g., Diplomacy message routing)
        if output.message.tool_calls:
            env.process_tool_calls(actor_name, output.message.tool_calls, phase)

        # Non-tool processing (e.g., Debate tracks first-speaker)
        env.process_discussion(actor_name, content, phase)

        turn = Turn(
            speaker=actor_name,
            content=content,
            round=phase.round,
            turn_index=0,  # placeholder; caller sets the real index
            metadata={"phase": phase.name, "phase_type": "discussion"},
        )
        turns.append(turn)

        # Opinion/stance extraction
        _update_agent_opinion_stance(env, actor_name, content, interaction)

    elif phase.phase_type == PhaseType.ACTION:
        action = None
        raw_content = ""
        result = None
        for attempt in range(max_action_retries + 1):
            output = await model.generate(
                messages,
                tools=tools,
                tool_choice=tool_choice,
                config=GenerateConfig(max_tokens=scenario.max_tokens),
            )
            raw_content = output.completion or ""

            if not output.message.tool_calls:
                if attempt < max_action_retries:
                    messages.append(output.message)
                    messages.append(
                        ChatMessageUser(
                            content="You must use a tool to submit your action."
                        )
                    )
                    continue
                action = (
                    obs.valid_actions[0] if obs.valid_actions else "pass:none"
                )
            else:
                try:
                    action = env.tool_calls_to_action(
                        actor_name, output.message.tool_calls
                    )
                except ValueError as e:
                    if attempt < max_action_retries:
                        _append_tool_errors(messages, output.message, str(e))
                        continue
                    action = (
                        obs.valid_actions[0]
                        if obs.valid_actions
                        else "pass:none"
                    )

            result = env.apply_action(actor_name, action)
            if result.valid or attempt == max_action_retries:
                break
            _append_tool_errors(messages, output.message, result.error)

        turn = Turn(
            speaker=actor_name,
            content=raw_content,
            round=phase.round,
            turn_index=0,  # placeholder; caller sets the real index
            metadata={
                "phase": phase.name,
                "phase_type": "action",
                "action": action,
                "action_valid": result.valid if result else False,
                "action_narrative": result.narrative if result else "",
            },
        )
        turns.append(turn)

        # Opinion/stance extraction
        _update_agent_opinion_stance(env, actor_name, raw_content, interaction)

    return turns


def _update_agent_opinion_stance(
    env: object,
    agent_name: str,
    content: str,
    interaction: InteractionState,
) -> None:
    """Extract opinion/stance and update agent_states via StoreModel reassignment."""
    opinion = env.extract_opinion(agent_name, content)
    stance = env.classify_stance(agent_name, content)

    current = interaction.agent_states.get(agent_name, AgentSnapshot())
    updated = current.model_copy(
        update={
            "opinions": [*current.opinions, opinion],
            "stances": [*current.stances, stance],
        }
    )
    # StoreModel reassignment pattern
    interaction.agent_states = {
        **interaction.agent_states,
        agent_name: updated,
    }


def _snapshot_network(
    network: Network, interaction: InteractionState, round_num: int
) -> None:
    """Capture network state as a NetworkSnapshot and append to interaction."""
    edges: list[tuple[str, str]] = []
    channels: list[str] = []
    for ch_id, ch in network.channels.items():
        channels.append(ch_id)
        members = sorted(ch.members)
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                if (a, b) not in edges:
                    edges.append((a, b))

    # Count adopters (agents with at least one non-None opinion)
    adopters = [
        name
        for name, snap in interaction.agent_states.items()
        if snap.adopted
    ]

    snapshot = NetworkSnapshot(
        round=round_num,
        edges=edges,
        channels=channels,
        adopters=adopters,
        total_messages=network.total_message_count(),
    )
    interaction.network_snapshots = [
        *interaction.network_snapshots,
        snapshot,
    ]


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
    network: Network | None = None,
    conversation_style: ConversationStyle | None = None,
    context_strategy: ContextStrategy | None = None,
) -> list[ChatMessageSystem | ChatMessageUser | ChatMessageAssistant]:
    """Build the message list for an agent in a game context.

    Enhanced version that supports persona injection, conversation style,
    and network-aware visibility.  Remains backward-compatible with the
    original 4-argument calling convention (``network``, ``conversation_style``,
    and ``context_strategy`` all default to ``None``).
    """
    messages: list[ChatMessageSystem | ChatMessageUser | ChatMessageAssistant] = []

    # ── System prompt (with optional persona injection) ──────────
    system_parts: list[str] = []
    if agent.persona:
        persona = agent.persona
        if isinstance(persona, PersonaCard):
            system_parts.append(persona.prompt_block())
        elif isinstance(persona, dict):
            system_parts.append(PersonaCard(**persona).prompt_block())
    system_parts.append(agent.system_prompt)
    messages.append(ChatMessageSystem(content="\n\n".join(system_parts)))

    if agent.prior_context:
        messages.append(ChatMessageUser(content=agent.prior_context))

    # ── Game context ─────────────────────────────────────────────
    context_parts = [obs.public_info]
    if obs.private_info:
        context_parts.append(f"[PRIVATE] {obs.private_info}")
    if obs.history_summary:
        context_parts.append(f"Game history:\n{obs.history_summary}")
    messages.append(ChatMessageUser(content="\n\n".join(context_parts)))

    # ── Prior turns (visible per topology) ───────────────────────
    if network is not None:
        visible_turns = interaction.turns_visible_to(
            agent.name, network=network
        )
    else:
        visible_turns = interaction.turns_visible_to(
            agent.name, scenario.visibility
        )

    action_narratives: list[str] = []
    for turn in visible_turns:
        phase_type = turn.metadata.get("phase_type")
        if phase_type == "discussion":
            if turn.speaker == agent.name:
                messages.append(ChatMessageAssistant(content=turn.content))
            else:
                messages.append(
                    ChatMessageUser(
                        content=f"[{turn.speaker}]: {turn.content}"
                    )
                )
        elif phase_type == "action" and turn.metadata.get("action_narrative"):
            action_narratives.append(turn.metadata["action_narrative"])
    if action_narratives:
        events = "\n".join(action_narratives)
        messages.append(
            ChatMessageUser(content=f"[Game Events]:\n{events}")
        )

    # ── Phase-specific prompt ────────────────────────────────────
    if obs.phase.phase_type == PhaseType.DISCUSSION:
        prompt = obs.engagement_prompt or "Discuss with the other players."

        # Inject conversation style participation prompt if available
        if conversation_style is not None and network is not None:
            try:
                from manipulation_bench.protocols import PromptContext
                from manipulation_bench.network import Node

                # Find the node for this agent
                node = None
                for n in network.nodes.values():
                    if n.persona.name == agent.name or n.id == agent.name:
                        node = n
                        break
                if node is None:
                    # Fallback: create a minimal node
                    node = Node(
                        id=agent.name,
                        persona=PersonaCard(name=agent.name, role="agent"),
                    )
                ctx = PromptContext(
                    node=node,
                    network=network,
                    scenario_name=scenario.topic,
                    round=obs.phase.round,
                    inbox=network.inbox(node.id, obs.phase.round),
                    node_state=None,
                )
                style_prompt = conversation_style.participation_prompt(ctx)
                if style_prompt:
                    prompt = f"{prompt}\n\n{style_prompt}"
            except Exception:
                pass  # Gracefully degrade if style prompt fails

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
            content = (
                f"{label}: {narrative}" if narrative else f"{label}: {turn.content}"
            )
        else:
            content = f"[{turn.speaker}, {phase}]: {turn.content}"
        messages.append(ChatMessageAssistant(content=content))

    return messages
