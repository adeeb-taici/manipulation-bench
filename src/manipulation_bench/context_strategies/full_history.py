"""Full history context strategy — perfect agent memory."""
from __future__ import annotations


class FullHistory:
    """Pass all prior conversation turns to the LLM."""
    name = "full_history"

    def build_history(self, full_history: list[dict], system_prompt: str, user_prompt: str) -> list[dict]:
        msgs = [{"role": "system", "content": system_prompt}]
        msgs.extend(full_history)
        msgs.append({"role": "user", "content": user_prompt})
        return msgs
