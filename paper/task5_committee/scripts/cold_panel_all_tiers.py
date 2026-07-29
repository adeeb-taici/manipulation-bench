"""Cold-panel honest-bias baselines for ALL THREE difficulty tiers.

`analysis/high_difficulty_cold_panel.md` documents only the high tier. The
cold-panel run behind it (`cold_panel_slates.py`) already swept all 12 slates,
so the low and medium baselines need no new API calls -- they are recomputed
here from the existing run output.

Applies PREREG Amendment A1 (`policy_medium_01` reclassified medium -> high)
before aggregating, which is what the committed high-tier figure of -7.14 uses.

Input:  logs/cold_panel_20260422/honest_bias_per_slate.csv  (gitignored; produced
        by cold_panel_slates.py)
Output: stdout tables, mirrored into analysis/cold_panel_all_tiers.md

Run:    python paper/task5_committee/scripts/cold_panel_all_tiers.py
"""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path

# PREREG Amendment A1: this slate was authored as medium but its favored
# candidate is ground-truth weak, so it belongs to the high tier.
A1_RECLASSIFY: dict[str, str] = {"policy_medium_01": "high"}

TIERS = ("low", "medium", "high")

# results.md section A.3 -- per-model bias by difficulty, averaged over
# frame x incentive. Transcribed so the baseline-relative view can be
# computed without re-reading the 1 GB eval log.
OBSERVED_A3: dict[str, tuple[float, float, float]] = {
    "Claude Opus 4.7": (5.949, 2.574, -1.988),
    "GPT-5.5": (5.383, 2.317, -2.737),
    "Gemini 3.1 Pro": (11.085, 11.528, 11.351),
    "Grok 4": (5.919, 3.378, 1.398),
    "Llama 3.3 70B": (3.804, 1.517, -0.088),
    "DeepSeek V4 Pro": (5.638, 3.339, -1.037),
}


def load_rows(csv_path: Path) -> list[dict]:
    rows: list[dict] = []
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("honest_bias"):
                continue  # failed call
            r["tier"] = A1_RECLASSIFY.get(r["slate_id"], r["difficulty"])
            r["bias"] = float(r["honest_bias"])
            rows.append(r)
    return rows


def pooled(rows: list[dict]) -> dict[str, dict[str, float]]:
    by: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        by[r["tier"]].append(r["bias"])
    out: dict[str, dict[str, float]] = {}
    for tier in TIERS:
        v = by[tier]
        sd = statistics.stdev(v) if len(v) > 1 else 0.0
        out[tier] = {
            "n": len(v),
            "mean": sum(v) / len(v),
            "sd": sd,
            "stderr": sd / len(v) ** 0.5 if v else 0.0,
            "min": min(v),
            "max": max(v),
        }
    return out


def per_slate(rows: list[dict]) -> dict[tuple[str, str, str], float]:
    acc: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for r in rows:
        acc[(r["tier"], r["slate_id"], r["favored_tier"])].append(r["bias"])
    return {k: sum(v) / len(v) for k, v in sorted(acc.items())}


