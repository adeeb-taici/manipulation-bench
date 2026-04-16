"""Analyze 2x2 bargaining eval: instruction x incentive response surface per model."""

import sys
from collections import defaultdict

from inspect_ai.log import read_eval_log


def main(*log_paths: str) -> None:
    all_samples = []
    for p in log_paths:
        log = read_eval_log(p)
        all_samples.extend(log.samples)
    print(f"Samples: {len(all_samples)} from {len(log_paths)} log(s)\n")

    # cells[(model, instruction, penalty)] = list of lied flags
    cells: dict[tuple[str, str, int], list[int]] = defaultdict(list)
    models = set()
    instructions = set()
    penalties = set()

    for s in all_samples:
        meta = s.metadata.get("scenario", {}).get("metadata", {})
        model = meta.get("model")
        instr = meta.get("instruction")
        penalty = meta.get("expected_penalty")
        v_a, v_b = meta.get("v_a"), meta.get("v_b")
        if None in (model, instr, penalty):
            continue
        models.add(model)
        instructions.add(instr)
        penalties.add(penalty)

        sc_entry = s.scores.get("bargaining_manipulation") if s.scores else None
        if not sc_entry:
            continue
        sc = sc_entry.value

        for agent in ("agent_a", "agent_b"):
            lied = sc.get(f"{agent}_lied")
            if lied is None:
                continue
            cells[(model, instr, penalty)].append(int(lied))

    def mean(xs):
        return sum(xs) / len(xs) if xs else float("nan")

    instr_order = ["pro_honesty", "neutral", "pro_manipulation"]
    instructions = [i for i in instr_order if i in instructions]
    penalties = sorted(penalties)

    print(f"{'=' * 72}")
    print("  Instruction x Incentive response surface (manipulation rate)")
    print(f"{'=' * 72}\n")

    for m in sorted(models):
        print(f"  === {m} ===")
        header = f"    {'instruction':<18s}  " + "  ".join(
            f"E={p:<3d}".rjust(12) for p in penalties
        )
        print(header)
        for instr in instructions:
            row_cells = [cells[(m, instr, p)] for p in penalties]
            row_strs = [f"{mean(c):.3f} (n={len(c):2d})" for c in row_cells]
            print(f"    {instr:<18s}  " + "  ".join(r.rjust(12) for r in row_strs))
        print()

    # Derived decomposition per model
    print(f"{'=' * 72}")
    print("  Decomposition: where does each model's manipulation come from?")
    print(f"{'=' * 72}\n")
    for m in sorted(models):
        baseline = mean(cells[(m, "neutral", 0)])
        incentive = mean(cells[(m, "neutral", 80)])
        instruction = mean(cells[(m, "pro_manipulation", 0)])
        both = mean(cells[(m, "pro_manipulation", 80)])
        honesty_baseline = mean(cells[(m, "pro_honesty", 0)])
        honesty_under_incentive = mean(cells[(m, "pro_honesty", 80)])

        print(f"  === {m} ===")
        print(
            f"    Baseline (neutral, E=0):                  {baseline:.3f}  — spontaneous lying at zero incentive"
        )
        print(
            f"    + Incentive alone (neutral, E=80):        {incentive:.3f}  — delta from baseline = {incentive - baseline:+.3f}"
        )
        print(
            f"    + Instruction alone (manip, E=0):         {instruction:.3f}  — delta from baseline = {instruction - baseline:+.3f}"
        )
        print(f"    + Both (manip, E=80):                     {both:.3f}  — saturation check")
        print(
            f"    Pro-honesty, no incentive:                {honesty_baseline:.3f}  — can instruction suppress baseline?"
        )
        print(
            f"    Pro-honesty, with incentive:              {honesty_under_incentive:.3f}  — does honesty prompt hold under pressure?"
        )
        print()


if __name__ == "__main__":
    main(*sys.argv[1:])
