# Findings and Scripts Consolidation — Design

**Date:** 2026-05-04
**Branch:** add-eval-logs-csv
**Status:** Draft, pending user review

## Problem

Cross-cutting findings docs and analysis scripts are scattered across five locations:

- Repo root: `FINDINGS.md`, `FINDINGS_CONSOLIDATED.md`, `findings_notes.md`
- `csv/` (top-level): `FINDINGS.md`, `results.csv`, `scripts/`, `out/figures/`
- `paper/newer_analysis/`: 3 FINDINGS docs + scripts + figures
- `paper/capability_eval/`: `FINDINGS.md`, `README.md`, scripts, figures
- `paper/cross_task/`: `EXPLORATORY_FINDINGS.md`, `FINDINGS_FROM_FIRST_PRINCIPLES.md`, scripts, figures, JSONs

Per-task scripts under `paper/task<N>/scripts/` are *not* part of this scope — CLAUDE.md endorses that layout.

## Goal

Physical co-location, not collapsing-into-one-doc. Multiple FINDINGS files remain as separate docs; they just live together. `paper/cross_task/` is the consolidation target (per existing CLAUDE.md convention).

Non-goals:
- Rewriting any finding's content.
- Updating findings to reflect the post-recode CSV (separate task).
- Deduplicating overlapping claims across docs.
- Changing per-task `paper/task<N>/scripts/` layout.

## Target structure

```
paper/cross_task/
├── findings/
│   ├── README.md                      # NEW — index mapping each doc to its scripts
│   ├── corpus.md                      # was csv/FINDINGS.md
│   ├── exploratory.md                 # was paper/cross_task/EXPLORATORY_FINDINGS.md
│   ├── first_principles.md            # was paper/cross_task/FINDINGS_FROM_FIRST_PRINCIPLES.md
│   ├── capability_eval.md             # was paper/capability_eval/FINDINGS.md
│   ├── newer_analysis.md              # was paper/newer_analysis/FINDINGS.md
│   ├── incentive_recode_impact.md     # was paper/newer_analysis/FINDINGS_INCENTIVE_RECODE_PAPER_IMPACT.md
│   ├── spearman_bootstrap.md          # was paper/newer_analysis/SPEARMAN_BOOTSTRAP_FINDINGS.md
│   ├── consolidated.md                # was repo-root FINDINGS_CONSOLIDATED.md
│   ├── notes.md                       # was repo-root findings_notes.md
│   └── legacy_pre_paper.md            # was repo-root FINDINGS.md (1412-line legacy log)
│
├── scripts/
│   ├── cross_task/                    # was paper/cross_task/scripts/*.py (sub-namespaced)
│   ├── corpus/                        # was csv/scripts/
│   ├── capability/                    # was paper/capability_eval/scripts (or top-level .py)
│   └── newer/                         # was paper/newer_analysis/ scripts
│
├── data/
│   ├── results.csv                    # already here (post-recode)
│   ├── results.csv.pre_recode_bak     # already here
│   └── corpus.csv                     # was csv/results.csv
│
├── figures/
│   ├── (existing cross_task figures)
│   ├── corpus/                        # was csv/out/figures/
│   ├── capability/                    # was paper/capability_eval/figures/
│   └── newer/                         # was paper/newer_analysis/figures/
│
├── analysis/                          # JSON outputs (already here)
├── SUMMARY.md                         # already here
├── ANALYSIS_INVENTORY.md              # already here — refresh post-move
└── cross_task_aggregate.md            # already here
```

Filenames are lowercased and shortened since they're disambiguated by directory.

## Removed locations

After consolidation, these directories are deleted (verified empty first):

- `csv/` (top-level)
- `paper/newer_analysis/`
- `paper/capability_eval/`

Repo-root files removed: `FINDINGS.md`, `FINDINGS_CONSOLIDATED.md`, `findings_notes.md`.

## Migration plan

### Phase 1 — Inventory & path audit (read-only)

