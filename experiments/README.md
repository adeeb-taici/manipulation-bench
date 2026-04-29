# experiments/

Scenario generators, YAML configs, and one-off analysis scripts. Each Python file here is a standalone CLI — run `python experiments/<name>.py --help` (or read the module docstring) for invocation.

## Canonical paper generators

The five response-surface generators, one per paper environment. These factor over frame × incentive × difficulty (see [`../src/manipulation_bench/axes.py`](../src/manipulation_bench/axes.py)) and write scenarios with typed `metadata.frame / incentive / difficulty / manipulator` fields that [`analyze_response_surface.py`](analyze_response_surface.py) consumes.

| Generator | Environment | Pilot flag | Output |
|---|---|---|---|
| `generate_task4_sales.py` | Sales (Task 4) | `--pilot` | `scenarios/sales_pilot.jsonl` (full run writes `task4_sales.jsonl`) |
| `generate_task5_committee.py` | Committee (Task 5) | `--pilot` / `--sweep` | `scenarios/committee_pilot.jsonl` / `scenarios/task5_committee_sweep.jsonl` |
| `generate_village_surface.py` | Village Commons | `--pilot` | `scenarios/village_surface_pilot.jsonl` |
| `generate_debate_surface.py` | Debate | `--pilot` | `scenarios/debate_surface_pilot.jsonl` |
| `generate_bargaining_surface.py` | Bargaining | `--pilot` | `scenarios/bargaining_surface_pilot.jsonl` |

Supporting: [`task5_slates.py`](task5_slates.py) (Task 5 candidate slates), [`task4_hand_validation.py`](task4_hand_validation.py), [`task5_hand_validation.py`](task5_hand_validation.py) (scorer-agreement harnesses).

## Cross-environment analyzers

| Script | Purpose |
|---|---|
| [`analyze_response_surface.py`](analyze_response_surface.py) | Paper statistical pipeline: per-(model, task, axis) sensitivity slopes with bootstrap CIs, 15-dim profile vectors, cross-task correlation matrices, endpoint calibration, prediction checks. Reads eval logs for any of the 5 paper environments. |
| `python -m manipulation_bench.analyze_surface` | Simpler companion: frame × incentive and frame × difficulty grids per model. Shares utilities with the statistical pipeline above. |

## Legacy generators (kept for FINDINGS reproducibility)

These produced the scenario JSONLs referenced by sections of [`../FINDINGS.md`](../FINDINGS.md). They predate the response-surface axes rename and are not wired into `analyze_response_surface.py`; the canonical analyzer normalizes their legacy frame/incentive names via `axes.canonical_frame / canonical_incentive` so archived eval logs still pivot.

- Debate predecessors: `generate_policy_debates.py`, `generate_topology_experiment.py`, `generate_uncertain_claims.py`, `generate_context_isolation.py`
- Bargaining predecessors: `generate_bargaining.py`, `generate_bargaining_2x2.py`, `generate_bargaining_supplement.py`, `generate_bargaining_neutral_variants.py` (+ sibling analyzers `analyze_bargaining*.py`)
- Village predecessors: `generate_village.py`, `generate_village_factorial.py`, `generate_village_topology.py` (+ `analyze_village_topology.py`)
- Old task numbering (Task 1 / Task 2 / Task 4 sycophancy variant): `generate_task1_bargaining.py`, `generate_task2_persuasion.py` (+ `analyze_task2_pilot.py`), `generate_task4_sycophancy.py`
- Non-paper environments: `generate_werewolf_8player.py`, `generate_werewolf_iterated.py`, `generate_diplomacy.py`

## Adding a new environment

Each step below lists the exact file(s) to touch. The pattern is parallel to how Committee (Task 5) was added on top of the existing Debate/Village scaffolding.

1. **Environment class** — implement the `Environment` ABC in a new `../src/manipulation_bench/environments/<name>.py`. Contract: `base.py`. Reference implementations: `village.py` (tool-call actions, deterministic state) and `committee.py` (multi-phase private → discussion → final). Register in `environments/__init__.py`.
2. **Task wrapper** — new `../src/manipulation_bench/<name>_task.py` that calls `game_solver.game_interaction()` with the scorer list. Single-agent tasks (no counterparty LLM) can write their own solver — see `sales_task.py`. Add the task name to `_registry.py` for Inspect discovery.
3. **Scorers** — new `../src/manipulation_bench/scorers/<name>.py`. **Every env must include a `manipulation_occurred` boolean scorer** so cross-env slopes in `analyze_response_surface.py` line up. Re-export the new scorers from `scorers/__init__.py`.
4. **Axis prompts** — add `FRAME_PROMPTS["<name>"]` (5 levels) and `INCENTIVE_PROMPTS["<name>"]` (3 levels) entries to `../src/manipulation_bench/axes.py`. For envs where interested/neutral roles get different framing, follow the nested `{"interested": ..., "neutral": ...}` shape from `committee`.
5. **Surface generator** — new `generate_<name>_surface.py` here in `experiments/`, producing a JSONL under `../src/manipulation_bench/scenarios/`. Set `ScenarioMetadata.frame / incentive / difficulty / manipulator` as typed fields (not just extra metadata).
6. **Analyzer dispatch** — teach the three analyzers about the new env. All three dispatch on scorer names:
   - [`../src/manipulation_bench/analyze_surface.py`](../src/manipulation_bench/analyze_surface.py) — extend `detect_environment()` and add a `_<env>_metric()` function to the `_METRIC_EXTRACTORS` dict (pick the canonical manipulation metric).
   - [`analyze_response_surface.py`](analyze_response_surface.py) — reuses `analyze_surface`'s detection; no edit needed unless you want a task-specific z-scored continuous metric for the robustness replication (`zscore_continuous`).
   - [`../src/manipulation_bench/analyze.py`](../src/manipulation_bench/analyze.py) — only needed if you want env-specific analysis beyond the surface pivot (susceptibility, per-role breakdown, etc.).
