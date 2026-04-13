from __future__ import annotations

from typing import Protocol

from manipulation_bench.models import InteractionState


class TurnProtocol(Protocol):
    """Determines the next speaker given current interaction state."""

    def next_speaker(self, state: InteractionState) -> str | None:
        """Return agent name of the next speaker, or None if the round is complete."""
        ...


class RoundRobinProtocol:
    """Agents take turns in the order they appear in agent_names."""

    def next_speaker(self, state: InteractionState) -> str | None:
        if not state.agent_names:
            return None
        agent_count = len(state.agent_names)
        turns_this_round = [t for t in state.turns if t.round == state.current_round]
        if len(turns_this_round) >= agent_count:
            return None
        return state.agent_names[len(turns_this_round)]


PROTOCOLS: dict[str, type] = {
    "round_robin": RoundRobinProtocol,
}


def get_protocol(name: str, **kwargs: object) -> TurnProtocol:
    if name not in PROTOCOLS:
        raise ValueError(f"Unknown protocol: {name!r}. Available: {list(PROTOCOLS)}")
    return PROTOCOLS[name](**kwargs)
