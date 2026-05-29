"""Pluggable mitigation resolver.

Each game ``@task`` accepts a ``mitigations`` parameter (default: ``"default"``)
that lets users turn defenses on from the CLI, exactly like ``scorers``:

    inspect eval src/manipulation_bench/task.py \\
        -T mitigations='prompt_suffix,critic_monitor'

    mb run debate --model openrouter/... \\
        -T mitigations=examples.new_mitigation.my_mitigation.my_defense

Resolution rules for ``spec``:

  - ``None`` or ``"default"`` — no mitigations. ``resolve_mitigations``
    returns ``None``; the solver runs undefended.
  - A pre-built ``list`` of ``Mitigation`` instances — used as-is.
  - A comma- or whitespace-separated ``str`` of names. Each name is
    one of:
      * A bare name like ``prompt_suffix`` — looked up in
        ``manipulation_bench.mitigations``.
      * A dotted path like ``my_pkg.my_module.my_defense`` — imported
        via ``importlib`` and the attribute is the mitigation factory.
    Each resolved factory is called with no args to produce a
    ``Mitigation`` instance.

If a name is unknown, ``resolve_mitigations`` raises ``ValueError`` so the
task fails fast with a clear message.
"""

from __future__ import annotations

import importlib
from typing import Any

DEFAULT_SENTINELS = {None, "default", "DEFAULT", ""}


def resolve_mitigations(spec: Any) -> list | None:
    """Turn a CLI/keyword spec into a list of Mitigation instances.

    Returns ``None`` to mean "no mitigations" — the solver runs undefended.
    """
    # Inspect's `-T mitigations=a,b` flag splits on commas and passes a
    # list[str]. A pre-built list[Mitigation] is also valid.
    if isinstance(spec, list):
        if not spec:
            return None
        if all(isinstance(item, str) for item in spec):
            names = [n.strip() for n in spec if n and n.strip()]
            return [_resolve_one(name) for name in names] if names else None
        return spec  # assume list of Mitigation instances
    if spec in DEFAULT_SENTINELS:
        return None
    if not isinstance(spec, str):
        raise TypeError(
            "mitigations spec must be None, 'default', a list, or a string; "
            f"got {type(spec).__name__}"
        )
    names = [n.strip() for chunk in spec.replace(";", ",").split(",") for n in chunk.split()]
    names = [n for n in names if n]
    if not names:
        return None
    return [_resolve_one(name) for name in names]


def _resolve_one(name: str):
    """Resolve a single mitigation name to a Mitigation instance.

    Bare names hit ``manipulation_bench.mitigations``; dotted names are
    imported via ``importlib``.
    """
    if "." in name:
        module_path, attr = name.rsplit(".", 1)
        module = importlib.import_module(module_path)
    else:
        module = importlib.import_module("manipulation_bench.mitigations")
        attr = name
    factory = getattr(module, attr, None)
    if factory is None:
        raise ValueError(
            f"unknown mitigation {name!r}; "
            f"check the name (or import path) and that the module is on sys.path"
        )
    if not callable(factory):
        raise ValueError(f"mitigation {name!r} is not callable; expected a factory function")
    return factory()