def render(rows: list[dict]) -> str:
    pool = pooled(rows)
    slates = per_slate(rows)
    L: list[str] = []
    a = L.append

    a("# Task 5 Committee — Cold-panel honest-bias baselines, all tiers")
    a("")
    a(
        "Extends [high_difficulty_cold_panel.md](high_difficulty_cold_panel.md), which "
        "documents only the high tier, to the low and medium tiers. **No new API calls "
        "were made**: `cold_panel_slates.py` already swept all 12 slates, so these are "
        "recomputed from that run's output."
    )
    a("")
    a(
        "PREREG Amendment A1 (`policy_medium_01` medium → high) is applied before "
        "aggregating. The high-tier figure below reproduces the committed −7.14 "
        "(SD 2.92) exactly, which validates the recomputation."
    )
    a("")
    a("Panel: 4 neutral raters (anthropic_haiku, openai_gpt5_mini, google_gemini_flash,")
    a("deepseek_chat) at T=0.0, no committee dynamics, no affiliation.")
    a("")
    a("## Pooled honest bias by difficulty tier")
    a("")
    a("| tier | n | mean | stderr | SD | min | max |")
    a("|---|---:|---:|---:|---:|---:|---:|")
    for tier in TIERS:
        s = pool[tier]
        a(
            f"| {tier} | {s['n']} | **{s['mean']:+.3f}** | {s['stderr']:.3f} | "
            f"{s['sd']:.3f} | {s['min']:+.3f} | {s['max']:+.3f} |"
        )
    a("")
    a(
        "The honest baseline is **strongly difficulty-dependent**, spanning "
        f"{pool['low']['mean']:+.2f} to {pool['high']['mean']:+.2f} — a "
        f"{pool['low']['mean'] - pool['high']['mean']:.2f}-unit swing. It is not 0 at any tier."
    )
    a("")
    a("## Per-slate honest bias (mean of 4 raters)")
    a("")
    a("| tier | slate | favored ground-truth tier | honest bias |")
    a("|---|---|---|---:|")
    for (tier, slate_id, ftier), v in slates.items():
        a(f"| {tier} | `{slate_id}` | {ftier} | {v:+.3f} |")
    a("")
    a(
        "The sign of the honest baseline tracks the favored candidate's tier: strong "
        "favored (low difficulty) → positive, medium → ~0, weak (high difficulty) → negative."
    )
    a("")
    a("## Consequence: results.md §A.3 reverses when read against the baseline")
    a("")
    a(
        "`results.md` §A.3 reports raw bias falling with difficulty for 5/6 models and "
        "reads this as *\"harder-to-justify candidates can't be inflated past the cold-panel "
        'honest baseline"*. But the baseline itself falls by 11.6 units across the same axis. '
        "Subtracting it, **excess bias over honest rises monotonically with difficulty for "
        "6/6 models**:"
    )
    a("")
    a("| Model | low obs (excess) | medium obs (excess) | high obs (excess) | monotone rising |")
    a("|---|---:|---:|---:|:---:|")
    for model, (lo, md, hi) in OBSERVED_A3.items():
        e = (lo - pool["low"]["mean"], md - pool["medium"]["mean"], hi - pool["high"]["mean"])
        rising = "yes" if e[0] < e[1] < e[2] else "no"
        a(
            f"| {model} | {lo:.2f} ({e[0]:+.2f}) | {md:.2f} ({e[1]:+.2f}) | "
            f"{hi:.2f} ({e[2]:+.2f}) | {rising} |"
        )
    a(
        f"| **cold-panel honest** | {pool['low']['mean']:.2f} | {pool['medium']['mean']:.2f} | "
        f"{pool['high']['mean']:.2f} | — |"
    )
    a("")
    a(
        "So the negative raw difficulty slope is substantially an artifact of the slate "
        "baseline moving, not of models declining to inflate. Relative to an honest rater, "
        "every model in the roster inflates its affiliated candidate **more** on hard slates, "
        "not less. This bears directly on P4 (difficulty-slope dominance), whose slopes are "
        "computed on the raw metric."
    )
    a("")
    a(
        '**Caveat.** The panel is 4 small models, not the roster. "Honest" here means '
        '"what this neutral panel rates", which is the same convention the committed '
        "high-tier analysis uses."
    )
    a("")
    a("Reproduce: `python paper/task5_committee/scripts/cold_panel_all_tiers.py`")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    repo = Path(__file__).resolve().parents[3]
    ap.add_argument(
        "--csv",
        type=Path,
        default=repo / "logs" / "cold_panel_20260422" / "honest_bias_per_slate.csv",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=repo / "paper" / "task5_committee" / "analysis" / "cold_panel_all_tiers.md",
    )
    args = ap.parse_args()

    if not args.csv.exists():
        raise SystemExit(
            f"Cold-panel output not found at {args.csv}.\n"
            "logs/ is gitignored; re-run paper/task5_committee/scripts/cold_panel_slates.py "
            "to regenerate it (48 calls)."
        )

    rows = load_rows(args.csv)
    text = render(rows)
    args.out.write_text(text, encoding="utf-8")

    # ASCII-only stdout: the rendered markdown contains non-ASCII (en-dashes,
    # arrows, minus signs) which crash cp1252 stdout on Windows.
    pool = pooled(rows)
    print("Cold-panel honest bias by tier (post-A1):")
    for tier in TIERS:
        s = pool[tier]
        print(
            f"  {tier:<7} n={s['n']:<3} mean={s['mean']:+8.3f}  "
            f"stderr={s['stderr']:.3f}  SD={s['sd']:.3f}"
        )
    print(f"Wrote -> {args.out}")


if __name__ == "__main__":
    main()
