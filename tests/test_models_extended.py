"""Tests for AgentSnapshot, NetworkSnapshot, and updated InteractionState."""

from manipulation_bench.agents import PersonaCard
from manipulation_bench.models import (
    AgentRole,
    AgentSnapshot,
    InteractionState,
    NetworkSnapshot,
    ScenarioConfig,
    Turn,
)
from manipulation_bench.network import broadcast


class TestAgentSnapshot:
    def test_defaults(self):
        snap = AgentSnapshot()
        assert snap.opinions == []
        assert snap.stances == []
        assert snap.beliefs == {}
        assert snap.adopted is False
        assert snap.alive is True
        assert snap.reputation == {}

    def test_track_opinions(self):
        snap = AgentSnapshot()
        snap.opinions = [50.0, 45.0, 42.0]
        assert len(snap.opinions) == 3


class TestNetworkSnapshot:
    def test_defaults(self):
        snap = NetworkSnapshot(round=0)
        assert snap.round == 0
        assert snap.edges == []
        assert snap.channels == []
        assert snap.total_messages == 0


class TestAgentRoleWithPersona:
    def test_persona_optional(self):
        role = AgentRole(name="alice", model_role="debater", system_prompt="Argue.")
        assert role.persona is None

    def test_persona_present(self):
        persona = PersonaCard(name="Alice", role="journalist", traits={"credulity": 0.8})
        role = AgentRole(
            name="alice", model_role="debater",
            system_prompt="Argue.", persona=persona,
        )
        assert role.persona is not None
        assert role.persona.traits["credulity"] == 0.8


class TestScenarioConfigTopology:
    def test_default_topology(self):
        config = ScenarioConfig(topic="test", agents=[])
        assert config.topology == "broadcast"

    def test_custom_topology(self):
        config = ScenarioConfig(topic="test", agents=[], topology="dense")
        assert config.topology == "dense"

    def test_visibility_still_works(self):
        config = ScenarioConfig(topic="test", agents=[], visibility="hub_spoke")
        assert config.visibility == "hub_spoke"


class TestInteractionStateChannelVisibility:
    def test_turns_visible_to_with_network(self):
        personas = [PersonaCard(name=n, role="agent") for n in ["Alice", "Bob"]]
        net = broadcast(personas)
        state = InteractionState()
        state.turns = [
            Turn(speaker="node_0", content="hello", round=0, turn_index=0, metadata={"channel_id": "general"}),
            Turn(speaker="node_1", content="hi", round=0, turn_index=1, metadata={"channel_id": "general"}),
        ]
        visible = state.turns_visible_to("node_0", network=net)
        assert len(visible) == 2

    def test_legacy_string_visibility_still_works(self):
        state = InteractionState()
        state.agent_names = ["alice", "bob"]
        state.turns = [
            Turn(speaker="alice", content="hello", round=0, turn_index=0),
            Turn(speaker="bob", content="hi", round=0, turn_index=1),
        ]
        visible = state.turns_visible_to("alice", visibility="all_to_all")
        assert len(visible) == 2

    def test_agent_states_dict(self):
        state = InteractionState()
        state.agent_states = {"alice": AgentSnapshot(), "bob": AgentSnapshot()}
        assert len(state.agent_states) == 2

    def test_network_snapshots_list(self):
        state = InteractionState()
        snap = NetworkSnapshot(round=0, edges=[("a", "b")], channels=["general"])
        state.network_snapshots = [snap]
        assert len(state.network_snapshots) == 1
