"""Build a Village-Hy3 rerun file containing only the scenarios still missing.

The first Village-Hy3 attempt stalled at 40/180 (39 hy3_on, 1 hy3_off) with no
output for 80+ minutes. Those 40 are scored and valid, so they are kept and the
rerun covers only the remaining 140.

Ordering puts hy3_off first. That arm runs ~5.4x faster (no reasoning tokens),
so banking it early secures full six-environment coverage for at least one Hy3
config before the slow arm risks stalling again.

Reads every .eval under the original log dir, treats a sample as complete only
if it carries a usable primary metric, and writes the complement.

Run: python paper/expanded_roster/scripts/build_village_hy3_remaining.py
"""

from __future__ import annotations

import json
import zipfile
from collections import Counter
from pathlib import Path

WT = Path(__file__).resolve().parents[3]
SCEN = WT / "paper" / "expanded_roster" / "scenarios"
LOGDIR = Path("C:/Users/zaman/workplace/manipulation-bench/logs/tier1_expanded/t3_village_hy3")

SRC = SCEN / "tier1_t3_village_hy3.jsonl"
OUT = SCEN / "tier1_t3_village_hy3_remaining.jsonl"


def completed_ids() -> set[str]:
    done: set[str] = set()
    for f in sorted(LOGDIR.glob("*.eval")):
        try:
            z = zipfile.ZipFile(f)
        except Exception:
            continue
        for nm in z.namelist():
            if not nm.startswith("samples/"):
                continue
            try:
                d = json.loads(z.read(nm))
            except Exception:
                continue
            if d.get("error"):
                continue
            sc = (d.get("scores") or {}).get("exploitation_rate")
            v = sc.get("value") if isinstance(sc, dict) else None
            if isinstance(v, dict) and v.get("agent_1") is not None:
                done.add(str(d.get("id")))
    return done


def main() -> None:
    done = completed_ids()
    rows = [json.loads(line) for line in open(SRC, encoding="utf-8")]

    remaining = [r for r in rows if str(r.get("id")) not in done]
    # hy3_off first: faster arm, bank full coverage for it before the slow arm.
    remaining.sort(key=lambda r: 0 if "hy3_off" in str(r.get("id")) else 1)

    with open(OUT, "w", encoding="utf-8") as w:
        for r in remaining:
            w.write(json.dumps(r, ensure_ascii=False) + "\n")

    def tally(rs):
        c = Counter()
        for r in rs:
            c["hy3_on" if "hy3_on" in str(r.get("id")) else "hy3_off"] += 1
        return dict(c)

    print(f"already complete : {len(done):3d}  {tally([{'id': i} for i in done])}")
    print(f"remaining to run : {len(remaining):3d}  {tally(remaining)}")
    print(f"wrote -> {OUT.name}")
    print("\norder check (first 3, last 3):")
    for r in remaining[:3]:
        print("   ", r["id"])
    print("    ...")
    for r in remaining[-3:]:
        print("   ", r["id"])


if __name__ == "__main__":
    main()
