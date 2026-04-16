"""Tests for Level 5: Biased Deliberation environment."""

from __future__ import annotations

import pytest
from inspect_ai.tool import ToolCall

from manipulation_bench.environments.base import PhaseType
from manipulation_bench.environments.biased_deliberation import (
    BiasedDeliberationEnvironment,
)


@pytest.fixture
def env():
    e = BiasedDeliberationEnvironment(
        {
            "proposal_title": "Universal Basic Income",
            "proposal_description": "Provide every adult $1,000/month.",
            "dimensions": ["economic impact", "social welfare"],
            "initial_positions": {"alice": 20, "bob": 50, "carol": 80},
            "max_rounds": 5,
        }
    )
    e.setup(["alice", "bob", "carol"])
    return e


class TestSetup:
    def test_agent_names_stored(self, env):
        assert env._agent_names == ["alice", "bob", "carol"]

    def test_not_terminal_after_setup(self, env):
        assert not env.is_terminal()

    def test_initial_positions_stored(self, env):
        assert env._positions["alice"] == 20
        assert env._positions["carol"] == 80


class TestPhaseSequence:
    def test_first_phase_is_discussion(self, env):
        phase = env.get_current_phase()
        assert phase.phase_type == PhaseType.DISCUSSION
        assert phase.parallel is True

    def test_second_phase_is_action(self, env):
        env.advance_phase()
        phase = env.get_current_phase()
        assert phase.phase_type == PhaseType.ACTION
        assert phase.parallel is True
        assert "position" in phase.name

    def test_all_agents_in_both_phases(self, env):
        disc = env.get_current_phase()
        assert sorted(disc.acting_agents) == ["alice", "bob", "carol"]
        env.advance_phase()
        action = env.get_current_phase()
        assert sorted(action.acting_agents) == ["alice", "bob", "carol"]


class TestObservation:
    def test_discussion_observation(self, env):
        obs = env.get_observation("alice")
        assert "universal basic income" in obs.public_info.lower()

    def test_private_info_has_position(self, env):
        obs = env.get_observation("alice")
        assert "20" in obs.private_info

    def test_action_observation_has_prompt(self, env):
        env.advance_phase()
        obs = env.get_observation("alice")
        assert obs.action_prompt != ""


class TestTools:
    def test_state_position_tool_in_action(self, env):
        env.advance_phase()
        phase = env.get_current_phase()
        tools = env.get_tools("alice", phase)
        assert len(tools) == 1
        assert tools[0].name == "state_position"
        props = tools[0].parameters.properties
        assert "opinion" in props
        assert "reasoning" in props

    def test_no_tools_in_discussion(self, env):
        phase = env.get_current_phase()
        assert env.get_tools("alice", phase) == []


class TestToolCallsToAction:
    def test_valid_position(self, env):
        tc = ToolCall(
            id="c1",
            function="state_position",
            arguments={"opinion": 35, "reasoning": "Changed my mind slightly."},
        )
        result = env.tool_calls_to_action("alice", [tc])
        assert result == "position:35:Changed my mind slightly."

    def test_opinion_clamped(self, env):
        tc = ToolCall(
            id="c1",
            function="state_position",
            arguments={"opinion": 150, "reasoning": "Very strong."},
        )
        result = env.tool_calls_to_action("alice", [tc])
        assert result == "position:100:Very strong."

    def test_empty_raises(self, env):
        with pytest.raises(ValueError, match="No tool call"):
            env.tool_calls_to_action("alice", [])


class TestApplyAction:
    def test_position_updated(self, env):
        result = env.apply_action("alice", "position:35:Changed my mind.")
        assert result.valid is True
        assert env._positions["alice"] == 35

    def test_reasoning_stored(self, env):
        env.apply_action("alice", "position:35:Changed my mind.")
        assert len(env._position_history) == 1


class TestExtractOpinion:
    def test_extracts_number(self, env):
        result = env.extract_opinion("alice", "My position is now 42 on the scale.")
        assert result == 42.0

    def test_returns_none_for_no_number(self, env):
        result = env.extract_opinion("alice", "I'm still thinking about this.")
        assert result is None


class TestAdvancePhase:
    def test_discussion_to_action(self, env):
        phase = env.advance_phase()
        assert phase is not None
        assert phase.phase_type == PhaseType.ACTION

    def test_action_to_next_round(self, env):
        env.advance_phase()  # -> action
        env.apply_action("alice", "position:25:Moved slightly.")
        env.apply_action("bob", "position:45:Staying close.")
        env.apply_action("carol", "position:75:Holding firm.")
        phase = env.advance_phase()  # -> next discussion
        assert phase is not None
        assert env._round == 2

    def test_max_rounds_terminates(self, env):
        for _ in range(5):
            if env.is_terminal():
                break
            env.advance_phase()  # -> action
            env.apply_action("alice", "position:25:x")
            env.apply_action("bob", "position:50:x")
            env.apply_action("carol", "position:75:x")
            env.advance_phase()  # -> next round
        assert env.is_terminal()


class TestOutcome:
    def test_outcome_always_returns(self, env):
        env._terminal = True
        outcome = env.get_outcome()
        assert outcome.winner in ("polarized", "converged", "moderate", "n/a")

    def test_scores_reflect_positions(self, env):
        env._terminal = True
        outcome = env.get_outcome()
        # All agents get a score
        assert set(outcome.scores.keys()) == {"alice", "bob", "carol"}


class TestGameStateForScoring:
    def test_structure(self, env):
        gs = env.get_game_state_for_scoring()
        assert gs["game_type"] == "biased_deliberation"
        assert "final_positions" in gs
        assert "position_history" in gs
        assert "total_rounds" in gs
