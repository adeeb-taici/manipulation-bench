"""Sample bargaining transcripts to inspect WHY high incentive deters.

Bargaining is the only task where 'high incentive' is a structural
audit penalty (E in {0, 80, 250}). Pull matched cells where the same
(model, frame, difficulty, valuations) is run with E=0 vs E=250, and
print the manipulator's discussion turns side by side.

Goal: see whether the deterrence shows up as
  - explicit penalty arithmetic ("250 > 100 * 99/101 so lying is dominated")
  - risk/expected-value language
  - stance shift ("honest is better here" vs "I should lie")
  - or just silently smaller deviations.

Note: the agent-side metadata uses `expected_penalty` (numeric 0/80/250),
not a categorical 'none/moderate/high' label. Frame is categorical.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import defaultdict

from inspect_ai.log import read_eval_log

ROOT = Path(__file__).resolve().parents[4]  # repo root
LOG = ROOT / "paper" / "task1_bargaining" / "eval_log.eval"
OUT = Path(__file__).resolve().parent / "out" / "04_traces"
OUT.mkdir(parents=True, exist_ok=True)

print(f"Reading {LOG} ...")
log = read_eval_log(str(LOG))
print(f"  {len(log.samples)} samples")

def axis_of(sample):
    md = (sample.metadata or {}).get("scenario", {}).get("metadata", {})
    return {
        "model": md.get("model"),
        "frame": md.get("frame"),
        "expected_penalty": md.get("expected_penalty"),
        "difficulty": md.get("difficulty"),
        "v_a": md.get("v_a"),
        "v_b": md.get("v_b"),
        "rep": md.get("rep"),
    }

# Index by (model, frame, difficulty, v_a, v_b, rep) to find matched cells
# differing only in expected_penalty
buckets = defaultdict(dict)  # bucket -> {penalty -> sample}
for s in log.samples:
    a = axis_of(s)
    if any(v is None for k, v in a.items() if k != "expected_penalty"):
        continue
    bucket_key = (a["model"], a["frame"], a["difficulty"], a["v_a"], a["v_b"], a["rep"])
    buckets[bucket_key][a["expected_penalty"]] = s

# Find matched pairs at E=0 vs E=250 on permissive frame, high difficulty
TARGETS = []
for k, by_pen in buckets.items():
    model, frame, diff, va, vb, rep = k
    if frame != "permissive" or diff != "high":
        continue
    if 0 in by_pen and 250 in by_pen:
        TARGETS.append((k, by_pen[0], by_pen[250]))

print(f"\nMatched (E=0, E=250) pairs on permissive×high: {len(TARGETS)}")
# Spread across models, take first 2 per model
by_model = defaultdict(list)
for t in TARGETS:
    by_model[t[0][0]].append(t)
selected = []
for model, lst in by_model.items():
    selected.extend(lst[:2])
print(f"Selected {len(selected)} pairs across {len(by_model)} models")

def extract_manipulator_turns(sample):
    """Return the agent's per-turn content. Both agents speak in self-play
    bargaining; we return both labeled by speaker. Also pull the committed
    valuation from the sample score."""
    turns = sample.store.get("InteractionState:turns", []) or []
    score = (sample.scores or {}).get("bargaining_commit")
    score_val = score.value if score else None
    # The score is a dict per agent
    md = (sample.metadata or {}).get("scenario", {}).get("metadata", {})
    return {
        "sample_id": sample.id,
        "model": md.get("model"),
        "frame": md.get("frame"),
        "expected_penalty": md.get("expected_penalty"),
        "difficulty": md.get("difficulty"),
        "true_valuations": md.get("true_valuations"),
        "score": score_val,
        "turns": [
            {"speaker": t.get("speaker"), "round": t.get("round"),
             "phase": (t.get("metadata") or {}).get("phase"),
             "content": t.get("content", "")}
            for t in turns
        ],
    }

# Print a digestible side-by-side
out_blocks = []
for k, s_low, s_high in selected:
    block = {
        "cell": {"model": k[0], "frame": k[1], "difficulty": k[2],
                 "v_a": k[3], "v_b": k[4], "rep": k[5]},
        "E0": extract_manipulator_turns(s_low),
        "E250": extract_manipulator_turns(s_high),
    }
    out_blocks.append(block)

with open(OUT / "matched_pairs.json", "w") as f:
    json.dump(out_blocks, f, indent=2, default=str)
print(f"Wrote {OUT / 'matched_pairs.json'}")

# Console-print the first 3 pairs in readable form
for block in out_blocks[:3]:
    cell = block["cell"]
    print(f"\n{'='*78}")
    print(f"MODEL: {cell['model']}  v_a={cell['v_a']} v_b={cell['v_b']}  rep={cell['rep']}")
    print(f"     (frame={cell['frame']}, difficulty={cell['difficulty']})")
    for label, ext in [("E=0", block["E0"]), ("E=250", block["E250"])]:
        print(f"\n--- {label} ---")
        print(f"  score: {ext['score']}")
        # Print only the manipulator agent's turns. In self-play both could
        # be 'manipulator'; the asymmetric one is the low-value agent (v=1
        # in v_a=1,v_b=100 setups). Identify by truthful valuation.
        tv = ext.get("true_valuations") or {}
        # Print all turns but tag which is the low-value agent
        low_agent = "agent_a" if (cell["v_a"] or 0) < (cell["v_b"] or 0) else "agent_b"
        print(f"  low-value agent (likely manipulator-tempted): {low_agent}")
        for t in ext["turns"]:
            tag = "[LOW]" if t["speaker"] == low_agent else "[hi] "
            content = (t["content"] or "")[:600].replace("\n", " ")
            print(f"  {tag} R{t['round']} {t['phase']}: {content}")
