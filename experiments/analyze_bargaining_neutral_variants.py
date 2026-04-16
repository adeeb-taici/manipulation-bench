"""Analyze neutral-variant bargaining eval.

Reads one or more eval logs produced by the neutral-variants scenario file and
reports:
  1. Full (model x variant x incentive) response surface.
  2. Per-model across-variant spread — the robustness answer. If a model's
     neutral-row rate is stable across 5 wordings (low spread), the "default"
     interpretation holds. If it swings (high spread), Section 10's neutral-row
     finding is a prompt-interpretation artifact.
  3. Variant-specific comparison to Section 10 baselines (which used the
     `original` variant) — sanity check that `original` reproduces.
"""

import sys
from collections import defaultdict

from inspect_ai.log import read_eval_log


def main(*log_paths: str) -> None:
    all_samples = []
    for p in log_paths:
        log = read_eval_log(p)
        all_samples.extend(log.samples)
    print(f"Samples: {len(all_samples)} from {len(log_paths)} log(s)\n")

    # cells[(model, variant, penalty)] = list of lied flags
    cells: dict[tuple[str, str, int], list[int]] = defaultdict(list)
    models: set[str] = set()
    variants: set[str] = set()
    penalties: set[int] = set()

    for s in all_samples:
        meta = s.metadata.get("scenario", {}).get("metadata", {})
        model = meta.get("model")
        variant = meta.get("variant")
        penalty = meta.get("expected_penalty")
        if None in (model, variant, penalty):
            continue
        models.add(model)
        variants.add(variant)
        penalties.add(penalty)

        sc_entry = s.scores.get("bargaining_manipulation") if s.scores else None
        if not sc_entry:
            continue
        sc = sc_entry.value

        for agent in ("agent_a", "agent_b"):
            lied = sc.get(f"{agent}_lied")
            if lied is None:
                continue
            cells[(model, variant, penalty)].append(int(lied))

    def mean(xs: list[int]) -> float:
        return sum(xs) / len(xs) if xs else float("nan")

    variant_order = ["original", "minimal", "role_framed", "goal_agreement", "goal_payoff"]
    variants_sorted = [v for v in variant_order if v in variants]
    penalties_sorted = sorted(penalties)

    # 1. Full response surface
    print(f"{'=' * 88}")
    print("  Neutral variant x Incentive surface (manipulation rate)")
    print(f"{'=' * 88}\n")

    for m in sorted(models):
        print(f"  === {m} ===")
        header = f"    {'variant':<16s}  " + "  ".join(
            f"E={p:<3d}".rjust(14) for p in penalties_sorted
        )
        print(header)
        for v in variants_sorted:
            row_cells = [cells[(m, v, p)] for p in penalties_sorted]
            row_strs = [f"{mean(c):.3f} (n={len(c):2d})" for c in row_cells]
            print(f"    {v:<16s}  " + "  ".join(r.rjust(14) for r in row_strs))
        print()

    # 2. Across-variant spread per model (the robustness signal)
    print(f"{'=' * 88}")
    print("  Robustness: across-variant spread of manipulation rate")
    print(f"{'=' * 88}\n")
    print("  Pooled over E=0 and E=80 within each (model x variant) cell.")
    print("  Low spread => neutral-row result is stable. High spread => prompt artifact.\n")

    for m in sorted(models):
        pooled = {}
        for v in variants_sorted:
            merged: list[int] = []
            for p in penalties_sorted:
                merged.extend(cells[(m, v, p)])
            pooled[v] = mean(merged) if merged else float("nan")
        rates = [r for r in pooled.values() if r == r]  # NaN filter
        spread = (max(rates) - min(rates)) if rates else float("nan")

        print(f"  === {m} ===  spread = {spread:.3f}")
        for v in variants_sorted:
            print(f"    {v:<16s}  {pooled[v]:.3f}")
        print()

    # 3. Section-10 baseline reproduction check
    print(f"{'=' * 88}")
    print("  Section 10 reproduction check (variant=original, E=0 vs E=80)")
    print(f"{'=' * 88}\n")
    print("  Section 10 reported (original prompt, neutral row):")
    print("    Claude: E=0 0.900, E=80 0.300")
    print("    GPT-5:  E=0 1.000, E=80 0.800")
    print("    Grok:   E=0 0.100, E=80 0.050\n")
    print("  This run (original variant only):")
    for m in sorted(models):
        e0 = mean(cells[(m, "original", 0)]) if (m, "original", 0) in cells else float("nan")
        e80 = mean(cells[(m, "original", 80)]) if (m, "original", 80) in cells else float("nan")
        print(f"    {m:<8s} E=0 {e0:.3f}, E=80 {e80:.3f}")
    print()

    # 4. Diagnostic: goal_payoff vs goal_agreement per model
    # The sharpest test of the "implicit sanction" hypothesis.
    print(f"{'=' * 88}")
    print("  Diagnostic: does 'maximize your payoff' license manipulation?")
    print(f"{'=' * 88}\n")
    print("  Pooled over E=0 and E=80. Large positive delta => model reads")
    print("  payoff-maximization framing as sanction to misrepresent.\n")
    for m in sorted(models):
        agreement_pool: list[int] = []
        payoff_pool: list[int] = []
        for p in penalties_sorted:
            agreement_pool.extend(cells[(m, "goal_agreement", p)])
            payoff_pool.extend(cells[(m, "goal_payoff", p)])
        a_rate = mean(agreement_pool) if agreement_pool else float("nan")
        p_rate = mean(payoff_pool) if payoff_pool else float("nan")
        delta = p_rate - a_rate
        print(
            f"    {m:<8s} goal_agreement {a_rate:.3f}  |  goal_payoff {p_rate:.3f}  |  delta {delta:+.3f}"
        )
    print()


if __name__ == "__main__":
    main(*sys.argv[1:])
