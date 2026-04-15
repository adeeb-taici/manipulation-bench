"""Tests for the unified solver."""

from __future__ import annotations


def test_backward_compat_import():
    """game_solver.game_interaction still importable."""
    from manipulation_bench.game_solver import game_interaction

    assert callable(game_interaction)


def test_new_import():
    """solver.game_interaction importable."""
    from manipulation_bench.solver import game_interaction

    assert callable(game_interaction)


def test_solver_accepts_new_params():
    """Verify the new parameters are accepted."""
    from manipulation_bench.solver import game_interaction

    # Should not raise -- just verify it accepts the params
    s = game_interaction(
        max_action_retries=3,
        conversation_style=None,
        context_strategy=None,
        bridge=None,
    )
    assert s is not None


def test_backward_compat_helpers():
    """Helpers re-exported through game_solver."""
    from manipulation_bench.game_solver import (
        _append_tool_errors,
        _build_game_messages,
        _build_game_transcript,
    )

    assert callable(_append_tool_errors)
    assert callable(_build_game_messages)
    assert callable(_build_game_transcript)


def test_solver_helpers_directly():
    """Helpers importable from solver directly."""
    from manipulation_bench.solver import (
        _append_tool_errors,
        _build_game_messages,
        _build_game_transcript,
    )

    assert callable(_append_tool_errors)
    assert callable(_build_game_messages)
    assert callable(_build_game_transcript)


def test_build_personas():
    """_build_personas creates PersonaCard from AgentRole."""
    from manipulation_bench.agents import PersonaCard
    from manipulation_bench.models import AgentRole
    from manipulation_bench.solver import _build_personas

    agents = [
        AgentRole(name="alice", model_role="debater", system_prompt="You are alice."),
        AgentRole(
            name="bob",
            model_role="debater",
            system_prompt="You are bob.",
            persona=PersonaCard(name="Bob", role="engineer"),
        ),
        AgentRole(
            name="carol",
            model_role="debater",
            system_prompt="You are carol.",
            persona={"name": "Carol", "role": "journalist"},
        ),
    ]

    personas = _build_personas(agents)
    assert len(personas) == 3
    assert personas[0].name == "alice"
    assert personas[0].role == "agent"  # default
    assert personas[1].name == "Bob"
    assert personas[1].role == "engineer"
    assert personas[2].name == "Carol"
    assert personas[2].role == "journalist"


def test_snapshot_network():
    """_snapshot_network captures edges and channels."""
    from manipulation_bench.agents import PersonaCard
    from manipulation_bench.models import InteractionState
    from manipulation_bench.network import broadcast
    from manipulation_bench.solver import _snapshot_network

    personas = [
        PersonaCard(name="alice", role="agent"),
        PersonaCard(name="bob", role="agent"),
    ]
    network = broadcast(personas)
    interaction = InteractionState()

    # Capture baseline (StoreModel may carry state from prior tests)
    before = len(interaction.network_snapshots)

    _snapshot_network(network, interaction, round_num=1)

    assert len(interaction.network_snapshots) == before + 1
    snap = interaction.network_snapshots[-1]
    assert snap.round == 1
    assert len(snap.channels) == 1
    assert snap.channels[0] == "general"
    assert len(snap.edges) == 1  # one edge between 2 nodes


def test_update_agent_opinion_stance():
    """_update_agent_opinion_stance records values in agent_states."""
    from manipulation_bench.models import AgentSnapshot, InteractionState
    from manipulation_bench.solver import _update_agent_opinion_stance

    class FakeEnv:
        def extract_opinion(self, agent_name, content):
            return 0.7

        def classify_stance(self, agent_name, content):
            return "for"

    interaction = InteractionState()
    # Use a unique agent name to avoid stale StoreModel contamination
    interaction.agent_states = {
        **interaction.agent_states,
        "solver_test_agent": AgentSnapshot(),
    }

    _update_agent_opinion_stance(FakeEnv(), "solver_test_agent", "I agree", interaction)

    snap = interaction.agent_states["solver_test_agent"]
    assert snap.opinions[-1] == 0.7
    assert snap.stances[-1] == "for"


def test_build_game_messages_persona_injection():
    """_build_game_messages prepends persona prompt_block to system prompt."""
    from manipulation_bench.agents import PersonaCard
    from manipulation_bench.environments.base import Observation, Phase, PhaseType
    from manipulation_bench.models import AgentRole, InteractionState, ScenarioConfig
    from manipulation_bench.solver import _build_game_messages

    persona = PersonaCard(name="Alice", role="journalist", backstory="Alice reports news.")
    agent = AgentRole(
        name="alice",
        model_role="debater",
        system_prompt="Argue your position.",
        persona=persona,
    )
    phase = Phase(
        name="discussion_1",
        phase_type=PhaseType.DISCUSSION,
        round=1,
        acting_agents=["alice"],
    )
    obs = Observation(
        agent_name="alice",
        phase=phase,
        public_info="Topic: AI safety",
    )
    scenario = ScenarioConfig(
        topic="AI safety",
        agents=[agent],
    )
    interaction = InteractionState()
    interaction.agent_names = ["alice"]

    messages = _build_game_messages(agent, obs, interaction, scenario)

    # First message should be system prompt with persona block prepended
    system_msg = messages[0]
    assert "Alice" in system_msg.content
    assert "journalist" in system_msg.content
    assert "Argue your position." in system_msg.content


def test_build_game_messages_no_persona():
    """_build_game_messages works normally without persona."""
    from manipulation_bench.environments.base import Observation, Phase, PhaseType
    from manipulation_bench.models import AgentRole, InteractionState, ScenarioConfig
    from manipulation_bench.solver import _build_game_messages

    agent = AgentRole(
        name="alice",
        model_role="debater",
        system_prompt="Argue your position.",
    )
    phase = Phase(
        name="discussion_1",
        phase_type=PhaseType.DISCUSSION,
        round=1,
        acting_agents=["alice"],
    )
    obs = Observation(
        agent_name="alice",
        phase=phase,
        public_info="Topic: AI safety",
    )
    scenario = ScenarioConfig(
        topic="AI safety",
        agents=[agent],
    )
    interaction = InteractionState()
    interaction.agent_names = ["alice"]

    messages = _build_game_messages(agent, obs, interaction, scenario)

    # System prompt should be just the original
    system_msg = messages[0]
    assert system_msg.content == "Argue your position."
