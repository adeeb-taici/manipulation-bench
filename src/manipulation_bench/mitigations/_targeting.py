"""Targeting helper for mitigations.

Defenses need to know which agent is the manipulator (to harden / monitor)
versus who to protect. The canonical source is the typed ``AgentRole.adversary``
flag, set by generators. There is intentionally **no fallback** to legacy
metadata keys (``metadata['manipulative']`` / ``metadata['manipulator']`` /
committee ``interested_party_name``) — those remain the *scorer*-side record,
but defenses read only ``adversary`` so targeting has one unambiguous source.
"""

from __future__ import annotations

from manipulation_bench.models import AgentRole, ScenarioConfig


def is_adversary(agent: AgentRole, scenario: ScenarioConfig) -> bool:
    """Return True if ``agent`` is the designated manipulator / interested party."""
    return agent.adversary
