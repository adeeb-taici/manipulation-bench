"""Inspect entry-point: import tasks lazily for discovery."""

_TASKS = {
    "binary_coordination_bench": "manipulation_bench.consensus_tasks",
    "naming_game_bench": "manipulation_bench.consensus_tasks",
    "continuous_convergence_bench": "manipulation_bench.consensus_tasks",
    "deliberative_consensus_bench": "manipulation_bench.consensus_tasks",
    "biased_deliberation_bench": "manipulation_bench.consensus_tasks",
    "diplomacy_bench": "manipulation_bench.diplomacy_task",
    "werewolf_bench": "manipulation_bench.game_task",
    "manipulation_bench": "manipulation_bench.task",
}


def __getattr__(name: str):
    if name in _TASKS:
        import importlib

        module = importlib.import_module(_TASKS[name])
        task = getattr(module, name)
        globals()[name] = task
        return task
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return list(_TASKS) + list(globals())
