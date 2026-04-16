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
