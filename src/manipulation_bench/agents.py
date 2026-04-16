"""Minimal PersonaCard stub for network.py consumers.

The full traits/backstory/persona system lives on archive/phase-2-3-4a and will
be ported in a later PR as other consensus levels (binary coordination,
deliberative consensus) need it. For now, `network.py` only needs name + role.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PersonaCard:
    """Agent identity used by the network layer for labelled routing."""

    name: str
    role: str = ""
