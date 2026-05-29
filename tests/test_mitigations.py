"""Tests for the mitigation (defense) plug-in system.

Covers the resolver round-trip, the ``adversary`` targeting flag, and both
reference defenses (``prompt_suffix`` synchronous, ``critic_monitor`` async).
The async hooks are driven with ``asyncio.run`` — there is no pytest-asyncio
in this repo.
"""

from __future__ import annotations

import asyncio

import pytest
from inspect_ai.model import ModelOutput

from manipulation_bench.mitigations import Mitigation, critic_monitor, prompt_suffix
from manipulation_bench.mitigations._resolve import resolve_mitigations
from manipulation_bench.mitigations._targeting import is_adversary
from manipulation_bench.mitigations.critic_monitor import CriticMonitor
from manipulation_bench.mitigations.prompt_suffix import DEFAULT_SUFFIX, PromptSuffix
from manipulation_bench.models import AgentRole, ScenarioConfig


def _scenario(agents: list[AgentRole]) -> ScenarioConfig:
    return ScenarioConfig(
        id="t",
        topic="Test",
        agents=agents,
        protocol="round_robin",
        num_rounds=2,
        visibility="all_to_all",
    )


def _agent(name: str, adversary: bool = False) -> AgentRole:
    return AgentRole(
        name=name,
        model_role="player",
        system_prompt=f"You are {name}.",
        adversary=adversary,
    )


# --- resolver round-trip -------------------------------------------------


@pytest.mark.parametrize("spec", [None, "default", "DEFAULT", "", []])
def test_resolve_sentinels_return_none(spec):
    assert resolve_mitigations(spec) is None


def test_resolve_bare_name():
    mits = resolve_mitigations("prompt_suffix")
    assert len(mits) == 1
    assert isinstance(mits[0], PromptSuffix)
    assert mits[0].name == "prompt_suffix"


def test_resolve_comma_and_whitespace_separated():
    mits = resolve_mitigations("prompt_suffix, critic_monitor")
    assert [m.name for m in mits] == ["prompt_suffix", "critic_monitor"]
    # Inspect's -T flag splits on commas into a list[str].
    mits2 = resolve_mitigations(["prompt_suffix", "critic_monitor"])
    assert [m.name for m in mits2] == ["prompt_suffix", "critic_monitor"]


def test_resolve_dotted_path():
    mits = resolve_mitigations(
        "examples.new_mitigation.my_mitigation.my_defense"
    )
    assert len(mits) == 1
    assert isinstance(mits[0], Mitigation)
    assert mits[0].name == "my_defense"


def test_resolve_unknown_name_raises():
    with pytest.raises(ValueError, match="unknown mitigation"):
        resolve_mitigations("no_such_defense")


def test_resolve_prebuilt_instances_passthrough():
    built = [prompt_suffix()]
    assert resolve_mitigations(built) is built


# --- targeting -----------------------------------------------------------


def test_is_adversary_reads_only_the_flag():
    scenario = _scenario([_agent("alice", adversary=True), _agent("bob")])
    alice, bob = scenario.agents
    assert is_adversary(alice, scenario) is True
    assert is_adversary(bob, scenario) is False


def test_adversary_defaults_false():
    assert _agent("alice").adversary is False


# --- prompt_suffix -------------------------------------------------------


def test_prompt_suffix_appends_to_protected_only():
    scenario = _scenario([_agent("alice", adversary=True), _agent("bob")])
    alice, bob = scenario.agents
    mit = PromptSuffix()

    new_alice = mit.transform_agent(alice, scenario)
    new_bob = mit.transform_agent(bob, scenario)

    assert new_alice.system_prompt == alice.system_prompt  # adversary untouched
    assert new_bob.system_prompt.endswith(DEFAULT_SUFFIX)
    assert new_bob.system_prompt.startswith("You are bob.")


def test_prompt_suffix_also_adversaries():
    scenario = _scenario([_agent("alice", adversary=True)])
    (alice,) = scenario.agents
    mit = PromptSuffix(also_adversaries=True)
    new_alice = mit.transform_agent(alice, scenario)
    assert new_alice.system_prompt.endswith(DEFAULT_SUFFIX)


def test_prompt_suffix_custom_suffix():
    scenario = _scenario([_agent("bob")])
    (bob,) = scenario.agents
    mit = PromptSuffix(suffix="STAY SKEPTICAL")
    new_bob = mit.transform_agent(bob, scenario)
    assert new_bob.system_prompt.endswith("STAY SKEPTICAL")


# --- critic_monitor ------------------------------------------------------


class _StubCritic:
    """Stand-in for a critic model: returns canned JSON regardless of input."""

    def __init__(self, payload: str):
        self._payload = payload

    async def generate(self, messages, config=None, **kwargs):
        return ModelOutput.from_content("mockllm/model", self._payload)


def _run_transform_response(mit, agent, scenario, output):
    return asyncio.run(mit.transform_response(agent, [], output, scenario))


def test_critic_monitor_skips_non_adversary():
    scenario = _scenario([_agent("bob")])
    (bob,) = scenario.agents
    mit = CriticMonitor(mode="flag")
    mit._get_critic = lambda: _StubCritic('{"verdict":"manipulative","reason":"x"}')
    out = ModelOutput.from_content("mockllm/model", "Honest point.")
    result = _run_transform_response(mit, bob, scenario, out)
    assert result.completion == "Honest point."


def test_critic_monitor_flag_prepends_warning():
    scenario = _scenario([_agent("alice", adversary=True)])
    (alice,) = scenario.agents
    mit = CriticMonitor(mode="flag")
    mit._get_critic = lambda: _StubCritic(
        '{"verdict":"manipulative","reason":"uses false urgency","rewrite":null}'
    )
    out = ModelOutput.from_content("mockllm/model", "Act now or lose everything!")
    result = _run_transform_response(mit, alice, scenario, out)
    assert result.completion.startswith("[Critic warning: uses false urgency]")
    assert "Act now or lose everything!" in result.completion


def test_critic_monitor_benign_leaves_output_unchanged():
    scenario = _scenario([_agent("alice", adversary=True)])
    (alice,) = scenario.agents
    mit = CriticMonitor(mode="flag")
    mit._get_critic = lambda: _StubCritic('{"verdict":"benign","reason":""}')
    out = ModelOutput.from_content("mockllm/model", "Here is my evidence.")
    result = _run_transform_response(mit, alice, scenario, out)
    assert result.completion == "Here is my evidence."


def test_critic_monitor_redact_replaces_message():
    scenario = _scenario([_agent("alice", adversary=True)])
    (alice,) = scenario.agents
    mit = CriticMonitor(mode="redact")
    mit._get_critic = lambda: _StubCritic(
        '{"verdict":"manipulative","reason":"deceptive","rewrite":null}'
    )
    out = ModelOutput.from_content("mockllm/model", "Trust me, I checked.")
    result = _run_transform_response(mit, alice, scenario, out)
    assert result.completion == "[Message withheld by critic: deceptive]"
    assert "Trust me" not in result.completion


def test_critic_monitor_rewrite_uses_paraphrase():
    scenario = _scenario([_agent("alice", adversary=True)])
    (alice,) = scenario.agents
    mit = CriticMonitor(mode="rewrite")
    mit._get_critic = lambda: _StubCritic(
        '{"verdict":"manipulative","reason":"hype","rewrite":"Here are the facts."}'
    )
    out = ModelOutput.from_content("mockllm/model", "This is the deal of a lifetime!")
    result = _run_transform_response(mit, alice, scenario, out)
    assert result.completion == "Here are the facts."
