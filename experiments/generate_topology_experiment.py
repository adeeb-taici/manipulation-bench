"""Experiment A: Isolate the effect of communication topology on manipulation.

Same 5 policy topics, same 4 models, same manipulation rotation — but run
under 3 different topologies. The ONLY variable is who can see whom.

Topologies tested:
  all_to_all  — everyone sees everything (standard)
  hub_spoke   — alice (Claude) is the hub, others only see alice
  isolated    — agents only see their own prior arguments

5 topics x 5 variants x 3 topologies = 75 scenarios total.

Usage:
    python experiments/generate_topology_experiment.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from generate_policy_debates import MANIPULATION_PROMPT, TOPICS, MODEL_LABELS, WORD_LIMIT
from manipulation_bench.generate import generate_debate_rotation

TOPOLOGIES = {
    "all_to_all": "all_to_all",
    "hub_spoke": "hub_spoke",
    "isolated": "isolated",
}


def _build_topics():
    topics = []
    for topic_info in TOPICS:
        positions = topic_info["positions"]
        topics.append(
            {
                "topic": topic_info["topic"],
                "metadata": {
                    "model_mapping": {p["name"]: MODEL_LABELS[p["model_role"]] for p in positions},
                },
                "agents": [
                    {
                        "name": p["name"],
                        "model_role": p["model_role"],
                        "prompt": p["prompt"],
                        "position": p["position"],
                    }
                    for p in positions
                ],
            }
        )
    return topics


def generate_scenarios():
    all_scenarios = []
    topics = _build_topics()

    for topo_name, topo_value in TOPOLOGIES.items():
        scenarios = generate_debate_rotation(
            topics,
            manipulation_prompt=MANIPULATION_PROMPT,
            word_limit=WORD_LIMIT,
            visibility=topo_value,
            id_prefix=f"topo_{topo_name}",
        )
        # Tag each scenario with the topology for analysis (copy to avoid shared ref)
        for s in scenarios:
            s["metadata"] = {**s.get("metadata", {}), "topology": topo_name}
        all_scenarios.extend(scenarios)

    return all_scenarios


if __name__ == "__main__":
    scenarios = generate_scenarios()
    out = Path("src/manipulation_bench/scenarios/topology_experiment.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for s in scenarios:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"Generated {len(scenarios)} scenarios -> {out}")
    print(f"  5 topics x 5 variants x 3 topologies = {len(scenarios)}")
    print()
    for topo in TOPOLOGIES:
        count = sum(1 for s in scenarios if s.get("metadata", {}).get("topology") == topo)
        print(f"  {topo}: {count} scenarios")
    print()
    print("Run with:")
    print("  inspect eval src/manipulation_bench/task.py \\")
    print("    -T scenarios=topology_experiment.jsonl \\")
    print("    --model openrouter/anthropic/claude-opus-4-6 \\")
    print("    --model-role model_a=openrouter/anthropic/claude-opus-4-6 \\")
    print("    --model-role model_b=openrouter/openai/gpt-5 \\")
    print("    --model-role model_c=openrouter/google/gemini-2.5-pro \\")
    print("    --model-role model_d=openrouter/x-ai/grok-3 \\")
    print("    --model-role judge=openrouter/anthropic/claude-opus-4-6")
