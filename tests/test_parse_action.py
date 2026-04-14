"""Test parse_action for Werewolf and Diplomacy with adversarial inputs."""

from __future__ import annotations

import pytest

from manipulation_bench.environments.werewolf import WerewolfEnvironment


@pytest.fixture
def werewolf_env():
    env = WerewolfEnvironment(
        {
            "seed": 42,
            "role_assignments": {"alice": "werewolf", "bob": "seer", "carol": "villager"},
        }
    )
    env.setup(["alice", "bob", "carol"])
    return env


class TestWerewolfParseAction:
    def test_standard_format(self, werewolf_env):
        result = werewolf_env.parse_action("alice", "I think so. ACTION: kill:bob")
        assert result == "kill:bob"

    def test_case_insensitive(self, werewolf_env):
        result = werewolf_env.parse_action("alice", "ACTION: Kill:Bob")
        assert result == "kill:bob"

    def test_no_action_raises(self, werewolf_env):
        with pytest.raises(ValueError, match="Could not find"):
            werewolf_env.parse_action("alice", "I don't want to do anything.")

    def test_unknown_target_raises(self, werewolf_env):
        with pytest.raises(ValueError, match="Unknown player"):
            werewolf_env.parse_action("alice", "ACTION: kill:nonexistent")

    def test_action_in_long_response(self, werewolf_env):
        long_response = "Let me think...\n" * 20 + "ACTION: kill:carol\nThat's my choice."
        result = werewolf_env.parse_action("alice", long_response)
        assert result == "kill:carol"

    def test_skip_target(self, werewolf_env):
        result = werewolf_env.parse_action("alice", "ACTION: vote:skip")
        assert result == "vote:skip"


try:
    from manipulation_bench.environments.diplomacy import DiplomacyEnvironment

    class TestDiplomacyParseAction:
        @pytest.fixture
        def diplomacy_env(self):
            env = DiplomacyEnvironment({"max_years": 1, "negotiation_rounds": 1})
            env.setup(["austria", "england", "france", "germany", "italy", "russia", "turkey"])
            return env

        def test_single_action(self, diplomacy_env):
            result = diplomacy_env.parse_action("austria", "ACTION: A VIE - BUD")
            assert "A VIE - BUD" in result

        def test_no_action_raises(self, diplomacy_env):
            with pytest.raises(ValueError, match="No ACTION"):
                diplomacy_env.parse_action("austria", "I'll just wait and see.")

        def test_multiple_blocks_takes_last(self, diplomacy_env):
            response = "ACTION: A VIE - BUD\nWait, let me reconsider.\nACTION: A VIE - TRI"
            result = diplomacy_env.parse_action("austria", response)
            assert "A VIE - TRI" in result
            assert "A VIE - BUD" not in result

        def test_arrow_normalization(self, diplomacy_env):
            result = diplomacy_env.parse_action("austria", "ACTION: A VIE -> BUD")
            assert "A VIE - BUD" in result

        def test_markdown_stripping(self, diplomacy_env):
            result = diplomacy_env.parse_action("austria", "ACTION: **A VIE - BUD**")
            assert "A VIE - BUD" in result

        def test_deduplication(self, diplomacy_env):
            response = "ACTION: A VIE - BUD\nACTION: A VIE - BUD\nACTION: F TRI - ALB"
            result = diplomacy_env.parse_action("austria", response)
            orders = result.split(",")
            assert len(orders) == 2

except ImportError:
    pass
