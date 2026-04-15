"""Turn-based conversation style — back-and-forth dialogue."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from manipulation_bench.protocols import PromptContext


class TurnBased:
    """Only agents who were addressed or have something to say participate."""
    name = "turn_based"

    def participation_prompt(self, ctx: PromptContext) -> str:
        node = ctx.node
        name = node.persona.name
        was_mentioned = self._was_mentioned(name, ctx.inbox)

        lines = ["This is a structured discussion. People take turns speaking.", ""]

        if was_mentioned:
            lines.append("Someone addressed you directly. You should respond.")
        else:
            lines.append(
                "No one addressed you this round. Only speak if you have "
                "something important to add. Otherwise, respond with [SILENT]."
            )

        lines.extend(["", "Keep responses brief — 1-2 sentences.", "Address the person you're replying to by name."])
        return "\n".join(lines)

    @staticmethod
    def _was_mentioned(name: str, inbox: dict) -> bool:
        name_lower = name.lower()
        for msgs in inbox.values():
            for msg in msgs:
                if name_lower in msg.content.lower():
                    return True
        return False
