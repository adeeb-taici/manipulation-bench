"""Sliding window context strategy — last N rounds of memory."""
from __future__ import annotations


class SlidingWindow:
    """Pass only the last N rounds of history."""
    name = "sliding_window"

    def __init__(self, window_size: int = 3) -> None:
        self.window_size = window_size

    def build_history(self, full_history: list[dict], system_prompt: str, user_prompt: str) -> list[dict]:
        keep = self.window_size * 2
        recent = full_history[-keep:] if len(full_history) > keep else full_history
        msgs = [{"role": "system", "content": system_prompt}]
        msgs.extend(recent)
        msgs.append({"role": "user", "content": user_prompt})
        return msgs
