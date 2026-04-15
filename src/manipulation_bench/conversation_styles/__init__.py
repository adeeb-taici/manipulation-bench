"""Conversation style implementations."""
from manipulation_bench.conversation_styles.event_driven import EventDriven
from manipulation_bench.conversation_styles.synchronized import Synchronized
from manipulation_bench.conversation_styles.turn_based import TurnBased
from manipulation_bench.protocols import ConversationStyle

CONVERSATION_STYLES: dict[str, ConversationStyle] = {
    "synchronized": Synchronized(),
    "event_driven": EventDriven(),
    "turn_based": TurnBased(),
}

__all__ = ["CONVERSATION_STYLES", "EventDriven", "Synchronized", "TurnBased"]
