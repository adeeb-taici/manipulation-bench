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

_ENV_PARAMS = ["debate", "naming_game", "werewolf"] + (["diplomacy"] if HAS_DIPLOMACY else [])


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
    elif request.param == "naming_game":
        from manipulation_bench.environments.naming_game import NamingGameEnvironment

        env = NamingGameEnvironment(
            {
                "object_description": "A glowing sphere that hovers and hums.",
                "topology": "broadcast",
                "attribution": "anonymous",
                "convergence": "strict",
                "max_rounds": 5,
                "seed": 0,
            }
        )
        env.setup(["alice", "bob", "carol", "dave"])
        return env
    elif request.param == "diplomacy":
        env = DiplomacyEnvironment({"max_years": 1, "negotiation_rounds": 1})
        env.setup(["austria", "england", "france", "germany", "italy", "russia", "turkey"])
        return env
