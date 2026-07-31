"""Write a `_remaining` scenario file: the scenarios a run has not yet scored.

Used when a sweep is restarted under changed run parameters and the work already
completed should be kept rather than re-run. Tier 1 set the precedent in
Amendment A3, where 40 scored Village-Hy3 samples were retained and merged while
only the remainder was re-collected.

A scenario counts as done if a sample with its id exists in the log directory
AND that sample yielded a usable primary metric. Errored and null-metric samples
are re-run.

usage: build_tier2_remaining.py <env_stem> <tag> [logdir]
   eg: build_tier2_remaining.py t1_bargaining ling
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

WT = Path(__file__).resolve().parents[3]
SCEN = WT / "paper/expanded_roster/scenarios"
LOGROOT = Path("C:/Users/zaman/workplace/manipulation-bench/logs/tier2_expanded")

PRIMARY = {
    "t1_bargaining": ("bargaining_commit", None),
    "t2_debate": ("ground_truth_persuasion", "manipulation_occurred"),
    "t3_village": ("exploitation_rate", "agent_1"),
    "t4_sales": ("sales_classifier", "manipulation_rate"),
    "t5_committee": ("initial_rating_bias", "initial_bias"),
    "t6_inbox": ("inbox_triage", "suppression_rate"),
}


def usable(stem: str, scores: dict) -> bool:
    scorer, key = PRIMARY[stem]
    s = scores.get(scorer)
    if not isinstance(s, dict):
        return False
    v = s.get("value")
    if not isinstance(v, dict):
        return False
    if stem == "t1_bargaining":
        lied = [x for k, x in v.items() if k.endswith("_lied")]
        return bool(lied) and all(x is not None for x in lied)
    return v.get(key) is not None


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    stem, tag = sys.argv[1], sys.argv[2]
    logdir = Path(sys.argv[3]) if len(sys.argv) > 3 else LOGROOT / f"{stem}_{tag}"

    src = SCEN / f"tier2_{stem}_{tag}.jsonl"
    rows = [json.loads(line) for line in open(src, encoding="utf-8")]

    done: set[str] = set()
    for f in sorted(logdir.glob("*.eval")):
        try:
            z = zipfile.ZipFile(f)
        except Exception:
            continue
        for nm in z.namelist():
            if not nm.startswith("samples/"):
                continue
            try:
                s = json.loads(z.read(nm))
            except Exception:
                continue
            if s.get("error"):
                continue
            if usable(stem, s.get("scores") or {}):
                done.add(str(s.get("id")))

    remaining = [r for r in rows if r["id"] not in done]
    out = SCEN / f"tier2_{stem}_{tag}_remaining.jsonl"
    with open(out, "w", encoding="utf-8") as w:
        for r in remaining:
            w.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"  source     {src.name}          {len(rows):5d}")
    print(f"  already done (usable)             {len(done):5d}")
    print(f"  {out.name:38s} {len(remaining):5d}")
    if len(done) + len(remaining) != len(rows):
        print(
            f"  WARNING: {len(done)} + {len(remaining)} != {len(rows)} "
            "-- log contains ids absent from the scenario file"
        )


if __name__ == "__main__":
    main()
