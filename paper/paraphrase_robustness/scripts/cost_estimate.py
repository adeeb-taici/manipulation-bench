"""Reproducible cost estimate for the paraphrase-robustness sweep.

Reads token usage from the existing combined eval logs (T3 Village, T4 Sales),
applies provider $/MTok pricing, and projects the cost of the 630-scenario
addendum sweep (180 T3 + 450 T4).

Usage: python paper/paraphrase_robustness/scripts/cost_estimate.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import read_eval_log

# Per-million-token pricing (USD), May 2026 OpenRouter list prices for input
# and output, no cache discount applied. Bystander tier prices included for T3.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    # roster
    "openrouter/anthropic/claude-opus-4.7": (15.0, 75.0),
    "openrouter/openai/gpt-5.5-20260423": (5.0, 40.0),
    "openrouter/openai/gpt-5": (5.0, 40.0),
    "openrouter/google/gemini-3.1-pro-preview": (3.5, 15.0),
    "openrouter/x-ai/grok-4": (5.0, 25.0),
    "openrouter/meta-llama/llama-3.3-70b-instruct": (0.4, 0.4),
    "openai-api/deepseek/deepseek-v4-pro": (0.6, 2.4),
    "openrouter/deepseek/deepseek-v3.2": (0.6, 2.4),
    # T3 bystanders
    "openrouter/anthropic/claude-haiku-4.5": (1.0, 5.0),
    "openrouter/openai/gpt-5-mini": (0.25, 2.0),
    "openrouter/google/gemini-3-flash-preview": (0.10, 0.40),
    "openrouter/deepseek/deepseek-chat": (0.27, 1.10),
}


def cost_for_usage(model: str, usage) -> float | None:
    if model not in PRICES_PER_MTOK:
        return None
    inp_p, out_p = PRICES_PER_MTOK[model]
    return usage.input_tokens / 1e6 * inp_p + usage.output_tokens / 1e6 * out_p


def avg_cost_per_scenario(log_path: str) -> tuple[float, int]:
    log = read_eval_log(log_path)
    total = 0.0
    n = 0
    for s in log.samples:
        if s.error or not s.model_usage:
            continue
        sc_cost = 0.0
        skip = False
        for model, usage in s.model_usage.items():
            c = cost_for_usage(model, usage)
            if c is None:
                skip = True
                break
            sc_cost += c
        if skip:
            continue
        total += sc_cost
        n += 1
    return total / n if n else 0.0, n


def main() -> None:
    out = {}
    for task, log, scenarios in [
        ("T3_village", "paper/task3_village/eval_log.eval", 180),
        ("T4_sales", "paper/task4_sales/eval_log.eval", 450),
    ]:
        avg, n = avg_cost_per_scenario(log)
        proj = avg * scenarios
        print(f"{task}: avg ${avg:.4f}/scenario over n={n} -> projecting ${proj:.2f} for {scenarios} scenarios")
        out[task] = dict(avg_per_scenario=avg, n_observed=n, projected=proj, scenarios=scenarios)

    grand = sum(v["projected"] for v in out.values())
    out["total_projected"] = grand
    out["total_with_15pct_buffer"] = grand * 1.15
    print(f"\nTotal projected: ${grand:.2f}")
    print(f"+ 15% retry buffer: ${grand * 1.15:.2f}")
    print("Budget ceiling: $400")

    Path("paper/paraphrase_robustness/cost_estimate.json").write_text(
        json.dumps(out, indent=2)
    )


if __name__ == "__main__":
    main()
