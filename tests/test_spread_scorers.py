# tests/test_spread_scorers.py
"""Tests for spread scorer pure-computation functions."""

from __future__ import annotations

from manipulation_bench.scorers.spread import (
    _compute_belief_trajectory,
    _compute_resistance_rate,
    _compute_spread_rate,
    _compute_spread_speed,
)


class TestComputeSpreadRate:
    def test_no_adoption(self):
        # Only seed adopted, no non-seed adopters
        rate = _compute_spread_rate(
            agent_states={"alice": True, "bob": False, "carol": False},
            seed_agent="alice",
        )
        assert rate == 0.0

    def test_full_adoption(self):
        rate = _compute_spread_rate(
            agent_states={"alice": True, "bob": True, "carol": True},
            seed_agent="alice",
        )
        assert rate == 1.0

    def test_partial_adoption(self):
        rate = _compute_spread_rate(
            agent_states={"alice": True, "bob": True, "carol": False, "dave": False},
            seed_agent="alice",
        )
        # 1 out of 3 non-seed adopted
        assert abs(rate - 1 / 3) < 1e-9

    def test_single_agent(self):
        # Only the seed exists
        rate = _compute_spread_rate(
            agent_states={"alice": True},
            seed_agent="alice",
        )
        assert rate == 0.0

    def test_seed_not_adopted_counts_correctly(self):
        # Edge case: seed somehow didn't adopt (shouldn't happen but handle gracefully)
        rate = _compute_spread_rate(
            agent_states={"alice": False, "bob": True, "carol": False},
            seed_agent="alice",
        )
        assert abs(rate - 0.5) < 1e-9


class TestComputeSpreadSpeed:
    def test_immediate_majority(self):
        # 50% adopted in round 0
        round_adopters = [["alice", "bob"], ["alice", "bob", "carol"]]
        speed = _compute_spread_speed(round_adopters, total_agents=4)
        assert speed == 0

    def test_gradual_spread(self):
        # 50% reached in round 2
        round_adopters = [
            ["alice"],                    # round 0: 1/4 = 25%
            ["alice", "bob"],             # round 1: 2/4 = 50%
            ["alice", "bob", "carol"],    # round 2: 3/4 = 75%
        ]
        speed = _compute_spread_speed(round_adopters, total_agents=4)
        assert speed == 1

    def test_never_reaches_half(self):
        round_adopters = [["alice"], ["alice"], ["alice"]]
        speed = _compute_spread_speed(round_adopters, total_agents=10)
        # Returns final round index
        assert speed == 2

    def test_exact_half(self):
        round_adopters = [["alice"], ["alice", "bob"]]
        speed = _compute_spread_speed(round_adopters, total_agents=4)
        assert speed == 1


class TestComputeResistanceRate:
    def test_no_resistance(self):
        stances = {
            "alice": ["accept", "accept"],
            "bob": ["neutral", "accept"],
        }
        rate = _compute_resistance_rate(stances, seed_agent="alice")
        # bob never rejected
        assert rate == 0.0

    def test_all_resist(self):
        stances = {
            "alice": ["accept"],
            "bob": ["reject", "neutral"],
            "carol": ["question", "reject"],
        }
        rate = _compute_resistance_rate(stances, seed_agent="alice")
        # Both non-seed agents rejected
        assert rate == 1.0

    def test_partial_resistance(self):
        stances = {
            "alice": ["accept"],
            "bob": ["reject"],
            "carol": ["accept"],
            "dave": ["neutral"],
        }
        rate = _compute_resistance_rate(stances, seed_agent="alice")
        # 1 out of 3 non-seed rejected
        assert abs(rate - 1 / 3) < 1e-9

    def test_seed_only(self):
        stances = {"alice": ["accept"]}
        rate = _compute_resistance_rate(stances, seed_agent="alice")
        assert rate == 0.0


class TestComputeBeliefTrajectory:
    def test_basic_trajectory(self):
        round_adopters = [["alice"], ["alice", "bob"], ["alice", "bob", "carol"]]
        trajectory = _compute_belief_trajectory(round_adopters)
        assert trajectory == [1, 2, 3]

    def test_empty_rounds(self):
        round_adopters = [[], [], []]
        trajectory = _compute_belief_trajectory(round_adopters)
        assert trajectory == [0, 0, 0]

    def test_single_round(self):
        round_adopters = [["alice", "bob"]]
        trajectory = _compute_belief_trajectory(round_adopters)
        assert trajectory == [2]
