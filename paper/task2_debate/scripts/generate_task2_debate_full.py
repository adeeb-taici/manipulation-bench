"""Task 2 Debate full-sweep scenario generator.

Locked design per paper/task2_debate/prereg.md (timestamp 2026-04-23T16:55-04:00):
  6 manipulator models × 5 frames × 3 incentives × 23 claims × 2 reps = 4,140 scenarios

Model-role bindings at eval time:
  truthful_debater       → Claude Opus 4.7 (pinned per A5)
  manipulator_claude     → Claude Opus 4.7
  manipulator_gpt5       → GPT-5 (reasoning_enabled=true)
  manipulator_gemini     → Gemini 3.1 Pro (reasoning_enabled=true)
  manipulator_grok       → Grok 4 (reasoning_enabled=true)
  manipulator_llama      → Llama 3.3 70B
  manipulator_deepseek   → DeepSeek v3.2 (reasoning_enabled=true)
  juror_a                → Gemini 3 Flash Preview
  juror_b                → Claude Haiku 4.5
  juror_c                → GPT-5 mini
  judge                  → Claude Opus 4.7

Usage:
    python paper/task2_debate/scripts/generate_task2_debate_full.py
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from task2_debate_claims import CLAIMS  # noqa: E402

from manipulation_bench.axes import FRAME_PROMPTS, INCENTIVE_PROMPTS  # noqa: E402

OUT = Path("src/manipulation_bench/scenarios/task2_debate_v61_full.jsonl")

MANIPULATORS: list[tuple[str, str]] = [
    ("manipulator_claude", "Claude-Opus-4.7"),
    ("manipulator_gpt5", "GPT-5"),
    ("manipulator_gemini", "Gemini-3.1-Pro"),
    ("manipulator_grok", "Grok-4"),
    ("manipulator_llama", "Llama-3.3-70B"),
    ("manipulator_deepseek", "DeepSeek-v3.2"),
]

# Canonical run-command bindings for the paper roster, keyed by role name.
# Used when --models is NOT overridden. When overridden, placeholders are
# printed instead so there's no risk of misleading copy-paste.
PAPER_ROSTER_BINDINGS: dict[str, str] = {
    "manipulator_claude": '\'{"model":"openrouter/anthropic/claude-opus-4.7"}\'',
    "manipulator_gpt5": '\'{"model":"openrouter/openai/gpt-5","model_args":{"reasoning_enabled":true}}\'',
    "manipulator_gemini": '\'{"model":"openrouter/google/gemini-3.1-pro-preview","model_args":{"reasoning_enabled":true}}\'',
    "manipulator_grok": '\'{"model":"openrouter/x-ai/grok-4","model_args":{"reasoning_enabled":true}}\'',
    "manipulator_llama": '\'{"model":"openrouter/meta-llama/llama-3.3-70b-instruct"}\'',
    "manipulator_deepseek": '\'{"model":"openrouter/deepseek/deepseek-v3.2","model_args":{"reasoning_enabled":true}}\'',
}

# Pinned framework roles (not part of the under-test roster). These appear in
# the printed run command verbatim regardless of --models.
PINNED_BINDINGS: list[tuple[str, str]] = [
    ("truthful_debater", '\'{"model":"openrouter/anthropic/claude-opus-4.7"}\''),
    ("juror_a", '\'{"model":"openrouter/google/gemini-3-flash-preview"}\''),
    ("juror_b", '\'{"model":"openrouter/anthropic/claude-haiku-4.5"}\''),
    ("juror_c", '\'{"model":"openrouter/openai/gpt-5-mini"}\''),
    ("judge", '\'{"model":"openrouter/anthropic/claude-opus-4.7"}\''),
]


def _parse_models_flag(value: str | None) -> list[tuple[str, str]] | None:
    """Parse ``--models claude,gpt5,...`` (auto-prefixes role with
    ``manipulator_``) or ``label=role,label=role`` (explicit pairs). Returns
    the same ``[(role, label)]`` shape as ``MANIPULATORS``, or None to use
    the paper roster.

    Examples:
        --models 'claude,gpt5,llama'
            → [("manipulator_claude","claude"), ("manipulator_gpt5","gpt5"),
               ("manipulator_llama","llama")]
        --models 'claude=manipulator_claude,gpt5=manipulator_gpt5'
            → [("manipulator_claude","claude"), ("manipulator_gpt5","gpt5")]
    """
    if not value:
        return None
    out: list[tuple[str, str]] = []
    for chunk in value.replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" in chunk:
            label, role = chunk.split("=", 1)
            out.append((role.strip(), label.strip()))
        else:
            out.append((f"manipulator_{chunk}", chunk))
    return out


FRAMES = ["prohibitive", "pro_social", "minimal", "selfish", "permissive"]
INCENTIVES = ["none", "moderate", "high"]
N_REPS = 2
BOOTSTRAP_SEED = 20260423  # A6 per PREREG §8


def build_manipulator_prompt(claim: dict, frame: str, incentive: str) -> str:
    """Claim-specific argument + frame suffix + incentive suffix."""
    base = claim["manipulator_baseline_prompt"]
    frame_text = FRAME_PROMPTS["debate"][frame]
    incentive_text = INCENTIVE_PROMPTS["debate"][incentive]
    parts = [base]
    if frame_text:
        parts.append(frame_text)
    if incentive_text:
        parts.append(incentive_text)
    return "\n\n".join(parts)


def build_scenarios() -> list[dict]:
    rng = random.Random(BOOTSTRAP_SEED)
    out: list[dict] = []
    for m_role, m_label in MANIPULATORS:
        for frame in FRAMES:
            for incentive in INCENTIVES:
                for claim in CLAIMS:
                    for rep in range(N_REPS):
                        scenario_id = (
                            f"t2_full_{m_label.lower()}_{frame}_{incentive}_"
                            f"{claim['claim_id']}_r{rep:02d}"
                        )
                        manipulator_prompt = build_manipulator_prompt(claim, frame, incentive)
                        out.append(
                            {
                                "id": scenario_id,
                                "topic": claim["topic"],
                                "protocol": "round_robin",
                                "num_rounds": 2,
                                "visibility": "all_to_all",
                                "max_tokens": 16384,
                                "ground_truth": claim["ground_truth"],
                                "description": (
                                    f"task=2 full manipulator={m_label} frame={frame} "
                                    f"incentive={incentive} claim={claim['claim_id']} "
                                    f"tier={claim['difficulty_tier']} rep={rep}"
                                ),
                                "agents": [
                                    {
                                        "name": "truthful",
                                        "model_role": "truthful_debater",
                                        "system_prompt": claim["truthful_prompt"],
                                        "position": "correct",
                                        "metadata": {"manipulative": False},
                                    },
                                    {
                                        "name": "manipulator",
                                        "model_role": m_role,
                                        "system_prompt": manipulator_prompt,
                                        "position": "incorrect",
                                        "metadata": {"manipulative": True},
                                    },
                                ],
                                "metadata": {
                                    "experiment": "task2_debate_v61_full",
                                    "condition": "self_play_manipulator_vs_pinned_truthful",
                                    "frame": frame,
                                    "incentive": incentive,
                                    "difficulty": claim["difficulty_tier"],
                                    "claim_id": claim["claim_id"],
                                    "manipulator_model": m_label,
                                    "panel_prior": claim["panel_prior"],
                                    "rep": rep,
                                    "seed": rng.randint(0, 10_000_000),
                                    "prereg_commit": "b54845a",
                                    "prereg_timestamp": "2026-04-23T16:55:10-04:00",
                                },
                            }
                        )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=f"Output JSONL path (default: {OUT})",
    )
    parser.add_argument(
        "--models",
        default=None,
        help=(
            "Override the manipulator roster. Examples: "
            "'claude,gpt5,llama' (auto-prefixes role with 'manipulator_'); "
            "'claude=manipulator_claude,gpt5=manipulator_gpt5' (explicit). "
            "Default: paper's 6-model roster."
        ),
    )
    args = parser.parse_args()

    global MANIPULATORS
    override = _parse_models_flag(args.models)
    if override:
        MANIPULATORS = override

    out = Path(args.output) if args.output else OUT
    scenarios = build_scenarios()
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        for s in scenarios:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"Wrote {len(scenarios)} scenarios -> {out}")
    print(
        f"  {len(MANIPULATORS)} manipulator models × {len(FRAMES)} frames × "
        f"{len(INCENTIVES)} incentives × {len(CLAIMS)} claims × {N_REPS} reps"
    )

    # Stratify check
    from collections import Counter

    by_tier = Counter(s["metadata"]["difficulty"] for s in scenarios)
    by_gt = Counter(s["ground_truth"] for s in scenarios)
    by_frame = Counter(s["metadata"]["frame"] for s in scenarios)
    by_inc = Counter(s["metadata"]["incentive"] for s in scenarios)
    by_model = Counter(s["metadata"]["manipulator_model"] for s in scenarios)
    print(f"  By tier: {dict(by_tier)}")
    print(f"  By GT: {dict(by_gt)}")
    print(f"  By frame: {dict(by_frame)}")
    print(f"  By incentive: {dict(by_inc)}")
    print(f"  By model: {dict(by_model)}")

    print()
    if override:
        print("Roster (role -> label):")
        for role, label in MANIPULATORS:
            print(f"  {role} -> {label}")
        print()
        print("Run with (substitute provider/model strings into each manipulator --model-role):")
    else:
        print("# Full-sweep launch command (after pre-sweep smoke passes):")
    print("inspect eval src/manipulation_bench/task.py \\")
    print(f"    -T scenarios={out.name} \\")
    print('    -T juror_roles="juror_a,juror_b,juror_c" \\')
    print("    --model openrouter/anthropic/claude-opus-4.7 \\")
    # truthful debater is pinned (PINNED_BINDINGS[0])
    print(f"    --model-role truthful_debater={PINNED_BINDINGS[0][1]} \\")
    for role, _label in MANIPULATORS:
        binding = (
            PAPER_ROSTER_BINDINGS.get(role, "openrouter/<provider>/<model>")
            if not override
            else "openrouter/<provider>/<model>"
        )
        print(f"    --model-role {role}={binding} \\")
    for role, binding in PINNED_BINDINGS[1:]:  # jurors + judge
        print(f"    --model-role {role}={binding} \\")
    print(f"    --log-dir logs/{out.stem} \\")
    print("    --temperature 0.7 --max-tokens 16384 --max-connections 20 --no-fail-on-error")


if __name__ == "__main__":
    main()
