"""Notebook context strategy — compressed per-round summaries."""
from __future__ import annotations


class Notebook:
    """Agent maintains a compressed notebook of key facts."""
    name = "notebook"

    def __init__(self, max_entries: int = 10) -> None:
        self.max_entries = max_entries
        self._notebooks: dict[str, list[str]] = {}

    def update_notebook(self, node_id: str, round_num: int, summary: str) -> None:
        if node_id not in self._notebooks:
            self._notebooks[node_id] = []
        entry = f"Round {round_num}: {summary}"
        self._notebooks[node_id].append(entry)
        if len(self._notebooks[node_id]) > self.max_entries:
            self._notebooks[node_id] = self._notebooks[node_id][-self.max_entries:]

    def get_notebook(self, node_id: str) -> str:
        entries = self._notebooks.get(node_id, [])
        if not entries:
            return "Your notebook is empty — this is the start of the conversation."
        return "Your notes from previous rounds:\n" + "\n".join(f"- {e}" for e in entries)

    def build_history(self, full_history: list[dict], system_prompt: str, user_prompt: str) -> list[dict]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
