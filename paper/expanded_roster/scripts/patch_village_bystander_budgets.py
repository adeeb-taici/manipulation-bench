"""Tighten Village bystander context budgets (prereg Amendment A2).

Village overflowed the two smallest-context pinned bystanders when the
manipulator is GPT-5.6 Luna: 104 of 105 errors were HTTP 400 context-length
rejections on agent_5 (deepseek-chat, 163,840 ctx) and agent_6
(claude-haiku-4.5, 200,000 ctx). The generator already caps those agents at
max_tokens=8192 (its own Amendments A1/A2) and that is not enough here,
because the manipulator emits up to scenario.max_tokens per turn and every
bystander must read all of it across 8 rounds x 3 phases.

Two per-agent levers are honoured by game_solver.py:
  - metadata['max_tokens']         overrides scenario.max_tokens (line ~105)
  - metadata['input_char_budget']  truncates visible turns, oldest first (~332)

This script tightens BOTH, on pinned bystanders only. The agent under test is
never modified, so the measured manipulator behaviour is unchanged and the
comparison to the frozen cohort remains on the manipulator side.

Applies to whichever bystander agents sit below LARGE_CTX_FLOOR.

Run: python paper/expanded_roster/scripts/patch_village_bystander_budgets.py
"""

from __future__ import annotations

import json
from pathlib import Path

SCEN = Path(__file__).resolve().parents[1] / "scenarios"

# Roles that need tightening, keyed by the model behind them.
# gpt-5-mini (400k) and gemini-3-flash (1.05M) have ample context and are left
# at their generator defaults.
TIGHTEN_ROLES = {
    "bystander_dschat": {"max_tokens": 1024, "input_char_budget": 60_000},  # 163,840 ctx
    "bystander_haiku": {"max_tokens": 1024, "input_char_budget": 80_000},  # 200,000 ctx
}

TARGETS = [
    "tier1_t3_village.jsonl",
    "tier1_t3_village_luna.jsonl",
    "tier1_t3_village_hy3.jsonl",
]


def main() -> None:
    for name in TARGETS:
        p = SCEN / name
        if not p.exists():
            print(f"  skip {name} (absent)")
            continue
        rows = [json.loads(line) for line in open(p, encoding="utf-8")]
        touched = 0
        for r in rows:
            for a in r.get("agents") or []:
                role = a.get("model_role")
                if role in TIGHTEN_ROLES:
                    md = a.setdefault("metadata", {})
                    md.update(TIGHTEN_ROLES[role])
                    touched += 1
        with open(p, "w", encoding="utf-8") as w:
            for r in rows:
                w.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  {name:34s} {len(rows):4d} scenarios, {touched} bystander agents tightened")

    # Show the resulting layout for one scenario as a check.
    p = SCEN / "tier1_t3_village_luna.jsonl"
    if p.exists():
        d = json.loads(open(p, encoding="utf-8").readline())
        print("\n  resulting agent budgets (first scenario):")
        for a in d["agents"]:
            md = a.get("metadata") or {}
            print(
                f"    {a['name']:9s} {a['model_role']:24s} "
                f"max_tokens={md.get('max_tokens', d.get('max_tokens'))!s:>6}  "
                f"char_budget={md.get('input_char_budget')!s:>7}"
            )


if __name__ == "__main__":
    main()
