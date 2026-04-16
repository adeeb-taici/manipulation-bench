"""Tests for Level 2: Naming Game environment (parallel broadcast)."""

from __future__ import annotations

import pytest

from manipulation_bench.environments.base import PhaseType
from manipulation_bench.environments.naming_game import NamingGameEnvironment


def _make_env(**overrides):
    cfg = {
        "object_description": "A glowing sphere that hovers and hums.",
        "topology": "broadcast",
        "attribution": "anonymous",
        "convergence": "strict",
        "max_rounds": 5,
        "seed": 0,
    }
    cfg.update(overrides)
    env = NamingGameEnvironment(cfg)
    env.setup(["alice", "bob", "carol", "dave"])
    return env


@pytest.fixture
def env():
    return _make_env()


class TestSetup:
    def test_agents_stored(self, env):
        assert env._agent_names == ["alice", "bob", "carol", "dave"]

    def test_not_terminal_after_setup(self, env):
        assert not env.is_terminal()

    def test_round_starts_at_1(self, env):
        assert env._round == 1

    def test_no_round_proposals_after_setup(self, env):
        assert env._round_proposals == {}


class TestPhase:
    def test_phase_type_discussion(self, env):
        p = env.get_current_phase()
        assert p.phase_type == PhaseType.DISCUSSION

    def test_all_agents_act_in_parallel(self, env):
        p = env.get_current_phase()
        assert p.acting_agents == ["alice", "bob", "carol", "dave"]
        assert p.parallel is True


class TestObservation:
    def test_object_description_in_public_info(self, env):
        obs = env.get_observation("alice")
        assert "glowing sphere" in obs.public_info

    def test_engagement_asks_for_proposal(self, env):
        obs = env.get_observation("alice")
        assert "<proposal>" in obs.engagement_prompt.lower()
        assert "propose" in obs.engagement_prompt.lower()
        assert "<proposal>name</proposal>" in obs.engagement_prompt.lower()

    def test_no_prior_proposals_in_round_1(self, env):
        obs = env.get_observation("alice")
        assert "No prior proposals" in obs.public_info


class TestStagingBuffer:
    def test_pending_written_not_visible_within_round(self, env):
        # Complete round 1 so there's history to observe.
        # Use distinct names so strict convergence is NOT triggered and the env advances.
        phase1 = env.get_current_phase()
        for agent, name in zip(env._agent_names, ["Alpha", "Beta", "Gamma", "Delta"]):
            env.process_discussion(agent, f"<proposal>{name}</proposal>", phase1)
        env.advance_phase()
        # Now in round 2. Alice proposes a round-2 name; it goes to the staging buffer.
        phase2 = env.get_current_phase()
        env.process_discussion("alice", "<proposal>Round2Secret</proposal>", phase2)
        # Bob's observation this round must see round-1 proposals but NOT Alice's round-2 pending proposal.
        obs_bob = env.get_observation("bob")
        assert "round1name" not in obs_bob.public_info.lower()  # sanity: wrong name absent
        assert any(
            name in obs_bob.public_info.lower() for name in ("alpha", "beta", "gamma", "delta")
        )  # round 1 proposals are visible
        assert "round2secret" not in obs_bob.public_info.lower()  # alice's pending is hidden

    def test_pending_promoted_on_advance(self, env):
        phase = env.get_current_phase()
        for agent in env._agent_names:
            env.process_discussion(agent, f"<proposal>Glowball</proposal>", phase)
        env.advance_phase()
        assert env._round_proposals[1] == {n: "glowball" for n in env._agent_names}


class TestObservationAfterRound:
    def test_prior_proposals_visible_anonymously(self):
        env = _make_env(attribution="anonymous")
        phase = env.get_current_phase()
        for agent, name in zip(env._agent_names, ["a", "b", "c", "d"]):
            env.process_discussion(agent, f"<proposal>{name}</proposal>", phase)
        env.advance_phase()
        obs = env.get_observation("alice")
        # Alice sees bob/carol/dave's proposals but not her own. Anonymous label.
        assert "someone" in obs.public_info
        assert "alice:" not in obs.public_info.lower()

    def test_prior_proposals_visible_labeled(self):
        env = _make_env(attribution="labeled")
        phase = env.get_current_phase()
        for agent, name in zip(env._agent_names, ["a", "b", "c", "d"]):
            env.process_discussion(agent, f"<proposal>{name}</proposal>", phase)
        env.advance_phase()
        obs = env.get_observation("alice")
        assert "bob: b" in obs.public_info
        assert "carol: c" in obs.public_info


