"""Context strategy implementations."""
from manipulation_bench.context_strategies.current_round import CurrentRoundOnly
from manipulation_bench.context_strategies.full_history import FullHistory
from manipulation_bench.context_strategies.notebook import Notebook
from manipulation_bench.context_strategies.sliding_window import SlidingWindow

CONTEXT_STRATEGIES: dict[str, type] = {
    "full_history": FullHistory,
    "current_round": CurrentRoundOnly,
    "sliding_window": SlidingWindow,
    "notebook": Notebook,
}


def make_context_strategy(name: str, **kwargs):
    """Create a context strategy by name."""
    cls = CONTEXT_STRATEGIES.get(name)
    if cls is None:
        raise ValueError(f"Unknown context strategy: {name}. Options: {list(CONTEXT_STRATEGIES)}")
    return cls(**kwargs)


__all__ = [
    "CONTEXT_STRATEGIES",
    "CurrentRoundOnly",
    "FullHistory",
    "Notebook",
    "SlidingWindow",
    "make_context_strategy",
]
