"""Root conftest: ensure worktree src takes precedence over installed package."""

from __future__ import annotations

import sys
from pathlib import Path

# Insert this worktree's src directory first so its modules shadow the
# editable-installed package from the main worktree.
_worktree_src = str(Path(__file__).parent / "src")
if _worktree_src not in sys.path:
    sys.path.insert(0, _worktree_src)
