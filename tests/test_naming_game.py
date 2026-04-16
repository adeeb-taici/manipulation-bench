"""Tests for Level 2: Naming Game environment."""

from __future__ import annotations

import pytest

from manipulation_bench.environments.base import PhaseType
from manipulation_bench.environments.naming_game import NamingGameEnvironment


@pytest.fixture
def env():
    e = NamingGameEnvironment(
        {
            "object_description": "A glowing sphere that hovers and hums.",
            "num_agents": 4,
            "pairs_per_round": 2,
            "max_rounds": 10,
            "seed": 42,
        }
    )
    e.setup(["alice", "bob", "carol", "dave"])
    return e


class TestSetup:
    def test_setup_stores_agent_names(self, env):
        assert env._agent_names == ["alice", "bob", "carol", "dave"]

    def test_not_terminal_after_setup(self, env):
        assert not env.is_terminal()

    def test_round_starts_at_1(self, env):
        assert env._round == 1

    def test_vocabulary_initialized_empty(self, env):
        for name in ["alice", "bob", "carol", "dave"]:
            assert env._vocabularies[name] == set()


class TestPhase:
    def test_initial_phase_is_discussion(self, env):
        phase = env.get_current_phase()
        assert phase.phase_type == PhaseType.DISCUSSION
        assert phase.parallel is False

    def test_phase_has_two_acting_agents(self, env):
        phase = env.get_current_phase()
        assert len(phase.acting_agents) == 2

    def test_phase_name_contains_pair(self, env):
        phase = env.get_current_phase()
        assert "pair" in phase.name


class TestObservation:
    def test_observation_has_object_description(self, env):
        phase = env.get_current_phase()
        agent = phase.acting_agents[0]
        obs = env.get_observation(agent)
        assert "glowing sphere" in obs.public_info

    def test_speaker_gets_speaker_role(self, env):
        phase = env.get_current_phase()
        speaker = phase.acting_agents[0]
        obs = env.get_observation(speaker)
        assert "propose" in obs.engagement_prompt.lower() or "name" in obs.engagement_prompt.lower()

    def test_hearer_gets_hearer_role(self, env):
        phase = env.get_current_phase()
        hearer = phase.acting_agents[1]
        obs = env.get_observation(hearer)
        assert "accept" in obs.engagement_prompt.lower() or "respond" in obs.engagement_prompt.lower()


class TestClassifyStance:
    def test_accept(self, env):
        assert env.classify_stance("alice", "Sure. <decision>accept</decision>") == "accept"

    def test_reject(self, env):
        assert env.classify_stance("alice", "Nope. <decision>reject</decision> <proposal>Lumino</proposal>") == "reject"

    def test_no_tag_is_neutral(self, env):
        assert env.classify_stance("alice", "I think we should call it a Floater.") == "neutral"


class TestProcessDiscussion:
    def test_speaker_name_added_to_vocabulary(self, env):
        phase = env.get_current_phase()
        speaker = phase.acting_agents[0]
        env.process_discussion(speaker, "I propose <proposal>Glowball</proposal>", phase)
        assert "glowball" in env._vocabularies[speaker]

    def test_hearer_accept_adds_name(self, env):
        phase = env.get_current_phase()
        speaker = phase.acting_agents[0]
        hearer = phase.acting_agents[1]
        env.process_discussion(speaker, "<proposal>Glowball</proposal>", phase)
        env.process_discussion(hearer, "Works for me. <decision>accept</decision>", phase)
        assert "glowball" in env._vocabularies[hearer]

    def test_hearer_reject_does_not_add_name(self, env):
        phase = env.get_current_phase()
        speaker = phase.acting_agents[0]
        hearer = phase.acting_agents[1]
        env.process_discussion(speaker, "<proposal>Glowball</proposal>", phase)
        env.process_discussion(
            hearer,
            "Prefer another. <decision>reject</decision> <proposal>Lumino</proposal>",
            phase,
        )
        assert "glowball" not in env._vocabularies[hearer]
        assert "lumino" in env._vocabularies[hearer]


class TestAdvancePhase:
    def test_advances_to_next_pair(self, env):
        phase1 = env.get_current_phase()
        assert len(phase1.acting_agents) == 2
        env.advance_phase()
        phase2 = env.get_current_phase()
        assert len(phase2.acting_agents) == 2

    def test_round_increments_after_all_pairs(self, env):
        # 2 pairs per round
        env.advance_phase()  # pair 1 done
        env.advance_phase()  # pair 2 done -> round 2
        assert env._round == 2

    def test_max_rounds_terminates(self, env):
        for _ in range(10 * 2):  # 10 rounds * 2 pairs
            if env.is_terminal():
                break
            env.advance_phase()
        assert env.is_terminal()


class TestConvergence:
    def test_convergence_detected(self, env):
        # Manually set all vocabularies to same single name
        for name in env._agent_names:
            env._vocabularies[name] = {"glowball"}
        # Force check
        assert env._check_convergence()

    def test_no_convergence_with_different_names(self, env):
        env._vocabularies["alice"] = {"glowball"}
        env._vocabularies["bob"] = {"lumino"}
        env._vocabularies["carol"] = {"glowball"}
        env._vocabularies["dave"] = {"floater"}
        assert not env._check_convergence()


class TestOutcome:
    def test_converged_outcome(self, env):
        for name in env._agent_names:
            env._vocabularies[name] = {"glowball"}
        env._terminal = True
        env._converged = True
        outcome = env.get_outcome()
        assert outcome.winner == "consensus"

    def test_no_convergence_outcome(self, env):
        env._terminal = True
        env._converged = False
        outcome = env.get_outcome()
        assert outcome.winner == "none"


class TestGameStateForScoring:
    def test_game_state_structure(self, env):
        gs = env.get_game_state_for_scoring()
        assert gs["game_type"] == "naming_game"
        assert "vocabularies" in gs
        assert "total_rounds" in gs
