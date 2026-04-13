from manipulation_bench.environments.base import (
    ActionResult,
    Environment,
    GameOutcome,
    Observation,
    Phase,
    PhaseType,
)

ENVIRONMENTS: dict[str, type[Environment]] = {}


def create_environment(config: dict) -> Environment:
    """Factory: create an Environment from a scenario metadata dict.

    config = {"type": "werewolf", "num_werewolves": 1, "has_seer": true, ...}
    """
    env_type = config.get("type", "")
    if env_type not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {env_type!r}. Available: {list(ENVIRONMENTS)}")
    return ENVIRONMENTS[env_type](config)


__all__ = [
    "ActionResult",
    "Environment",
    "GameOutcome",
    "Observation",
    "Phase",
    "PhaseType",
    "create_environment",
]
