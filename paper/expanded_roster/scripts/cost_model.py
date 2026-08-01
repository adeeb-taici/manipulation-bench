"""Cost and wall-clock model for the expanded-roster run.

Every token figure is MEASURED from the committed eval logs, not assumed:
per-environment, per-model input/output tokens were read out of
paper/task<N>/eval_log.eval and split into

  under-test   tokens spent by the model being evaluated (scales with the
               new model's price)
  pinned       tokens spent by fixed support agents that run in every
               scenario regardless of which model is under test (Debate's
               truthful debater, Village's 5 bystanders, Committee's 4
               neutral panellists, Debate's 3 jurors)

The pinned split is what makes this estimate non-obvious: in Debate,
Claude Opus 4.7 is the *pinned truthful debater* in all 4,140 committed
scenarios and accounts for 91% of that environment's input tokens, while each
under-test manipulator accounts for ~0.4%. So most of the marginal cost of
adding a model is NOT the new model.

Prices are $/M tokens from the OpenRouter catalogue, accessed 2026-07-29.

Run: python paper/expanded_roster/scripts/cost_model.py
"""

from __future__ import annotations

# ── Measured per-scenario token counts ────────────────────────────────
# under_in/out: tokens for the single under-test agent per scenario
#   (T1 is self-play, so both negotiating agents are the model under test)
# pinned: [(model, in_per_scenario, out_per_scenario), ...] support agents
# n: scenarios per model per environment (full factorial)
ENVS = {
    "T1 bargaining": {
        "n": 900,
        "under_in": 5_998,
        "under_out": 6_950,
        "pinned": [],
    },
    "T2 debate": {
        "n": 690,
        "under_in": 1_346,
        "under_out": 1_286,
        "pinned": [
            # LABEL CORRECTED. This line was "claude-opus-4.7 (truthful debater)".
            # prereg.md sec.3 pins the judge and the truthful debater to the SAME
            # slug, so the aggregate cannot separate them -- but per-call audit of
            # the committed log shows the debate turns are only ~4.7k input tokens
            # per scenario and essentially all of this is the scorer stack, of
            # which ~75% is juror_voting(n_jurors=7) re-sending the transcript.
            # The total is unchanged and still correct; only the attribution moved.
            # See scripts/pinned_cost_audit.py.
            ("claude-opus-4.7 (judge + scorer stack)", 52_732, 2_073),
            ("claude-haiku-4.5 (juror)", 1_478, 10),
            ("gemini-3-flash (juror)", 1_355, 4),
            ("gpt-5-mini (juror)", 1_314, 811),
        ],
    },
    "T3 village": {
        "n": 90,
        "under_in": 92_317,
        "under_out": 19_212,
        "pinned": [
            ("claude-haiku-4.5 (2 bystanders)", 211_135, 10_982),
            ("deepseek-chat (bystander)", 96_137, 3_796),
            ("gpt-5-mini (bystander)", 83_676, 22_689),
            ("gemini-3-flash (bystander)", 82_182, 1_508),
        ],
    },
    "T4 sales": {
        "n": 225,
        "under_in": 2_056,
        "under_out": 1_529,
        "pinned": [],
    },
    "T5 committee": {
        "n": 180,
        "under_in": 7_956,
        "under_out": 2_887,
        "pinned": [
            ("claude-haiku-4.5 (neutral)", 8_512, 922),
            ("deepseek-chat (neutral)", 6_900, 823),
            ("gemini-3-flash (neutral)", 6_721, 708),
            ("gpt-5-mini (neutral)", 6_587, 3_560),
        ],
    },
    "T6 inbox": {
        "n": 180,
        "under_in": 2_681,
        "under_out": 3_786,
        "pinned": [],
    },
}

# $/M tokens, OpenRouter catalogue accessed 2026-07-29.
PRICES = {
    "claude-opus-4.7 (judge + scorer stack)": (5.00, 25.00),
    "claude-haiku-4.5 (juror)": (1.00, 5.00),
    "claude-haiku-4.5 (2 bystanders)": (1.00, 5.00),
    "claude-haiku-4.5 (neutral)": (1.00, 5.00),
    "deepseek-chat (bystander)": (0.20, 0.80),
    "deepseek-chat (neutral)": (0.20, 0.80),
    "gpt-5-mini (juror)": (0.25, 2.00),
    "gpt-5-mini (bystander)": (0.25, 2.00),
    "gpt-5-mini (neutral)": (0.25, 2.00),
    "gemini-3-flash (juror)": (0.50, 3.00),
    "gemini-3-flash (bystander)": (0.50, 3.00),
    "gemini-3-flash (neutral)": (0.50, 3.00),
}

# Roster: (tier, label, slug, $in/M, $out/M, reasoning_mode)
# reasoning_mode scales expected OUTPUT tokens relative to the measured
# blend across the original six-model cohort:
#   "on"  -> 2.5x  (reasoning traces billed as output)
#   "off" -> 0.6x
#   "n/a" -> 1.0x  (no reasoning parameter exposed)
ROSTER = [
    (1, "GPT-5.6 Luna (reasoning ON)", "openai/gpt-5.6-luna", 0.50, 3.00, "on"),
    (1, "GPT-5.6 Luna (reasoning OFF)", "openai/gpt-5.6-luna", 0.50, 3.00, "off"),
    (1, "Tencent Hy3 (reasoning ON)", "tencent/hy3", 0.13, 0.53, "on"),
    (1, "Tencent Hy3 (reasoning OFF)", "tencent/hy3", 0.13, 0.53, "off"),
    (2, "Mistral Large 3", "mistralai/mistral-large-2512", 0.50, 1.50, "n/a"),
    (2, "Ling-2.6-1T", "inclusionai/ling-2.6-1t", 0.07, 0.62, "n/a"),
    (3, "Qwen3.5 9B", "qwen/qwen3.5-9b", 0.10, 0.15, "off"),
    (3, "Qwen3.5 27B", "qwen/qwen3.5-27b", 0.20, 1.56, "off"),
    (3, "Qwen3.5 122B-A10B", "qwen/qwen3.5-122b-a10b", 0.26, 2.08, "off"),
    (3, "Qwen3.5 397B-A17B", "qwen/qwen3.5-397b-a17b", 0.39, 2.34, "off"),
    (4, "Llama 4 Scout", "meta-llama/llama-4-scout", 0.10, 0.30, "n/a"),
    (4, "Llama 4 Maverick", "meta-llama/llama-4-maverick", 0.20, 0.80, "n/a"),
]

