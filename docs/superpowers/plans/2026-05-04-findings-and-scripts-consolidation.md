# Findings and Scripts Consolidation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Physically co-locate every cross-cutting findings doc and analysis script into `paper/cross_task/`, fixing all paths so every script still runs.

**Architecture:** Five-phase migration. Phase 1 audits paths (read-only). Phases 2a–2c move scripts + their figures + their outputs one source dir at a time, fixing in-script paths during the move. Phase 3 sub-namespaces existing `paper/cross_task/scripts/*.py` and moves their CSVs into `data/`. Phase 4 moves findings docs and updates internal links. Phase 5 deletes empty source dirs and updates CLAUDE.md.

**Tech Stack:** Python 3.12, pandas, git, bash. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-05-04-findings-and-scripts-consolidation-design.md`

---

## Pre-flight

Working directory: `/home/borneans/Documents/TAICI/manipulation-bench`. Git branch: `add-eval-logs-csv`. Confirm clean working tree before starting beyond the already-committed spec; the modified files in `git status` are pre-existing on this branch and unrelated.

---

## Phase 1 — Inventory and path audit

### Task 1.1: Generate the path-reference inventory

**Files:**
- Create: `docs/superpowers/plans/consolidation-audit.md` (working notes; not committed to repo permanently)

- [ ] **Step 1: Run the inventory grep**

```bash
{
  echo "## csv/scripts (CSV reads, figure writes, sibling imports)"
  grep -nE "Path\(|read_csv|to_csv|savefig|open\(|from _" csv/scripts/*.py
  echo ""
  echo "## paper/newer_analysis/scripts"
  grep -nE "Path\(|read_csv|to_csv|savefig|open\(|from _" paper/newer_analysis/scripts/*.py
  echo ""
  echo "## paper/capability_eval/scripts"
  grep -nE "Path\(|read_csv|to_csv|savefig|open\(|from _" paper/capability_eval/scripts/*.py
  echo ""
  echo "## paper/cross_task/scripts (existing — will be sub-namespaced)"
  grep -nE "Path\(|read_csv|to_csv|savefig|open\(|results\.csv|model_capability" paper/cross_task/scripts/*.py
} > docs/superpowers/plans/consolidation-audit.md
```

- [ ] **Step 2: Verify the audit captures what we expect**

Run: `wc -l docs/superpowers/plans/consolidation-audit.md`
Expected: roughly 200–400 lines.

Eyeball-check for: every `_loader.py`-importing script in `csv/scripts/`; every `_capability_io.py`-importing script in capability; the absolute path in `paper/newer_analysis/scripts/04_incentive_traces.py:26` (hardcoded `/home/borneans/...`).

- [ ] **Step 3: Commit Phase 1**

```bash
git add docs/superpowers/plans/consolidation-audit.md
git commit -m "Phase 1: path-reference inventory for consolidation"
```

---

## Phase 2 — Move cross-cutting scripts (one source dir at a time)

Phase 2 is one git commit. Each sub-step within it leaves the working tree consistent (every moved script has its paths updated before you continue), so if you stop partway you can still run the moved scripts.

### Task 2a.1: Create target directories

**Files:**
- Create: `paper/cross_task/data/`
- Create: `paper/cross_task/figures/corpus/`
- Create: `paper/cross_task/figures/capability/`
- Create: `paper/cross_task/figures/newer/`
- Create: `paper/cross_task/scripts/corpus/`
- Create: `paper/cross_task/scripts/capability/`
- Create: `paper/cross_task/scripts/newer/`

- [ ] **Step 1: Create the directories**

```bash
mkdir -p paper/cross_task/data \
         paper/cross_task/figures/corpus \
         paper/cross_task/figures/capability \
         paper/cross_task/figures/newer \
         paper/cross_task/scripts/corpus \
         paper/cross_task/scripts/capability \
         paper/cross_task/scripts/newer
```

- [ ] **Step 2: Verify**

Run: `ls -d paper/cross_task/data paper/cross_task/figures/{corpus,capability,newer} paper/cross_task/scripts/{corpus,capability,newer}`
Expected: all 7 directories listed without error.

### Task 2a.2: Move the canonical CSVs into `data/`

**Files:**
- Move: `paper/cross_task/results.csv` → `paper/cross_task/data/results.csv`
- Move: `paper/cross_task/results.csv.bak` → `paper/cross_task/data/results.csv.bak`
- Move: `paper/cross_task/results.csv.pre_recode_bak` → `paper/cross_task/data/results.csv.pre_recode_bak`
- Move: `paper/cross_task/model_capability.csv` → `paper/cross_task/data/model_capability.csv`
- Move: `csv/results.csv` → `paper/cross_task/data/corpus.csv`

- [ ] **Step 1: Move using `git mv` (preserves history)**

```bash
git mv paper/cross_task/results.csv paper/cross_task/data/results.csv
git mv paper/cross_task/results.csv.bak paper/cross_task/data/results.csv.bak
git mv paper/cross_task/results.csv.pre_recode_bak paper/cross_task/data/results.csv.pre_recode_bak
git mv paper/cross_task/model_capability.csv paper/cross_task/data/model_capability.csv
git mv csv/results.csv paper/cross_task/data/corpus.csv
```

`paper/cross_task/results.csv` is git-LFS-tracked (per CLAUDE.md). `git mv` preserves the LFS pointer.

- [ ] **Step 2: Verify**

Run: `ls paper/cross_task/data/`
Expected: `results.csv  results.csv.bak  results.csv.pre_recode_bak  model_capability.csv  corpus.csv`

Run: `ls csv/`
Expected: `FINDINGS.md  scripts  out` (no `results.csv` anymore)

### Task 2a.3: Patch existing `paper/cross_task/scripts/*.py` for the new CSV location

These scripts will be sub-namespaced in Phase 3, but their CSV references need fixing **now** because Phase 2b/2c scripts (capability, newer) compute paths relative to `paper/cross_task/` and they assume the CSV is reachable. Editing these now keeps the tree consistent.

**Files:**
- Modify: `paper/cross_task/scripts/load.py:267` — `RESULTS_CSV` constant
- Modify: `paper/cross_task/scripts/append_t6_to_csv.py:28` — `DEFAULT_OUTPUT`
- Modify: `paper/cross_task/scripts/append_t6_to_results.py:25,26` — `EXISTING_CSV`, `DEST_CSV`
- Modify: `paper/cross_task/scripts/append_t6_to_results.py:27` — `CSV_MIRROR` (corpus.csv now lives in `data/`)
- Modify: `paper/cross_task/scripts/eval_logs_to_csv.py:62` — `DEFAULT_OUTPUT`

- [ ] **Step 1: Patch `load.py`**

In `paper/cross_task/scripts/load.py:267`, change:

```python
RESULTS_CSV = REPO_ROOT / "paper/cross_task/results.csv"
```

to:

```python
RESULTS_CSV = REPO_ROOT / "paper/cross_task/data/results.csv"
```

Update the docstring around line 273 ("Read paper/cross_task/results.csv ...") and 342 to say `paper/cross_task/data/results.csv`.

- [ ] **Step 2: Patch the append/eval-logs scripts**

In `paper/cross_task/scripts/append_t6_to_csv.py:28`, change:

```python
DEFAULT_OUTPUT = REPO_ROOT / "paper/cross_task/results.csv"
```

to:

```python
DEFAULT_OUTPUT = REPO_ROOT / "paper/cross_task/data/results.csv"
```

In `paper/cross_task/scripts/append_t6_to_results.py:25-27`, change:

```python
EXISTING_CSV = REPO_ROOT / "paper/cross_task/results.csv"
DEST_CSV = REPO_ROOT / "paper/cross_task/results.csv"
CSV_MIRROR = REPO_ROOT / "csv/results.csv"
```

to:

```python
EXISTING_CSV = REPO_ROOT / "paper/cross_task/data/results.csv"
DEST_CSV = REPO_ROOT / "paper/cross_task/data/results.csv"
CSV_MIRROR = REPO_ROOT / "paper/cross_task/data/corpus.csv"
```

In `paper/cross_task/scripts/eval_logs_to_csv.py:62`, change:

```python
DEFAULT_OUTPUT = REPO_ROOT / "paper/cross_task/results.csv"
```

to:

```python
DEFAULT_OUTPUT = REPO_ROOT / "paper/cross_task/data/results.csv"
```

- [ ] **Step 3: Smoke-check `load.py`**

Run: `python -c "from paper.cross_task.scripts.load import load_corpus; df = load_corpus(); print(len(df), 'rows')"`

Wait — `paper/cross_task/scripts/` is not on `sys.path` and has no `__init__.py`. Use the script-direct invocation:

```bash
python -c "import sys; sys.path.insert(0, 'paper/cross_task/scripts'); import load; df = load.load_corpus(); print(len(df), 'rows')"
```

Expected: prints something like `26637 rows` (or similar > 10000) without `FileNotFoundError`.

If load_corpus has different signature, fall back to the AST-only check:

```bash
python -c "import ast; ast.parse(open('paper/cross_task/scripts/load.py').read())"
```

Expected: no output (parse OK).

### Task 2b.1: Move `csv/scripts/` → `paper/cross_task/scripts/corpus/`

**Files:**
- Move: `csv/scripts/_loader.py` → `paper/cross_task/scripts/corpus/_loader.py`
- Move: `csv/scripts/01_overview.py` → `paper/cross_task/scripts/corpus/01_overview.py`
- Move: `csv/scripts/02_model_ranking.py` → `paper/cross_task/scripts/corpus/02_model_ranking.py`
- Move: `csv/scripts/03_axis_effects.py` → `paper/cross_task/scripts/corpus/03_axis_effects.py`
- Move: `csv/scripts/04_interactions.py` → `paper/cross_task/scripts/corpus/04_interactions.py`
- Move: `csv/scripts/05_variance_decomposition.py` → `paper/cross_task/scripts/corpus/05_variance_decomposition.py`
- Move: `csv/scripts/06_cluster_bootstrap_ci.py` → `paper/cross_task/scripts/corpus/06_cluster_bootstrap_ci.py`
- Move: `csv/scripts/07_within_task_correlations.py` → `paper/cross_task/scripts/corpus/07_within_task_correlations.py`
- Move: `csv/scripts/08_paired_head_to_head.py` → `paper/cross_task/scripts/corpus/08_paired_head_to_head.py`
- Move: `csv/scripts/09_capability_analysis.py` → `paper/cross_task/scripts/corpus/09_capability_analysis.py`
- Move: `csv/scripts/10_haiku_collapse.py` → `paper/cross_task/scripts/corpus/10_haiku_collapse.py`
- Move: `csv/out/figures/` (whole dir) → `paper/cross_task/figures/corpus/`
- Move: `csv/out/tables/` (whole dir) → `paper/cross_task/scripts/corpus/out/tables/`
- Modify: `paper/cross_task/scripts/corpus/_loader.py:6` — `CSV_PATH` constant

- [ ] **Step 1: Move the scripts**

```bash
git mv csv/scripts/_loader.py paper/cross_task/scripts/corpus/_loader.py
for f in csv/scripts/[0-9]*.py; do
  git mv "$f" "paper/cross_task/scripts/corpus/$(basename $f)"
done
```

- [ ] **Step 2: Move the outputs**

```bash
mkdir -p paper/cross_task/scripts/corpus/out
git mv csv/out/tables paper/cross_task/scripts/corpus/out/tables
# csv/out/figures may have many files — single git mv works:
git mv csv/out/figures paper/cross_task/figures/corpus
# csv/out/ directory may now be empty:
rmdir csv/out 2>/dev/null || true
```

- [ ] **Step 3: Delete the pyc cache (not tracked, just rm)**

```bash
rm -rf csv/scripts/__pycache__
rmdir csv/scripts 2>/dev/null || true
```

- [ ] **Step 4: Patch `_loader.py` (the linchpin)**

In `paper/cross_task/scripts/corpus/_loader.py:6`, change:

```python
CSV_PATH = Path(__file__).resolve().parent.parent / "results.csv"
```

to:

```python
CSV_PATH = Path(__file__).resolve().parents[3] / "data" / "corpus.csv"
```

`Path(__file__)` is now `paper/cross_task/scripts/corpus/_loader.py`. `parents[3]` reaches `paper/cross_task/`, then `/ data / corpus.csv`.

Then update `_loader.py`'s `save_table` and `fig_path` helpers (look around lines 30–60 for definitions like `OUT_DIR = ... / "out" / "tables"` and `FIG_DIR = ... / "out" / "figures"`). The new locations are:
- tables → `paper/cross_task/scripts/corpus/out/tables/` — this is `Path(__file__).resolve().parent / "out" / "tables"`
- figures → `paper/cross_task/figures/corpus/` — this is `Path(__file__).resolve().parents[3] / "figures" / "corpus"`

Read `_loader.py` first to see exactly how those constants are spelled, then edit them to those targets. The pattern: the script lives 3 levels deep under `paper/cross_task/`, so `parents[3]` reaches `paper/cross_task/`.

- [ ] **Step 5: Smoke-test `_loader.py`**

```bash
python -c "import sys; sys.path.insert(0, 'paper/cross_task/scripts/corpus'); import _loader; df = _loader.load(); print(len(df), 'rows', df.columns[:5].tolist())"
```

Expected: prints row count > 20000 and the first 5 columns. No `FileNotFoundError`.

- [ ] **Step 6: Smoke-test one downstream script**

```bash
python -c "import sys; sys.path.insert(0, 'paper/cross_task/scripts/corpus'); exec(open('paper/cross_task/scripts/corpus/01_overview.py').read())"
```

(The numbered scripts use `from _loader import ...`, so adding `corpus/` to `sys.path` resolves them.)

Expected: completes without `FileNotFoundError`. May produce output to stdout and write CSVs into `paper/cross_task/scripts/corpus/out/tables/`. If there is an error unrelated to paths (e.g., a stats library issue), flag it as pre-existing breakage in the audit and continue.

- [ ] **Step 7: AST-check the remaining 9 numbered scripts**

```bash
for f in paper/cross_task/scripts/corpus/0[2-9]_*.py paper/cross_task/scripts/corpus/10_*.py; do
  python -c "import ast; ast.parse(open('$f').read())" && echo "OK $f" || echo "FAIL $f"
done
```

Expected: 9 lines of `OK ...`. None of these scripts hardcode paths (they all go through `_loader.py`), so AST + the `_loader.py` smoke-test on Step 5 covers them.

### Task 2b.2: Move `paper/capability_eval/` → `paper/cross_task/scripts/capability/`

**Files:**
- Move: `paper/capability_eval/scripts/_capability_io.py` → `paper/cross_task/scripts/capability/_capability_io.py`
- Move: `paper/capability_eval/scripts/capability_analysis.py` → `paper/cross_task/scripts/capability/capability_analysis.py`
- Move: `paper/capability_eval/scripts/capability_anova.py` → `paper/cross_task/scripts/capability/capability_anova.py`
- Move: `paper/capability_eval/scripts/capability_clustering.py` → `paper/cross_task/scripts/capability/capability_clustering.py`
- Move: `paper/capability_eval/scripts/capability_frontier_lift.py` → `paper/cross_task/scripts/capability/capability_frontier_lift.py`
- Move: `paper/capability_eval/scripts/capability_regression.py` → `paper/cross_task/scripts/capability/capability_regression.py`
- Move: `paper/capability_eval/scripts/capability_response_surface.py` → `paper/cross_task/scripts/capability/capability_response_surface.py`
- Move: `paper/capability_eval/figures/*.png` → `paper/cross_task/figures/capability/`
- Move: `paper/capability_eval/analysis/*.json` → `paper/cross_task/analysis/` (merge with existing JSONs)
- Modify: `paper/cross_task/scripts/capability/_capability_io.py` — `RESULTS_CSV`, `CAPABILITY_CSV`, `ANALYSIS_DIR`, `FIG_DIR`
- Modify: `paper/cross_task/scripts/capability/capability_analysis.py` — `RESULTS`, `CAPABILITY`, `ANALYSIS_DIR`, `FIG_DIR`

- [ ] **Step 1: Move scripts**

```bash
git mv paper/capability_eval/scripts/_capability_io.py paper/cross_task/scripts/capability/_capability_io.py
for f in paper/capability_eval/scripts/capability_*.py; do
  git mv "$f" "paper/cross_task/scripts/capability/$(basename $f)"
done
rm -rf paper/capability_eval/scripts/__pycache__
rmdir paper/capability_eval/scripts 2>/dev/null || true
```

- [ ] **Step 2: Move figures and analysis**

```bash
git mv paper/capability_eval/figures/*.png paper/cross_task/figures/capability/
rmdir paper/capability_eval/figures 2>/dev/null || true

# Capability analysis JSONs go into the existing paper/cross_task/analysis/. Some filenames may clash:
ls paper/capability_eval/analysis/
# Output: capability_analysis.json capability_anova.json capability_clustering.json
#         capability_frontier_lift.json capability_regression.json response_surface_by_tier.json
ls paper/cross_task/analysis/ | grep capability
# Output: capability_analysis.json (clash!)
```

If any names clash with `paper/cross_task/analysis/` (notably `capability_analysis.json` already exists there from the v2 reanalysis), prefix the moved capability files with `capability_eval_`:

```bash
for f in paper/capability_eval/analysis/*.json; do
  base=$(basename "$f")
  if [ -f "paper/cross_task/analysis/$base" ]; then
    git mv "$f" "paper/cross_task/analysis/capability_eval_$base"
  else
    git mv "$f" "paper/cross_task/analysis/$base"
  fi
done
rmdir paper/capability_eval/analysis 2>/dev/null || true
```

- [ ] **Step 3: Patch `_capability_io.py`**

In `paper/cross_task/scripts/capability/_capability_io.py:18-22`, change:

```python
ROOT = Path(__file__).resolve().parents[2]
RESULTS_CSV = ROOT / "cross_task" / "results.csv"
CAPABILITY_CSV = ROOT / "cross_task" / "model_capability.csv"
ANALYSIS_DIR = ROOT / "capability_eval" / "analysis"
FIG_DIR = ROOT / "capability_eval" / "figures"
```

to:

```python
# Script lives at paper/cross_task/scripts/capability/_capability_io.py
# parents[3] = repo root; parents[2] = paper/; parents[1] = paper/cross_task/
ROOT = Path(__file__).resolve().parents[1]  # paper/cross_task
RESULTS_CSV = ROOT / "data" / "results.csv"
CAPABILITY_CSV = ROOT / "data" / "model_capability.csv"
ANALYSIS_DIR = ROOT / "analysis"
FIG_DIR = ROOT / "figures" / "capability"
```

- [ ] **Step 4: Patch `capability_analysis.py`**

In `paper/cross_task/scripts/capability/capability_analysis.py:24-28`, apply the same depth/destination fix:

```python
ROOT = Path(__file__).resolve().parents[1]  # paper/cross_task
RESULTS = ROOT / "data" / "results.csv"
CAPABILITY = ROOT / "data" / "model_capability.csv"
ANALYSIS_DIR = ROOT / "analysis"
FIG_DIR = ROOT / "figures" / "capability"
```

If after move `capability_analysis.py` writes to a JSON whose name collided in Step 2 (we renamed `capability_analysis.json` → `capability_eval_capability_analysis.json`), update the output filename literal in this script to match. Search for `out_json = ANALYSIS_DIR / "capability_analysis.json"` and replace with `"capability_eval_capability_analysis.json"`.

- [ ] **Step 5: Patch the other 5 capability scripts**

`capability_anova.py`, `capability_clustering.py`, `capability_frontier_lift.py`, `capability_regression.py`, `capability_response_surface.py` all `from _capability_io import ...`, so they pick up the patched constants automatically. They may still have inline path literals for output JSON names — grep:

```bash
grep -nE "ANALYSIS_DIR / \"|FIG_DIR / \"" paper/cross_task/scripts/capability/capability_*.py
```

For each output filename, check if Step 2 renamed its analysis JSON. If so, update the inline literal to match the renamed file.

- [ ] **Step 6: Smoke-test capability**

```bash
python -c "import sys; sys.path.insert(0, 'paper/cross_task/scripts/capability'); import _capability_io; df = _capability_io.load_joined(); print(len(df), 'rows', df['model'].nunique(), 'models')"
```

Expected: prints row count and model count without `FileNotFoundError`.

- [ ] **Step 7: AST-check the rest**

```bash
for f in paper/cross_task/scripts/capability/capability_*.py; do
  python -c "import ast; ast.parse(open('$f').read())" && echo "OK $f" || echo "FAIL $f"
done
```

Expected: 6 lines of `OK ...`.

### Task 2b.3: Move `paper/newer_analysis/` → `paper/cross_task/scripts/newer/`

**Files:**
- Move: `paper/newer_analysis/scripts/01_mixed_effects.py` → `paper/cross_task/scripts/newer/01_mixed_effects.py`
- Move: `paper/newer_analysis/scripts/02_task_model_interaction.py` → `paper/cross_task/scripts/newer/02_task_model_interaction.py`
- Move: `paper/newer_analysis/scripts/03_multiple_testing.py` → `paper/cross_task/scripts/newer/03_multiple_testing.py`
- Move: `paper/newer_analysis/scripts/04_incentive_traces.py` → `paper/cross_task/scripts/newer/04_incentive_traces.py`
- Move: `paper/newer_analysis/scripts/05_refusal_scan.py` → `paper/cross_task/scripts/newer/05_refusal_scan.py`
- Move: `paper/newer_analysis/scripts/05_spearman_bootstrap.py` → `paper/cross_task/scripts/newer/05_spearman_bootstrap.py`
- Move: `paper/newer_analysis/scripts/incentive_forest.py` → `paper/cross_task/scripts/newer/incentive_forest.py`
- Move: `paper/newer_analysis/figures/*.{pdf,png}` → `paper/cross_task/figures/newer/`
- Move: `paper/newer_analysis/out/` (entire tree) → `paper/cross_task/scripts/newer/out/`
- Modify each script's path constants

- [ ] **Step 1: Move scripts**

```bash
for f in paper/newer_analysis/scripts/*.py; do
  git mv "$f" "paper/cross_task/scripts/newer/$(basename $f)"
done
rmdir paper/newer_analysis/scripts 2>/dev/null || true
```

- [ ] **Step 2: Move figures and outputs**

```bash
git mv paper/newer_analysis/figures/incentive_forest.pdf paper/cross_task/figures/newer/
git mv paper/newer_analysis/figures/incentive_forest.png paper/cross_task/figures/newer/
rmdir paper/newer_analysis/figures 2>/dev/null || true

git mv paper/newer_analysis/out paper/cross_task/scripts/newer/out
```

- [ ] **Step 3: Patch `01_mixed_effects.py`**

In `paper/cross_task/scripts/newer/01_mixed_effects.py:27-29`, change:

```python
ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "cross_task" / "results.csv"
OUT = Path(__file__).resolve().parents[1] / "out"
```

to:

```python
# Script lives at paper/cross_task/scripts/newer/01_mixed_effects.py
ROOT = Path(__file__).resolve().parents[1]  # paper/cross_task
CSV = ROOT / "data" / "results.csv"
OUT = Path(__file__).resolve().parent / "out"
```

- [ ] **Step 4: Patch `02_task_model_interaction.py`**

Same change as Step 3, applied at `paper/cross_task/scripts/newer/02_task_model_interaction.py:23-25`.

- [ ] **Step 5: Patch `03_multiple_testing.py`**

In `paper/cross_task/scripts/newer/03_multiple_testing.py:17`, change:

```python
OUT = Path(__file__).resolve().parents[1] / "out"
```

to:

```python
OUT = Path(__file__).resolve().parent / "out"
```

(This script doesn't read the CSV — it works from hand-coded p-values per its docstring — so no `CSV` constant to update.)

- [ ] **Step 6: Patch `04_incentive_traces.py`**

In `paper/cross_task/scripts/newer/04_incentive_traces.py:25-27`, change:

```python
LOG = Path("/home/borneans/Documents/TAICI/manipulation-bench/paper/task1_bargaining/eval_log.eval")
OUT = Path(__file__).resolve().parents[1] / "out" / "04_traces"
```

to:

```python
ROOT = Path(__file__).resolve().parents[3]  # repo root
LOG = ROOT / "paper" / "task1_bargaining" / "eval_log.eval"
OUT = Path(__file__).resolve().parent / "out" / "04_traces"
```

This also fixes the original "hardcoded absolute path" smell — the script now works for any clone of the repo.

- [ ] **Step 7: Patch `05_refusal_scan.py`**

In `paper/cross_task/scripts/newer/05_refusal_scan.py:25-26`, change:

```python
ROOT = Path("/home/borneans/Documents/TAICI/manipulation-bench/paper")
OUT = Path(__file__).resolve().parents[1] / "out" / "05_refusals"
```

to:

```python
ROOT = Path(__file__).resolve().parents[3] / "paper"  # repo_root/paper
OUT = Path(__file__).resolve().parent / "out" / "05_refusals"
```

Same hardcoded-absolute-path fix as Step 6.

- [ ] **Step 8: Patch `05_spearman_bootstrap.py`**

In `paper/cross_task/scripts/newer/05_spearman_bootstrap.py:38-40`, change:

```python
ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "cross_task" / "results.csv"
OUT = Path(__file__).resolve().parents[1] / "out"
```

to:

```python
ROOT = Path(__file__).resolve().parents[1]  # paper/cross_task
CSV = ROOT / "data" / "results.csv"
OUT = Path(__file__).resolve().parent / "out"
```

- [ ] **Step 9: Patch `incentive_forest.py`**

In `paper/cross_task/scripts/newer/incentive_forest.py:23-26`, change:

```python
REPO = Path(__file__).resolve().parents[3]
CSV = REPO / "paper" / "cross_task" / "results.csv"
OUT_CSV = REPO / "paper" / "newer_analysis" / "out" / "incentive_forest.csv"
FIG_DIR = REPO / "paper" / "newer_analysis" / "figures"
```

to:

```python
# Script lives at paper/cross_task/scripts/newer/incentive_forest.py — parents[3] still equals repo root
REPO = Path(__file__).resolve().parents[3]
CSV = REPO / "paper" / "cross_task" / "data" / "results.csv"
OUT_CSV = Path(__file__).resolve().parent / "out" / "incentive_forest.csv"
FIG_DIR = REPO / "paper" / "cross_task" / "figures" / "newer"
```

- [ ] **Step 10: Smoke-test the cheap newer scripts**

```bash
# 03_multiple_testing.py is fastest (no CSV read):
python paper/cross_task/scripts/newer/03_multiple_testing.py
# Expected: writes paper/cross_task/scripts/newer/out/03_multiple_testing.csv, prints summary
```

```bash
# 02_task_model_interaction.py reads CSV but is medium-cost:
python paper/cross_task/scripts/newer/02_task_model_interaction.py
# Expected: writes paper/cross_task/scripts/newer/out/02_*; prints F-stat
```

If either errors with `FileNotFoundError`, the path patch is wrong — fix before continuing.

- [ ] **Step 11: AST-check the expensive newer scripts**

```bash
for f in 01_mixed_effects.py 04_incentive_traces.py 05_refusal_scan.py 05_spearman_bootstrap.py incentive_forest.py; do
  python -c "import ast; ast.parse(open('paper/cross_task/scripts/newer/$f').read())" && echo "OK $f" || echo "FAIL $f"
done
```

Expected: 5 lines of `OK ...`. (These are LLM-call / multi-minute-bootstrap scripts; we accept AST-only per the spec's smoke-test rule.)

Also grep for residual old paths inside them:

```bash
grep -nE "newer_analysis|capability_eval|^.*\"csv/" paper/cross_task/scripts/newer/*.py
```

Expected: no matches. If any, patch.

### Task 2c: Commit Phase 2

- [ ] **Step 1: Verify the working tree is consistent**

```bash
git status --short | head -50
```

Expected: a long list of `R` (renames) plus a few `M` (the path patches in `paper/cross_task/scripts/load.py`, `_loader.py`, `_capability_io.py`, etc.). No untracked `.py` files in moved dirs.

- [ ] **Step 2: Verify nothing references old paths**

```bash
grep -rnE "paper/newer_analysis|paper/capability_eval|^[^:]+:[0-9]+:\s*.*[\"']csv/" paper/cross_task/scripts/ 2>/dev/null
```

Expected: no matches inside `paper/cross_task/scripts/`. (Matches inside finding markdown docs in `paper/cross_task/` are fine — those are handled in Phase 4.)

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
Phase 2: consolidate cross-cutting scripts under paper/cross_task/

Move csv/scripts/, paper/capability_eval/scripts/, and
paper/newer_analysis/scripts/ into paper/cross_task/scripts/{corpus,
capability,newer}/. Move associated figures, JSON outputs, and CSV
tables. Move canonical CSVs from paper/cross_task/*.csv into
paper/cross_task/data/. Patch every script's hardcoded path constants
to match the new layout. Smoke-tested where cheap; AST-checked
otherwise.
EOF
)"
```

---

## Phase 3 — Sub-namespace existing `paper/cross_task/scripts/*.py`

The four directories `corpus/`, `capability/`, `newer/` now sit inside `paper/cross_task/scripts/` alongside the original ~20 .py files. Move those into a sibling `cross_task/` subdirectory so all four sources are at the same level.

### Task 3.1: Move existing scripts into `cross_task/` subdir

**Files:**
- Move: every `paper/cross_task/scripts/*.py` → `paper/cross_task/scripts/cross_task/*.py`
- Move: `paper/cross_task/scripts/README.md` → `paper/cross_task/scripts/cross_task/README.md`

- [ ] **Step 1: Create the directory and move**

```bash
mkdir -p paper/cross_task/scripts/cross_task
git mv paper/cross_task/scripts/README.md paper/cross_task/scripts/cross_task/README.md
for f in paper/cross_task/scripts/*.py; do
  git mv "$f" "paper/cross_task/scripts/cross_task/$(basename $f)"
done
```

- [ ] **Step 2: Re-patch the path constants we already touched in Task 2a.3**

Scripts now live one level deeper. Their previous `REPO_ROOT = Path(__file__).resolve().parents[N]` constants need recomputing.

Specifically:
- `paper/cross_task/scripts/cross_task/load.py`: was `parents[3]` for repo root, now `parents[4]`.
- `paper/cross_task/scripts/cross_task/append_t6_to_csv.py`, `append_t6_to_results.py`, `eval_logs_to_csv.py`: same shift.

Find all `parents[` occurrences:

```bash
grep -nE "parents\[[0-9]+\]|REPO_ROOT|REPO " paper/cross_task/scripts/cross_task/*.py
```

For every `Path(__file__).resolve().parents[N]` in this directory, increment `N` by 1. The script depth shifted from 3 levels under repo root (`paper/cross_task/scripts/foo.py`) to 4 levels (`paper/cross_task/scripts/cross_task/foo.py`).

Apply the increments file-by-file using Edit.

- [ ] **Step 3: Smoke-test load.py one more time**

```bash
python -c "import sys; sys.path.insert(0, 'paper/cross_task/scripts/cross_task'); import load; df = load.load_corpus(); print(len(df), 'rows')"
```

Expected: prints row count, no error.

- [ ] **Step 4: AST-check the rest**

```bash
for f in paper/cross_task/scripts/cross_task/*.py; do
  python -c "import ast; ast.parse(open('$f').read())" && echo "OK $f" || echo "FAIL $f"
done
```

Expected: ~20 `OK` lines.

- [ ] **Step 5: Grep for residual old paths**

```bash
grep -rnE "paper/cross_task/results\.csv|paper/cross_task/model_capability\.csv|paper/cross_task/results\.csv\.bak" paper/cross_task/scripts/
```

Expected: no matches. (All references should now go via `paper/cross_task/data/`.)

- [ ] **Step 6: Commit Phase 3**

```bash
git add -A
git commit -m "Phase 3: sub-namespace existing paper/cross_task/scripts/*.py into cross_task/"
```

---

## Phase 4 — Move findings docs

### Task 4.1: Move + rename findings docs

**Files:**
- Move: `csv/FINDINGS.md` → `paper/cross_task/findings/corpus.md`
- Move: `paper/cross_task/EXPLORATORY_FINDINGS.md` → `paper/cross_task/findings/exploratory.md`
- Move: `paper/cross_task/FINDINGS_FROM_FIRST_PRINCIPLES.md` → `paper/cross_task/findings/first_principles.md`
- Move: `paper/cross_task/REANALYSIS_NOTES.md` → `paper/cross_task/findings/reanalysis_notes.md`
- Move: `paper/capability_eval/FINDINGS.md` → `paper/cross_task/findings/capability_eval.md`
- Move: `paper/capability_eval/README.md` → `paper/cross_task/findings/capability_eval_README.md`
- Move: `paper/newer_analysis/FINDINGS.md` → `paper/cross_task/findings/newer_analysis.md`
- Move: `paper/newer_analysis/FINDINGS_INCENTIVE_RECODE_PAPER_IMPACT.md` → `paper/cross_task/findings/incentive_recode_impact.md`
- Move: `paper/newer_analysis/SPEARMAN_BOOTSTRAP_FINDINGS.md` → `paper/cross_task/findings/spearman_bootstrap.md`
- Move: `paper/newer_analysis/METHODS.md` → `paper/cross_task/findings/methods.md`
- Move: `paper/newer_analysis/REFUSAL_SCAN.md` → `paper/cross_task/findings/refusal_scan.md`
- Move: `paper/newer_analysis/INCENTIVE_TRACES.md` → `paper/cross_task/findings/incentive_traces.md`

- [ ] **Step 1: Create findings/ and move**

```bash
mkdir -p paper/cross_task/findings

git mv csv/FINDINGS.md paper/cross_task/findings/corpus.md
git mv paper/cross_task/EXPLORATORY_FINDINGS.md paper/cross_task/findings/exploratory.md
git mv paper/cross_task/FINDINGS_FROM_FIRST_PRINCIPLES.md paper/cross_task/findings/first_principles.md
git mv paper/cross_task/REANALYSIS_NOTES.md paper/cross_task/findings/reanalysis_notes.md
git mv paper/capability_eval/FINDINGS.md paper/cross_task/findings/capability_eval.md
git mv paper/capability_eval/README.md paper/cross_task/findings/capability_eval_README.md
git mv paper/newer_analysis/FINDINGS.md paper/cross_task/findings/newer_analysis.md
git mv paper/newer_analysis/FINDINGS_INCENTIVE_RECODE_PAPER_IMPACT.md paper/cross_task/findings/incentive_recode_impact.md
git mv paper/newer_analysis/SPEARMAN_BOOTSTRAP_FINDINGS.md paper/cross_task/findings/spearman_bootstrap.md
git mv paper/newer_analysis/METHODS.md paper/cross_task/findings/methods.md
git mv paper/newer_analysis/REFUSAL_SCAN.md paper/cross_task/findings/refusal_scan.md
git mv paper/newer_analysis/INCENTIVE_TRACES.md paper/cross_task/findings/incentive_traces.md
```

- [ ] **Step 2: Verify**

```bash
ls paper/cross_task/findings/
```

Expected: 12 markdown files.

### Task 4.2: Update internal links inside findings docs

Each finding doc has links to its scripts and figures. After the move, these links break. Repair them.

- [ ] **Step 1: Find all internal links**

```bash
grep -nE "\]\(.*\.(py|md|png|pdf|csv)\)|\]\(\.\./.*\)" paper/cross_task/findings/*.md
```

This produces a list of `(file, line, link)` triples. For each:
- Links to `scripts/*.py` (relative or `csv/scripts/`, `paper/newer_analysis/scripts/`, etc.) → repoint to the new script location.
- Links to `figures/*.png` → repoint to `paper/cross_task/figures/{corpus,capability,newer}/`.
- Links to `out/*.csv` (output tables) → repoint to the script-paired `out/` subdir.
- Links to other findings docs (cross-references like `FINDINGS_CONSOLIDATED.md` referencing `FINDINGS.md`) → repoint to `paper/cross_task/findings/<new-name>.md`.

**Mapping table** (use this to mechanically rewrite):

| Old reference | New reference |
|---|---|
| `csv/FINDINGS.md` | `paper/cross_task/findings/corpus.md` |
| `csv/scripts/<X>.py` | `paper/cross_task/scripts/corpus/<X>.py` |
| `csv/results.csv` | `paper/cross_task/data/corpus.csv` |
| `csv/out/figures/<X>.png` | `paper/cross_task/figures/corpus/<X>.png` |
| `csv/out/tables/<X>.csv` | `paper/cross_task/scripts/corpus/out/tables/<X>.csv` |
| `paper/newer_analysis/FINDINGS.md` | `paper/cross_task/findings/newer_analysis.md` |
| `paper/newer_analysis/<other>.md` | `paper/cross_task/findings/<lowercase-name>.md` |
| `paper/newer_analysis/scripts/<X>.py` | `paper/cross_task/scripts/newer/<X>.py` |
| `paper/newer_analysis/figures/<X>.{pdf,png}` | `paper/cross_task/figures/newer/<X>.{pdf,png}` |
| `paper/newer_analysis/out/<X>` | `paper/cross_task/scripts/newer/out/<X>` |
| `paper/capability_eval/FINDINGS.md` | `paper/cross_task/findings/capability_eval.md` |
| `paper/capability_eval/README.md` | `paper/cross_task/findings/capability_eval_README.md` |
| `paper/capability_eval/scripts/<X>.py` | `paper/cross_task/scripts/capability/<X>.py` |
| `paper/capability_eval/figures/<X>.png` | `paper/cross_task/figures/capability/<X>.png` |
| `paper/capability_eval/analysis/<X>.json` | `paper/cross_task/analysis/<X>.json` (or `capability_eval_<X>.json` if renamed in Task 2b.2 Step 2) |
| `paper/cross_task/EXPLORATORY_FINDINGS.md` | `paper/cross_task/findings/exploratory.md` |
| `paper/cross_task/FINDINGS_FROM_FIRST_PRINCIPLES.md` | `paper/cross_task/findings/first_principles.md` |
| `paper/cross_task/REANALYSIS_NOTES.md` | `paper/cross_task/findings/reanalysis_notes.md` |
| `paper/cross_task/results.csv` | `paper/cross_task/data/results.csv` |
| `paper/cross_task/model_capability.csv` | `paper/cross_task/data/model_capability.csv` |

- [ ] **Step 2: Apply rewrites**

For each markdown file in `paper/cross_task/findings/`, walk through the links found in Step 1 and apply the mapping table. Use Edit.

A practical way: take the longest old-path match first (e.g., `paper/newer_analysis/scripts/05_spearman_bootstrap.py`) before the shorter ones (e.g., `paper/newer_analysis/`), to avoid partial replacements. Within a single doc, `replace_all=true` is safe for a fully-qualified old path.

- [ ] **Step 3: Verify no stale paths remain**

```bash
grep -rnE "csv/(scripts|out|FINDINGS|results)|paper/(newer_analysis|capability_eval)/" paper/cross_task/findings/
```

Expected: no matches.

### Task 4.3: Move root-level findings docs

**Files:**
- Move: `FINDINGS.md` (repo root) → `paper/cross_task/findings/legacy_pre_paper.md`
- Move: `FINDINGS_CONSOLIDATED.md` → `paper/cross_task/findings/consolidated.md`
- Move: `findings_notes.md` → `paper/cross_task/findings/notes.md`

- [ ] **Step 1: Move**

```bash
git mv FINDINGS.md paper/cross_task/findings/legacy_pre_paper.md
git mv FINDINGS_CONSOLIDATED.md paper/cross_task/findings/consolidated.md
git mv findings_notes.md paper/cross_task/findings/notes.md
```

- [ ] **Step 2: Repeat the link-rewrite (same mapping table as Task 4.2)**

`consolidated.md` and `notes.md` are the synthesis docs — they cross-reference every other FINDINGS file by old path. Run the grep and apply the table.

```bash
grep -nE "\]\(.*\.(py|md|png|pdf|csv)\)" paper/cross_task/findings/{legacy_pre_paper,consolidated,notes}.md
```

Apply edits.

- [ ] **Step 3: Verify**

```bash
grep -rnE "csv/(scripts|out|FINDINGS|results)|paper/(newer_analysis|capability_eval)/|^FINDINGS\.md|^FINDINGS_CONSOLIDATED\.md|^findings_notes\.md" paper/cross_task/findings/
```

Expected: no matches.

### Task 4.4: Write `paper/cross_task/findings/README.md` (the new index)

**Files:**
- Create: `paper/cross_task/findings/README.md`

- [ ] **Step 1: Write the index**

Create the file with this content:

```markdown
# Findings index

Cross-cutting findings from the manipulation-bench project. Per-task findings
live with their tasks (`paper/task<N>/results.md`).

## Synthesis (start here)

- [`consolidated.md`](consolidated.md) — master synthesis with conflict resolution across all 4 sources
- [`notes.md`](notes.md) — mid-level synthesis: 5 robust claims + 5 conflicts resolved
- [`exploratory.md`](exploratory.md) — post-PREREG analyses on combined eval logs
- [`first_principles.md`](first_principles.md) — independent bottom-up reanalysis of `data/results.csv`

## Corpus analysis (the 26k-row trajectory CSV)

- [`corpus.md`](corpus.md) — full corpus analysis with cluster-bootstrap CIs
  - Scripts: [`../scripts/corpus/`](../scripts/corpus/)
  - Figures: [`../figures/corpus/`](../figures/corpus/)
  - Data: [`../data/corpus.csv`](../data/corpus.csv)

## Newer statistical analyses (mixed-effects, multi-test, bootstrap)

- [`newer_analysis.md`](newer_analysis.md) — three statistical gap-fillers + incentive forest plot
- [`incentive_recode_impact.md`](incentive_recode_impact.md) — paper.tex edits required after Bargaining incentive label inversion
- [`spearman_bootstrap.md`](spearman_bootstrap.md) — bootstrap CIs on the rank-instability headline
- [`methods.md`](methods.md) — terse list of every statistical procedure
- [`refusal_scan.md`](refusal_scan.md) — refusal/non-compliance scan across canonical roster
- [`incentive_traces.md`](incentive_traces.md) — reasoning traces for high-incentive deterrence
  - Scripts: [`../scripts/newer/`](../scripts/newer/)
  - Figures: [`../figures/newer/`](../figures/newer/)

## Capability axis (LMArena ELO, tier, generation)

- [`capability_eval.md`](capability_eval.md) — post-hoc capability axis analysis
- [`capability_eval_README.md`](capability_eval_README.md) — overview + scope
  - Scripts: [`../scripts/capability/`](../scripts/capability/)
  - Figures: [`../figures/capability/`](../figures/capability/)

## v2 paper reanalysis

- [`reanalysis_notes.md`](reanalysis_notes.md) — v2 statistical reanalysis notes
  - Scripts: [`../scripts/cross_task/`](../scripts/cross_task/)
  - Analysis JSONs: [`../analysis/`](../analysis/)

## Legacy pre-paper

- [`legacy_pre_paper.md`](legacy_pre_paper.md) — frozen pre-paper exploratory log (4-model roster, last runs 2026-04-15/16)
```

### Task 4.5: Commit Phase 4

- [ ] **Step 1: Verify findings/ is complete**

```bash
ls paper/cross_task/findings/ | sort
```

Expected: 13 files (12 moved + 1 new README.md).

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "Phase 4: move findings docs into paper/cross_task/findings/ + index"
```

---

## Phase 5 — Cleanup, references, CLAUDE.md

### Task 5.1: Delete now-empty source directories

- [ ] **Step 1: Verify empty**

```bash
find csv paper/newer_analysis paper/capability_eval -type f 2>/dev/null
```

Expected: no output (all files moved).

If any files remain, audit them. They're either:
- pyc caches (delete)
- something we missed (route to the appropriate target dir)

- [ ] **Step 2: Delete the directories**

```bash
rm -rf csv paper/newer_analysis paper/capability_eval
```

(`rm -rf` is fine here — these dirs should be empty of tracked files; `git status` will confirm. Don't `git rm -rf` because everything inside is already moved/staged.)

- [ ] **Step 3: Verify**

```bash
git status --short | grep -E "^.D" | head
ls csv paper/newer_analysis paper/capability_eval 2>&1 | head
```

Expected: no `D` (deleted) entries — the renames in Phase 2/4 already accounted for everything. The `ls` should report "No such file or directory" for all three.

### Task 5.2: Update `manipulation-bench/CLAUDE.md`

Many references to old paths. Apply this mapping:

| Old | New |
|---|---|
| `paper/cross_task/scripts/<X>.py` | `paper/cross_task/scripts/cross_task/<X>.py` |
| `paper/newer_analysis/` | `paper/cross_task/findings/` (for docs) or `paper/cross_task/scripts/newer/` (for scripts) |
| `paper/capability_eval/` | `paper/cross_task/findings/` (for docs) or `paper/cross_task/scripts/capability/` (for scripts) |
| `csv/` | `paper/cross_task/scripts/corpus/` (for scripts) or `paper/cross_task/findings/corpus.md` (for the FINDINGS doc) or `paper/cross_task/data/corpus.csv` (for the CSV) |
| `FINDINGS.md` (root reference) | `paper/cross_task/findings/legacy_pre_paper.md` |
| `paper/cross_task/EXPLORATORY_FINDINGS.md` | `paper/cross_task/findings/exploratory.md` |
| `paper/cross_task/FINDINGS_FROM_FIRST_PRINCIPLES.md` | `paper/cross_task/findings/first_principles.md` |
| `paper/cross_task/results.csv` | `paper/cross_task/data/results.csv` |
| `paper/cross_task/model_capability.csv` | `paper/cross_task/data/model_capability.csv` |

- [ ] **Step 1: Find all references**

```bash
grep -nE "csv/|paper/newer_analysis|paper/capability_eval|paper/cross_task/(scripts|results\.csv|model_capability|EXPLORATORY|FINDINGS_FROM)" CLAUDE.md
```

- [ ] **Step 2: Apply the mapping using Edit, one match at a time.**

Pay special attention to:
- The "Paper analysis scripts" section, which lists per-task script directories — those are out of scope, leave them alone, but the cross-task list needs updating to use `paper/cross_task/scripts/cross_task/` (and capability_eval / newer_analysis bullets need to be removed or repointed).
- The "Prior experimental results" section that says "See `FINDINGS.md`" — repoint to `paper/cross_task/findings/legacy_pre_paper.md`.
- Any reproduction commands.

- [ ] **Step 3: Verify**

```bash
grep -nE "csv/|paper/newer_analysis|paper/capability_eval" CLAUDE.md
```

Expected: no matches (any remaining matches indicate a missed reference; fix it).

### Task 5.3: Update `paper/cross_task/SUMMARY.md` and `ANALYSIS_INVENTORY.md`

- [ ] **Step 1: Update SUMMARY.md**

```bash
grep -nE "scripts/|FINDINGS|results\.csv|capability_eval|newer_analysis|EXPLORATORY" paper/cross_task/SUMMARY.md
```

For each match, apply the mapping table from Task 5.2. The reproduction block in particular needs every `python paper/cross_task/scripts/<X>.py` updated to `python paper/cross_task/scripts/cross_task/<X>.py`.

- [ ] **Step 2: Update ANALYSIS_INVENTORY.md**

Same procedure for `paper/cross_task/ANALYSIS_INVENTORY.md`.

### Task 5.4: Check `paper/paper.tex` for figure-path references

- [ ] **Step 1: Grep**

```bash
grep -nE "newer_analysis|capability_eval|csv/" paper/paper.tex
```

- [ ] **Step 2: For each match**

Apply mapping. Most likely candidates:
- `\includegraphics{paper/newer_analysis/figures/incentive_forest.pdf}` → `paper/cross_task/figures/newer/incentive_forest.pdf`
- Any `\input{paper/cross_task/EXPLORATORY_FINDINGS.md}`-style include (unlikely, but possible).

If no matches, skip.

### Task 5.5: Final smoke battery

Re-verify a representative script from each consolidated source still runs.

- [ ] **Step 1: Corpus smoke**

```bash
python -c "import sys; sys.path.insert(0, 'paper/cross_task/scripts/corpus'); import _loader; print(_loader.load().shape)"
```

Expected: `(>20000, ~30)` shape.

- [ ] **Step 2: Capability smoke**

```bash
python -c "import sys; sys.path.insert(0, 'paper/cross_task/scripts/capability'); import _capability_io; print(_capability_io.load_joined().shape)"
```

Expected: shape printed without error.

- [ ] **Step 3: Newer smoke**

```bash
python paper/cross_task/scripts/newer/03_multiple_testing.py
```

Expected: writes to new `out/`, prints summary.

- [ ] **Step 4: Cross-task (sub-namespaced) smoke**

```bash
python -c "import sys; sys.path.insert(0, 'paper/cross_task/scripts/cross_task'); import load; print(load.load_corpus().shape)"
```

Expected: shape printed without error.

- [ ] **Step 5: Verify no stale paths anywhere**

```bash
grep -rnE "csv/results\.csv|paper/cross_task/results\.csv\b|paper/newer_analysis|paper/capability_eval" \
  CLAUDE.md \
  paper/paper.tex \
  paper/cross_task/ \
  docs/superpowers/specs/ \
  docs/superpowers/plans/
```

The only matches allowed are in:
- `docs/superpowers/specs/2026-05-04-findings-and-scripts-consolidation-design.md` (it documents the moves)
- `docs/superpowers/plans/2026-05-04-findings-and-scripts-consolidation.md` (this plan)
- `docs/superpowers/plans/consolidation-audit.md` (the Phase 1 inventory)

Anywhere else is a missed reference. Fix.

### Task 5.6: Commit Phase 5

- [ ] **Step 1: Final commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
Phase 5: cleanup, update CLAUDE.md and SUMMARY references

Delete now-empty csv/, paper/newer_analysis/, paper/capability_eval/.
Update CLAUDE.md, paper/cross_task/SUMMARY.md, ANALYSIS_INVENTORY.md,
and paper/paper.tex to reference the new locations.
EOF
)"
```

- [ ] **Step 2: Final verify**

```bash
git log --oneline -6
```

Expected: 5 phase commits at the top, with the spec commits below them.

```bash
ls paper/cross_task/
```

Expected:
```
ANALYSIS_INVENTORY.md  analysis/  cross_task_aggregate.md  data/  figures/
findings/  scripts/  SUMMARY.md
```

(No more `EXPLORATORY_FINDINGS.md`, `FINDINGS_FROM_FIRST_PRINCIPLES.md`, `REANALYSIS_NOTES.md`, `results.csv`, `model_capability.csv` at the dir root — they all moved.)

```bash
ls paper/cross_task/scripts/
```

Expected: `capability/  corpus/  cross_task/  newer/`.

---

## Done

The repo now has one place to look:

- **All cross-cutting findings:** `paper/cross_task/findings/`
- **All cross-cutting scripts:** `paper/cross_task/scripts/{cross_task,corpus,capability,newer}/`
- **All canonical CSVs:** `paper/cross_task/data/`
- **All cross-cutting figures:** `paper/cross_task/figures/{,corpus,capability,newer}/`
- **Per-task scripts unchanged:** `paper/task<N>/scripts/` (out of scope)

Five commits, bisectable. Every script smoke-tested or AST-checked.
