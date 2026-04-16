"""Base types and ABC for game environments."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from inspect_ai.tool import ToolCall, ToolInfo


class PhaseType(str, Enum):
    """Whether agents should talk freely or submit structured actions."""

    DISCUSSION = "discussion"
    ACTION = "action"


class Phase(BaseModel, frozen=True):
    """Describes the current game phase."""

    name: str
    phase_type: PhaseType
    round: int
    acting_agents: list[str]
    description: str = ""
    # Reserved for future environments that run acting_agents concurrently.
    # No solver reads this today; naming_game sets it explicitly as a marker.
    parallel: bool = False


class Observation(BaseModel, frozen=True):
    """What a single agent can see right now."""

    agent_name: str
    phase: Phase
    public_info: str
    private_info: str = ""
    valid_actions: list[str] = Field(default_factory=list)
    action_prompt: str = ""
    history_summary: str = ""
    engagement_prompt: str = ""


class ActionResult(BaseModel, frozen=True):
    """Result of processing one agent's action."""

    agent_name: str
    action: str
    valid: bool
    narrative: str = ""
    error: str = ""


class GameOutcome(BaseModel, frozen=True):
    """Terminal game result."""

    winner: str
    reason: str
    scores: dict[str, float] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Environment(ABC):
    """Abstract base for game environments.

    Supports both code-orchestrated games (rules in Python) and external
    game APIs (rules on a server) through the same interface.

    Lifecycle:
        env.setup(agent_names)
        while not env.is_terminal():
            phase = env.get_current_phase()
            for agent in phase.acting_agents:
                obs = env.get_observation(agent)
                tools = env.get_tools(agent, phase)
                # ... LLM generates response with tools ...
                if phase.phase_type == PhaseType.ACTION:
                    action = env.tool_calls_to_action(agent, tool_calls)
                    env.apply_action(agent, action)
                if phase.phase_type == PhaseType.DISCUSSION:
                    env.process_tool_calls(agent, tool_calls, phase)
            env.advance_phase()
        outcome = env.get_outcome()
    """

    @abstractmethod
    def setup(self, agent_names: list[str]) -> None:
        """Initialize game state (assign roles, deal cards, etc.)."""
        ...

    @abstractmethod
    def get_current_phase(self) -> Phase:
        """Return the current phase descriptor."""
        ...

    @abstractmethod
    def get_observation(self, agent_name: str) -> Observation:
        """Build the observation for a specific agent. Information asymmetry lives here."""
        ...

    @abstractmethod
    def apply_action(self, agent_name: str, action: str) -> ActionResult:
        """Validate and apply an action, mutating game state."""
        ...

    @abstractmethod
    def advance_phase(self) -> Phase | None:
        """Move to the next phase. Returns new Phase, or None if game is over."""
        ...

    @abstractmethod
    def is_terminal(self) -> bool:
        """Has the game ended?"""
        ...

    @abstractmethod
    def get_outcome(self) -> GameOutcome:
        """Return the final game result. Only valid after is_terminal()."""
        ...

    @abstractmethod
    def get_game_state_for_scoring(self) -> dict[str, Any]:
        """Return full game state for scorers (roles, actions, votes, etc.)."""
        ...

    def process_discussion(self, agent_name: str, content: str, phase: Phase) -> None:
        """Optional hook: process free-text discussion content.

        Called by the game solver after generating discussion content.
        Default: no-op. Override in environments that need non-tool processing
        (e.g., debate tracks first-speaker status).
        """

    # ── Tool calling interface ─────────────────────────────────────────

    def get_tools(self, agent_name: str, phase: Phase) -> list[ToolInfo]:
        """Tool schemas available to this agent in this phase.

        Default: empty list (no tools). Override in environments that use
        structured actions (Werewolf, Diplomacy).
        """
        return []

    def get_tool_choice(self, phase: Phase) -> str | None:
        """Tool choice setting for model.generate().

        Default: ``"any"`` for ACTION (must call a tool), ``None`` for
        DISCUSSION (no tools). Override for environments with discussion
        tools (e.g., Diplomacy messaging returns ``"auto"``).
        """
        if phase.phase_type == PhaseType.ACTION:
            return "any"
        return None

    def tool_calls_to_action(self, agent_name: str, tool_calls: list[ToolCall]) -> str:
        """Convert ACTION-phase tool calls to an action string for apply_action.

        Raises ValueError if tool calls are missing or malformed.
        """
        raise NotImplementedError

    def process_tool_calls(
        self, agent_name: str, tool_calls: list[ToolCall], phase: Phase
    ) -> list[str]:
        """Process DISCUSSION-phase tool calls (message routing, promises).

        Returns a response string per tool call (for ChatMessageTool content).
        Default: empty list.
        """
        return []
