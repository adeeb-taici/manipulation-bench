"""Current-round-only context strategy — no memory."""
from __future__ import annotations


class CurrentRoundOnly:
    """Only pass the current round's prompt — no history."""
    name = "current_round"

    def build_history(self, full_history: list[dict], system_prompt: str, user_prompt: str) -> list[dict]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
