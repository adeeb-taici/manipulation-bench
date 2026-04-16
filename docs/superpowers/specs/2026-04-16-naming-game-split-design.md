# Naming Game Split — Design

**Date:** 2026-04-16
**Status:** Proposed
**Repo:** `manipulation-bench`

## Problem

Local `main` is 35 commits ahead of `origin/main`. Those commits bundle Phase 2/3/4a work: the full consensus game suite (5 levels), a ported misinformation environment, 30+ new scorers, a viz module, and associated tests. Pushing this as-is produces a single unreviewable PR.

We want `origin/main` to evolve through a series of **small, reviewable PRs**, starting with the Level 2 Naming Game environment only. Other levels and infrastructure land in follow-up PRs.

## Goals

1. Preserve every commit currently on local `main` — nothing lost.
2. First PR to `origin/main` adds **only** the Naming Game: environment, scorer, task, scenario data, tests.
3. The naming-game PR is self-contained — no code, imports, or registry entries for Levels 1/3/4/5, misinformation, or the new scorer/viz suites.
4. Leave a clean starting point for subsequent targeted PRs off `origin/main`.

## Non-goals

- No refactoring of existing environments or the solver.
- No introduction of new abstractions beyond what the naming-game commit already defined.
- No changes to CI, packaging, or docs outside what the naming-game code itself requires.

## Current state (verified 2026-04-16)

- Local `main` = `d592b74`, 35 commits ahead of `origin/main`.
- Naming-game code was introduced in `3ebc3d6 feat: add Level 2 Naming Game environment` (env + tests + novel_objects.json + conftest tweak + registry line).
- Scorer `scorers/naming.py` and task wiring in `consensus_tasks.py` / `_registry.py` were added **later**, in commits that also wire the other 4 levels — so these can't be cherry-picked cleanly.
- `origin/main` already has: `models.py` (incl. `InteractionState`), `game_solver.py`, `dataset.py`, `environments/base.py`, and the debate/werewolf/diplomacy environments. Nothing else on the naming-game branch needs to be ported from archive to make it run.

## Approach

### Step 1 — Archive branch

Create `archive/phase-2-3-4a` from current local `main` and push it to origin. This is the safety net; no commit is discarded, only re-routed. The archive includes this spec commit, which rides along as a record of the split plan.

```
git branch archive/phase-2-3-4a main
git push -u origin archive/phase-2-3-4a
```

### Step 2 — Reset local `main` to match origin

```
git switch main
git reset --hard origin/main
```

The archive branch retains every commit. This is destructive to local `main`'s ref only; the commits remain reachable via the archive.

### Step 3 — Branch `feature/naming-game` off `origin/main`

```
git switch -c feature/naming-game origin/main
```

### Step 4 — Port the naming-game surface

The spec file (`docs/superpowers/specs/2026-04-16-naming-game-split-design.md`) is also copied from the archive onto `feature/naming-game` so the PR includes its own design record.


Files copied verbatim from `archive/phase-2-3-4a` (using `git checkout archive/phase-2-3-4a -- <path>`):

| Path | Source commit | Notes |
|---|---|---|
| `src/manipulation_bench/environments/naming_game.py` | `3ebc3d6` | Unchanged |
| `src/manipulation_bench/scorers/naming.py` | later commit | Unchanged; imports only `InteractionState` from `models`, which is on origin/main |
| `src/manipulation_bench/scenarios/naming_game.jsonl` | later commit | Unchanged |
| `datasets/novel_objects.json` | `3ebc3d6` | Unchanged |
| `tests/test_naming_game.py` | `3ebc3d6` | Unchanged |

Files modified surgically (only naming-game lines added; no Level 1/3/4/5 or misinformation entries):

| Path | Change |
|---|---|
| `src/manipulation_bench/environments/__init__.py` | Add `NamingGameEnvironment` import, `"naming_game"` registry entry, `__all__` entry |
| `src/manipulation_bench/scorers/__init__.py` | Add `vocabulary_convergence` import and `__all__` entry |
| `src/manipulation_bench/_registry.py` | Add `"naming_game_bench": "manipulation_bench.consensus_tasks"` to `_TASKS` dict |
| `tests/conftest.py` | Add the naming-game fixture branch from `3ebc3d6` (no other level fixtures) |

File **created new** (minimal, does not exist on origin/main):

- `src/manipulation_bench/consensus_tasks.py` — contains only the `naming_game_bench` `@task` function. Other levels' tasks are **not** included.

### Step 5 — Commit as one

Single commit titled `feat: add Level 2 Naming Game environment and task`. Keeps the PR coherent and matches how debate/werewolf/diplomacy were each introduced on origin/main.

### Step 6 — Verify

- `pytest tests/test_naming_game.py -v` must pass.
- `inspect eval src/manipulation_bench/consensus_tasks.py@naming_game_bench --model mockllm/model --limit 1` smoke test must complete without import errors.
- `ruff check` / existing lint must pass.

