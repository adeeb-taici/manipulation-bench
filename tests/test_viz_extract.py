# tests/test_viz_extract.py
"""Tests for viz extract functions."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest


class TestExtractSimulationData:
    @pytest.fixture
    def eval_zip(self, tmp_path: Path) -> Path:
        """Create a minimal .eval zip file for testing."""
        header = {
            "eval": {
                "task_args": {
                    "topology": "broadcast",
                    "n_agents": 3,
                    "max_rounds": 5,
                    "seed": 42,
                },
                "model": "mockllm/model",
            },
            "results": {
                "scores": [
                    {
                        "name": "spread_rate",
                        "metrics": {"mean": {"value": 0.5}},
                    }
                ]
            },
        }

        interaction_state = {
            "scenario": {
                "topic": "misinformation test",
                "agents": [
                    {"name": "alice", "model_role": "agent", "system_prompt": ""},
                    {"name": "bob", "model_role": "agent", "system_prompt": ""},
                    {"name": "carol", "model_role": "agent", "system_prompt": ""},
                ],
                "metadata": {
                    "environment": {
                        "type": "misinformation",
                        "claim": "Test claim",
                        "seed_agent": "alice",
                    }
                },
            },
            "agent_names": ["alice", "bob", "carol"],
            "agent_states": {
                "alice": {
                    "opinions": [],
                    "stances": ["accept", "accept"],
                    "adopted": True,
                },
                "bob": {
                    "opinions": [],
                    "stances": ["neutral", "accept"],
                    "adopted": True,
                },
                "carol": {
                    "opinions": [],
                    "stances": ["neutral", "reject"],
                    "adopted": False,
                },
            },
            "network_snapshots": [
                {
                    "round": 1,
                    "edges": [["alice", "bob"], ["alice", "carol"], ["bob", "carol"]],
                    "channels": ["general"],
                    "adopters": ["alice"],
                    "total_messages": 3,
                },
                {
                    "round": 2,
                    "edges": [["alice", "bob"], ["alice", "carol"], ["bob", "carol"]],
                    "channels": ["general"],
                    "adopters": ["alice", "bob"],
                    "total_messages": 6,
                },
            ],
            "turns": [
                {
                    "speaker": "alice",
                    "content": "I heard that Test claim!",
                    "round": 1,
                    "turn_index": 0,
                    "metadata": {"phase_type": "discussion"},
                },
                {
                    "speaker": "bob",
                    "content": "Interesting!",
                    "round": 1,
                    "turn_index": 1,
                    "metadata": {"phase_type": "discussion"},
                },
                {
                    "speaker": "carol",
                    "content": "I doubt that.",
                    "round": 1,
                    "turn_index": 2,
                    "metadata": {"phase_type": "discussion"},
                },
            ],
        }

        sample = {
            "id": "sample_0",
            "store": {"InteractionState": interaction_state},
        }

        eval_path = tmp_path / "test.eval"
        with zipfile.ZipFile(eval_path, "w") as zf:
            zf.writestr("header.json", json.dumps(header))
            zf.writestr("samples/sample_0.json", json.dumps(sample))

        return eval_path

    def test_extract_returns_dict(self, eval_zip: Path):
        from manipulation_bench.viz.extract import extract_simulation_data

        data = extract_simulation_data(eval_zip)
        assert isinstance(data, dict)

    def test_extract_metadata(self, eval_zip: Path):
        from manipulation_bench.viz.extract import extract_simulation_data

        data = extract_simulation_data(eval_zip)
        meta = data["metadata"]
        assert meta["topology"] == "broadcast"
        assert meta["n_agents"] == 3
        assert meta["model"] == "mockllm/model"
        assert meta["seed_agent"] == "alice"

    def test_extract_scores(self, eval_zip: Path):
        from manipulation_bench.viz.extract import extract_simulation_data

        data = extract_simulation_data(eval_zip)
        assert data["scores"]["spread_rate"] == 0.5

    def test_extract_nodes(self, eval_zip: Path):
        from manipulation_bench.viz.extract import extract_simulation_data

        data = extract_simulation_data(eval_zip)
        nodes = data["nodes"]
        assert len(nodes) == 3
        names = {n["id"] for n in nodes}
        assert names == {"alice", "bob", "carol"}

        seed_nodes = [n for n in nodes if n["is_seed"]]
        assert len(seed_nodes) == 1
        assert seed_nodes[0]["id"] == "alice"

    def test_extract_rounds(self, eval_zip: Path):
        from manipulation_bench.viz.extract import extract_simulation_data

        data = extract_simulation_data(eval_zip)
        rounds = data["rounds"]
        assert len(rounds) == 2
        assert rounds[0]["round"] == 1
        assert rounds[0]["adopters"] == ["alice"]
        assert rounds[1]["adopters"] == ["alice", "bob"]

    def test_extract_stances_per_round(self, eval_zip: Path):
        from manipulation_bench.viz.extract import extract_simulation_data

        data = extract_simulation_data(eval_zip)
        rounds = data["rounds"]
        # Round 1 (index 0): alice=accept, bob=neutral, carol=neutral
        assert rounds[0]["stances"]["alice"] == "accept"
        assert rounds[0]["stances"]["bob"] == "neutral"
        # Round 2 (index 1): alice=accept, bob=accept, carol=reject
        assert rounds[1]["stances"]["bob"] == "accept"
        assert rounds[1]["stances"]["carol"] == "reject"

    def test_extract_edges(self, eval_zip: Path):
        from manipulation_bench.viz.extract import extract_simulation_data

        data = extract_simulation_data(eval_zip)
        edges = data["edges"]
        assert len(edges) == 3

    def test_extract_messages(self, eval_zip: Path):
        from manipulation_bench.viz.extract import extract_simulation_data

        data = extract_simulation_data(eval_zip)
        messages = data["messages"]
        assert "alice" in messages
        assert len(messages["alice"]) >= 1

    def test_no_samples_raises(self, tmp_path: Path):
        from manipulation_bench.viz.extract import extract_simulation_data

        eval_path = tmp_path / "empty.eval"
        with zipfile.ZipFile(eval_path, "w") as zf:
            zf.writestr("header.json", json.dumps({"eval": {}, "results": {}}))

        with pytest.raises(ValueError, match="No samples"):
            extract_simulation_data(eval_path)
