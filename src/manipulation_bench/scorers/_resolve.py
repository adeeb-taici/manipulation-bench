"""Pluggable scorer resolver.

Each ``@task`` accepts a ``scorers`` parameter (default: ``"default"``)
that lets users override the hardcoded scorer list from the CLI:

    inspect eval src/manipulation_bench/task.py \\
        -T scorers='manipulation_detection,argument_quality'

    mb run debate --model openrouter/... \\
        -T scorers=examples.new_scorer.my_scorer.guess_accuracy

Resolution rules for ``spec``:

  - ``None`` or ``"default"`` — task supplies its own list (sentinel).
    ``resolve_scorers`` returns ``None``; callers fall back to the
    hardcoded default.
  - A pre-built ``list`` of ``Scorer`` instances — used as-is.
  - A comma- or whitespace-separated ``str`` of names. Each name is
    one of:
      * A bare name like ``manipulation_detection`` — looked up in
        ``manipulation_bench.scorers``.
      * A dotted path like ``my_pkg.my_module.my_scorer`` — imported
        via ``importlib`` and the attribute is the scorer factory.
    Each resolved factory is called with no args to produce a
    ``Scorer`` instance.

If a name is unknown, ``resolve_scorers`` raises ``ValueError`` so the
task fails fast with a clear message.
"""

from __future__ import annotations

import importlib
from typing import Any

DEFAULT_SENTINELS = {None, "default", "DEFAULT"}


def resolve_scorers(spec: Any) -> list | None:
    """Turn a CLI/keyword spec into a list of Scorer instances.

    Returns ``None`` to mean "use the task's own default list" — let
    callers handle the sentinel rather than baking a default here.
    """
    # Inspect's `-T scorers=a,b,c` flag splits on commas and passes a
    # list[str]. A pre-built list[Scorer] is also valid.
    if isinstance(spec, list):
        if not spec:
            return None
        if all(isinstance(item, str) for item in spec):
            names = [n.strip() for n in spec if n and n.strip()]
            return [_resolve_one(name) for name in names] if names else None
        return spec  # assume list of Scorer instances
    if spec in DEFAULT_SENTINELS:
        return None
    if not isinstance(spec, str):
        raise TypeError(
            f"scorers spec must be None, 'default', a list, or a string; got {type(spec).__name__}"
        )
    names = [n.strip() for chunk in spec.replace(";", ",").split(",") for n in chunk.split()]
    names = [n for n in names if n]
    if not names:
        return None
    return [_resolve_one(name) for name in names]


def _resolve_one(name: str):
    """Resolve a single scorer name to a Scorer instance.

    Bare names hit ``manipulation_bench.scorers``; dotted names are
    imported via ``importlib``.
    """
    if "." in name:
        module_path, attr = name.rsplit(".", 1)
        module = importlib.import_module(module_path)
    else:
        module = importlib.import_module("manipulation_bench.scorers")
        attr = name
    factory = getattr(module, attr, None)
    if factory is None:
        raise ValueError(
            f"unknown scorer {name!r}; "
            f"check the name (or import path) and that the module is on sys.path"
        )
    if not callable(factory):
        raise ValueError(f"scorer {name!r} is not callable; expected a factory function")
    return factory()
