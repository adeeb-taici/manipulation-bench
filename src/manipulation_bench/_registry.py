"""Inspect entry-point: import tasks lazily for discovery."""

_TASKS = {
    "bargaining_bench": "manipulation_bench.bargaining_task",
    "diplomacy_bench": "manipulation_bench.diplomacy_task",
    "village_bench": "manipulation_bench.village_task",
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
