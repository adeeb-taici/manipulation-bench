"""Tests for context strategy implementations."""
import pytest

from manipulation_bench.context_strategies import CONTEXT_STRATEGIES, make_context_strategy
from manipulation_bench.context_strategies.full_history import FullHistory
from manipulation_bench.context_strategies.sliding_window import SlidingWindow
from manipulation_bench.context_strategies.current_round import CurrentRoundOnly
from manipulation_bench.context_strategies.notebook import Notebook


def _history(n_rounds: int) -> list[dict]:
    h = []
    for i in range(n_rounds):
        h.append({"role": "user", "content": f"user-{i}"})
        h.append({"role": "assistant", "content": f"assistant-{i}"})
    return h


class TestFullHistory:
    def test_includes_all_turns(self):
        s = FullHistory()
        history = _history(5)
        result = s.build_history(history, "sys", "user-now")
        assert result[0] == {"role": "system", "content": "sys"}
        assert len(result) == 1 + 10 + 1
        assert result[-1] == {"role": "user", "content": "user-now"}


class TestCurrentRoundOnly:
    def test_no_history(self):
        s = CurrentRoundOnly()
        history = _history(5)
        result = s.build_history(history, "sys", "user-now")
        assert len(result) == 2
        assert result[0]["content"] == "sys"
        assert result[1]["content"] == "user-now"


class TestSlidingWindow:
    def test_keeps_last_n_rounds(self):
        s = SlidingWindow(window_size=2)
        history = _history(5)
        result = s.build_history(history, "sys", "user-now")
        assert len(result) == 6
        assert result[1]["content"] == "user-3"

    def test_short_history_kept_fully(self):
        s = SlidingWindow(window_size=10)
        history = _history(2)
        result = s.build_history(history, "sys", "user-now")
        assert len(result) == 1 + 4 + 1


class TestNotebook:
    def test_empty_notebook(self):
        s = Notebook()
        text = s.get_notebook("node_0")
        assert "empty" in text.lower()

    def test_update_and_get(self):
        s = Notebook()
        s.update_notebook("node_0", 0, "saw a claim about X")
        s.update_notebook("node_0", 1, "Bob agreed with X")
        text = s.get_notebook("node_0")
        assert "Round 0" in text
        assert "Round 1" in text

    def test_max_entries_enforced(self):
        s = Notebook(max_entries=3)
        for i in range(10):
            s.update_notebook("node_0", i, f"summary-{i}")
        text = s.get_notebook("node_0")
        assert "summary-7" in text
        assert "summary-9" in text
        assert "summary-0" not in text

    def test_build_history_no_raw_history(self):
        s = Notebook()
        result = s.build_history(_history(5), "sys", "user-now")
        assert len(result) == 2


class TestRegistry:
    def test_all_strategies_registered(self):
        assert "full_history" in CONTEXT_STRATEGIES
        assert "current_round" in CONTEXT_STRATEGIES
        assert "sliding_window" in CONTEXT_STRATEGIES
        assert "notebook" in CONTEXT_STRATEGIES

    def test_make_context_strategy(self):
        s = make_context_strategy("sliding_window", window_size=2)
        assert s.name == "sliding_window"

    def test_make_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            make_context_strategy("nonexistent")
