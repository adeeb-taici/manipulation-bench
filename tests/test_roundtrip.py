"""Round-trip test: generate scenarios, serialize, load, validate."""

from __future__ import annotations

import json

from manipulation_bench.dataset import record_to_sample
from manipulation_bench.models import ScenarioConfig


def test_debate_scenario_roundtrip():
    """A debate scenario dict round-trips through JSONL and ScenarioConfig."""
    scenario = {
        "id": "test_001",
        "topic": "Is water wet?",
        "description": "Test debate",
        "agents": [
            {
                "name": "pro",
                "model_role": "debater",
                "system_prompt": "Argue yes.",
                "position": "yes",
            },
            {
                "name": "con",
                "model_role": "debater",
                "system_prompt": "Argue no.",
                "position": "no",
            },
        ],
        "protocol": "round_robin",
        "num_rounds": 2,
        "visibility": "all_to_all",
    }

    line = json.dumps(scenario, ensure_ascii=False)
    loaded = json.loads(line)

    config = ScenarioConfig(**loaded)
    assert config.topic == "Is water wet?"
    assert len(config.agents) == 2
    assert config.num_rounds == 2
    assert config.metadata.environment == {}
    assert config.metadata.game_state is None

    sample = record_to_sample(loaded)
    assert sample.input == "Is water wet?"
    assert sample.metadata["scenario"]["topic"] == "Is water wet?"


def test_game_scenario_roundtrip():
    """A game scenario with environment metadata round-trips correctly."""
    scenario = {
        "id": "werewolf_test",
        "topic": "Werewolf test",
        "agents": [
            {"name": "alice", "model_role": "player", "system_prompt": "Play."},
            {"name": "bob", "model_role": "player", "system_prompt": "Play."},
            {"name": "carol", "model_role": "player", "system_prompt": "Play."},
        ],
        "metadata": {
            "environment": {"type": "werewolf", "num_werewolves": 1, "seed": 42},
            "model_mapping": {"alice": "claude", "bob": "gpt5"},
        },
    }

    line = json.dumps(scenario, ensure_ascii=False)
    loaded = json.loads(line)

    config = ScenarioConfig(**loaded)
    assert config.metadata.environment["type"] == "werewolf"
    assert config.metadata.model_mapping["alice"] == "claude"
    assert config.metadata.game_outcome is None


def test_metadata_extra_keys_preserved():
    """Extra keys in metadata are preserved through ScenarioConfig."""
    scenario = {
        "id": "test",
        "topic": "test",
        "agents": [],
        "metadata": {
            "environment": {},
            "custom_experiment_key": "preserved",
        },
    }
    config = ScenarioConfig(**scenario)
    assert config.metadata.custom_experiment_key == "preserved"
