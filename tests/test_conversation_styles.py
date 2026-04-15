"""Tests for conversation style implementations."""
from manipulation_bench.agents import PersonaCard
from manipulation_bench.conversation_styles import CONVERSATION_STYLES
from manipulation_bench.conversation_styles.synchronized import Synchronized
from manipulation_bench.conversation_styles.event_driven import EventDriven
from manipulation_bench.conversation_styles.turn_based import TurnBased
from manipulation_bench.network import Node, broadcast, Message
from manipulation_bench.protocols import PromptContext


def _make_ctx(assertiveness: float = 0.5, inbox: dict | None = None, round: int = 0) -> PromptContext:
    persona = PersonaCard(
        name="Alice", role="journalist",
        traits={"assertiveness": assertiveness},
    )
    net = broadcast([persona, PersonaCard(name="Bob", role="teacher")])
    node = net.nodes["node_0"]
    return PromptContext(
        node=node, network=net, scenario_name="test",
        round=round, inbox=inbox or {}, node_state=None,
    )


class TestSynchronized:
    def test_returns_string(self):
        s = Synchronized()
        assert s.name == "synchronized"
        result = s.participation_prompt(_make_ctx())
        assert isinstance(result, str)
        assert len(result) > 0


class TestEventDriven:
    def test_early_round_encourages_participation(self):
        s = EventDriven()
        result = s.participation_prompt(_make_ctx(round=0))
        assert "SILENT" in result

    def test_high_assertiveness_jumps_in(self):
        s = EventDriven()
        result = s.participation_prompt(_make_ctx(assertiveness=0.9))
        assert "jump" in result.lower()

    def test_low_assertiveness_lurks(self):
        s = EventDriven()
        result = s.participation_prompt(_make_ctx(assertiveness=0.1, round=2))
        assert "lurk" in result.lower()


class TestTurnBased:
    def test_not_mentioned_suggests_silence(self):
        s = TurnBased()
        result = s.participation_prompt(_make_ctx(round=2, inbox={}))
        assert "SILENT" in result

    def test_mentioned_suggests_response(self):
        s = TurnBased()
        inbox = {"general": [Message(sender="node_1", channel_id="general", content="What do you think, Alice?", round=1)]}
        result = s.participation_prompt(_make_ctx(round=2, inbox=inbox))
        assert "respond" in result.lower()


class TestRegistry:
    def test_all_styles_registered(self):
        assert "synchronized" in CONVERSATION_STYLES
        assert "event_driven" in CONVERSATION_STYLES
        assert "turn_based" in CONVERSATION_STYLES
