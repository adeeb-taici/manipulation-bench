"""Pluggable manipulation defenses.

Resolve from the CLI with ``-T mitigations=prompt_suffix,critic_monitor`` (see
:mod:`manipulation_bench.mitigations._resolve`). Add a new defense by
subclassing :class:`Mitigation` — see ``examples/new_mitigation/``.
"""

from manipulation_bench.mitigations.base import Mitigation
from manipulation_bench.mitigations.critic_monitor import critic_monitor
from manipulation_bench.mitigations.prompt_suffix import prompt_suffix

__all__ = ["Mitigation", "prompt_suffix", "critic_monitor"]
