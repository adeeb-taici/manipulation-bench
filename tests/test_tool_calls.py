"""Test tool schemas, tool_calls_to_action, and process_tool_calls."""

from __future__ import annotations

import pytest
from inspect_ai.tool import ToolCall

from manipulation_bench.environments.base import PhaseType
from manipulation_bench.environments.werewolf import WerewolfEnvironment


@pytest.fixture
def werewolf_env():
    env = WerewolfEnvironment(
        {
            "seed": 42,
            "role_assignments": {
                "alice": "werewolf",
                "bob": "seer",
                "carol": "villager",
            },
        }
    )
    env.setup(["alice", "bob", "carol"])
    return env


class TestWerewolfTools:
    def test_kill_tools_have_enum(self, werewolf_env):
        phase = werewolf_env.get_current_phase()
        assert phase.name == "night_werewolf_kill"
        tools = werewolf_env.get_tools("alice", phase)
        assert len(tools) == 1
        assert tools[0].name == "kill"
        targets = tools[0].parameters.properties["target"].enum
        assert "bob" in targets
        assert "carol" in targets
        assert "alice" not in targets  # werewolf can't kill self

    def test_vote_tools_include_skip(self, werewolf_env):
        # Advance to day_vote phase
        from manipulation_bench.environments.base import Phase

        day_vote = Phase(
            name="day_vote",
            phase_type=PhaseType.ACTION,
            round=1,
            acting_agents=["alice", "bob", "carol"],
        )
        tools = werewolf_env.get_tools("alice", day_vote)
        assert len(tools) == 1
        assert tools[0].name == "vote"
        targets = tools[0].parameters.properties["target"].enum
        assert "skip" in targets
        assert "alice" not in targets  # can't vote for self

    def test_tool_calls_to_action_valid(self, werewolf_env):
        tc = ToolCall(id="c1", function="kill", arguments={"target": "bob"})
        result = werewolf_env.tool_calls_to_action("alice", [tc])
        assert result == "kill:bob"

    def test_tool_calls_to_action_case_insensitive(self, werewolf_env):
        tc = ToolCall(id="c1", function="vote", arguments={"target": "Bob"})
        result = werewolf_env.tool_calls_to_action("alice", [tc])
        assert result == "vote:bob"

    def test_tool_calls_to_action_skip(self, werewolf_env):
        tc = ToolCall(id="c1", function="vote", arguments={"target": "skip"})
        result = werewolf_env.tool_calls_to_action("alice", [tc])
        assert result == "vote:skip"

    def test_tool_calls_to_action_empty_raises(self, werewolf_env):
        with pytest.raises(ValueError, match="No tool call"):
            werewolf_env.tool_calls_to_action("alice", [])

    def test_tool_calls_to_action_unknown_target_raises(self, werewolf_env):
        tc = ToolCall(id="c1", function="kill", arguments={"target": "nobody"})
        with pytest.raises(ValueError, match="Unknown player"):
            werewolf_env.tool_calls_to_action("alice", [tc])

    def test_discussion_has_no_tools(self, werewolf_env):
        from manipulation_bench.environments.base import Phase

        discussion = Phase(
            name="day_discussion",
            phase_type=PhaseType.DISCUSSION,
            round=1,
            acting_agents=["alice", "bob", "carol"],
        )
        tools = werewolf_env.get_tools("alice", discussion)
        assert tools == []

    def test_tool_choice_action_is_any(self, werewolf_env):
        phase = werewolf_env.get_current_phase()
        assert werewolf_env.get_tool_choice(phase) == "any"

    def test_tool_choice_discussion_is_none(self, werewolf_env):
        from manipulation_bench.environments.base import Phase

        discussion = Phase(
            name="day_discussion",
            phase_type=PhaseType.DISCUSSION,
            round=1,
            acting_agents=[],
        )
        assert werewolf_env.get_tool_choice(discussion) is None


