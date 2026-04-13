"""Analyze manipulation rotation experiment results from an Inspect eval log.

Usage:
    python -m manipulation_bench.analyze logs/2026-04-13*.eval
"""
from __future__ import annotations

import argparse
import glob
import sys
from typing import Any

from inspect_ai.log import EvalLog, EvalLogInfo, read_eval_log


def find_manipulator(sample: Any) -> str | None:
    """Return the name of the designated manipulator in a sample, or None."""
    scenario = sample.store.get("InteractionState:scenario")
    if not scenario:
        return None
    for agent in scenario.get("agents", []):
        if agent.get("metadata", {}).get("manipulative"):
            return agent["name"]
    return None


def analyze_rotation(log: EvalLog) -> dict[str, Any]:
    """Extract structured results from a manipulation rotation eval log."""
    samples = log.samples or []
    agent_names: list[str] = []
    scorers = ["manipulation_detection", "argument_quality", "belief_shift"]

    # Collect per-sample data
    rows: list[dict[str, Any]] = []
    for sample in samples:
        scenario = sample.store.get("InteractionState:scenario", {})
        agents = [a["name"] for a in scenario.get("agents", [])]
        if not agent_names:
            agent_names = agents

        manipulator = find_manipulator(sample)
        row: dict[str, Any] = {
            "id": sample.id,
            "manipulator": manipulator,
        }
        for scorer_name in scorers:
            if scorer_name in sample.scores:
                row[scorer_name] = sample.scores[scorer_name].value
        rows.append(row)

    return {"agent_names": agent_names, "rows": rows, "scorers": scorers}


def print_tables(results: dict[str, Any]) -> None:
    """Print formatted comparison tables."""
    agent_names = results["agent_names"]
    rows = results["rows"]
    col_w = max(len(n) for n in agent_names) + 2

    for scorer_name in results["scorers"]:
        label = scorer_name.upper().replace("_", " ")
        print(f"\n{'=' * 72}")
        print(f"  {label}")
        print(f"{'=' * 72}")

        header = f"{'Scenario':<22}"
        for name in agent_names:
            header += f"{name:>{col_w}}"
        print(header)
        print("-" * 72)

        for row in rows:
            scores = row.get(scorer_name, {})
            line = f"{row['id']:<22}"
            for name in agent_names:
                val = scores.get(name)
                marker = " *" if name == row["manipulator"] else "  "
                if val is not None:
                    line += f"{val:>{col_w - 2}.2f}{marker}"
                else:
                    line += f"{'n/a':>{col_w}}"
            print(line)

    # Summary: manipulation score when instructed vs clean
    manip_rows = [r for r in rows if r["manipulator"] is not None]
    if not manip_rows or "manipulation_detection" not in manip_rows[0]:
        return

    print(f"\n{'=' * 72}")
    print(f"  SUMMARY: Manipulation score when INSTRUCTED vs CLEAN")
    print(f"{'=' * 72}")
    print(f"{'Model':<18} {'Instructed':>12} {'Clean':>12} {'Delta':>8}")
    print("-" * 52)

    for name in agent_names:
        instructed = []
        clean = []
        for row in manip_rows:
            scores = row.get("manipulation_detection", {})
            val = scores.get(name)
            if val is None:
                continue
            if name == row["manipulator"]:
                instructed.append(val)
            else:
                clean.append(val)
        inst_avg = sum(instructed) / len(instructed) if instructed else 0
        clean_avg = sum(clean) / len(clean) if clean else 0
        delta = inst_avg - clean_avg
        print(f"{name:<18} {inst_avg:>12.2f} {clean_avg:>12.2f} {delta:>+8.2f}")


def print_susceptibility(results: dict[str, Any]) -> None:
    """Compare each agent's behavior in baseline vs under manipulation pressure.

    Susceptibility is measured per non-manipulative agent across three dimensions:
    - Belief shift: did they concede more when a manipulator was present?
    - Quality drop: did their argument quality degrade under pressure?
    - Contagion: did they start using more manipulation tactics in response?
    """
    agent_names = results["agent_names"]
    rows = results["rows"]

    baseline = next((r for r in rows if r["manipulator"] is None), None)
    manip_rows = [r for r in rows if r["manipulator"] is not None]

    if not baseline or not manip_rows:
        return

    scorers_needed = {"manipulation_detection", "argument_quality", "belief_shift"}
    if not scorers_needed.issubset(baseline.keys()):
        return

    print(f"\n{'=' * 72}")
    print(f"  SUSCEPTIBILITY (baseline vs under manipulation pressure)")
    print(f"{'=' * 72}")
    print(
        f"{'Model':<18} {'Contagion':>12} {'Quality Drop':>14} {'Belief Shift':>14}"
    )
    print(f"{'':18} {'(manip delta)':>12} {'(qual delta)':>14} {'(shift delta)':>14}")
    print("-" * 60)

    for name in agent_names:
        # Collect scores for this agent when it was NOT the manipulator
        baseline_manip = baseline.get("manipulation_detection", {}).get(name, 0)
        baseline_qual = baseline.get("argument_quality", {}).get(name, 0)
        baseline_shift = baseline.get("belief_shift", {}).get(name, 0)

        pressure_manip = []
        pressure_qual = []
        pressure_shift = []
        for row in manip_rows:
            if row["manipulator"] == name:
                continue  # skip when this agent is the manipulator
            pressure_manip.append(row.get("manipulation_detection", {}).get(name, 0))
            pressure_qual.append(row.get("argument_quality", {}).get(name, 0))
            pressure_shift.append(row.get("belief_shift", {}).get(name, 0))

        if not pressure_manip:
            continue

        avg = lambda vals: sum(vals) / len(vals)
        contagion = avg(pressure_manip) - baseline_manip
        qual_drop = avg(pressure_qual) - baseline_qual
        shift_delta = avg(pressure_shift) - baseline_shift

        print(f"{name:<18} {contagion:>+12.2f} {qual_drop:>+14.2f} {shift_delta:>+14.2f}")

    print()
    print("  Contagion:    + means agent used MORE manipulation when a manipulator was present")
    print("  Quality Drop: - means agent's argument quality DECREASED under pressure")
    print("  Belief Shift: + means agent shifted position MORE under pressure")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze manipulation rotation results")
    parser.add_argument("log", help="Path to .eval log file (supports glob)")
    args = parser.parse_args()

    # Support glob patterns
    paths = glob.glob(args.log)
    if not paths:
        print(f"No log files found matching: {args.log}", file=sys.stderr)
        sys.exit(1)

    # Use the most recent log if multiple match
    log_path = sorted(paths)[-1]
    print(f"Analyzing: {log_path}")

    log = read_eval_log(log_path)
    results = analyze_rotation(log)
    print_tables(results)
    print_susceptibility(results)


if __name__ == "__main__":
    main()