REASONING_OUT_MULT = {"on": 2.5, "off": 0.6, "n/a": 1.0}

# Observed throughput: the T5 committee full sweep ran 1,080 scenarios in
# 3h22m at --max-connections 20 (results.md provenance) = 5.35 scenarios/min.
# Village scenarios are ~14x larger in tokens, so throughput is scaled by
# each environment's token weight relative to committee.
T5_SCEN_PER_MIN_AT_20 = 1080 / 202.0


def pinned_cost_per_scenario(env: dict) -> float:
    total = 0.0
    for name, tin, tout in env["pinned"]:
        pin, pout = PRICES[name]
        total += tin * pin / 1e6 + tout * pout / 1e6
    return total


def env_tokens(env: dict) -> tuple[int, int]:
    return env["under_in"], env["under_out"]


def main() -> None:
    print("=" * 92)
    print("MEASURED TOKEN STRUCTURE (per scenario, from committed eval logs)")
    print("=" * 92)
    print(
        f"{'env':<16}{'scen/model':>11}{'UT in':>10}{'UT out':>9}{'pinned in':>11}{'pinned out':>11}{'pinned $/scen':>15}"
    )
    tot_ut_in = tot_ut_out = 0
    pinned_total = 0.0
    for name, e in ENVS.items():
        p_in = sum(t for _, t, _ in e["pinned"])
        p_out = sum(t for _, _, t in e["pinned"])
        pc = pinned_cost_per_scenario(e)
        pinned_total += pc * e["n"]
        tot_ut_in += e["under_in"] * e["n"]
        tot_ut_out += e["under_out"] * e["n"]
        print(
            f"{name:<16}{e['n']:>11}{e['under_in']:>10,}{e['under_out']:>9,}"
            f"{p_in:>11,}{p_out:>11,}{pc:>15.4f}"
        )
    print(
        f"\n  Per added model: under-test {tot_ut_in / 1e6:.2f}M in / {tot_ut_out / 1e6:.2f}M out"
        f"   |   PINNED SUPPORT COST = ${pinned_total:,.2f} (fixed, model-independent)"
    )
    print(
        f"  Total scenarios per model (all 6 envs, full factorial): {sum(e['n'] for e in ENVS.values()):,}"
    )
    print()

    print("=" * 92)
    print("COST PER ADDED MODEL-CONFIG")
    print("=" * 92)
    print(f"{'tier':>5}  {'config':<32}{'UT $':>9}{'pinned $':>10}{'TOTAL $':>10}")
    by_tier: dict[int, float] = {}
    for tier, label, _slug, pin, pout, mode in ROSTER:
        mult = REASONING_OUT_MULT[mode]
        ut = tot_ut_in * pin / 1e6 + tot_ut_out * mult * pout / 1e6
        total = ut + pinned_total
        by_tier[tier] = by_tier.get(tier, 0.0) + total
        print(f"{tier:>5}  {label:<32}{ut:>9.2f}{pinned_total:>10.2f}{total:>10.2f}")
    print()
    print("  Cumulative by tier (priority order):")
    run = 0.0
    for t in sorted(by_tier):
        run += by_tier[t]
        n_cfg = sum(1 for r in ROSTER if r[0] == t)
        print(f"    Tier {t} ({n_cfg} configs): ${by_tier[t]:>9,.2f}   cumulative ${run:>10,.2f}")
    print()

    # ── Wall clock ────────────────────────────────────────────────────
    print("=" * 92)
    print("WALL-CLOCK (at --max-connections 20, scaled from the T5 sweep's observed rate)")
    print("=" * 92)
    t5_tokens = ENVS["T5 committee"]["under_in"] + sum(
        t for _, t, _ in ENVS["T5 committee"]["pinned"]
    )
    total_hours = 0.0
    for name, e in ENVS.items():
        tokens = e["under_in"] + sum(t for _, t, _ in e["pinned"])
        rate = T5_SCEN_PER_MIN_AT_20 * (t5_tokens / tokens)
        hours_per_model = e["n"] / rate / 60
        total_hours += hours_per_model
        print(f"  {name:<16} {rate:>7.2f} scen/min   {hours_per_model:>6.2f} h per model")
    print(f"\n  Per model-config: {total_hours:.1f} h")
    for t in sorted(by_tier):
        n_cfg = sum(1 for r in ROSTER if r[0] == t)
        print(
            f"    Tier {t}: {n_cfg} configs x {total_hours:.1f} h = {n_cfg * total_hours:.0f} h sequential"
            f"  ({n_cfg * total_hours / 24:.1f} days)"
        )
    all_cfg = len(ROSTER)
    print(
        f"    All tiers: {all_cfg} configs = {all_cfg * total_hours:.0f} h ({all_cfg * total_hours / 24:.1f} days) sequential"
    )
    print()


if __name__ == "__main__":
    main()
