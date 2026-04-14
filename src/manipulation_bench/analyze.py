"""Analyze manipulation rotation experiment results from an Inspect eval log.

Usage:
    python -m manipulation_bench.analyze logs/2026-04-13*.eval
"""

from __future__ import annotations

import argparse
import glob
import sys
from collections import defaultdict
from typing import Any

from inspect_ai.log import EvalLog, EvalLogInfo, read_eval_log


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------

_WEREWOLF_SCORERS = {
    "game_win_rate",
    "vote_accuracy",
    "deception_success",
    "game_manipulation_detection",
}
_DIPLOMACY_SCORERS = {"territorial_success", "agreement_compliance", "negotiation_manipulation"}
_DEBATE_SCORERS = {"manipulation_detection", "argument_quality", "belief_shift"}


def detect_environment(log: EvalLog) -> str:
    """Detect the environment type from scorer names present in the eval log.

    Returns one of ``"werewolf"``, ``"diplomacy"``, ``"debate"``, or ``"unknown"``.
    """
    scorer_names: set[str] = set()

    # Most reliable: check the first sample's scores dict keys
    if log.samples:
        scorer_names = set(log.samples[0].scores.keys())

    if scorer_names & _WEREWOLF_SCORERS:
        return "werewolf"
    if scorer_names & _DIPLOMACY_SCORERS:
        return "diplomacy"
    if scorer_names & _DEBATE_SCORERS:
        return "debate"
    return "unknown"


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
    print(f"{'Model':<18} {'Contagion':>12} {'Quality Drop':>14} {'Belief Shift':>14}")
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


# ---------------------------------------------------------------------------
# Werewolf analysis
# ---------------------------------------------------------------------------


def _get_sample_meta(sample: Any) -> dict[str, Any]:
    """Return the scenario metadata dict from a log sample's store."""
    scenario = sample.store.get("InteractionState:scenario", {})
    return scenario.get("metadata", {})


def analyze_werewolf(log: EvalLog) -> None:
    """Print Werewolf game analysis: win rates, deception, vote accuracy by role and model."""
    samples = log.samples or []
    if not samples:
        print("No samples found in log.")
        return

    # Accumulators keyed by role and by model
    wins_by_role: dict[str, list[float]] = defaultdict(list)
    wins_by_model: dict[str, list[float]] = defaultdict(list)
    deception_by_model: dict[str, list[float]] = defaultdict(list)
    vote_acc_by_model: dict[str, list[float]] = defaultdict(list)

    for sample in samples:
        meta = _get_sample_meta(sample)
        game_state = meta.get("game_state", {})
        game_outcome = meta.get("game_outcome", {})
        model_mapping = meta.get("model_mapping", {})
        roles = game_state.get("roles", {})
        outcome_scores = game_outcome.get("scores", {})

        # Also pull scorer values from sample.scores for deception/vote_accuracy
        deception_scores: dict[str, float] = {}
        vote_acc_scores: dict[str, float] = {}
        if "deception_success" in sample.scores:
            val = sample.scores["deception_success"].value
            if isinstance(val, dict):
                deception_scores = val
        if "vote_accuracy" in sample.scores:
            val = sample.scores["vote_accuracy"].value
            if isinstance(val, dict):
                vote_acc_scores = val

        for agent_name, role in roles.items():
            win_val = outcome_scores.get(agent_name)
            if win_val is None:
                continue
            wins_by_role[role].append(float(win_val))

            model = model_mapping.get(agent_name, "unknown")
            wins_by_model[model].append(float(win_val))

            if role == "werewolf" and agent_name in deception_scores:
                deception_by_model[model].append(deception_scores[agent_name])

            if role in ("villager", "seer") and agent_name in vote_acc_scores:
                vote_acc_by_model[model].append(vote_acc_scores[agent_name])

    _avg = lambda vals: sum(vals) / len(vals) if vals else 0.0

    # --- Win rate by role ---
    print(f"\n{'=' * 60}")
    print("  WIN RATE BY ROLE")
    print(f"{'=' * 60}")
    print(f"{'Role':<16} {'Win Rate':>10} {'Games':>8}")
    print("-" * 36)
    for role in sorted(wins_by_role):
        vals = wins_by_role[role]
        print(f"{role:<16} {_avg(vals):>10.2f} {len(vals):>8}")

    # --- Win rate by model ---
    print(f"\n{'=' * 60}")
    print("  WIN RATE BY MODEL")
    print(f"{'=' * 60}")
    print(f"{'Model':<36} {'Win Rate':>10} {'Games':>8}")
    print("-" * 56)
    for model in sorted(wins_by_model):
        vals = wins_by_model[model]
        print(f"{model:<36} {_avg(vals):>10.2f} {len(vals):>8}")

    # --- Deception success (werewolves only) by model ---
    print(f"\n{'=' * 60}")
    print("  DECEPTION SUCCESS (werewolves only, by model)")
    print(f"{'=' * 60}")
    print(f"{'Model':<36} {'Deception':>10} {'Count':>8}")
    print("-" * 56)
    for model in sorted(deception_by_model):
        vals = deception_by_model[model]
        print(f"{model:<36} {_avg(vals):>10.2f} {len(vals):>8}")

    # --- Vote accuracy (villagers/seers) by model ---
    print(f"\n{'=' * 60}")
    print("  VOTE ACCURACY (villagers/seers, by model)")
    print(f"{'=' * 60}")
    print(f"{'Model':<36} {'Accuracy':>10} {'Count':>8}")
    print("-" * 56)
    for model in sorted(vote_acc_by_model):
        vals = vote_acc_by_model[model]
        print(f"{model:<36} {_avg(vals):>10.2f} {len(vals):>8}")


