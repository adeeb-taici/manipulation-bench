# Naming Game Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split 35 commits of local bundled work into an archive branch, then land only the Level 2 Naming Game as a clean, targeted PR off `origin/main`.

**Architecture:** Archive current `main` to `archive/phase-2-3-4a` (preserved on origin), reset local `main` to `origin/main`, branch `feature/naming-game` off `origin/main`, port only the naming-game surface — environment, scorer, task, scenario, tests, novel-objects dataset, and surgical registry edits — then push and open a PR.

**Tech Stack:** Python 3.14 · Inspect AI · pytest · git · GitHub CLI (`gh`)

---

## File Structure

**Working directory throughout this plan:** `/home/borneans/Documents/TAICI/manipulation-bench`

**Reference source for ports:** branch `archive/phase-2-3-4a` (created in Task 1).

### Files to create on `feature/naming-game`

| Path | Origin | Role |
|---|---|---|
| `src/manipulation_bench/environments/naming_game.py` | copied from archive (unchanged) | `NamingGameEnvironment` class |
| `src/manipulation_bench/scorers/naming.py` | copied from archive (unchanged) | `vocabulary_convergence` scorer |
| `src/manipulation_bench/scenarios/naming_game.jsonl` | copied from archive | Scenario dataset |
| `src/manipulation_bench/consensus_tasks.py` | **new, minimal** (naming-game only) | `@task naming_game_bench` |
| `datasets/novel_objects.json` | copied from archive | Novel-object prompts |
| `tests/test_naming_game.py` | copied from archive (unchanged) | Unit tests |
| `docs/superpowers/specs/2026-04-16-naming-game-split-design.md` | copied from archive | Design record (already on archive as commit `1d66ad3`) |
| `docs/superpowers/plans/2026-04-16-naming-game-split.md` | this file (already on archive after Task 2 commit) | Plan record |

### Files to modify on `feature/naming-game` (surgical, naming-game lines only)

| Path | Change |
|---|---|
| `src/manipulation_bench/environments/__init__.py` | Add `NamingGameEnvironment` import, `"naming_game"` registry entry, `__all__` |
| `src/manipulation_bench/scorers/__init__.py` | Add `vocabulary_convergence` import + `__all__` entry |
| `src/manipulation_bench/_registry.py` | Add `"naming_game_bench": "manipulation_bench.consensus_tasks"` to `_TASKS` |
| `tests/conftest.py` | Add `"naming_game"` fixture branch only |

### Files to NOT touch

- Any other consensus level (binary coordination, continuous convergence, deliberative consensus, biased deliberation)
- Misinformation environment
- New scorer modules (opinion, dynamics, network_metrics, behavioral, spread)
- Viz module

---

## Task 1: Create archive branch and reset local main

**Files:**
- Branch: `archive/phase-2-3-4a` (new)
- Ref: `refs/heads/main` (reset)

- [ ] **Step 1: Verify clean working tree**

Run:
```bash
cd /home/borneans/Documents/TAICI/manipulation-bench
git status
```
Expected: `nothing to commit, working tree clean`. If not clean, stop and ask the user — do NOT proceed.

- [ ] **Step 2: Verify current HEAD and ahead count**

Run:
```bash
git log --oneline -1
git rev-list --count origin/main..main
```
Expected: HEAD is `1d66ad3 docs: add naming-game split design spec` (or a later commit containing this plan — see Step 3). `rev-list` prints `36` (35 feature commits + 1 spec commit). If plan is not yet committed on main, commit it first — see Task 2 Step 1.

- [ ] **Step 3: Create archive branch from main**

Run:
```bash
git branch archive/phase-2-3-4a main
git branch -vv | grep archive
```
Expected: `archive/phase-2-3-4a 1d66ad3 ...` listed.

- [ ] **Step 4: Push archive to origin**

