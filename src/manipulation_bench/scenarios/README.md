# Scenarios

JSONL files describing scenario configurations for `inspect eval`. One JSON object per line = one scenario (one `inspect` sample).

Most files here are **generator output** — reproducible by running the matching script in `experiments/`. A few hand-written files exist as minimal examples. Delete-and-regenerate anything from `experiments/` is safe.

## Starting points (read these first)

| File | What it is | How to regenerate |
|------|------------|-------------------|
| `debate_2agent.jsonl` | Minimal 2-agent debate (1 scenario). Hand-written example. | — |
| `personhood_rotation.jsonl` | Standard debate rotation: 4 debaters, baseline + 1 scenario per manipulator (5 total). | `python -m manipulation_bench.generate experiments/personhood.yaml -o src/manipulation_bench/scenarios/personhood_rotation.jsonl` |
| `werewolf_5player.jsonl` | Smallest social-deduction game (1 game, 5 players). | — |
| `village_6player.jsonl` | Smallest public-goods game (1 game, 6 players). | — |
| `diplomacy_7player.jsonl` | One 7-power Diplomacy game. | — |
| `naming_game.jsonl` | Naming-game vocabulary-convergence example. | — |

## Published experiment outputs

Each of these was used for a section in [`FINDINGS.md`](../../../FINDINGS.md). The scenario JSONL is committed so results are reproducible bit-for-bit.

| File | FINDINGS section | Generator |
|------|------------------|-----------|
| `policy_debates.jsonl` | §1 Policy debates | `experiments/generate_policy_debates.py` |
| `topology_experiment.jsonl` | §2 Topology | `experiments/generate_topology_experiment.py` |
| `belief_shift_claims.jsonl` | §3 Belief shift | `experiments/generate_belief_shift.py` |
| `uncertain_claims.jsonl` | §3, §7 Uncertain claims | `experiments/generate_uncertain_claims.py` |
| `contested_claims.jsonl` | §3 Contested claims | `experiments/generate_contested.py` |
| `factual_claims.jsonl` | §7 Factual claims | `experiments/generate_factual.py` |
| `werewolf_8player.jsonl` | §4 Werewolf tournament | `experiments/generate_werewolf_8player.py` |
| `werewolf_iterated_p2.jsonl` | §5 Werewolf iterated Phase 2 | `experiments/generate_werewolf_iterated.py` |
| `diplomacy_multimodel.jsonl` | §6 Diplomacy multi-model | `experiments/generate_diplomacy.py` |
| `context_isolation.jsonl` | §8 Context isolation | `experiments/generate_context_isolation.py` |
| `bargaining.jsonl` | §9 Bargaining gradient | `experiments/generate_bargaining.py` |
| `bargaining_supp.jsonl` | §9 Bargaining supplement | `experiments/generate_bargaining_supplement.py` |
| `bargaining_2x2.jsonl` | §10 Instruction × incentive | `experiments/generate_bargaining_2x2.py` |
| `bargaining_neutral_variants.jsonl` | §11 Neutral-prompt robustness | `experiments/generate_bargaining_neutral_variants.py` |
| `village_experiment.jsonl` | §12 Village Commons | `experiments/generate_village.py` |

## Other experimental outputs (not yet in FINDINGS)

| File | Generator |
|------|-----------|
| `active_resistance.jsonl` | `experiments/generate_active_resistance.py` |
| `analytical_reasoning.jsonl` | `experiments/generate_analytical_reasoning.py` |
| `contagion_p1.jsonl`, `contagion_p2.jsonl` | `experiments/generate_contagion.py` |
| `cross_env_antibody.jsonl` | `experiments/generate_cross_env_antibody.py` |
| `debate_iterated_p2.jsonl` | `experiments/generate_debate_iterated.py` |
| `inoculation_test.jsonl` | `experiments/generate_inoculation.py` |
| `village_factorial.jsonl` | `experiments/generate_village_factorial.py` |
| `werewolf_rotation.jsonl` | `experiments/generate_werewolf.py` |
| `manipulation_rotation.jsonl`, `debate_cross_model.jsonl` | Legacy ad-hoc outputs |
