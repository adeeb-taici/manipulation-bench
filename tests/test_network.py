"""Tests for Network, Channel, Message, and topology factories."""

from manipulation_bench.environments.network import (
    Channel,
    ChannelType,
    Message,
    Node,
    PersonaCard,
    broadcast,
    commons,
    dense,
    ring,
    star,
    TOPOLOGIES,
)


def _make_personas(n: int) -> list[PersonaCard]:
    return [PersonaCard(name=f"Agent{i}", role="agent") for i in range(n)]


class TestChannelAndNode:
    def test_channel_creation(self):
        ch = Channel(
            id="general",
            name="#general",
            channel_type=ChannelType.PUBLIC,
            members={"node_0", "node_1"},
        )
        assert ch.id == "general"
        assert ch.channel_type == ChannelType.PUBLIC
        assert "node_0" in ch.members

    def test_node_creation(self):
        persona = PersonaCard(name="Alice", role="journalist")
        node = Node(id="node_0", persona=persona)
        assert node.id == "node_0"
        assert node.persona.name == "Alice"
        assert node.is_human is False


class TestNetwork:
    def test_route_and_inbox(self):
        personas = _make_personas(2)
        net = broadcast(personas)
        msg = Message(sender="node_0", channel_id="general", content="hello", round=0)
        net.route(msg)

        inbox = net.inbox("node_1", 0)
        assert "general" in inbox
        assert len(inbox["general"]) == 1
        assert inbox["general"][0].content == "hello"

    def test_inbox_excludes_self(self):
        personas = _make_personas(2)
        net = broadcast(personas)
        msg = Message(sender="node_0", channel_id="general", content="hello", round=0)
        net.route(msg)

        inbox = net.inbox("node_0", 0)
        assert inbox == {}

    def test_inbox_filters_by_round(self):
        personas = _make_personas(2)
        net = broadcast(personas)
        net.route(Message(sender="node_0", channel_id="general", content="r0", round=0))
        net.route(Message(sender="node_0", channel_id="general", content="r1", round=1))

        inbox = net.inbox("node_1", 0)
        assert len(inbox["general"]) == 1
        assert inbox["general"][0].content == "r0"

    def test_node_channels(self):
        personas = _make_personas(3)
        net = broadcast(personas)
        channels = net.node_channels("node_0")
        assert len(channels) == 1
        assert channels[0].channel_type == ChannelType.PUBLIC

    def test_total_message_count(self):
        personas = _make_personas(2)
        net = broadcast(personas)
        assert net.total_message_count() == 0
        net.route(Message(sender="node_0", channel_id="general", content="hi", round=0))
        assert net.total_message_count() == 1

    def test_add_channel(self):
        personas = _make_personas(2)
        net = broadcast(personas)
        new_ch = Channel(
            id="private-0",
            name="#private",
            channel_type=ChannelType.PRIVATE,
            members={"node_0"},
        )
        net.add_channel(new_ch)
        assert "private-0" in net.channels
        assert len(net.node_channels("node_0")) == 2

    def test_remove_channel(self):
        personas = _make_personas(2)
        net = broadcast(personas)
        net.remove_channel("general")
        assert "general" not in net.channels
        assert net.node_channels("node_0") == []


class TestTopologies:
    def test_broadcast_creates_one_public_channel(self):
        personas = _make_personas(4)
        net = broadcast(personas)
        assert len(net.channels) == 1
        ch = list(net.channels.values())[0]
        assert ch.channel_type == ChannelType.PUBLIC
        assert len(ch.members) == 4

    def test_broadcast_all_nodes_present(self):
        personas = _make_personas(3)
        net = broadcast(personas)
        assert len(net.nodes) == 3
        assert "node_0" in net.nodes
        assert "node_2" in net.nodes

    def test_dense_creates_pairwise_dms(self):
        personas = _make_personas(4)
        net = dense(personas)
        assert len(net.channels) == 6
        for ch in net.channels.values():
            assert ch.channel_type == ChannelType.DM
            assert len(ch.members) == 2

    def test_star_hub_has_all_dms(self):
        personas = _make_personas(4)
        net = star(personas)
        assert len(net.channels) == 3
        hub_channels = net.node_channels("node_0")
        assert len(hub_channels) == 3
        leaf_channels = net.node_channels("node_1")
        assert len(leaf_channels) == 1

    def test_ring_creates_circular_dms(self):
        personas = _make_personas(4)
        net = ring(personas)
        assert len(net.channels) == 4
        for i in range(4):
            channels = net.node_channels(f"node_{i}")
            assert len(channels) == 2

    def test_commons_has_public_plus_dms(self):
        personas = _make_personas(3)
        net = commons(personas)
        assert len(net.channels) == 4
        public = [ch for ch in net.channels.values() if ch.channel_type == ChannelType.PUBLIC]
        dms = [ch for ch in net.channels.values() if ch.channel_type == ChannelType.DM]
        assert len(public) == 1
        assert len(dms) == 3

    def test_topologies_registry(self):
        assert "broadcast" in TOPOLOGIES
        assert "dense" in TOPOLOGIES
        assert "star" in TOPOLOGIES
        assert "ring" in TOPOLOGIES
        assert "commons" in TOPOLOGIES
