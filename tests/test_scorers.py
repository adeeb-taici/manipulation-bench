"""Unit tests for scorer helpers."""

from __future__ import annotations

from manipulation_bench.models import InteractionState, Turn
from manipulation_bench.scorers._helpers import format_transcript, parse_json_score


class TestParseJsonScore:
    def test_plain_json(self):
        result = parse_json_score('{"score": 0.7, "reasoning": "Good"}')
        assert result["score"] == 0.7

    def test_markdown_fenced(self):
        result = parse_json_score('```json\n{"score": 0.3}\n```')
        assert result["score"] == 0.3

    def test_json_in_text(self):
        result = parse_json_score('Here is my analysis: {"score": 0.5, "reasoning": "ok"}')
        assert result["score"] == 0.5

    def test_unparseable_returns_default(self):
        result = parse_json_score("This is not JSON at all")
        assert result["score"] == 0.5

    def test_empty_string(self):
        result = parse_json_score("")
        assert result["score"] == 0.5


class TestFormatTranscript:
    def test_format_basic(self):
        interaction = InteractionState()
        interaction.turns = [
            Turn(speaker="alice", content="Hello", round=0, turn_index=0),
            Turn(speaker="bob", content="Hi", round=0, turn_index=1),
        ]
        text = format_transcript(interaction)
        assert "[alice, Round 1]" in text
        assert "[bob, Round 1]" in text
        assert "Hello" in text
        assert "Hi" in text

    def test_format_empty(self):
        interaction = InteractionState()
        interaction.turns = []
        text = format_transcript(interaction)
        assert text == ""
