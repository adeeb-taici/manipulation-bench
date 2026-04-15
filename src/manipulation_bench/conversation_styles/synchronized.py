"""Synchronized conversation style — every agent responds every round."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from manipulation_bench.protocols import PromptContext


class Synchronized:
    """Every agent responds in every channel every round."""
    name = "synchronized"

    def participation_prompt(self, ctx: PromptContext) -> str:
        channels = ctx.network.node_channels(ctx.node.id)
        if len(channels) <= 1:
            return "Respond to what you see. Keep your response to 2-3 sentences."
        return (
            "Respond in each of your channels separately. "
            "Include a separate message for each channel, each on its own line. "
            "Keep each message to 2-3 sentences."
        )
