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
    metadata: dict[str, Any] = Field(default_factory=dict)


class Turn(BaseModel, frozen=True):
    """One turn in the interaction transcript."""

    speaker: str
    content: str
    round: int
    turn_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioConfig(BaseModel, frozen=True):
    """Full specification of one multi-agent interaction scenario."""

    topic: str
    description: str = ""
    agents: list[AgentRole]
    protocol: str = "round_robin"
    num_rounds: int = 3
    visibility: str = "full"  # "full" | "own_role"
    max_tokens: int = 2048
    judge_prompt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class InteractionState(StoreModel):
    """Persisted interaction state, shared between solver and scorers via store_as()."""

    scenario: ScenarioConfig | None = None
    turns: list[Turn] = Field(default_factory=list)
    current_round: int = 0
    agent_names: list[str] = Field(default_factory=list)

    def turns_for_agent(self, agent_name: str) -> list[Turn]:
        return [t for t in self.turns if t.speaker == agent_name]

    def turns_visible_to(self, agent_name: str, visibility: str) -> list[Turn]:
        if visibility == "full":
            return list(self.turns)
        if visibility == "own_role":
            return [t for t in self.turns if t.speaker == agent_name]
        return list(self.turns)
