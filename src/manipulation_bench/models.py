from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from inspect_ai.util import StoreModel


class AgentRole(BaseModel, frozen=True):
    """One participant in a scenario. Defined per-scenario in the dataset, not in code."""

    name: str
    model_role: str
    system_prompt: str
    position: str | None = None
    prior_context: str | None = None
    persona: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Turn(BaseModel, frozen=True):
    """One turn in the interaction transcript."""

    speaker: str
    content: str
    round: int
    turn_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioMetadata(BaseModel, extra="allow"):
    """Typed metadata for a scenario. ``extra='allow'`` preserves unknown keys."""

    environment: dict[str, Any] = Field(default_factory=dict)
    model_mapping: dict[str, str] = Field(default_factory=dict)
    game_outcome: dict[str, Any] | None = None
    game_state: dict[str, Any] | None = None


class AgentSnapshot(BaseModel):
    """Per-agent state tracked across rounds."""

    opinions: list[float | None] = Field(default_factory=list)
    stances: list[str] = Field(default_factory=list)
    beliefs: dict[str, Any] = Field(default_factory=dict)
    adopted: bool = False
    alive: bool = True
    reputation: dict[str, float] = Field(default_factory=dict)


class NetworkSnapshot(BaseModel):
    """Per-round network state for adaptive network tracking."""

    round: int
    edges: list[tuple[str, str]] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=list)
    adopters: list[str] = Field(default_factory=list)
    total_messages: int = 0


class ScenarioConfig(BaseModel, frozen=True):
    """Full specification of one multi-agent interaction scenario."""

    topic: str
    description: str = ""
    agents: list[AgentRole]
    protocol: str = "round_robin"
    num_rounds: int = 3
    visibility: str | dict[str, list[str]] = "all_to_all"
    topology: str = "broadcast"
    max_tokens: int = 2048
    ground_truth: str | None = None  # "true" or "false" — enables grounded metrics
    judge_prompt: str | None = None
    metadata: ScenarioMetadata = Field(default_factory=ScenarioMetadata)


class InteractionState(StoreModel):
    """Persisted interaction state, shared between solver and scorers via store_as()."""

    scenario: ScenarioConfig | None = None
    turns: list[Turn] = Field(default_factory=list)
    agent_states: dict[str, AgentSnapshot] = Field(default_factory=dict)
    network_snapshots: list[NetworkSnapshot] = Field(default_factory=list)
    current_round: int = 0
    agent_names: list[str] = Field(default_factory=list)

    def turns_for_agent(self, agent_name: str) -> list[Turn]:
        return [t for t in self.turns if t.speaker == agent_name]

    def turns_visible_to(
        self,
        agent_name: str,
        visibility: str | dict[str, list[str]] | None = None,
        network: Any | None = None,
    ) -> list[Turn]:
        """Filter turns by visibility.

        Supports two modes:
        - Channel-based (network provided): filter by channel membership
        - Legacy string-based (visibility provided): filter by visibility rules
        """
        if network is not None:
            visible_channels = {ch.id for ch in network.node_channels(agent_name)}
            return [
                t for t in self.turns
                if t.metadata.get("channel_id") in visible_channels
                or t.speaker == agent_name
            ]

        # Legacy string-based visibility (backward compat)
        if visibility is None:
            visibility = "all_to_all"

        # String shortcuts
        if isinstance(visibility, str):
            if visibility in ("all_to_all", "full"):
                return list(self.turns)
            if visibility == "isolated":
                return [t for t in self.turns if t.speaker == agent_name]
            if visibility == "hub_spoke":
                # First agent in agent_names is the hub, sees everyone.
                # Others only see the hub and themselves.
                hub = self.agent_names[0] if self.agent_names else None
                if agent_name == hub:
                    return list(self.turns)
                return [t for t in self.turns if t.speaker == agent_name or t.speaker == hub]
            # Unknown string — default to all_to_all
            return list(self.turns)

        # Explicit adjacency dict: {"agent_a": ["agent_b", "agent_c"], ...}
        visible_speakers = set(visibility.get(agent_name, []))
        visible_speakers.add(agent_name)  # always see your own turns
        if "*" in visible_speakers:
            return list(self.turns)
        return [t for t in self.turns if t.speaker in visible_speakers]