try:
    from manipulation_bench.environments.diplomacy import DiplomacyEnvironment

    class TestDiplomacyTools:
        @pytest.fixture
        def diplomacy_env(self):
            env = DiplomacyEnvironment({"max_years": 1, "negotiation_rounds": 1})
            env.setup(["austria", "england", "france", "germany", "italy", "russia", "turkey"])
            return env

        def test_action_phase_has_submit_orders_tool(self, diplomacy_env):
            # Advance to the orders phase (skip negotiation)
            phase = diplomacy_env.get_current_phase()
            # First phase is negotiation; find the action phase
            while phase.phase_type != PhaseType.ACTION:
                phase = diplomacy_env.advance_phase()
            tools = diplomacy_env.get_tools("austria", phase)
            assert len(tools) == 1
            assert tools[0].name == "submit_orders"
            assert tools[0].parameters.properties["orders"].type == "array"

        def test_discussion_phase_has_messaging_tools(self, diplomacy_env):
            phase = diplomacy_env.get_current_phase()
            assert phase.phase_type == PhaseType.DISCUSSION
            tools = diplomacy_env.get_tools("austria", phase)
            tool_names = {t.name for t in tools}
            assert "send_message" in tool_names
            assert "make_promise" in tool_names

        def test_send_message_enum_excludes_self(self, diplomacy_env):
            phase = diplomacy_env.get_current_phase()
            tools = diplomacy_env.get_tools("austria", phase)
            send_msg = next(t for t in tools if t.name == "send_message")
            recipients = send_msg.parameters.properties["recipient"].enum
            assert "austria" not in recipients
            assert "england" in recipients

        def test_tool_calls_to_action_orders(self, diplomacy_env):
            # Advance to action phase
            phase = diplomacy_env.get_current_phase()
            while phase.phase_type != PhaseType.ACTION:
                phase = diplomacy_env.advance_phase()
            tc = ToolCall(
                id="c1",
                function="submit_orders",
                arguments={"orders": ["A VIE - BUD", "A BUD - SER", "F TRI - ALB"]},
            )
            result = diplomacy_env.tool_calls_to_action("austria", [tc])
            assert "A VIE - BUD" in result
            assert "A BUD - SER" in result

        def test_tool_calls_to_action_empty_raises(self, diplomacy_env):
            with pytest.raises(ValueError, match="No tool call"):
                diplomacy_env.tool_calls_to_action("austria", [])

        def test_tool_calls_to_action_empty_orders_raises(self, diplomacy_env):
            tc = ToolCall(id="c1", function="submit_orders", arguments={"orders": []})
            with pytest.raises(ValueError, match="Empty orders"):
                diplomacy_env.tool_calls_to_action("austria", [tc])

        def test_tool_calls_to_action_normalizes_arrows(self, diplomacy_env):
            tc = ToolCall(
                id="c1",
                function="submit_orders",
                arguments={"orders": ["A VIE -> BUD"]},
            )
            result = diplomacy_env.tool_calls_to_action("austria", [tc])
            assert "A VIE - BUD" in result

        def test_process_tool_calls_send_message(self, diplomacy_env):
            phase = diplomacy_env.get_current_phase()
            tc = ToolCall(
                id="c1",
                function="send_message",
                arguments={"recipient": "england", "content": "Let's ally!"},
            )
            responses = diplomacy_env.process_tool_calls("austria", [tc], phase)
            assert len(responses) == 1
            assert "sent to england" in responses[0].lower()
            # Verify message was routed
            assert len(diplomacy_env._messages) == 1
            assert diplomacy_env._messages[0].sender == "austria"
            assert diplomacy_env._messages[0].recipient == "england"

        def test_process_tool_calls_make_promise(self, diplomacy_env):
            phase = diplomacy_env.get_current_phase()
            tc = ToolCall(
                id="c1",
                function="make_promise",
                arguments={"recipient": "england", "order": "A VIE - BUD"},
            )
            responses = diplomacy_env.process_tool_calls("austria", [tc], phase)
            assert len(responses) == 1
            assert "promise recorded" in responses[0].lower()
            assert len(diplomacy_env._promises) == 1

        def test_process_tool_calls_multiple(self, diplomacy_env):
            phase = diplomacy_env.get_current_phase()
            tool_calls = [
                ToolCall(
                    id="c1",
                    function="send_message",
                    arguments={"recipient": "england", "content": "Hello"},
                ),
                ToolCall(
                    id="c2",
                    function="send_message",
                    arguments={"recipient": "france", "content": "Bonjour"},
                ),
                ToolCall(
                    id="c3",
                    function="make_promise",
                    arguments={"recipient": "england", "order": "A VIE - BUD"},
                ),
            ]
            responses = diplomacy_env.process_tool_calls("austria", tool_calls, phase)
            assert len(responses) == 3
            assert len(diplomacy_env._messages) == 2
            assert len(diplomacy_env._promises) == 1

        def test_discussion_tool_choice_is_auto(self, diplomacy_env):
            phase = diplomacy_env.get_current_phase()
            assert phase.phase_type == PhaseType.DISCUSSION
            assert diplomacy_env.get_tool_choice(phase) == "auto"

        def test_action_tool_choice_is_any(self, diplomacy_env):
            phase = diplomacy_env.get_current_phase()
            while phase.phase_type != PhaseType.ACTION:
                phase = diplomacy_env.advance_phase()
            assert diplomacy_env.get_tool_choice(phase) == "any"

except ImportError:
    pass
