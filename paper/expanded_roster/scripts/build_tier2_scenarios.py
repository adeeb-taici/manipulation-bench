"""Build Tier 2 scenario files from the Tier 1 factorial.

Tier 2 adds two independently non-reasoning models -- Mistral Large 3 and
Ling-2.6-1T -- so the design is the same full factorial Tier 1 ran, with the
config tag and seed swapped. Verified before writing: within an environment the
four Tier 1 configs are byte-identical once the config tag is normalised, apart
from a per-config `seed`. So cloning one config's rows is a faithful copy of the
design rather than a re-derivation of it.

Reasoning-mode note: Tier 1 carried two arms per model (`_on` / `_off`) because
the reasoning switch was the treatment. Neither Tier 2 model exposes a reasoning
parameter, so each contributes exactly one config.

Writes, alongside the Tier 1 files:
  tier2_<env>.jsonl            both configs        (2 x 2,265 = 4,530 total)
  tier2_<env>_<tag>.jsonl      per-model split, for concurrent streams

Run: python paper/expanded_roster/scripts/build_tier2_scenarios.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

SCEN = Path(__file__).resolve().parents[1] / "scenarios"

TEMPLATE_TAG = "luna_on"  # any Tier 1 config; they differ only by seed
TAGS = ("mistral", "ling")

ENVS = {
    "t1_bargaining": 900,
    "t2_debate": 690,
    "t3_village": 90,
    "t4_sales": 225,
    "t5_committee": 180,
    "t6_inbox": 180,
}


def derive_seed(scenario_id: str) -> int:
    """Deterministic per-scenario seed, so a rebuild reproduces byte-identically."""
    h = hashlib.sha256(scenario_id.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 9_000_000 + 1_000_000


def retag(row: dict, tag: str) -> dict:
    """Swap the config tag everywhere it appears, then re-seed."""
    s = json.dumps(row, ensure_ascii=False)
    if TEMPLATE_TAG not in s:
        raise ValueError(f"template tag missing from row {row.get('id')!r}")
    out = json.loads(s.replace(TEMPLATE_TAG, tag))
    if "seed" in out:
        out["seed"] = derive_seed(out["id"])
    return out


def main() -> None:
    grand = 0
    for env, expected in ENVS.items():
        src = SCEN / f"tier1_{env}.jsonl"
        if not src.exists():
            print(f"  SKIP {env}: {src.name} not found")
            continue
        rows = [json.loads(line) for line in open(src, encoding="utf-8")]
        template = [r for r in rows if TEMPLATE_TAG in r["id"]]
        if len(template) != expected:
            raise SystemExit(
                f"{env}: template has {len(template)} rows, expected {expected} "
                "-- refusing to build a factorial that is not full"
            )

        combined: list[dict] = []
        for tag in TAGS:
            built = [retag(r, tag) for r in template]
            ids = {r["id"] for r in built}
            if len(ids) != len(built):
                raise SystemExit(f"{env}/{tag}: duplicate scenario ids after retag")
            # The template tag must not survive anywhere in the output.
            leaked = [r["id"] for r in built if TEMPLATE_TAG in json.dumps(r)]
            if leaked:
                raise SystemExit(f"{env}/{tag}: template tag leaked into {len(leaked)} rows")
            out = SCEN / f"tier2_{env}_{tag}.jsonl"
            with open(out, "w", encoding="utf-8") as w:
                for r in built:
                    w.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"  {out.name:38s} {len(built):5d} scenarios")
            combined += built

        allf = SCEN / f"tier2_{env}.jsonl"
        with open(allf, "w", encoding="utf-8") as w:
            for r in combined:
                w.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  {allf.name:38s} {len(combined):5d} scenarios (both configs)")
        grand += len(combined)

    print(f"\n  TOTAL {grand} scenarios ({grand // len(TAGS)} per config x {len(TAGS)} configs)")


if __name__ == "__main__":
    main()