Run:
```bash
git push -u origin archive/phase-2-3-4a
```
Expected: `Branch 'archive/phase-2-3-4a' set up to track 'origin/archive/phase-2-3-4a'` (or similar). If push is rejected, stop and diagnose — do NOT force.

- [ ] **Step 5: Fetch to confirm archive is on remote**

Run:
```bash
git fetch origin
git ls-remote origin archive/phase-2-3-4a
```
Expected: one line showing the archive SHA on origin. This is the safety net — confirm before the reset.

- [ ] **Step 6: Reset local main to origin/main**

Run:
```bash
git switch main
git reset --hard origin/main
git log --oneline -1
```
Expected: HEAD is now whatever `origin/main` points at (at time of writing: `69f06e7 Add empirically-validated uncertain claims ...`). If HEAD is still `1d66ad3`, the reset failed — stop.

- [ ] **Step 7: Confirm commits survived on archive**

Run:
```bash
git log archive/phase-2-3-4a --oneline | head -5
```
Expected: Top commit is `1d66ad3 docs: add naming-game split design spec`, followed by `d592b74 Ordering`, etc. Archive is intact.

*(No git commit needed — this task only manipulates refs.)*

---

## Task 2: Create feature branch and port the plan document

**Files:**
- Branch: `feature/naming-game` (new, off `origin/main`)
- Copy: `docs/superpowers/specs/2026-04-16-naming-game-split-design.md`
- Copy: `docs/superpowers/plans/2026-04-16-naming-game-split.md`

**Note:** If this plan file was written *after* Task 1's archive branch was created, it exists only on the current working tree, not on `archive/phase-2-3-4a`. In that case, commit it to `main` BEFORE Task 1 Step 3, or copy it from the working tree rather than from the archive. The steps below assume it's on the archive.

- [ ] **Step 1: Branch off origin/main**

Run:
```bash
git switch -c feature/naming-game origin/main
git log --oneline -1
```
Expected: HEAD matches `origin/main`.

- [ ] **Step 2: Copy spec and plan docs from archive**

Run:
```bash
git checkout archive/phase-2-3-4a -- \
  docs/superpowers/specs/2026-04-16-naming-game-split-design.md \
  docs/superpowers/plans/2026-04-16-naming-game-split.md
```
Expected: both files appear as staged (`git status` shows them under "Changes to be committed").

- [ ] **Step 3: Commit docs**

Run:
```bash
git commit -m "docs: add naming-game split design and plan"
```
Expected: one commit added on `feature/naming-game`.

---

## Task 3: Port the naming-game environment module

**Files:**
- Create: `src/manipulation_bench/environments/naming_game.py` (copy from archive)
- Test: deferred to Task 7 (copy tests wholesale from archive)

- [ ] **Step 1: Copy environment file from archive**

Run:
```bash
git checkout archive/phase-2-3-4a -- src/manipulation_bench/environments/naming_game.py
```
Expected: file staged.

- [ ] **Step 2: Verify file imports only origin/main symbols**

