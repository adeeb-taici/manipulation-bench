"""Phase-1 scouting menu for the Qwen / Llama / DeepSeek family grid.

Enumerates every candidate configuration across the three families and prices a
full factorial (2,265 scenarios x 6 environments) for each, so the roster can be
trimmed on cost and coverage before anything is pre-registered.

Two inputs, both committed so the menu is reproducible without re-hitting the API:

  scouting/or_snapshot_2026-08-01.json      OpenRouter catalogue + per-model
                                            endpoints (providers, quantization,
                                            per-endpoint pricing and parameters)
  scouting/reasoning_probe_2026-08-01.json  live reasoning-toggle probe

Token structure is MEASURED, reused verbatim from cost_model.py, which read it
out of the committed eval logs. The single most important number it produces is
not the model price: pinned support agents (Debate's truthful debater and
jurors, Village's bystanders, Committee's neutral panel) cost a fixed
~$262/config regardless of which model is under test, and dominate every row.

Provider pinning rule, applied here and inherited from expanded-roster A1:
prefer the cheapest tool-capable endpoint with DISCLOSED quantization, and
record whether a second such endpoint exists as a fallback. Endpoints without
tools/tool_choice cannot run this benchmark at all -- ACTION phases require tool
calls -- so they are excluded from pricing even when they are much cheaper.

Run: python paper/expanded_roster/scripts/scout_grid.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCOUT = REPO / "paper/expanded_roster/scouting"
SNAP = json.loads((SCOUT / "or_snapshot_2026-08-01.json").read_text(encoding="utf-8"))
PROBE = json.loads((SCOUT / "reasoning_probe_2026-08-01.json").read_text(encoding="utf-8"))

# ── Measured per-scenario token counts, verbatim from cost_model.py ──────────
ENVS = {
    "T1 bargaining": {"n": 900, "under_in": 5_998, "under_out": 6_950, "pinned": []},
    "T2 debate": {
        "n": 690,
        "under_in": 1_346,
        "under_out": 1_286,
        "pinned": [
            ("claude-opus-4.7", 52_732, 2_073, 5.00, 25.00),
            ("claude-haiku-4.5", 1_478, 10, 1.00, 5.00),
            ("gemini-3-flash", 1_355, 4, 0.50, 3.00),
            ("gpt-5-mini", 1_314, 811, 0.25, 2.00),
        ],
    },
    "T3 village": {
        "n": 90,
        "under_in": 92_317,
        "under_out": 19_212,
        "pinned": [
            ("claude-haiku-4.5", 211_135, 10_982, 1.00, 5.00),
            ("deepseek-chat", 96_137, 3_796, 0.20, 0.80),
            ("gpt-5-mini", 83_676, 22_689, 0.25, 2.00),
            ("gemini-3-flash", 82_182, 1_508, 0.50, 3.00),
        ],
    },
    "T4 sales": {"n": 225, "under_in": 2_056, "under_out": 1_529, "pinned": []},
    "T5 committee": {
        "n": 180,
        "under_in": 7_956,
        "under_out": 2_887,
        "pinned": [
            ("claude-haiku-4.5", 8_512, 922, 1.00, 5.00),
            ("deepseek-chat", 6_900, 823, 0.20, 0.80),
            ("gemini-3-flash", 6_721, 708, 0.50, 3.00),
            ("gpt-5-mini", 6_587, 3_560, 0.25, 2.00),
        ],
    },
    "T6 inbox": {"n": 180, "under_in": 2_681, "under_out": 3_786, "pinned": []},
}

UT_IN = sum(e["n"] * e["under_in"] for e in ENVS.values())
UT_OUT = sum(e["n"] * e["under_out"] for e in ENVS.values())
N_SCEN = sum(e["n"] for e in ENVS.values())
PINNED = sum(
    e["n"] * sum(ti * pi / 1e6 + to * po / 1e6 for _, ti, to, pi, po in e["pinned"])
    for e in ENVS.values()
)

# Reasoning pinned OFF costs less output than the corpus blend (cost_model.py).
OUT_MULT_OFF = 0.6
OUT_MULT_NA = 1.0

# ── Candidate grid ──────────────────────────────────────────────────────────
# series: the within-generation size series a config belongs to. Configs sharing
#         a series are directly comparable; configs in different series are not
#         a single parameter ladder and must never be plotted as one.
# total/active: billions. For dense models the two are equal. A trailing "?" in
# the printed table marks a config whose parameter count the provider does NOT
# state in the catalogue -- the value shown is lineage inference, not a recorded
# fact, and must not be plotted on a parameter axis until sourced.
PARAMS_UNVERIFIED = {"deepseek/deepseek-v3.2"}
CANDIDATES = [
    # (series, slug, total_B, active_B, arch, note)
    ("Qwen3.5", "qwen/qwen3.5-9b", 9, 9, "dense", ""),
    ("Qwen3.5", "qwen/qwen3.5-27b", 27, 27, "dense", ""),
    ("Qwen3.5", "qwen/qwen3.5-35b-a3b", 35, 3, "MoE", "rung not in the original plan"),
    ("Qwen3.5", "qwen/qwen3.5-122b-a10b", 122, 10, "MoE", ""),
    ("Qwen3.5", "qwen/qwen3.5-397b-a17b", 397, 17, "MoE", ""),
    ("Llama 3.1", "meta-llama/llama-3.1-8b-instruct", 8, 8, "dense", ""),
    ("Llama 3.1", "meta-llama/llama-3.1-70b-instruct", 70, 70, "dense", ""),
    ("Llama 4", "meta-llama/llama-4-scout", 109, 17, "MoE", "16 experts"),
    ("Llama 4", "meta-llama/llama-4-maverick", 400, 17, "MoE", "128 experts"),
    ("DeepSeek V4", "deepseek/deepseek-v4-flash-0731", 284, 13, "MoE", ""),
    (
        "DeepSeek V4",
        "deepseek/deepseek-v4-pro",
        1600,
        49,
        "MoE",
        "in frozen corpus w/ reasoning ON",
    ),
    ("DeepSeek V3", "deepseek/deepseek-chat-v3.1", 671, 37, "MoE", "hybrid thinking/non-thinking"),
    ("DeepSeek V3", "deepseek/deepseek-v3.2", 671, 37, "MoE", "params not stated in catalogue"),
]

REUSE = [
    ("Llama 3.3", "meta-llama/llama-3.3-70b-instruct", 70, 70, "dense", "frozen corpus, not re-run")
]


def pin_provider(slug: str) -> dict:
    """Cheapest tool-capable endpoint with disclosed quantization, + fallback count."""
    eps = SNAP["models"][slug]["endpoints"]
    usable = [
        e
        for e in eps
        if "tools" in e["supported_parameters"] and "tool_choice" in e["supported_parameters"]
    ]
    disclosed = [e for e in usable if e["quantization"] not in (None, "unknown")]
    pool = disclosed or usable
    pool = sorted(pool, key=lambda e: float(e["prompt"]))
    if not pool:
        return {
            "provider": None,
            "quant": None,
            "in": None,
            "out": None,
            "n_tool": 0,
            "n_disclosed": 0,
        }
    best = pool[0]
    return {
        "provider": best["provider_name"],
        "quant": best["quantization"] or "undisclosed",
        "in": float(best["prompt"]) * 1e6,
        "out": float(best["completion"]) * 1e6,
        "n_tool": len(usable),
        "n_disclosed": len(disclosed),
        "n_total": len(eps),
    }


def reasoning_mode(slug: str) -> str:
    sp = SNAP["models"][slug]["supported_parameters"]
    if "reasoning" not in sp and "include_reasoning" not in sp:
        return "none"
    v = (PROBE["results"].get(slug) or {}).get("verdict")
    if v and v.startswith("off-able"):
        return "off-able (verified)"
    return "present (UNVERIFIED)"


def cost(pin: dict, mode: str) -> float:
    if pin["in"] is None:
        return float("nan")
    mult = OUT_MULT_OFF if mode.startswith("off-able") else OUT_MULT_NA
    return UT_IN * pin["in"] / 1e6 + UT_OUT * mult * pin["out"] / 1e6


def main() -> None:
    print("=" * 118)
    print(
        f"PHASE-1 SCOUTING MENU   accessed {SNAP['accessed_utc']}   "
        f"{N_SCEN:,} scenarios x 6 envs per config"
    )
    print("=" * 118)
    print(f"  under-test tokens per config: {UT_IN / 1e6:.2f}M in / {UT_OUT / 1e6:.2f}M out")
    print(
        f"  PINNED SUPPORT COST: ${PINNED:,.2f} per config -- fixed, identical for every row below"
    )
    print()

    hdr = (
        f"{'series':<13}{'config':<34}{'total':>7}{'act':>6}{'arch':>7}  "
        f"{'reasoning':<22}{'provider|quant':<22}{'$in':>6}{'$out':>7}{'UT $':>8}{'TOTAL $':>9}"
    )
    print(hdr)
    print("-" * 118)

    rows, subtotal = [], {}
    for series, slug, tot, act, arch, note in CANDIDATES:
        pin = pin_provider(slug)
        mode = reasoning_mode(slug)
        ut = cost(pin, mode)
        total = ut + PINNED
        rows.append((series, slug, tot, act, arch, mode, pin, ut, total, note))
        subtotal[series] = subtotal.get(series, 0.0) + total

    last = None
    for series, slug, tot, act, arch, mode, pin, ut, total, _note in rows:
        if last is not None and series != last:
            print(
                f"{'':13}{'-- ' + last + ' subtotal':<34}{'':>26}{'':<22}{'':>19}{subtotal[last]:>9,.0f}"
            )
        short = slug.split("/", 1)[1]
        pq = f"{pin['provider']}|{pin['quant']}"
        u = "?" if slug in PARAMS_UNVERIFIED else " "
        print(
            f"{series:<13}{short:<34}{str(tot) + u:>7}{str(act) + u:>6}{arch:>7}  "
            f"{mode:<22}{pq:<22}{pin['in']:>6.2f}{pin['out']:>7.2f}{ut:>8.2f}{total:>9,.0f}"
        )
        last = series
    print(f"{'':13}{'-- ' + last + ' subtotal':<34}{'':>26}{'':<22}{'':>19}{subtotal[last]:>9,.0f}")

    grand = sum(subtotal.values())
    print("-" * 118)
    print(
        f"{'':13}{'GRAND TOTAL (' + str(len(rows)) + ' configs)':<34}{'':>26}{'':<22}{'':>19}{grand:>9,.0f}"
    )
    print(
        f"{'':13}{'  of which pinned support':<34}{'':>26}{'':<22}{'':>19}"
        f"{PINNED * len(rows):>9,.0f}"
    )
    print(
        f"{'':13}{'  of which models under test':<34}{'':>26}{'':<22}{'':>19}"
        f"{grand - PINNED * len(rows):>9,.0f}"
    )
    print()

    print("=" * 118)
    print(
        "REPRODUCIBILITY FLAGS (expanded-roster A1: no single-provider undisclosed-quantization configs)"
    )
    print("=" * 118)
    for series, slug, *_rest, pin, _ut, _t, _n in [
        (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9]) for r in rows
    ]:
        flags = []
        if pin["n_tool"] == 0:
            flags.append("NO TOOL-CAPABLE ENDPOINT -- cannot run this benchmark")
        elif pin["n_tool"] == 1:
            flags.append(f"single tool-capable endpoint ({pin['provider']}) -- no fallback")
        if pin["n_disclosed"] == 0 and pin["n_tool"]:
            flags.append("no tool-capable endpoint discloses quantization")
        if pin["n_tool"] and pin["n_tool"] < pin["n_total"]:
            flags.append(
                f"{pin['n_total'] - pin['n_tool']}/{pin['n_total']} endpoints lack tools (must pin provider)"
            )
        if flags:
            print(f"  {slug:<36} {'; '.join(flags)}")
    print()

    print("=" * 118)
    print("ABSENT / EXCLUDED")
    print("=" * 118)
    for slug in SNAP["absent_from_catalogue"]:
        print(f"  ABSENT    {slug:<44} not in the OpenRouter catalogue on {SNAP['accessed_utc']}")
    for slug, why in SNAP["excluded_by_rule"].items():
        print(f"  EXCLUDED  {slug:<44} {why}")
    print()
    print("  REUSE (no cost):")
    for series, slug, tot, act, arch, note in REUSE:
        print(f"    {series:<12}{slug:<40}{tot}B/{act}B {arch}  -- {note}")


if __name__ == "__main__":
    main()
