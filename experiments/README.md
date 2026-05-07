# experiments/

Generic, study-agnostic harness — scenario generators and a cross-env analyzer that work with any model roster. Study-specific generators and analyses (with PREREG-locked configs) live next to their artifacts under [`../paper/task<N>/scripts/`](../paper/) and [`../paper/cross_task/scripts/`](../paper/cross_task/scripts/).

Each script here is a standalone CLI — `python experiments/<name>.py --help`.

## Response-surface generators

The three cross-env generators that produce typed scenarios (frame × incentive × difficulty axes from [`../src/manipulation_bench/axes.py`](../src/manipulation_bench/axes.py)). Each takes `--pilot` and writes a JSONL under [`../src/manipulation_bench/scenarios/`](../src/manipulation_bench/scenarios/).

| Generator | Environment | Output |
|---|---|---|
| [`generate_bargaining_surface.py`](generate_bargaining_surface.py) | Bargaining | `bargaining_surface_pilot.jsonl` |
| [`generate_debate_surface.py`](generate_debate_surface.py) | Debate | `debate_surface_pilot.jsonl` |
| [`generate_village_surface.py`](generate_village_surface.py) | Village Commons | `village_surface_pilot.jsonl` |

Sales and Committee generators carry PREREG-locked study configs and live under [`../paper/task4_sales/scripts/`](../paper/task4_sales/scripts/) / [`../paper/task5_committee/scripts/`](../paper/task5_committee/scripts/).

## Single-env demos (one each)

| Script | Environment |
|---|---|
| [`generate_diplomacy.py`](generate_diplomacy.py) | Diplomacy negotiation (7 powers) |
| [`generate_werewolf_8player.py`](generate_werewolf_8player.py) | Werewolf social deduction |

## Cross-env analyzer

`python -m manipulation_bench.analyze_surface <log>` (defined in `src/`) auto-detects the env and pivots into a frame × incentive / frame × difficulty grid per model. The heavier statistical pipeline (sensitivity slopes + bootstrap CIs + 15-dim profile vectors + cross-task correlations) lives at [`../paper/cross_task/scripts/analyze_response_surface.py`](../paper/cross_task/scripts/analyze_response_surface.py).

## Adding a new environment

Each step below lists the exact file(s) to touch. The pattern is parallel to how Committee was added on top of the existing Debate/Village scaffolding.

1. **Environment class** — implement the `Environment` ABC in a new `../src/manipulation_bench/environments/<name>.py`. Contract: `base.py`. Reference implementations: `village.py` (tool-call actions, deterministic state) and `committee.py` (multi-phase private → discussion → final). Register in `environments/__init__.py`.
2. **Task wrapper** — new `../src/manipulation_bench/<name>_task.py` that calls `game_solver.game_interaction()` with the scorer list. Single-agent tasks (no counterparty LLM) can write their own solver — see `sales_task.py`. Add the task name to `_registry.py` for Inspect discovery.
3. **Scorers** — new `../src/manipulation_bench/scorers/<name>.py`. **Every env must include a `manipulation_occurred` boolean scorer** so cross-env slopes in `analyze_response_surface.py` line up. Re-export the new scorers from `scorers/__init__.py`.
4. **Axis prompts** — add `FRAME_PROMPTS["<name>"]` (5 levels) and `INCENTIVE_PROMPTS["<name>"]` (3 levels) entries to `../src/manipulation_bench/axes.py`. For envs where interested/neutral roles get different framing, follow the nested `{"interested": ..., "neutral": ...}` shape from `committee`.
5. **Surface generator** — new `generate_<name>_surface.py` here in `experiments/`, producing a JSONL under `../src/manipulation_bench/scenarios/`. Set `ScenarioMetadata.frame / incentive / difficulty / manipulator` as typed fields (not just extra metadata).
6. **Analyzer dispatch** — teach `analyze_surface.py` about the new env: extend `detect_environment()` and add a `_<env>_metric()` function to `_METRIC_EXTRACTORS`. The `analyze.py` and `analyze_response_surface.py` analyzers reuse this detection.
