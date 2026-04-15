# src/manipulation_bench/viz/extract.py
"""Extract simulation data from Inspect AI eval logs.

Adapted from manipulationbench.viz.extract to read from the unified
InteractionState format (agent_states dict with AgentSnapshot) instead of
per-node StoreModel instances.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path


def extract_simulation_data(eval_path: str | Path) -> dict:
    """Read an .eval zip file and return structured simulation data.

    The data structure is designed for the D3+Chart.js template:
    - metadata: topology, n_agents, model, seed, seed_agent, etc.
    - scores: scorer name -> mean value
    - nodes: list of {id, label, is_seed}
    - edges: list of {source, target}
    - rounds: list of {round, adopters, total_messages, stances}
    - messages: agent_name -> list of message content strings
    """
    eval_path = Path(eval_path)

    with zipfile.ZipFile(eval_path, "r") as zf:
        with zf.open("header.json") as f:
            header = json.load(f)

        sample_files = [n for n in zf.namelist() if n.startswith("samples/")]
        if not sample_files:
            raise ValueError(f"No samples found in {eval_path}")

        with zf.open(sample_files[0]) as f:
            sample = json.load(f)

    store = sample.get("store", {})
    task_args = header.get("eval", {}).get("task_args", {})

    # Read InteractionState from store
    interaction_data = store.get("InteractionState", {})
    agent_states = interaction_data.get("agent_states", {})
    agent_names = interaction_data.get("agent_names", list(agent_states.keys()))
    network_snapshots = interaction_data.get("network_snapshots", [])
    turns = interaction_data.get("turns", [])

    # Extract scenario metadata
    scenario = interaction_data.get("scenario", {})
    env_config = scenario.get("metadata", {}).get("environment", {})
    seed_agent = env_config.get("seed_agent", "")

    metadata = {
        "topology": task_args.get("topology", scenario.get("topology", "unknown")),
        "n_agents": task_args.get("n_agents", len(agent_names)),
        "max_rounds": task_args.get("max_rounds", scenario.get("num_rounds", 0)),
        "model": header.get("eval", {}).get("model", "unknown"),
        "seed": task_args.get("seed", 0),
        "seed_agent": seed_agent,
        "final_round": len(network_snapshots),
    }

    # Extract scores
    scores = {}
    raw_scores = header.get("results", {}).get("scores", [])
    for s in raw_scores:
        name = s.get("name", "")
        mean_metric = s.get("metrics", {}).get("mean", {})
        scores[name] = mean_metric.get("value", 0.0)

    # Build nodes from agent_names
    nodes = []
    for name in agent_names:
        nodes.append(
            {
                "id": name,
                "label": name,
                "is_seed": name == seed_agent,
            }
        )

    # Build edges from network_snapshots
    edges = []
    if network_snapshots:
        seen = set()
        last_snapshot = network_snapshots[-1]
        for edge in last_snapshot.get("edges", []):
            if isinstance(edge, (list, tuple)) and len(edge) == 2:
                pair = tuple(sorted(edge))
                if pair not in seen:
                    seen.add(pair)
                    edges.append({"source": pair[0], "target": pair[1]})

    # Build per-round data
    rounds = []
    for snap in network_snapshots:
        round_num = snap.get("round", 0)

        # Build stances for this round from agent_states
        stances = {}
        for name, agent_data in agent_states.items():
            stance_list = agent_data.get("stances", [])
            round_idx = round_num - 1  # rounds are 1-based, list is 0-based
            if 0 <= round_idx < len(stance_list):
                stances[name] = stance_list[round_idx]
            else:
                stances[name] = "neutral"

        rounds.append(
            {
                "round": round_num,
                "adopters": snap.get("adopters", []),
                "total_messages": snap.get("total_messages", 0),
                "stances": stances,
            }
        )

    # Build per-agent message lists from turns
    messages: dict[str, list[str]] = {name: [] for name in agent_names}
    for turn in turns:
        speaker = turn.get("speaker", "")
        content = turn.get("content", "")
        if speaker in messages:
            messages[speaker].append(content)

    return {
        "metadata": metadata,
        "scores": scores,
        "nodes": nodes,
        "edges": edges,
        "rounds": rounds,
        "messages": messages,
    }