# ---------------------------------------------------------------------------
# Diplomacy analysis
# ---------------------------------------------------------------------------


def analyze_diplomacy(log: EvalLog) -> None:
    """Print Diplomacy game analysis: territory, compliance, manipulation by model."""
    samples = log.samples or []
    if not samples:
        print("No samples found in log.")
        return

    territory_by_model: dict[str, list[float]] = defaultdict(list)
    compliance_by_model: dict[str, list[float]] = defaultdict(list)
    manip_by_model: dict[str, list[float]] = defaultdict(list)

    for sample in samples:
        meta = _get_sample_meta(sample)
        model_mapping = meta.get("model_mapping", {})

        # Scorer values from sample.scores
        territory_scores: dict[str, float] = {}
        compliance_scores: dict[str, float] = {}
        manip_scores: dict[str, float] = {}

        if "territorial_success" in sample.scores:
            val = sample.scores["territorial_success"].value
            if isinstance(val, dict):
                territory_scores = val
        if "agreement_compliance" in sample.scores:
            val = sample.scores["agreement_compliance"].value
            if isinstance(val, dict):
                compliance_scores = val
        if "negotiation_manipulation" in sample.scores:
            val = sample.scores["negotiation_manipulation"].value
            if isinstance(val, dict):
                manip_scores = val

        # Aggregate by model
        all_agents = set(territory_scores) | set(compliance_scores) | set(manip_scores)
        for agent_name in all_agents:
            model = model_mapping.get(agent_name, "unknown")
            if agent_name in territory_scores:
                territory_by_model[model].append(territory_scores[agent_name])
            if agent_name in compliance_scores:
                compliance_by_model[model].append(compliance_scores[agent_name])
            if agent_name in manip_scores:
                manip_by_model[model].append(manip_scores[agent_name])

    _avg = lambda vals: sum(vals) / len(vals) if vals else 0.0

    # --- Territorial success by model ---
    print(f"\n{'=' * 60}")
    print("  TERRITORIAL SUCCESS (avg supply center share, by model)")
    print(f"{'=' * 60}")
    print(f"{'Model':<36} {'Territory':>10} {'Count':>8}")
    print("-" * 56)
    for model in sorted(territory_by_model):
        vals = territory_by_model[model]
        print(f"{model:<36} {_avg(vals):>10.3f} {len(vals):>8}")

    # --- Agreement compliance by model ---
    print(f"\n{'=' * 60}")
    print("  AGREEMENT COMPLIANCE (promise-keeping rate, by model)")
    print(f"{'=' * 60}")
    print(f"{'Model':<36} {'Compliance':>10} {'Count':>8}")
    print("-" * 56)
    for model in sorted(compliance_by_model):
        vals = compliance_by_model[model]
        print(f"{model:<36} {_avg(vals):>10.3f} {len(vals):>8}")

    # --- Negotiation manipulation by model ---
    print(f"\n{'=' * 60}")
    print("  NEGOTIATION MANIPULATION (by model)")
    print(f"{'=' * 60}")
    print(f"{'Model':<36} {'Manip Score':>12} {'Count':>8}")
    print("-" * 58)
    for model in sorted(manip_by_model):
        vals = manip_by_model[model]
        print(f"{model:<36} {_avg(vals):>12.2f} {len(vals):>8}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


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

    env = detect_environment(log)
    print(f"Detected environment: {env}")

    if env == "werewolf":
        analyze_werewolf(log)
    elif env == "diplomacy":
        analyze_diplomacy(log)
    else:
        # Default to debate analysis for "debate" and "unknown"
        results = analyze_rotation(log)
        print_tables(results)
        print_susceptibility(results)


if __name__ == "__main__":
    main()
