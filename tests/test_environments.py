"""Contract tests for the Environment ABC — every environment must pass these."""

from __future__ import annotations

from manipulation_bench.environments.base import PhaseType


def test_initial_phase_is_valid(environment):
    phase = environment.get_current_phase()
    assert phase.name
    assert phase.phase_type in (PhaseType.DISCUSSION, PhaseType.ACTION)
    assert len(phase.acting_agents) > 0


def test_observation_for_each_acting_agent(environment):
    phase = environment.get_current_phase()
    for agent in phase.acting_agents:
        obs = environment.get_observation(agent)
        assert obs.agent_name == agent
        assert obs.public_info


def test_not_terminal_after_setup(environment):
    assert not environment.is_terminal()


def test_advance_phase_returns_phase_or_none(environment):
    result = environment.advance_phase()
    assert result is None or hasattr(result, "name")


def test_get_tools_returns_list(environment):
    phase = environment.get_current_phase()
    for agent in phase.acting_agents:
        tools = environment.get_tools(agent, phase)
        assert isinstance(tools, list)


def test_action_phase_has_tools(environment):
    """ACTION phases should provide at least one tool."""
    phase = environment.get_current_phase()
    # Walk phases until we find an ACTION phase or run out
    seen = 0
    while phase is not None and seen < 20:
        if phase.phase_type == PhaseType.ACTION and phase.acting_agents:
            agent = phase.acting_agents[0]
            tools = environment.get_tools(agent, phase)
            assert len(tools) > 0, f"ACTION phase {phase.name} has no tools"
            return
        phase = environment.advance_phase()
        seen += 1
