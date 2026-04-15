"""Shared fixtures for manipulation-bench tests."""

from __future__ import annotations

import pytest

from manipulation_bench.environments.debate import DebateEnvironment
from manipulation_bench.environments.werewolf import WerewolfEnvironment

try:
    from manipulation_bench.environments.diplomacy import DiplomacyEnvironment

    HAS_DIPLOMACY = True
except ImportError:
    HAS_DIPLOMACY = False

_ENV_PARAMS = ["debate", "misinformation", "werewolf"] + (["diplomacy"] if HAS_DIPLOMACY else [])


@pytest.fixture(params=_ENV_PARAMS)
def environment(request):
    """Parameterized fixture yielding each Environment subclass, already set up."""
    if request.param == "debate":
        env = DebateEnvironment({"num_rounds": 2, "topic": "Test topic"})
        env.setup(["alice", "bob"])
        return env
    elif request.param == "werewolf":
        env = WerewolfEnvironment(
            {
                "num_werewolves": 1,
                "has_seer": False,
                "max_rounds": 3,
                "seed": 42,
                "role_assignments": {"alice": "werewolf", "bob": "villager", "carol": "villager"},
            }
        )
        env.setup(["alice", "bob", "carol"])
        return env
    elif request.param == "misinformation":
        from manipulation_bench.environments.misinformation import MisinformationEnvironment
        from manipulation_bench.network import broadcast
        from manipulation_bench.agents import PersonaCard

        env = MisinformationEnvironment(
            {"claim": "Test claim for fixture", "seed_agent": "alice", "max_rounds": 3}
        )
        personas = [PersonaCard(name=n, role="agent") for n in ["alice", "bob", "carol"]]
        network = broadcast(personas)
        env.setup(["alice", "bob", "carol"], network=network)
        return env
    elif request.param == "diplomacy":
        env = DiplomacyEnvironment({"max_years": 1, "negotiation_rounds": 1})
        env.setup(["austria", "england", "france", "germany", "italy", "russia", "turkey"])
        return env
