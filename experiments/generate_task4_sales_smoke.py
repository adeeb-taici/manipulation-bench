"""Task 4 Sales pre-sweep smoke generator.

Per paper/task4_sales/prereg.md §7: before the full sweep launches, run a
6-scenario smoke (1 per roster model) to confirm all 6 roster models handle
the 5-turn sales conversation at the v6.1 generation config. Fixed at
prohibitive × moderate × medium difficulty.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_task4_sales import (  # noqa: E402
    MODELS,
    SCENARIOS,
    build_sample,
)

OUT = Path("src/manipulation_bench/scenarios/task4_sales_smoke.jsonl")

FRAME = "prohibitive"
INCENTIVE = "moderate"
DIFFICULTY = "medium"


def main() -> None:
    medium_scenarios = [s for s in SCENARIOS if s["difficulty"] == DIFFICULTY]
    # Pick the first medium-difficulty scenario as the canonical smoke product.
    smoke_scenario = medium_scenarios[0]

    samples = []
    for model in MODELS:
        sample = build_sample(smoke_scenario, FRAME, INCENTIVE, model)
        # Mark as smoke
        sample["metadata"]["experiment"] = "task4_sales_smoke"
        sample["metadata"]["condition"] = "pre_sweep_smoke"
        samples.append(sample)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"Wrote {len(samples)} samples -> {OUT}")
    print(
        f"  6 roster models × 1 frame ({FRAME}) × 1 incentive ({INCENTIVE}) × 1 scenario ({smoke_scenario['scenario_id']})"
    )
    print()
    print("# Pre-sweep smoke launch command:")
    print("inspect eval src/manipulation_bench/sales_task.py \\")
    print(f"    -T scenarios={OUT.name} \\")
    print("    --model openrouter/anthropic/claude-opus-4.7 \\")
    print('    --model-role model_a=\'{"model":"openrouter/anthropic/claude-opus-4.7"}\' \\')
    print(
        '    --model-role model_b=\'{"model":"openrouter/openai/gpt-5","model_args":{"reasoning_enabled":true}}\' \\'
    )
    print(
        '    --model-role model_c=\'{"model":"openrouter/google/gemini-3.1-pro-preview","model_args":{"reasoning_enabled":true}}\' \\'
    )
    print(
        '    --model-role model_d=\'{"model":"openrouter/x-ai/grok-4","model_args":{"reasoning_enabled":true}}\' \\'
    )
    print(
        '    --model-role model_e=\'{"model":"openrouter/meta-llama/llama-3.3-70b-instruct"}\' \\'
    )
    print(
        '    --model-role model_f=\'{"model":"openrouter/deepseek/deepseek-v3.2","model_args":{"reasoning_enabled":true}}\' \\'
    )
    print("    --log-dir logs/task4_sales_v61_smoke \\")
    print("    --temperature 0.7 --max-tokens 4096 --max-connections 6 --no-fail-on-error")


if __name__ == "__main__":
    main()