### Step 7 — Push and open PR

```
git push -u origin feature/naming-game
gh pr create --base main --title "feat: add Level 2 Naming Game environment and task"
```

## Risk / rollback

- **Local `main` reset is destructive to the ref.** Mitigation: `archive/phase-2-3-4a` is pushed to origin *before* the reset, so the commits are preserved on the remote.
- **Hidden dependency surfaces.** Mitigation: `scorers/naming.py` was inspected — it imports only `InteractionState` from `models`, which is on origin/main. No other naming-game file imports from the new scorer/viz/dynamics modules.
- **Test fixtures may pull in deps from other levels.** Mitigation: `tests/conftest.py` edit is the targeted 15-line addition from `3ebc3d6` only; fixtures for Levels 1/3/4/5 are not added.

## Follow-up PRs (not part of this spec)

Each off `origin/main`, each its own spec if non-trivial:

- Level 1 Binary Coordination
- Level 3 Continuous Convergence (may depend on opinion/dynamics scorer PR)
- Level 4 Deliberative Consensus
- Level 5 Biased Deliberation
- Misinformation environment port
- Scorer suite expansion (opinion, dynamics, network_metrics, behavioral, spread)
- Viz module

Archive branch `archive/phase-2-3-4a` is the reference for what code needs porting.

---

## Addendum (2026-04-16): topology redesign

After the faithful port landed on `feature/naming-game`, an end-to-end run with `gpt-oss-120b` produced no convergence in 6 rounds — each agent ended with 2–4 distinct names. The root cause is the speaker/hearer pairwise mechanic: rejected counter-proposals never reach the original speaker, information propagates slowly, and agents get no population-level signal.

### Revised design

The naming game is redesigned around **parallel broadcast proposals** with configurable **communication topology**. This aligns with the classical Baronchelli et al. naming game literature and makes convergence failure an interpretable signal instead of a mechanical artifact.

**Mechanics:**
- Each round is a single DISCUSSION phase with `acting_agents = [all]`, `parallel = True`.
- Every agent proposes one name in parallel.
- Between rounds, each agent sees the list of proposals visible to them under the current topology — not necessarily all N.
- Convergence is checked at round end under a configurable rule.

**New scenario config keys:**
- `topology: "broadcast" | "ring" | "star" | "dense" | "commons"` — default `broadcast`
- `attribution: "anonymous" | "labeled"` — whether proposals carry speaker names. Default `anonymous`.
- `convergence: "strict" | "majority"` — default `strict`
- `majority_threshold: float` — only used when `convergence: majority`. Default `0.5`.

**Topology semantics for naming game:**
- `broadcast` / `dense` / `commons` — each agent sees all N proposals
- `ring` — each agent sees only their two neighbors
- `star` — hub sees all; leaves see only the hub

**Deleted config keys:** `pairs_per_round`. Speaker/hearer logic is removed entirely.

### Infrastructure port

To support topologies, `src/manipulation_bench/network.py` is ported from `archive/phase-2-3-4a` (183 lines, unchanged). It provides `Network`, `Node`, `Channel`, `Message`, `ChannelType` plus topology factories (`broadcast`, `ring`, `star`, `dense`, `commons`).

A minimal `src/manipulation_bench/agents.py` stub is added containing just `PersonaCard(name: str, role: str = "")` — enough to satisfy `network.py`'s imports without bringing over the full traits/backstory system. That expansion lands in later PRs as other levels need it.

The archive's `tests/test_network.py` is ported unchanged to cover the topology factories and channel routing.

### Scorer revision

`vocabulary_convergence` now reports:
- `strict_converged` — 0/1, all N agents proposed the same name in the final round
- `majority_converged` — 0/1, a single name was proposed by >`majority_threshold` fraction of agents
- `majority_fraction_final` — the largest name's share in the final round (useful even without convergence)
- `unique_names_final` — count of distinct names in the final round (1 = unanimous)
- `rounds_to_convergence` — round number when the configured rule first fired, or `max_rounds`

Both strict and majority are always computed; the `convergence` config only controls which one stops the loop early.

### Commits on top of `456eeef`

Two additional commits, not squashed:

1. `feat: port network.py and minimal PersonaCard stub` — adds `network.py`, `agents.py` (stub), `tests/test_network.py`. No behavior change to any existing environment.
2. `refactor: rewrite naming game around parallel broadcast proposals` — rewrites `environments/naming_game.py`, updates `scorers/naming.py`, rewrites `tests/test_naming_game.py`, updates `scenarios/naming_game.jsonl`, updates the `naming_game` fixture in `tests/conftest.py`.

### PR retitle

`feat: add Level 2 Naming Game environment and task` → `feat: add network topology module and parallel Naming Game`

### Risk / rollback

If the topology rewrite is too risky to land in this PR, the refactor commit can be reverted, leaving the `network.py` port (commit 1) as pure infrastructure. The pairwise naming game from commit `456eeef` would remain in place.

