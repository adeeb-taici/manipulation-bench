"""Backward-compatible re-export of the unified solver.

Import from ``manipulation_bench.solver`` instead.
"""

from manipulation_bench.solver import game_interaction  # noqa: F401
from manipulation_bench.solver import (  # noqa: F401
    _append_tool_errors,
    _build_game_messages,
    _build_game_transcript,
)
