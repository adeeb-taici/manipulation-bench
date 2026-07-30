"""Split each Tier 1 scenario file into per-model files.

GPT-5.6 Luna is served by OpenAI and Tencent Hy3 by DeepInfra, so the two
models can run as concurrent streams without contending for the same endpoint.
That requires scenario files containing only one model's scenarios, otherwise
each stream would re-run the other model's work.

A scenario belongs to a model if any of its under-test agent roles contains
that model's tag. Pinned support roles (truthful_debater, bystander_*,
model_neutral_*) are left untouched and appear in both splits, which is
correct: they are per-scenario counterparties, not the model under test.

Writes tier1_<env>_<tag>.jsonl alongside the originals.

Run: python paper/expanded_roster/scripts/split_scenarios_by_model.py
"""

from __future__ import annotations

import json
from pathlib import Path

SCEN = Path(__file__).resolve().parents[1] / "scenarios"
TAGS = ("luna", "hy3")
ENVS = ("t1_bargaining", "t2_debate", "t3_village", "t4_sales", "t5_committee", "t6_inbox")


def roles_of(d: dict) -> set[str]:
    out = set()
    for a in d.get("agents") or []:
        r = a.get("model_role")
        if r:
            out.add(r)
    md = d.get("metadata") or {}
    for r in (md.get("model_role"), d.get("model_role")):
        if r:
            out.add(r)
    for r in md.get("model_mapping") or {}:
        out.add(r)
    return out


def main() -> None:
    for env in ENVS:
        src = SCEN / f"tier1_{env}.jsonl"
        if not src.exists():
            print(f"  skip {env} (no source)")
            continue
        rows = [json.loads(line) for line in open(src, encoding="utf-8")]
        for tag in TAGS:
            keep = [r for r in rows if any(tag in role for role in roles_of(r))]
            out = SCEN / f"tier1_{env}_{tag}.jsonl"
            with open(out, "w", encoding="utf-8") as w:
                for r in keep:
                    w.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  {out.name:38s} {len(keep):5d} scenarios")
        total = sum(1 for r in rows if any(t in role for role in roles_of(r) for t in TAGS))
        if total != len(rows):
            print(f"    WARNING {env}: {len(rows) - total} scenarios matched no tag")


if __name__ == "__main__":
    main()
