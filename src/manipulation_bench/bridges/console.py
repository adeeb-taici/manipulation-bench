"""Console bridge for development — prints messages to terminal."""
from __future__ import annotations

from manipulation_bench.network import Channel, Message


class ConsoleBridge:
    """Development bridge that prints messages to the terminal."""

    def __init__(self, interactive: bool = False) -> None:
        self._interactive = interactive
        self._channels: dict[str, Channel] = {}

    async def setup(self, channels: dict[str, Channel]) -> None:
        self._channels = channels
        print("=== Simulation started ===")
        for ch in channels.values():
            print(f"  Channel: {ch.name} ({ch.channel_type.value}) — {len(ch.members)} members")

    async def post_message(self, channel_id: str, sender_name: str, content: str, round: int) -> None:
        ch = self._channels.get(channel_id)
        ch_label = ch.name if ch else channel_id
        print(f"  [{ch_label}] {sender_name}: {content}")

    async def collect_human_messages(self, round: int, timeout: float) -> list[Message]:
        if not self._interactive:
            return []
        print(f"\n[Round {round}] Your turn (type message, empty line to skip):")
        try:
            line = input("> ").strip()
        except EOFError:
            return []
        if not line:
            return []
        return [Message(sender="human", channel_id="", content=line, round=round, metadata={})]

    async def mark_round(self, round: int) -> None:
        print(f"\n--- Round {round} complete ---\n")

    async def teardown(self) -> None:
        print("=== Simulation ended ===")
