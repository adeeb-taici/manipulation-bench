"""mb — single-command runner for manipulation-bench.

Wraps the common Inspect AI flow (generate → eval → analyze) so new
researchers can launch a run with one intuitive command instead of
binding every model_role manually.

Subcommands:
    mb run <env> [<env2> ...] --model <id>           # all roles → <id>
    mb run <env> --models name=<id>,name=<id> [...]  # explicit per-role
    mb run <env> --scenarios <file.jsonl>            # custom scenario
    mb analyze <log_pattern>                         # auto-detect + report
    mb envs                                          # list registered envs

Power users can keep using ``inspect eval src/manipulation_bench/<task>.py``
directly; the CLI is a convenience layer, not a replacement.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Environment registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvSpec:
    name: str
    task_module: str  # e.g., "src/manipulation_bench/task.py"
    task_function: str  # e.g., "manipulation_bench" — the @task name
    default_scenario: str  # filename under src/manipulation_bench/scenarios/
    description: str


ENVS: dict[str, EnvSpec] = {
    "debate": EnvSpec(
        name="debate",
        task_module="src/manipulation_bench/task.py",
        task_function="manipulation_bench",
        default_scenario="debate_2agent.jsonl",
        description="2-N agent debates with persuasion / argument-quality / belief-shift scoring.",
    ),
    "werewolf": EnvSpec(
        name="werewolf",
        task_module="src/manipulation_bench/game_task.py",
        task_function="werewolf_bench",
        default_scenario="werewolf_5player.jsonl",
        description="5-8 player social deduction; deception success and vote accuracy.",
    ),
    "diplomacy": EnvSpec(
        name="diplomacy",
        task_module="src/manipulation_bench/diplomacy_task.py",
        task_function="diplomacy_bench",
        default_scenario="diplomacy_7player.jsonl",
        description="7-power negotiation with promise-tracking; agreement-compliance scoring.",
    ),
    "village": EnvSpec(
        name="village",
        task_module="src/manipulation_bench/village_task.py",
        task_function="village_bench",
        default_scenario="village_6player.jsonl",
        description="6-agent public-goods game; exploitation rate, promise-action gap, fairness.",
    ),
    "sales": EnvSpec(
        name="sales",
        task_module="src/manipulation_bench/sales_task.py",
        task_function="sales_bench",
        default_scenario="sales_pilot.jsonl",
        description="Single-agent sales; rule-based accurate / misleading / false classification.",
    ),
    "committee": EnvSpec(
        name="committee",
        task_module="src/manipulation_bench/committee_task.py",
        task_function="committee_bench",
        default_scenario="committee_pilot.jsonl",
        description="5-agent committee with conflict-of-interest; rating-bias and decision outcome.",
    ),
    "bargaining": EnvSpec(
        name="bargaining",
        task_module="src/manipulation_bench/bargaining_task.py",
        task_function="bargaining_commit_bench",
        default_scenario="bargaining_surface_pilot.jsonl",
        description="2-agent bargaining; lying detected via threshold against true valuation.",
    ),
    "naming": EnvSpec(
        name="naming",
        task_module="src/manipulation_bench/consensus_tasks.py",
        task_function="naming_game_bench",
        default_scenario="naming_game.jsonl",
        description="N-agent vocabulary convergence; broadcast/ring/star/dense/commons topologies.",
    ),
}


SCENARIOS_DIR = Path(__file__).parent / "scenarios"


# ---------------------------------------------------------------------------
# Role discovery from scenario JSONL
# ---------------------------------------------------------------------------


def discover_roles(scenario_filename: str) -> list[str]:
    """Return the unique sorted list of model_role values across the scenario.

    Scenarios store role bindings in two places:
    - ``agents[*].model_role`` (debate / werewolf / village / committee / etc.)
    - top-level ``model_role`` (sales — single-agent)
    """
    path = scenario_filename
    if not Path(path).exists():
        path = str(SCENARIOS_DIR / scenario_filename)
        if not Path(path).exists():
            return []
    roles: set[str] = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec.get("model_role"), str):
                roles.add(rec["model_role"])
            for agent in rec.get("agents", []) or []:
                if isinstance(agent.get("model_role"), str):
                    roles.add(agent["model_role"])
    return sorted(roles)


# ---------------------------------------------------------------------------
# `mb run` — build inspect eval command and exec
# ---------------------------------------------------------------------------


def parse_models_arg(value: str) -> dict[str, str]:
    """Parse ``name=id,name=id`` into {name: id} (commas or whitespace allowed)."""
    out: dict[str, str] = {}
    for chunk in value.replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise argparse.ArgumentTypeError(
                f"--models entry {chunk!r} missing '=': expected name=provider/model"
            )
        name, model_id = chunk.split("=", 1)
        out[name.strip()] = model_id.strip()
    return out


def build_eval_cmd(
    env: EnvSpec,
    *,
    model: str | None,
    models: dict[str, str],
    scenarios: str | None,
    judge: str | None,
    extra: list[str],
) -> list[str]:
    """Assemble the underlying ``inspect eval`` invocation."""
    scenario_file = scenarios or env.default_scenario
    cmd: list[str] = ["inspect", "eval", env.task_module, "-T", f"scenarios={scenario_file}"]

    # Roles in this scenario
    roles = discover_roles(scenario_file)
    # If the scenario references no roles (e.g., older or empty), skip auto-binding
    bindings: dict[str, str] = {}

    # 1) Explicit per-role models always win.
    for role, mid in models.items():
        bindings[role] = mid

    # 2) Default any remaining roles to --model.
    if model:
        for role in roles:
            bindings.setdefault(role, model)
        # Also default judge if not explicitly bound.
        bindings.setdefault("judge", judge or model)

    # 3) Honor an explicit --judge override.
    if judge:
        bindings["judge"] = judge

    if model:
        cmd.extend(["--model", model])
    elif bindings:
        # Inspect requires --model even when only role bindings are set.
        # Pick any bound model as the primary model.
        cmd.extend(["--model", next(iter(bindings.values()))])

    for role, mid in sorted(bindings.items()):
        cmd.extend(["--model-role", f"{role}={mid}"])

    cmd.extend(extra)
    return cmd


def cmd_run(args: argparse.Namespace) -> int:
    if not args.envs:
        print("error: at least one <env> argument is required", file=sys.stderr)
        return 2
    unknown = [e for e in args.envs if e not in ENVS]
    if unknown:
        print(f"error: unknown env(s) {unknown}; try `mb envs`", file=sys.stderr)
        return 2
    if not args.model and not args.models:
        print(
            "error: pass --model <id> for single-model runs, "
            "or --models name=<id>,name=<id> for multi-model.",
            file=sys.stderr,
        )
        return 2

    models = parse_models_arg(args.models) if args.models else {}
    extra = args.extra or []
    if "--limit" not in extra and args.limit is not None:
        extra.extend(["--limit", str(args.limit)])
    if args.no_fail_on_error:
        extra.append("--no-fail-on-error")
    if args.max_connections is not None:
        extra.extend(["--max-connections", str(args.max_connections)])

    rc = 0
    for env_name in args.envs:
        env = ENVS[env_name]
        cmd = build_eval_cmd(
            env,
            model=args.model,
            models=models,
            scenarios=args.scenarios,
            judge=args.judge,
            extra=extra,
        )
        if args.dry_run:
            print(" ".join(shlex.quote(c) for c in cmd))
            continue
        # Flush so the banner prints BEFORE inspect eval output (Python's
        # stdout is block-buffered when piped; subprocess.run writes directly).
        print(
            f"\n=== {env_name} ===\n$ {' '.join(shlex.quote(c) for c in cmd)}\n",
            flush=True,
        )
        result = subprocess.run(cmd)
        if result.returncode != 0:
            rc = result.returncode
            if not args.continue_on_error:
                return rc
    return rc


# ---------------------------------------------------------------------------
# `mb analyze` — defer to manipulation_bench.analyze
# ---------------------------------------------------------------------------


def cmd_analyze(args: argparse.Namespace) -> int:
    cmd = [sys.executable, "-m", "manipulation_bench.analyze", args.log]
    if args.dry_run:
        print(" ".join(shlex.quote(c) for c in cmd))
        return 0
    return subprocess.run(cmd).returncode


# ---------------------------------------------------------------------------
# `mb envs`
# ---------------------------------------------------------------------------


def cmd_envs(args: argparse.Namespace) -> int:
    width = max(len(name) for name in ENVS)
    for name, spec in ENVS.items():
        print(f"  {name:<{width}}  {spec.description}")
    return 0


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mb",
        description=(
            "manipulation-bench launcher. Wraps inspect eval so single-model and "
            "multi-model runs can be triggered with one command."
        ),
        epilog=(
            "Examples:\n"
            "  mb run debate --model openrouter/anthropic/claude-opus-4.7\n"
            "  mb run debate village --model openrouter/openai/gpt-5\n"
            "  mb run debate --models debater=openrouter/anthropic/claude-opus-4.7,judge=openrouter/openai/gpt-5\n"
            "  mb analyze 'logs/2026*.eval'\n"
            "  mb envs"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # run
    p_run = sub.add_parser("run", help="Run one or more environments.")
    p_run.add_argument("envs", nargs="+", help="One or more env names from `mb envs`.")
    p_run.add_argument(
        "--model",
        help="Provider/model id; binds to ALL roles in the scenario unless --models overrides.",
    )
    p_run.add_argument(
        "--models",
        help="Per-role bindings, e.g. 'debater=openrouter/...,judge=openrouter/...'",
    )
    p_run.add_argument(
        "--judge", help="Override the judge role specifically (defaults to --model)."
    )
    p_run.add_argument(
        "--scenarios", help="Override the env's default scenario JSONL filename or path."
    )
    p_run.add_argument(
        "--limit",
        type=int,
        help="Limit the number of samples (useful for smoke tests).",
    )
    p_run.add_argument(
        "--max-connections",
        type=int,
        help="Per-provider concurrency cap (passed through to inspect).",
    )
    p_run.add_argument(
        "--no-fail-on-error",
        action="store_true",
        help="Continue running on per-sample errors (passed through to inspect).",
    )
    p_run.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Keep running remaining envs if one env's eval exits non-zero.",
    )
    p_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the inspect eval command(s) without executing.",
    )
    # NOTE: extra inspect-eval args are captured via parse_known_args (see main()),
    # so anything mb does not recognize is forwarded verbatim. Use ``--`` to separate
    # if the passthrough flag collides with mb's own flags.
    p_run.set_defaults(func=cmd_run)

    # analyze
    p_analyze = sub.add_parser("analyze", help="Analyze an eval log (auto-detects environment).")
    p_analyze.add_argument("log", help="Path or glob pattern for .eval log(s).")
    p_analyze.add_argument(
        "--dry-run", action="store_true", help="Print the analyze command without executing."
    )
    p_analyze.set_defaults(func=cmd_analyze)

    # envs
    p_envs = sub.add_parser("envs", help="List registered environments.")
    p_envs.set_defaults(func=cmd_envs)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    # Use parse_known_args so unrecognized flags pass through to `inspect eval`.
    args, extra = parser.parse_known_args(argv)
    args.extra = extra
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