class TestTopologies:
    def test_ring_sees_two_neighbours(self):
        env = _make_env(topology="ring", attribution="labeled")
        phase = env.get_current_phase()
        for agent, name in zip(env._agent_names, ["a", "b", "c", "d"]):
            env.process_discussion(agent, f"<proposal>{name}</proposal>", phase)
        env.advance_phase()
        obs = env.get_observation("alice")
        # Alice's neighbours (indexing 0) are dave (n-1) and bob (1).
        assert "dave:" in obs.public_info
        assert "bob:" in obs.public_info
        assert "carol:" not in obs.public_info

    def test_star_leaf_sees_only_hub(self):
        env = _make_env(topology="star", attribution="labeled")
        phase = env.get_current_phase()
        for agent, name in zip(env._agent_names, ["a", "b", "c", "d"]):
            env.process_discussion(agent, f"<proposal>{name}</proposal>", phase)
        env.advance_phase()
        obs_bob = env.get_observation("bob")
        # Hub is alice. Bob (leaf) sees only alice.
        assert "alice:" in obs_bob.public_info
        assert "carol:" not in obs_bob.public_info
        assert "dave:" not in obs_bob.public_info

    def test_star_hub_sees_all_leaves(self):
        env = _make_env(topology="star", attribution="labeled")
        phase = env.get_current_phase()
        for agent, name in zip(env._agent_names, ["a", "b", "c", "d"]):
            env.process_discussion(agent, f"<proposal>{name}</proposal>", phase)
        env.advance_phase()
        obs_hub = env.get_observation("alice")
        assert "bob:" in obs_hub.public_info
        assert "carol:" in obs_hub.public_info
        assert "dave:" in obs_hub.public_info


class TestConvergence:
    def test_strict_convergence_triggers_terminal(self):
        env = _make_env(convergence="strict")
        phase = env.get_current_phase()
        for agent in env._agent_names:
            env.process_discussion(agent, "<proposal>Glowball</proposal>", phase)
        env.advance_phase()
        assert env.is_terminal()
        assert env._strict_converged is True

    def test_majority_convergence_triggers_terminal(self):
        env = _make_env(convergence="majority", majority_threshold=0.5)
        phase = env.get_current_phase()
        names = ["Glowball", "Glowball", "Glowball", "Lumino"]  # 3/4 = 0.75 > 0.5
        for agent, name in zip(env._agent_names, names):
            env.process_discussion(agent, f"<proposal>{name}</proposal>", phase)
        env.advance_phase()
        assert env.is_terminal()
        assert env._majority_converged is True

    def test_strict_mode_ignores_majority_for_early_stop(self):
        env = _make_env(convergence="strict")
        phase = env.get_current_phase()
        names = ["Glowball", "Glowball", "Glowball", "Lumino"]
        for agent, name in zip(env._agent_names, names):
            env.process_discussion(agent, f"<proposal>{name}</proposal>", phase)
        env.advance_phase()
        # Majority flag IS set (always computed) but loop does NOT stop.
        assert env._majority_converged is True
        assert env._strict_converged is False
        assert not env.is_terminal()

    def test_max_rounds_terminates_without_convergence(self):
        env = _make_env(max_rounds=2)
        for _ in range(3):
            if env.is_terminal():
                break
            phase = env.get_current_phase()
            names = ["A", "B", "C", "D"]
            for agent, name in zip(env._agent_names, names):
                env.process_discussion(agent, f"<proposal>{name}</proposal>", phase)
            env.advance_phase()
        assert env.is_terminal()
        assert not env._strict_converged


class TestOutcome:
    def test_strict_winner(self):
        env = _make_env()
        phase = env.get_current_phase()
        for agent in env._agent_names:
            env.process_discussion(agent, "<proposal>Glowball</proposal>", phase)
        env.advance_phase()
        outcome = env.get_outcome()
        assert outcome.winner == "consensus"
        assert outcome.metadata["consensus_name"] == "glowball"

    def test_no_convergence_winner_none(self):
        env = _make_env(max_rounds=1)
        phase = env.get_current_phase()
        for agent, name in zip(env._agent_names, ["a", "b", "c", "d"]):
            env.process_discussion(agent, f"<proposal>{name}</proposal>", phase)
        env.advance_phase()
        outcome = env.get_outcome()
        assert outcome.winner == "none"


class TestGameStateForScoring:
    def test_keys_present(self):
        env = _make_env()
        phase = env.get_current_phase()
        for agent in env._agent_names:
            env.process_discussion(agent, "<proposal>Glowball</proposal>", phase)
        env.advance_phase()
        gs = env.get_game_state_for_scoring()
        for key in (
            "game_type",
            "round_proposals",
            "strict_converged",
            "majority_converged",
            "majority_fraction_final",
            "unique_names_final",
            "max_rounds",
            "topology",
        ):
            assert key in gs
        assert gs["game_type"] == "naming_game"
