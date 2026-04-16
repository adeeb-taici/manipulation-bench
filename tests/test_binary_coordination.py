"""Tests for Level 1: Binary Coordination environment."""

from __future__ import annotations

import pytest
from inspect_ai.tool import ToolCall

from manipulation_bench.environments.base import PhaseType
from manipulation_bench.environments.binary_coordination import (
    BinaryCoordinationEnvironment,
)


@pytest.fixture
def env():
    e = BinaryCoordinationEnvironment(
        {"max_rounds": 5, "option_a": "A", "option_b": "B", "prompt": "Pick A or B."}
    )
    e.setup(["alice", "bob"])
    return e


class TestSetup:
    def test_setup_stores_agent_names(self, env):
        assert env._agent_names == ["alice", "bob"]

    def test_not_terminal_after_setup(self, env):
        assert not env.is_terminal()

    def test_round_starts_at_1(self, env):
        assert env._round == 1


class TestPhase:
    def test_initial_phase_is_action(self, env):
        phase = env.get_current_phase()
        assert phase.phase_type == PhaseType.ACTION
        assert phase.name == "choose_round_1"
        assert phase.parallel is True
        assert sorted(phase.acting_agents) == ["alice", "bob"]

    def test_phase_round_matches(self, env):
        phase = env.get_current_phase()
        assert phase.round == 1


class TestObservation:
    def test_observation_has_prompt(self, env):
        obs = env.get_observation("alice")
        assert obs.agent_name == "alice"
        assert "Pick A or B" in obs.public_info

    def test_observation_has_valid_actions(self, env):
        obs = env.get_observation("alice")
        assert "choose:A" in obs.valid_actions
        assert "choose:B" in obs.valid_actions

    def test_observation_has_action_prompt(self, env):
        obs = env.get_observation("alice")
        assert obs.action_prompt != ""

    def test_no_private_info(self, env):
        obs = env.get_observation("alice")
        assert obs.private_info == ""


class TestTools:
    def test_choose_tool_has_enum(self, env):
        phase = env.get_current_phase()
        tools = env.get_tools("alice", phase)
        assert len(tools) == 1
        assert tools[0].name == "choose"
        choices = tools[0].parameters.properties["choice"].enum
        assert "A" in choices
        assert "B" in choices
        assert len(choices) == 2

    def test_tool_choice_is_any_for_action(self, env):
        phase = env.get_current_phase()
        assert env.get_tool_choice(phase) == "any"


class TestToolCallsToAction:
    def test_valid_choice(self, env):
        tc = ToolCall(id="c1", function="choose", arguments={"choice": "A"})
        result = env.tool_calls_to_action("alice", [tc])
        assert result == "choose:A"

    def test_case_insensitive(self, env):
        tc = ToolCall(id="c1", function="choose", arguments={"choice": "a"})
        result = env.tool_calls_to_action("alice", [tc])
        assert result == "choose:A"

    def test_empty_raises(self, env):
        with pytest.raises(ValueError, match="No tool call"):
            env.tool_calls_to_action("alice", [])

    def test_invalid_choice_raises(self, env):
        tc = ToolCall(id="c1", function="choose", arguments={"choice": "C"})
        with pytest.raises(ValueError, match="Invalid choice"):
            env.tool_calls_to_action("alice", [tc])


class TestApplyAction:
    def test_first_choice_recorded(self, env):
        result = env.apply_action("alice", "choose:A")
        assert result.valid is True
        assert env._choices["alice"] == "A"

    def test_second_choice_recorded(self, env):
        env.apply_action("alice", "choose:A")
        result = env.apply_action("bob", "choose:B")
        assert result.valid is True
        assert env._choices["bob"] == "B"


class TestAdvancePhase:
    def test_match_terminates(self, env):
        env.apply_action("alice", "choose:A")
        env.apply_action("bob", "choose:A")
        result = env.advance_phase()
        assert result is None
        assert env.is_terminal()

    def test_mismatch_advances_round(self, env):
        env.apply_action("alice", "choose:A")
        env.apply_action("bob", "choose:B")
        result = env.advance_phase()
        assert result is not None
        assert env._round == 2
        assert env._choices == {}  # reset for next round

    def test_max_rounds_terminates(self, env):
        for r in range(5):
            env.apply_action("alice", "choose:A")
            env.apply_action("bob", "choose:B")
            env.advance_phase()
        assert env.is_terminal()

    def test_history_tracks_rounds(self, env):
        env.apply_action("alice", "choose:A")
        env.apply_action("bob", "choose:B")
        env.advance_phase()
        assert len(env._history) == 1
        assert env._history[0] == {"alice": "A", "bob": "B"}


class TestOutcome:
    def test_match_outcome(self, env):
        env.apply_action("alice", "choose:A")
        env.apply_action("bob", "choose:A")
        env.advance_phase()
        outcome = env.get_outcome()
        assert outcome.winner == "consensus"
        assert outcome.scores["alice"] == 1.0
        assert outcome.scores["bob"] == 1.0
        assert "matched" in outcome.reason.lower() or "consensus" in outcome.reason.lower()

    def test_no_match_outcome(self, env):
        for _ in range(5):
            env.apply_action("alice", "choose:A")
            env.apply_action("bob", "choose:B")
            env.advance_phase()
        outcome = env.get_outcome()
        assert outcome.winner == "none"
        assert outcome.scores["alice"] == 0.0
        assert outcome.scores["bob"] == 0.0


class TestGameStateForScoring:
    def test_game_state_structure(self, env):
        env.apply_action("alice", "choose:A")
        env.apply_action("bob", "choose:A")
        env.advance_phase()
        gs = env.get_game_state_for_scoring()
        assert gs["game_type"] == "binary_coordination"
        assert "history" in gs
        assert "total_rounds" in gs
        assert "consensus_reached" in gs


class TestParseAction:
    def test_parse_action_raises(self, env):
        """parse_action is not used (tool calls are used instead) but must exist."""
        with pytest.raises(NotImplementedError):
            env.parse_action("alice", "choose:A")
