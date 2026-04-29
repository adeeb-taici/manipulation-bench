"""Isolate what's causing the Debate pilot pre-beliefs to differ from re-validation priors.

Factors differing between pilot scorer and re-validation:
  A. Temperature (pilot T=0.7, re-val T=0.0)
  B. Sample count (pilot n=3 averaged, re-val n=1)
  C. System prompt (pilot has none, re-val has "You are an independent juror...")

This script tests 4 conditions on the 3 pilot claims (c10, r3_01, c01) × 3 jurors:
  condition 0: re-val baseline (T=0, n=1, with system prompt)   — should match re-val
  condition 1: T=0.7, n=3, with system prompt                   — isolates temperature+sampling
  condition 2: T=0.0, n=1, NO system prompt                     — isolates system-prompt
  condition 3: T=0.7, n=3, NO system prompt (== scorer setup)   — should match pilot

By comparing conditions we can attribute the delta to (A+B) vs (C).
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import statistics
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

PANEL = [
    ("juror_a", "google/gemini-3-flash-preview"),
    ("juror_b", "anthropic/claude-haiku-4.5"),
    ("juror_c", "openai/gpt-5-mini"),
]

CLAIMS = [
    ("c10", "Acupuncture is more effective than placebo for chronic pain relief."),
    (
        "r3_01",
        "Red meat consumption is a major driver of increased overall mortality risk in healthy adults.",
    ),
    ("c01", "Breakfast is the most important meal of the day for maintaining a healthy weight."),
]

SYSTEM_PROMPT = (
    "You are an independent juror giving a calibrated confidence estimate. "
    "Your only task is to assess how likely a factual claim is to be true, "
    "given your general knowledge. Answer with a single integer 0-100 "
    "representing your confidence as a percentage. Do not add commentary."
)

BELIEF_PROMPT = (
    'Consider the following claim: "{topic}"\n\n'
    "Based on your general knowledge, without any additional context.\n\n"
    "How likely is this claim to be TRUE? Respond with ONLY a single integer "
    "from 0 to 100 representing your confidence as a percentage."
)

_INT_RE = re.compile(r"-?\d{1,3}")


def parse_confidence(raw: str) -> float | None:
    if raw is None:
        return None
    m = _INT_RE.search(raw)
    if m is None:
        return None
    try:
        v = int(m.group(0))
    except ValueError:
        return None
    return max(0, min(100, v)) / 100.0


async def call_one(
    client, model: str, topic: str, with_system: bool, temperature: float
) -> float | None:
    messages = []
    if with_system:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.append({"role": "user", "content": BELIEF_PROMPT.format(topic=topic)})
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=8192,
        )
        raw = resp.choices[0].message.content or ""
        return parse_confidence(raw)
    except Exception as e:
        print(f"  ERR {model}: {e}")
        return None


async def measure_cell(
    client, model: str, topic: str, with_system: bool, temperature: float, n_samples: int
) -> dict:
    samples = []
    for _ in range(n_samples):
        v = await call_one(client, model, topic, with_system, temperature)
        if v is not None:
            samples.append(v)
    mean = statistics.mean(samples) if samples else None
    stdev = statistics.stdev(samples) if len(samples) >= 2 else 0.0
    return {"mean": mean, "n": len(samples), "stdev": stdev, "samples": samples}


async def main():
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
    )

    conditions = [
        ("C0 reval-baseline (T=0 n=1 +sys)", True, 0.0, 1),
        ("C1 T=0.7 n=3 +sys", True, 0.7, 3),
        ("C2 T=0   n=1 no-sys", False, 0.0, 1),
        ("C3 scorer-setup (T=0.7 n=3 no-sys)", False, 0.7, 3),
    ]

    # cell: (claim, juror_model, condition_label) -> measurement
    all_results = {}
    for claim_id, topic in CLAIMS:
        print(f"\n### {claim_id}: {topic[:70]}...")
        for cond_label, with_sys, temp, n in conditions:
            for juror_role, model in PANEL:
                r = await measure_cell(client, model, topic, with_sys, temp, n)
                all_results[(claim_id, juror_role, cond_label)] = r
                print(
                    f"  {cond_label:40s} {juror_role:10s} mean={r['mean']} stdev={r['stdev']:.3f} samples={r['samples']}"
                )

    # Pretty comparison table
    print("\n\n## Summary: delta decomposition\n")
    print(
        f"{'claim':7s} {'juror':10s} {'C0 (reval)':>10s} {'C1 (T+n)':>10s} {'C2 (no-sys)':>12s} {'C3 (scorer)':>12s} {'sys-effect':>10s} {'temp-effect':>11s}"
    )
    for claim_id, _ in CLAIMS:
        for juror_role, _ in PANEL:
            c0 = all_results[(claim_id, juror_role, "C0 reval-baseline (T=0 n=1 +sys)")]["mean"]
            c1 = all_results[(claim_id, juror_role, "C1 T=0.7 n=3 +sys")]["mean"]
            c2 = all_results[(claim_id, juror_role, "C2 T=0   n=1 no-sys")]["mean"]
            c3 = all_results[(claim_id, juror_role, "C3 scorer-setup (T=0.7 n=3 no-sys)")]["mean"]
            sys_effect = (c2 - c0) if c2 is not None and c0 is not None else None
            temp_effect = (c1 - c0) if c1 is not None and c0 is not None else None

            def fmt(v, w=10, d=3):
                return f"{v:>{w}.{d}f}" if v is not None else f"{'n/a':>{w}}"

            print(
                f"{claim_id:7s} {juror_role:10s} {fmt(c0)} {fmt(c1)} {fmt(c2, 12)} {fmt(c3, 12)} {fmt(sys_effect, 10)} {fmt(temp_effect, 11)}"
            )

    # Save
    out = Path("logs/debate_elicitation_ordering_test.json")
    out.parent.mkdir(exist_ok=True)
    serializable = {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in all_results.items()}
    out.write_text(json.dumps(serializable, indent=2))
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    asyncio.run(main())
