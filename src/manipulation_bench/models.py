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
    environment_type: str = ""
    model_mapping: dict[str, str] = Field(default_factory=dict)
    game_outcome: dict[str, Any] | None = None
    game_state: dict[str, Any] | None = None

    # Response-surface axes — canonical names defined in axes.py.
    # ``None`` means the axis is inapplicable to the scenario.
    # Generators that designate a specific agent (e.g., "manipulator",
    # "interested_party", "buyer") store that under their own key in
    # ``metadata`` — ``extra='allow'`` preserves arbitrary keys, so
    # study-specific role labels don't need to be typed here.
    frame: str | None = None
    incentive: str | None = None
    difficulty: str | None = None


class ScenarioConfig(BaseModel, frozen=True):
    """Full specification of one multi-agent interaction scenario."""

    topic: str
    description: str = ""
    agents: list[AgentRole]
    protocol: str = "round_robin"
    num_rounds: int = 3
    visibility: str | dict[str, list[str]] = "all_to_all"
    max_tokens: int = 2048
    ground_truth: str | None = None  # "true" or "false" — enables grounded metrics
    judge_prompt: str | None = None
    metadata: ScenarioMetadata = Field(default_factory=ScenarioMetadata)


class InteractionState(StoreModel):
    """Persisted interaction state, shared between solver and scorers via store_as()."""

    scenario: ScenarioConfig | None = None
    turns: list[Turn] = Field(default_factory=list)
    current_round: int = 0
    agent_names: list[str] = Field(default_factory=list)

    def turns_for_agent(self, agent_name: str) -> list[Turn]:
        return [t for t in self.turns if t.speaker == agent_name]

    def turns_visible_to(
        self, agent_name: str, visibility: str | dict[str, list[str]]
    ) -> list[Turn]:
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
