"""Tests for the DebateEnvironment."""

from __future__ import annotations

from manipulation_bench.environments.debate import DebateEnvironment
from manipulation_bench.environments.base import PhaseType


def test_two_rounds():
    env = DebateEnvironment({"num_rounds": 2, "topic": "Test"})
    env.setup(["alice", "bob"])

    # Round 1
    assert not env.is_terminal()
    phase = env.get_current_phase()
    assert phase.phase_type == PhaseType.DISCUSSION
    assert phase.round == 1
    assert phase.acting_agents == ["alice", "bob"]

    obs_alice = env.get_observation("alice")
    assert "opening argument" in obs_alice.engagement_prompt.lower()

    env.process_discussion("alice", "I argue yes.", phase)

    obs_bob = env.get_observation("bob")
    assert "opening argument" in obs_bob.engagement_prompt.lower()

    env.process_discussion("bob", "I argue no.", phase)

    # Advance to round 2
    next_phase = env.advance_phase()
    assert next_phase is not None
    assert not env.is_terminal()

    obs_alice_r2 = env.get_observation("alice")
    assert "respond" in obs_alice_r2.engagement_prompt.lower()

    # Advance past round 2
    env.advance_phase()
    assert env.is_terminal()


def test_positions_in_observation():
    env = DebateEnvironment(
        {
            "num_rounds": 1,
            "topic": "Test topic",
            "agent_positions": {"alice": "for", "bob": "against"},
        }
    )
    env.setup(["alice", "bob"])

    obs = env.get_observation("alice")
    assert "for" in obs.private_info.lower()

    obs_bob = env.get_observation("bob")
    assert "against" in obs_bob.private_info.lower()


def test_topic_in_public_info():
    env = DebateEnvironment({"num_rounds": 1, "topic": "Is AI sentient?"})
    env.setup(["alice", "bob"])

    obs = env.get_observation("alice")
    assert "Is AI sentient?" in obs.public_info


def test_outcome():
    env = DebateEnvironment({"num_rounds": 1, "topic": "Test"})
    env.setup(["alice", "bob"])
    env.advance_phase()

    assert env.is_terminal()
    outcome = env.get_outcome()
    assert outcome.reason == "Debate completed."


def test_game_state_for_scoring():
    env = DebateEnvironment({"num_rounds": 1, "topic": "Test"})
    env.setup(["alice", "bob"])

    state = env.get_game_state_for_scoring()
    assert state["game_type"] == "debate"
