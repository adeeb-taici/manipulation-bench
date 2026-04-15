# src/manipulation_bench/protocols.py
"""Canonical protocol definitions for manipulation-bench.

All structural protocols (interfaces) live here. Concrete implementations
import from this module.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from manipulation_bench.network import Message, Network, Node


class PromptContext:
    """Shared context available to all prompt blocks."""

    __slots__ = ("node", "network", "scenario_name", "round", "inbox", "node_state")

    def __init__(
        self,
        node: Node,
        network: Network,
        scenario_name: str,
        round: int,
        inbox: dict[str, list[Message]],
        node_state: Any,
    ) -> None:
        self.node = node
        self.network = network
        self.scenario_name = scenario_name
        self.round = round
        self.inbox = inbox
        self.node_state = node_state


@runtime_checkable
class ConversationStyle(Protocol):
    """Protocol for conversation pacing and social norms."""

    name: str

    def participation_prompt(self, ctx: PromptContext) -> str: ...


@runtime_checkable
class ContextStrategy(Protocol):
    """Protocol for controlling agent memory/context."""

    name: str

    def build_history(
        self,
        full_history: list[dict],
        system_prompt: str,
        user_prompt: str,
    ) -> list[dict]: ...


class NotebookStrategy(ContextStrategy, Protocol):
    """Extended context strategy that maintains a per-node notebook."""

    def get_notebook(self, node_id: str) -> str: ...
    def update_notebook(self, node_id: str, round_num: int, summary: str) -> None: ...


@runtime_checkable
class PlatformBridge(Protocol):
    """Protocol for optional platform integration."""

    async def setup(self, channels: dict) -> None: ...
    async def post_message(
        self, channel_id: str, sender_name: str, content: str, round: int
    ) -> None: ...
    async def collect_human_messages(self, round: int, timeout: float) -> list[Message]: ...
    async def mark_round(self, round: int) -> None: ...
    async def teardown(self) -> None: ...


@runtime_checkable
class StanceClassifier(Protocol):
    """Protocol for classifying stance from text."""

    def classify(self, text: str, claim: str) -> str: ...