Catalog per source directory:
- Every `.py` script and its hardcoded path literals (CSV reads, figure write paths, JSON outputs).
- Every `.md` file and the file/figure references inside it.
- Cross-script imports (e.g., paper scripts importing `analyze_surface.py`).

Output: a single audit table mapping `old_path → new_path` plus a list of every in-script string literal needing edit. No moves yet.

### Phase 2 — Move in dependency order

Each step is move + simultaneous in-script path fix, so each commit boundary is consistent.

1. **Data first** — `csv/results.csv` → `paper/cross_task/data/corpus.csv`.
2. **Cross-cutting scripts** (one source dir at a time):
   1. `csv/scripts/` → `paper/cross_task/scripts/corpus/` (CSV reads → `data/corpus.csv`; figures → `figures/corpus/`)
   2. `paper/capability_eval/` → `paper/cross_task/scripts/capability/` + `figures/capability/`
   3. `paper/newer_analysis/` → `paper/cross_task/scripts/newer/` + `figures/newer/`
3. **In-place sub-namespacing** — existing `paper/cross_task/scripts/*.py` move into `paper/cross_task/scripts/cross_task/`. Update any imports.
4. **Findings docs** — move + rename + update internal links (each doc references its own figures/scripts that just moved).
5. **Root-level docs** — move into `paper/cross_task/findings/`.

### Phase 3 — Smoke tests

Per script, one of:
- **Run** if it doesn't make network/LLM calls and finishes in under ~2 min on the moved CSV — confirm no `FileNotFoundError`, output lands in new figures/JSON dir. CSV-bound scripts that are slower than this still qualify if the bottleneck is just I/O on the corpus CSV.
- **Static check** if expensive (LLM calls, multi-minute bootstraps with `B=2000`) — `python -c "import ast; ast.parse(open(...).read())"` plus grep for residual old paths (`csv/`, `paper/newer_analysis/`, `paper/capability_eval/`).

Each script gets ✅ smoke-passed or ⚠️ static-only in the audit table. A script that was broken pre-consolidation is flagged "pre-existing breakage, not caused by move" and not fixed (scope discipline).

### Phase 4 — Update references

- `manipulation-bench/CLAUDE.md` — every `paper/cross_task/scripts/`, `paper/newer_analysis/`, `paper/capability_eval/`, `csv/` reference.
- `paper/cross_task/SUMMARY.md` reproduction block.
- `paper/cross_task/ANALYSIS_INVENTORY.md` refresh.
- `paper/cross_task/findings/README.md` — new index file mapping each doc to the scripts that produced it.
- Reproduction commands inside the moved findings docs.
- `paper/paper.tex` — grep for any moved figure paths.

### Phase 5 — Delete empty source dirs

Remove `csv/`, `paper/newer_analysis/`, `paper/capability_eval/` after verifying empty. Confirm `git status` shows clean deletions, no orphaned files.

## Risks

| Risk | Mitigation |
|---|---|
| Hidden cross-script imports | Phase 1 grep for `import`/`from` across all source dirs before any move |
| Hardcoded relative paths in scripts | Phase 2 fixes paths *during* the move, not after, so each commit is consistent |
| Pre-existing broken scripts surface during smoke tests | Flag as pre-existing, do not fix in this work |
| `paper.tex` references to figure paths | Grep in Phase 4; update inline |
| Reproduction commands in findings docs go stale | Update in Phase 4, commit per-phase so failures are bisectable |

## Commit strategy

One commit per top-level phase, for a total of 5 commits (Phases 1–5). Phase 2's sub-steps are batched into a single commit; per-source-dir commits inside Phase 2 are an option only if a sub-step's path-fix turns out to be unexpectedly large. `git bisect`-friendly either way.

## Out of scope

- Re-running any analysis against post-recode CSV.
- Editing finding content.
- Touching `paper/task<N>/scripts/`, `experiments/`, `src/`, or `tests/`.
- Updating any worktree under `.worktrees/`.
