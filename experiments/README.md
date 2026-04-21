# experiments/

Scenario generators, YAML configs, and one-off analysis scripts. Each Python file here is a standalone CLI — run `python experiments/<name>.py --help` (or read the module docstring) for invocation.

## Canonical paper generators

The five response-surface generators, one per paper environment. These factor over frame × incentive × difficulty (see [`../src/manipulation_bench/axes.py`](../src/manipulation_bench/axes.py)) and write scenarios with typed `metadata.frame / incentive / difficulty / manipulator` fields that [`analyze_response_surface.py`](analyze_response_surface.py) consumes.

| Generator | Environment | Pilot flag | Output |
|---|---|---|---|
| `generate_task4_sales.py` | Sales (Task 4) | `--pilot` | `scenarios/task4_sales_pilot.jsonl` |
| `generate_task5_committee.py` | Committee (Task 5) | `--pilot` / `--sweep` | `scenarios/task5_committee_{pilot,sweep}.jsonl` |
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

1. Implement the `Environment` ABC in [`../src/manipulation_bench/environments/`](../src/manipulation_bench/environments/) (contract in `base.py`, pattern in `village.py` / `committee.py`).
2. Add a `@task` file in [`../src/manipulation_bench/`](../src/manipulation_bench/) that wires it to `game_solver` (or writes its own solver for single-agent tasks like Sales).
3. Add env-specific scorers under [`../src/manipulation_bench/scorers/`](../src/manipulation_bench/scorers/) — include a `manipulation_occurred` boolean so cross-env slopes line up.
4. Add per-env `FRAME_PROMPTS[env]` + `INCENTIVE_PROMPTS[env]` blocks to `axes.py` (5 frame levels × 3 incentive levels).
5. Write `generate_<env>_surface.py` that emits scenarios with typed `ScenarioMetadata.frame / incentive / difficulty / manipulator`.
6. Teach [`analyze_response_surface.py`](analyze_response_surface.py) how to detect the new env (scorer-name heuristic) and which metric to use for the manipulation-response slope.