Run:
```bash
grep -n "^from manipulation_bench" src/manipulation_bench/environments/naming_game.py
grep -n "^import manipulation_bench" src/manipulation_bench/environments/naming_game.py
```
Expected: only imports from `manipulation_bench.environments.base` and (under `TYPE_CHECKING`) `manipulation_bench.network`. Both modules exist on `origin/main` — verify:
```bash
ls src/manipulation_bench/environments/base.py src/manipulation_bench/network.py
```
Both must exist. If `network.py` does NOT exist on origin/main, the `TYPE_CHECKING` import is dead-code-safe (it's string-only at runtime), so this is still fine — note it and proceed.

- [ ] **Step 3: Do NOT commit yet**

Environment file will be committed together with its test and registry entry in later tasks.

---

## Task 4: Add NamingGameEnvironment to the environment registry

**Files:**
- Modify: `src/manipulation_bench/environments/__init__.py`

- [ ] **Step 1: Add import (after other environment imports)**

Edit `src/manipulation_bench/environments/__init__.py`. Find:

```python
from manipulation_bench.environments.debate import DebateEnvironment
from manipulation_bench.environments.diplomacy import DiplomacyEnvironment
from manipulation_bench.environments.werewolf import WerewolfEnvironment
```

Add one line — alphabetical order matters:

```python
from manipulation_bench.environments.debate import DebateEnvironment
from manipulation_bench.environments.diplomacy import DiplomacyEnvironment
from manipulation_bench.environments.naming_game import NamingGameEnvironment
from manipulation_bench.environments.werewolf import WerewolfEnvironment
```

- [ ] **Step 2: Add registry entry**

Find:

```python
ENVIRONMENTS: dict[str, type[Environment]] = {
    "debate": DebateEnvironment,
    "diplomacy": DiplomacyEnvironment,
    "werewolf": WerewolfEnvironment,
}
```

Add one line — keep alphabetical:

```python
ENVIRONMENTS: dict[str, type[Environment]] = {
    "debate": DebateEnvironment,
    "diplomacy": DiplomacyEnvironment,
    "naming_game": NamingGameEnvironment,
    "werewolf": WerewolfEnvironment,
}
```

- [ ] **Step 3: Add to `__all__`**

Find the `__all__` list and add `"NamingGameEnvironment"` in alphabetical order between the existing environment class names. Example result:

```python
__all__ = [
    "ActionResult",
    "DebateEnvironment",
    "DiplomacyEnvironment",
    "Environment",
    "GameOutcome",
    "NamingGameEnvironment",
    "Observation",
    "Phase",
    "PhaseType",
    "WerewolfEnvironment",
    "create_environment",
]
```
(If the exact existing shape differs, preserve existing entries and only add `"NamingGameEnvironment"`.)

- [ ] **Step 4: Smoke-test imports**

Run:
```bash
python -c "from manipulation_bench.environments import NamingGameEnvironment, ENVIRONMENTS; assert 'naming_game' in ENVIRONMENTS; print('OK')"
```
Expected: `OK`. If `ModuleNotFoundError` or `ImportError`, stop — fix before proceeding.

- [ ] **Step 5: Do NOT commit yet** (committed with Task 7).

---

## Task 5: Port the naming-game scorer module and register it

**Files:**
- Create: `src/manipulation_bench/scorers/naming.py` (copy from archive)
- Modify: `src/manipulation_bench/scorers/__init__.py`

- [ ] **Step 1: Copy scorer file from archive**

Run:
```bash
git checkout archive/phase-2-3-4a -- src/manipulation_bench/scorers/naming.py
```
Expected: file staged.

- [ ] **Step 2: Verify scorer imports**

Run:
```bash
grep -n "^from" src/manipulation_bench/scorers/naming.py
```
Expected: imports only from `inspect_ai.scorer`, `inspect_ai.solver`, `manipulation_bench.models`. All exist on `origin/main`. If any other `manipulation_bench.*` import appears, stop — it signals a hidden dependency; report to the user.

- [ ] **Step 3: Register in scorers/__init__.py**

Edit `src/manipulation_bench/scorers/__init__.py`. Find the existing imports block (from `grounded`, `judges`, `social_deduction`, `negotiation`, `voting`). Add one new import line. Exact addition:

```python
from manipulation_bench.scorers.naming import vocabulary_convergence
```

Place it in alphabetical order among the module imports (between `judges` and `negotiation`).

- [ ] **Step 4: Add to `__all__`**

In the same file, add `"vocabulary_convergence"` to the `__all__` list. Keep the existing comment-grouped structure if present; add a `# Naming game` group if the file groups by category, otherwise insert alphabetically. Example:

```python
__all__ = [
    # ... existing entries ...
    "vocabulary_convergence",
]
```

- [ ] **Step 5: Smoke-test imports**

Run:
```bash
python -c "from manipulation_bench.scorers import vocabulary_convergence; print(vocabulary_convergence.__name__)"
```
Expected: `vocabulary_convergence`. If import fails, stop.

- [ ] **Step 6: Do NOT commit yet** (committed with Task 7).

---

## Task 6: Create minimal consensus_tasks.py and register the task

**Files:**
- Create: `src/manipulation_bench/consensus_tasks.py` (new, minimal — naming game only)
- Modify: `src/manipulation_bench/_registry.py`
- Copy: `src/manipulation_bench/scenarios/naming_game.jsonl` from archive
- Copy: `datasets/novel_objects.json` from archive

- [ ] **Step 1: Create `consensus_tasks.py` with naming-game task only**

Write the full file contents to `src/manipulation_bench/consensus_tasks.py`:

```python
"""@task definitions for consensus game levels.

Currently only Level 2 (Naming Game) is implemented. Additional levels will be
added in follow-up PRs off origin/main.
"""

from __future__ import annotations

from inspect_ai import Task, task

from manipulation_bench.dataset import load_scenarios
from manipulation_bench.game_solver import game_interaction
from manipulation_bench.scorers import vocabulary_convergence


@task
def naming_game_bench(
    scenarios: str = "naming_game.jsonl",
) -> Task:
    """Level 2: Naming Game -- vocabulary convergence through pairwise encounters."""
    return Task(
        dataset=load_scenarios(scenarios),
        solver=game_interaction(),
        scorer=[
            vocabulary_convergence(),
        ],
    )
```

**Do NOT import tasks for other levels.** This file replaces (does not extend) the archive's 5-level version.

- [ ] **Step 2: Register `naming_game_bench` in `_registry.py`**

Edit `src/manipulation_bench/_registry.py`. Find the `_TASKS` dict:

```python
_TASKS = {
    "diplomacy_bench": "manipulation_bench.diplomacy_task",
    "werewolf_bench": "manipulation_bench.game_task",
    "manipulation_bench": "manipulation_bench.task",
}
```

Add one line, alphabetical:

```python
_TASKS = {
    "diplomacy_bench": "manipulation_bench.diplomacy_task",
    "manipulation_bench": "manipulation_bench.task",
    "naming_game_bench": "manipulation_bench.consensus_tasks",
    "werewolf_bench": "manipulation_bench.game_task",
}
```

- [ ] **Step 3: Copy the scenarios JSONL**

Run:
```bash
git checkout archive/phase-2-3-4a -- src/manipulation_bench/scenarios/naming_game.jsonl
```

- [ ] **Step 4: Copy the novel-objects dataset**

Run:
```bash
git checkout archive/phase-2-3-4a -- datasets/novel_objects.json
```

- [ ] **Step 5: Smoke-test the task loads**

Run:
```bash
python -c "from manipulation_bench._registry import naming_game_bench; t = naming_game_bench(); print(type(t).__name__)"
```
Expected: `Task`. Any `ImportError` or `FileNotFoundError` on the JSONL — stop and fix before proceeding.

- [ ] **Step 6: Do NOT commit yet** (committed with Task 7).

---

## Task 7: Port tests and wire up conftest fixture

**Files:**
- Create: `tests/test_naming_game.py` (copy from archive)
- Modify: `tests/conftest.py` (add naming-game fixture branch only)

- [ ] **Step 1: Copy test file from archive**

Run:
```bash
git checkout archive/phase-2-3-4a -- tests/test_naming_game.py
```

- [ ] **Step 2: Edit `tests/conftest.py` — update `_ENV_PARAMS`**

Current `origin/main` line 17:

```python
_ENV_PARAMS = ["debate", "werewolf"] + (["diplomacy"] if HAS_DIPLOMACY else [])
```

Replace with (only `"naming_game"` added — NOT the other levels or misinformation):

```python
_ENV_PARAMS = ["debate", "naming_game", "werewolf"] + (["diplomacy"] if HAS_DIPLOMACY else [])
```

- [ ] **Step 3: Edit `tests/conftest.py` — add the `naming_game` fixture branch**

Find the existing `elif request.param == "diplomacy":` block in the fixture function. Insert a new `elif` branch for `naming_game` BEFORE the `diplomacy` branch. Exact code to add:

```python
    elif request.param == "naming_game":
        from manipulation_bench.environments.naming_game import NamingGameEnvironment

        env = NamingGameEnvironment(
            {
                "object_description": "A glowing sphere that hovers and hums.",
                "pairs_per_round": 2,
                "max_rounds": 5,
                "seed": 0,
            }
        )
        env.setup(["alice", "bob", "carol", "dave"])
        return env
```

Do NOT add `biased_deliberation`, `binary_coordination`, `continuous_convergence`, `deliberative_consensus`, or `misinformation` branches — those belong to later PRs.

- [ ] **Step 4: Run the naming-game tests**

Run:
```bash
pytest tests/test_naming_game.py -v
```
Expected: all tests PASS (the archive had them passing). If any fail, inspect the test file for imports that reference missing modules (e.g., a new scorer base class) — most likely cause would be a test that imports from `manipulation_bench.scorers.dynamics` or similar. If found, report to user — do NOT stub or modify the test.

- [ ] **Step 5: Run the full test suite**

Run:
```bash
pytest tests/ -v
```
Expected: all existing `origin/main` tests still pass, plus the new naming-game tests. If a previously-passing test now fails, the `conftest.py` edit likely broke something — revert to the exact diff from Step 2 and Step 3.

- [ ] **Step 6: Stage everything for the single feature commit**

Run:
```bash
git add \
  src/manipulation_bench/environments/naming_game.py \
  src/manipulation_bench/environments/__init__.py \
  src/manipulation_bench/scorers/naming.py \
  src/manipulation_bench/scorers/__init__.py \
  src/manipulation_bench/consensus_tasks.py \
  src/manipulation_bench/_registry.py \
  src/manipulation_bench/scenarios/naming_game.jsonl \
  datasets/novel_objects.json \
  tests/test_naming_game.py \
  tests/conftest.py
git status
```
Expected: all 10 paths listed under "Changes to be committed", nothing else staged or unstaged.

- [ ] **Step 7: Commit**

Run:
```bash
git commit -m "$(cat <<'EOF'
feat: add Level 2 Naming Game environment and task

Adds the NamingGameEnvironment (pairwise DISCUSSION encounters where agents
invent names for a novel object, tracking vocabulary convergence), the
vocabulary_convergence scorer, a minimal consensus_tasks module exposing
naming_game_bench, the scenarios JSONL, novel-objects dataset, and tests.

Other consensus levels (1, 3, 4, 5) will follow in separate PRs.
EOF
)"
```
Expected: single commit on `feature/naming-game` on top of the docs commit from Task 2.

---

## Task 8: Smoke-test the task end-to-end

**Files:** (none modified)

- [ ] **Step 1: Run the naming-game task with a mock model**

Run:
```bash
inspect eval src/manipulation_bench/consensus_tasks.py@naming_game_bench \
  --model mockllm/model --limit 1
```
Expected: eval completes without errors, produces a log file under `logs/`. A mockllm won't produce realistic convergence, but the pipeline should run without ImportError, KeyError, or AttributeError.

- [ ] **Step 2: Confirm scorer emits its metric**

Scan the eval output or open the log in `inspect view`. The `vocabulary_convergence` scorer should appear with a dict value containing `converged`, `rounds_to_convergence`, `vocab_size_mean`.

- [ ] **Step 3: Run lint / type check if the project uses them**

Run:
```bash
ls pyproject.toml | xargs grep -l "ruff\|mypy" 2>/dev/null && {
  grep -q "ruff" pyproject.toml && ruff check src/ tests/ || true
  grep -q "mypy" pyproject.toml && mypy src/ || true
}
```
Expected: any existing lint config passes. If lint finds new issues in the naming-game files, fix them (import ordering, unused imports). If lint complains about unrelated files, those are pre-existing on `origin/main` — leave alone.

*(No commit — Task 8 is verification only.)*

---

## Task 9: Push branch and open PR

**Files:** (none modified)

- [ ] **Step 1: Confirm branch state**

Run:
```bash
git log origin/main..feature/naming-game --oneline
```
Expected: exactly 2 commits — the docs commit from Task 2, then the feature commit from Task 7. If more commits are present, stop and reconcile before pushing.

- [ ] **Step 2: Push feature branch**

Run:
```bash
git push -u origin feature/naming-game
```
Expected: remote tracking set up.

- [ ] **Step 3: Open the PR**

Run:
```bash
gh pr create --base main --title "feat: add Level 2 Naming Game environment and task" --body "$(cat <<'EOF'
## Summary

- Adds the `NamingGameEnvironment` (Level 2 of the consensus game suite): N agents invent names for a novel object through random pairwise encounters; vocabularies are tracked per agent and the environment terminates when all agents share a common name or `max_rounds` is reached.
- Adds the `vocabulary_convergence` scorer reporting `converged`, `rounds_to_convergence`, and `vocab_size_mean`.
- Introduces a minimal `consensus_tasks.py` exposing `naming_game_bench` only; other consensus levels will land in follow-up PRs.
- Registers the environment in `environments/__init__.py` and the task in `_registry.py`.
- Adds the scenarios JSONL, novel-objects dataset, and test suite.

Design spec: `docs/superpowers/specs/2026-04-16-naming-game-split-design.md`
Plan: `docs/superpowers/plans/2026-04-16-naming-game-split.md`

## Test plan

- [ ] `pytest tests/test_naming_game.py -v` passes
- [ ] Full test suite `pytest tests/ -v` still passes
- [ ] `inspect eval src/manipulation_bench/consensus_tasks.py@naming_game_bench --model mockllm/model --limit 1` runs to completion

## Follow-ups (separate PRs)

- Level 1 Binary Coordination
- Level 3 Continuous Convergence (depends on opinion/dynamics scorer PR)
- Level 4 Deliberative Consensus
- Level 5 Biased Deliberation
- Misinformation environment port
- Scorer suite expansion
- Viz module

All of the above are preserved on branch `archive/phase-2-3-4a` as a reference for porting.
EOF
)"
```
Expected: PR URL printed. Report it to the user.

---

## Rollback procedure (if any step goes wrong)

- **After Task 1, before pushing feature branch:** `git reset --hard archive/phase-2-3-4a` on local `main` restores everything. The archive on origin is untouched.
- **After Task 7 commit, before push:** `git switch main && git branch -D feature/naming-game` deletes the feature branch without affecting origin.
- **After push:** `git push origin --delete feature/naming-game` removes the remote branch. The archive remains the source of truth.

---

## Self-Review Notes

Checked against the spec:

- Spec Goal 1 (preserve commits): Task 1 Steps 3–5.
- Spec Goal 2 (naming game only in first PR): Tasks 3–7 only touch naming-game files + surgical registry edits.
- Spec Goal 3 (self-contained): Task 3 Step 2, Task 5 Step 2, Task 6 Step 5 verify imports.
- Spec Goal 4 (clean start for follow-ups): Task 9 PR body lists follow-ups; archive preserves source.
- Spec Step 1 → Task 1. Step 2 → Task 1 Step 6. Step 3 → Task 2. Step 4 → Tasks 3–7. Step 5 → Task 7 Step 7. Step 6 → Task 8. Step 7 → Task 9. Full coverage.

No placeholders. All commands are exact. Type/name consistency verified (`naming_game_bench`, `vocabulary_convergence`, `NamingGameEnvironment`, `"naming_game"` — same spelling throughout).
