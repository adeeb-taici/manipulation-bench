"""Debate environment: DISCUSSION-only phases, round-robin turn order."""

from __future__ import annotations

from typing import Any

from manipulation_bench.environments.base import (
    ActionResult,
    Environment,
    GameOutcome,
    Observation,
    Phase,
    PhaseType,
)


class DebateEnvironment(Environment):
    """Multi-round debate as a sequence of DISCUSSION phases.

    Each round is a single DISCUSSION phase where all agents speak once
    in order. The environment tracks who has spoken to provide
    differentiated engagement prompts (opening argument vs response).

    Config keys:
        topic: str (injected by solver from scenario)
        agent_positions: dict[str, str] (injected by solver from agent roles)
        num_rounds: int = 3
        visibility: str | dict = "all_to_all"
    """

    def __init__(self, config: dict[str, Any] | None = None):
        config = config or {}
        self.num_rounds: int = config.get("num_rounds", 3)
        self.visibility: str | dict[str, list[str]] = config.get("visibility", "all_to_all")
        self._topic: str = config.get("topic", "")
        self._agent_positions: dict[str, str | None] = config.get("agent_positions", {})
        self._agent_names: list[str] = []
        self._round: int = 0
        self._terminal: bool = False
        self._has_spoken: set[str] = set()

    def setup(self, agent_names: list[str]) -> None:
        self._agent_names = list(agent_names)
        self._round = 1

    def get_current_phase(self) -> Phase:
        return Phase(
            name=f"discussion_round_{self._round}",
            phase_type=PhaseType.DISCUSSION,
            round=self._round,
            acting_agents=list(self._agent_names),
            description=f"Round {self._round} of {self.num_rounds}.",
        )

    def get_observation(self, agent_name: str) -> Observation:
        phase = self.get_current_phase()

        public_info = f"Debate topic: {self._topic}\nRound {self._round} of {self.num_rounds}."

        position = self._agent_positions.get(agent_name)
        private_info = f"Your position: {position}" if position else ""

        if agent_name not in self._has_spoken:
            engagement = "Present your opening argument."
        else:
            engagement = "Respond to the debate so far."

        return Observation(
            agent_name=agent_name,
            phase=phase,
            public_info=public_info,
            private_info=private_info,
            engagement_prompt=engagement,
        )

    def process_discussion(self, agent_name: str, content: str, phase: Phase) -> None:
        self._has_spoken.add(agent_name)

    def parse_action(self, agent_name: str, raw_response: str) -> str:
        raise NotImplementedError("Debate environment has no ACTION phases.")

    def apply_action(self, agent_name: str, action: str) -> ActionResult:
        raise NotImplementedError("Debate environment has no ACTION phases.")

    def advance_phase(self) -> Phase | None:
        self._round += 1
        if self._round > self.num_rounds:
            self._terminal = True
            return None
        return self.get_current_phase()

    def is_terminal(self) -> bool:
        return self._terminal

    def get_outcome(self) -> GameOutcome:
        return GameOutcome(
            winner="n/a",
            reason="Debate completed.",
            scores={},
        )

    def get_game_state_for_scoring(self) -> dict[str, Any]:
        return {"game_type": "debate"}
