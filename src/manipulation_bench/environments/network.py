"""Network graph, topologies, and message routing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from manipulation_bench.agents import PersonaCard


class ChannelType(str, Enum):
    """Type of communication channel."""

    PUBLIC = "public"
    PRIVATE = "private"
    DM = "dm"
    THREAD = "thread"


@dataclass
class Channel:
    """A communication channel that agents can post in and read from."""

    id: str
    name: str
    channel_type: ChannelType
    members: set[str]
    parent_id: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Message:
    """A message sent through the network."""

    sender: str
    channel_id: str
    content: str
    round: int
    metadata: dict = field(default_factory=dict)
    sender_name: str = ""
    reply_to: str | None = None


@dataclass
class Node:
    """A node in the network graph."""

    id: str
    persona: PersonaCard
    is_human: bool = False


class Network:
    """Graph of nodes communicating through channels."""

    def __init__(self, nodes: dict[str, Node], channels: dict[str, Channel]) -> None:
        self.nodes = nodes
        self.channels = channels
        self.message_log: dict[str, list[Message]] = {ch_id: [] for ch_id in channels}

    def node_channels(self, node_id: str) -> list[Channel]:
        """Return all channels this node is a member of."""
        return [ch for ch in self.channels.values() if node_id in ch.members]

    def route(self, msg: Message) -> None:
        """Deliver message to the specified channel's log."""
        if msg.channel_id not in self.message_log:
            self.message_log[msg.channel_id] = []
        self.message_log[msg.channel_id].append(msg)

    def inbox(self, node_id: str, round: int) -> dict[str, list[Message]]:
        """Messages visible to node_id in the given round, grouped by channel."""
        result: dict[str, list[Message]] = {}
        for ch in self.node_channels(node_id):
            msgs = [
                m
                for m in self.message_log.get(ch.id, [])
                if m.round == round and m.sender != node_id
            ]
            if msgs:
                result[ch.id] = msgs
        return result

    def total_message_count(self) -> int:
        """Total messages across all channels."""
        return sum(len(msgs) for msgs in self.message_log.values())

    def add_channel(self, channel: Channel) -> None:
        """Add a channel to the network (for adaptive networks)."""
        self.channels[channel.id] = channel
        if channel.id not in self.message_log:
            self.message_log[channel.id] = []

    def remove_channel(self, channel_id: str) -> None:
        """Remove a channel from the network (for adaptive networks)."""
        self.channels.pop(channel_id, None)
        self.message_log.pop(channel_id, None)


def _make_dm_channel(node_a: str, node_b: str, nodes: dict[str, Node]) -> Channel:
    """Create a DM channel between two nodes."""
    name_a = nodes[node_a].persona.name
    name_b = nodes[node_b].persona.name
    sorted_ids = sorted([node_a, node_b])
    ch_id = f"dm-{sorted_ids[0]}-{sorted_ids[1]}"
    return Channel(
        id=ch_id,
        name=f"@{name_b}" if node_a < node_b else f"@{name_a}",
        channel_type=ChannelType.DM,
        members={node_a, node_b},
    )


def _build_nodes(personas: list[PersonaCard]) -> dict[str, Node]:
    """Create node dict from persona list."""
    return {f"node_{i}": Node(id=f"node_{i}", persona=p) for i, p in enumerate(personas)}


def _build_network(personas: list[PersonaCard], channels: list[Channel]) -> Network:
    """Helper to create a Network from a persona list and channel list."""
    nodes = _build_nodes(personas)
    ch_dict = {ch.id: ch for ch in channels}
    return Network(nodes=nodes, channels=ch_dict)


def broadcast(personas: list[PersonaCard]) -> Network:
    """Broadcast topology: one PUBLIC channel with all members."""
    nodes = _build_nodes(personas)
    all_ids = set(nodes.keys())
    ch = Channel(id="general", name="#general", channel_type=ChannelType.PUBLIC, members=all_ids)
    return _build_network(personas, [ch])


def star(personas: list[PersonaCard]) -> Network:
    """Star topology: hub (node_0) has a DM channel with each leaf."""
    nodes = _build_nodes(personas)
    channels = [_make_dm_channel("node_0", f"node_{i}", nodes) for i in range(1, len(personas))]
    return _build_network(personas, channels)


def dense(personas: list[PersonaCard]) -> Network:
    """Fully connected: DM channel for every pair of nodes."""
    nodes = _build_nodes(personas)
    channels = [
        _make_dm_channel(f"node_{i}", f"node_{j}", nodes)
        for i in range(len(personas))
        for j in range(i + 1, len(personas))
    ]
    return _build_network(personas, channels)


def commons(personas: list[PersonaCard]) -> Network:
    """One public channel plus DM channels for every pair."""
    nodes = _build_nodes(personas)
    all_ids = set(nodes.keys())
    public_ch = Channel(
        id="general", name="#general", channel_type=ChannelType.PUBLIC, members=all_ids
    )
    dm_channels = [
        _make_dm_channel(f"node_{i}", f"node_{j}", nodes)
        for i in range(len(personas))
        for j in range(i + 1, len(personas))
    ]
    return _build_network(personas, [public_ch] + dm_channels)


def ring(personas: list[PersonaCard]) -> Network:
    """Circular ring: DM channel between each adjacent pair."""
    n = len(personas)
    nodes = _build_nodes(personas)
    channels = [_make_dm_channel(f"node_{i}", f"node_{(i + 1) % n}", nodes) for i in range(n)]
    return _build_network(personas, channels)


TOPOLOGIES: dict[str, Callable[..., Network]] = {
    "broadcast": broadcast,
    "dense": dense,
    "star": star,
    "ring": ring,
    "commons": commons,
}
