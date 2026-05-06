"""Diff-check: paraphrase_version=1 produces byte-identical system prompts to
the production T3 + T4 generators.

This guarantees the paraphrase axis is purely additive — pre-addendum
behavior is preserved when paraphrase_version=1.

For T3: build a v1 scenario via the paraphrase generator at the held-fixed
cell, build the equivalent scenario via the production generator, compare
each agent's system_prompt byte-for-byte.

For T4: same, but at the held-fixed (incentive, difficulty) cell.

Exits non-zero on any mismatch.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "paper" / "task3_village" / "scripts"))
sys.path.insert(0, str(ROOT / "paper" / "task4_sales" / "scripts"))
sys.path.insert(0, str(ROOT / "paper" / "paraphrase_robustness" / "scripts"))


def diff_t3() -> list[str]:
    from generate_task3_village_full import (  # type: ignore[import-not-found]
        build_agent_prompt as production_build,
    )
    from generate_paraphrase_sweep import (  # type: ignore[import-not-found]
        T3_INCENTIVE,
        T3_DIFFICULTY,
        FRAMES,
        t3_build_agent_prompt,
    )
    from manipulation_bench.axes import VILLAGE_DIFFICULTY_MULTIPLIERS

    multiplier = VILLAGE_DIFFICULTY_MULTIPLIERS[T3_DIFFICULTY]
    issues: list[str] = []
    # Manipulator prompts
    for frame in FRAMES:
        prod = production_build("agent_1", frame, T3_INCENTIVE, multiplier)
        addendum = t3_build_agent_prompt(
            "agent_1", frame, T3_INCENTIVE, multiplier, paraphrase_version=1
        )
        if prod != addendum:
            issues.append(
                f"T3 manipulator/{frame}: lengths {len(prod)} vs {len(addendum)}"
            )
    # Bystander prompt (always minimal/none)
    for name in ("agent_2", "agent_3", "agent_4", "agent_5", "agent_6"):
        prod = production_build(name, "minimal", "none", multiplier)
        addendum = t3_build_agent_prompt(
            name, "minimal", "none", multiplier, paraphrase_version=1
        )
        if prod != addendum:
            issues.append(f"T3 bystander/{name}: mismatch")
    return issues


def diff_t4() -> list[str]:
    from generate_task4_sales import (  # type: ignore[import-not-found]
        SCENARIOS,
        build_system_prompt as production_build,
    )
    from generate_paraphrase_sweep import (  # type: ignore[import-not-found]
        T4_INCENTIVE,
        T4_DIFFICULTY,
        FRAMES,
        t4_build_system_prompt,
    )

    medium_scenarios = [s for s in SCENARIOS if s["difficulty"] == T4_DIFFICULTY]
    issues: list[str] = []
    for scen in medium_scenarios:
        for frame in FRAMES:
            prod = production_build(scen, frame, T4_INCENTIVE)
            addendum = t4_build_system_prompt(scen, frame, paraphrase_version=1)
            if prod != addendum:
                # Find first divergence
                first_diff = next(
                    (i for i, (a, b) in enumerate(zip(prod, addendum)) if a != b),
                    min(len(prod), len(addendum)),
                )
                issues.append(
                    f"T4 {scen['scenario_id']}/{frame}: mismatch at char {first_diff} "
                    f"(lengths {len(prod)} vs {len(addendum)})"
                )
    return issues


def main() -> None:
    print("Diff-checking paraphrase_version=1 against production generators...")
    print()
    t3_issues = diff_t3()
    print(f"T3 Village: {len(t3_issues)} mismatches")
    for issue in t3_issues:
        print(f"  - {issue}")
    print()
    t4_issues = diff_t4()
    print(f"T4 Sales: {len(t4_issues)} mismatches")
    for issue in t4_issues:
        print(f"  - {issue}")
    print()
    total = len(t3_issues) + len(t4_issues)
    if total:
        print(f"FAIL: {total} mismatches. Paraphrase generator's v1 path is NOT byte-identical to production.")
        sys.exit(1)
    print("PASS: paraphrase_version=1 is byte-identical to production T3 + T4 generators.")


if __name__ == "__main__":
    main()
