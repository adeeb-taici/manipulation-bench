from manipulation_bench.environments.base import (
    ActionResult,
    Environment,
    GameOutcome,
    Observation,
    Phase,
    PhaseType,
)

from manipulation_bench.environments.bargaining import BargainingEnvironment
from manipulation_bench.environments.committee import CommitteeEnvironment
from manipulation_bench.environments.debate import DebateEnvironment
from manipulation_bench.environments.diplomacy import DiplomacyEnvironment
from manipulation_bench.environments.naming_game import NamingGameEnvironment
from manipulation_bench.environments.village import VillageEnvironment
from manipulation_bench.environments.werewolf import WerewolfEnvironment

ENVIRONMENTS: dict[str, type[Environment]] = {
    "bargaining": BargainingEnvironment,
    "committee": CommitteeEnvironment,
    "debate": DebateEnvironment,
    "diplomacy": DiplomacyEnvironment,
    "naming_game": NamingGameEnvironment,
    "village": VillageEnvironment,
    "werewolf": WerewolfEnvironment,
}


def create_environment(config: dict) -> Environment:
    """Factory: create an Environment from a scenario metadata dict.

    config = {"type": "werewolf", "num_werewolves": 1, "has_seer": true, ...}

    Defaults to "debate" when no type is specified (backward compat for
    debate scenarios that predate the environment system).
    """
    env_type = config.get("type", "debate")
    if env_type not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {env_type!r}. Available: {list(ENVIRONMENTS)}")
    return ENVIRONMENTS[env_type](config)


__all__ = [
    "ActionResult",
    "Environment",
    "GameOutcome",
    "NamingGameEnvironment",
    "Observation",
    "Phase",
    "PhaseType",
    "create_environment",
]
