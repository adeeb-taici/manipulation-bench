# eval_logs_to_csv Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a re-runnable script that flattens the 5-task paper eval logs (canonical + extended, 9 logs total) into a single tidy CSV at `paper/cross_task/results.csv`, one row per sample, with identity/setup columns plus all scorer scores flattened.

**Architecture:** Thin wrapper around `experiments.reanalysis.load._row_from_sample` (which already handles axis canonicalization, model remapping, and the headline `manipulation_metric`). The wrapper adds: (a) extra setup columns (epoch, scenario_id, manipulator, num_agents, topology, topic, model_mapping JSON), (b) full flattening of every `sample.scores[scorer].value` into `<scorer>__<key>` columns, and (c) `task` / `variant` / `log_path` provenance from path inference.

**Tech Stack:** Python 3.14, `inspect_ai.log.read_eval_log`, pandas. No new dependencies — everything is already in use by `experiments/reanalysis/load.py`.

---

## File Structure

- **Create:** `paper/cross_task/scripts/eval_logs_to_csv.py` — the script
- **Create:** `tests/test_eval_logs_to_csv.py` — pytest tests with synthetic eval-log-shaped objects (no real `.eval` file needed for unit tests)
- **Output (not tracked here, written by the script):** `paper/cross_task/results.csv`

The script is self-contained — one file, ~200 LOC. Helpers from `experiments/reanalysis/load.py` are imported, not duplicated.

---

## Task 1: Scaffold the script and CLI

**Files:**
- Create: `paper/cross_task/scripts/eval_logs_to_csv.py`

- [ ] **Step 1: Create the file with imports, default log paths, and CLI skeleton**

```python
"""Flatten paper eval logs into a single tidy CSV.

One row per sample (rollout) across the 5 paper tasks × {canonical, extended}
log variants. Columns: identity/setup + normalized manipulation_metric +
flattened <scorer>__<key> scores.

Re-runnable. Does not modify or delete any source data.

Usage:
    python paper/cross_task/scripts/eval_logs_to_csv.py
    python paper/cross_task/scripts/eval_logs_to_csv.py -o foo.csv
    python paper/cross_task/scripts/eval_logs_to_csv.py --logs 'logs/*.eval'
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from inspect_ai.log import read_eval_log

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from experiments.reanalysis.load import _row_from_sample, _flatten_metadata  # noqa: E402

DEFAULT_LOGS = [
    REPO_ROOT / "paper/task1_bargaining/eval_log.eval",
    REPO_ROOT / "paper/task1_bargaining/eval_log_extended.eval",
    REPO_ROOT / "paper/task2_debate/eval_log.eval",
    REPO_ROOT / "paper/task3_village/eval_log.eval",
    REPO_ROOT / "paper/task3_village/eval_log_extended.eval",
    REPO_ROOT / "paper/task4_sales/eval_log.eval",
    REPO_ROOT / "paper/task4_sales/eval_log_extended.eval",
    REPO_ROOT / "paper/task5_committee/eval_log.eval",
    REPO_ROOT / "paper/task5_committee/eval_log_extended.eval",
]

DEFAULT_OUTPUT = REPO_ROOT / "paper/cross_task/results.csv"

TASK_DIR_TO_KEY = {
    "task1_bargaining": "bargaining",
    "task2_debate": "debate",
    "task3_village": "village",
    "task4_sales": "sales",
    "task5_committee": "committee",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--logs",
        type=str,
        default=None,
        help="Glob for input .eval logs (overrides default 9 paper logs)",
    )
    args = parser.parse_args()

    log_paths = _resolve_log_paths(args.logs)
    if not log_paths:
        print("[eval_logs_to_csv] no input logs found", file=sys.stderr)
        sys.exit(1)

    rows: list[dict[str, Any]] = []
    for path in log_paths:
        rows.extend(_rows_from_log(path))

    if not rows:
        print("[eval_logs_to_csv] no samples extracted", file=sys.stderr)
        sys.exit(1)

    df = pd.DataFrame.from_records(rows)
    df = _order_columns(df)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"[eval_logs_to_csv] wrote {len(df)} rows × {len(df.columns)} cols -> {args.output}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the script parses and prints help**

Run: `python paper/cross_task/scripts/eval_logs_to_csv.py --help`
Expected: argparse usage block, no traceback. (It will fail import if `_resolve_log_paths` / `_rows_from_log` / `_order_columns` aren't defined — that's fine, those come in later tasks. For this step, comment out the `main()` body except the parser lines, OR define the three helpers as `pass` stubs so the import works. Use stubs:)

```python
def _resolve_log_paths(arg: str | None) -> list[Path]: return []
def _rows_from_log(path: Path) -> list[dict[str, Any]]: return []
def _order_columns(df: pd.DataFrame) -> pd.DataFrame: return df
```

Add those stubs above `main()`. Re-run `--help`. Expected: clean usage output.

- [ ] **Step 3: Commit**

```bash
git add paper/cross_task/scripts/eval_logs_to_csv.py
git commit -m "Scaffold eval_logs_to_csv: CLI and default log paths"
```

---

## Task 2: Implement `_resolve_log_paths` (path resolution)

**Files:**
- Modify: `paper/cross_task/scripts/eval_logs_to_csv.py` (replace stub)
- Create: `tests/test_eval_logs_to_csv.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_eval_logs_to_csv.py`:

```python
"""Tests for paper/cross_task/scripts/eval_logs_to_csv.py."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "paper/cross_task/scripts"))

import eval_logs_to_csv as elt  # noqa: E402


def test_resolve_default_returns_existing_paper_logs():
    paths = elt._resolve_log_paths(None)
    # At least the canonical 5 must exist; the 4 extended may or may not.
    assert len(paths) >= 5
    for p in paths:
        assert p.exists(), f"{p} reported but does not exist"
        assert p.suffix == ".eval"


def test_resolve_glob_returns_matched_paths(tmp_path):
    (tmp_path / "a.eval").touch()
    (tmp_path / "b.eval").touch()
    (tmp_path / "c.txt").touch()
    paths = elt._resolve_log_paths(str(tmp_path / "*.eval"))
    assert len(paths) == 2
    assert all(p.suffix == ".eval" for p in paths)


def test_resolve_glob_no_matches_returns_empty(tmp_path):
    assert elt._resolve_log_paths(str(tmp_path / "nope*.eval")) == []
```

- [ ] **Step 2: Run tests, verify failure**

Run: `pytest tests/test_eval_logs_to_csv.py::test_resolve_default_returns_existing_paper_logs -v`
Expected: FAIL — stub returns `[]`.

- [ ] **Step 3: Replace the stub with real implementation**

Replace the `_resolve_log_paths` stub in `paper/cross_task/scripts/eval_logs_to_csv.py` with:

```python
def _resolve_log_paths(glob_arg: str | None) -> list[Path]:
    """Default: 9 paper logs that exist on disk. Glob: explicit override."""
    if glob_arg:
        return sorted(Path(p) for p in glob.glob(glob_arg) if Path(p).suffix == ".eval")
    return [p for p in DEFAULT_LOGS if p.exists()]
```

- [ ] **Step 4: Run tests, verify pass**

Run: `pytest tests/test_eval_logs_to_csv.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add paper/cross_task/scripts/eval_logs_to_csv.py tests/test_eval_logs_to_csv.py
git commit -m "Implement _resolve_log_paths with default + glob"
```

---

## Task 3: Implement task/variant inference from log path

**Files:**
- Modify: `paper/cross_task/scripts/eval_logs_to_csv.py`
- Modify: `tests/test_eval_logs_to_csv.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_eval_logs_to_csv.py`:

```python
def test_infer_task_variant_canonical():
    p = REPO_ROOT / "paper/task1_bargaining/eval_log.eval"
    assert elt._infer_task_variant(p) == ("bargaining", "canonical")


def test_infer_task_variant_extended():
    p = REPO_ROOT / "paper/task4_sales/eval_log_extended.eval"
    assert elt._infer_task_variant(p) == ("sales", "extended")


def test_infer_task_variant_unknown():
    p = Path("/tmp/some/random.eval")
    assert elt._infer_task_variant(p) == ("unknown", "other")


def test_infer_task_variant_logs_dir_with_taskN():
    p = Path("/x/logs/task3_village_sweep_42.eval")
    assert elt._infer_task_variant(p) == ("village", "other")
```

- [ ] **Step 2: Run tests, verify failure**

Run: `pytest tests/test_eval_logs_to_csv.py -v`
Expected: 4 new tests fail (`_infer_task_variant` not defined → AttributeError).

- [ ] **Step 3: Add `_infer_task_variant`**

Add this function to `eval_logs_to_csv.py` (above `main`):

```python
def _infer_task_variant(path: Path) -> tuple[str, str]:
    """Infer (task, variant) from log path.

    Looks for `taskN_<env>` in any path component; treats names ending in
    `eval_log_extended.eval` as extended, `eval_log.eval` as canonical, and
    anything else as `other`.
    """
    task = "unknown"
    for part in path.parts:
        m = re.match(r"task\d+_\w+", part)
        if m:
            task = TASK_DIR_TO_KEY.get(m.group(0), "unknown")
            break
        # also recognize "taskN_<env>" embedded in a filename (e.g. logs/ dir)
        m = re.search(r"task\d+_(bargaining|debate|village|sales|committee)", part)
        if m:
            task = TASK_DIR_TO_KEY.get(m.group(0), "unknown")
            break

    name = path.name
    if name == "eval_log_extended.eval":
        variant = "extended"
    elif name == "eval_log.eval":
        variant = "canonical"
    else:
        variant = "other"
    return task, variant
```

- [ ] **Step 4: Run tests, verify pass**

Run: `pytest tests/test_eval_logs_to_csv.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add paper/cross_task/scripts/eval_logs_to_csv.py tests/test_eval_logs_to_csv.py
git commit -m "Infer task and variant from eval log path"
```

---

## Task 4: Implement scorer-score flattening

**Files:**
- Modify: `paper/cross_task/scripts/eval_logs_to_csv.py`
- Modify: `tests/test_eval_logs_to_csv.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_eval_logs_to_csv.py`:

```python
def test_flatten_scores_dict_value():
    scores = {
        "sales_classifier": SimpleNamespace(value={
            "accurate": 0.6, "misleading": 0.3, "false": 0.1,
            "manipulation_rate": 0.4,
        }),
    }
    out = elt._flatten_scores(scores)
    assert out == {
        "sales_classifier__accurate": 0.6,
        "sales_classifier__misleading": 0.3,
        "sales_classifier__false": 0.1,
        "sales_classifier__manipulation_rate": 0.4,
    }


def test_flatten_scores_scalar_value():
    scores = {"some_scalar_scorer": SimpleNamespace(value=0.42)}
    out = elt._flatten_scores(scores)
    assert out == {"some_scalar_scorer": 0.42}


def test_flatten_scores_skips_none_value():
    scores = {"broken": SimpleNamespace(value=None)}
    assert elt._flatten_scores(scores) == {}


def test_flatten_scores_handles_empty():
    assert elt._flatten_scores({}) == {}
    assert elt._flatten_scores(None) == {}


def test_flatten_scores_stringifies_non_numeric():
    scores = {"decision": SimpleNamespace(value={"favored_won": True, "favored_rank": 2})}
    out = elt._flatten_scores(scores)
    assert out == {"decision__favored_won": True, "decision__favored_rank": 2}
```

- [ ] **Step 2: Run tests, verify failure**

Run: `pytest tests/test_eval_logs_to_csv.py -v`
Expected: 5 new tests fail (`_flatten_scores` not defined).

- [ ] **Step 3: Add `_flatten_scores`**

Add this function to `eval_logs_to_csv.py`:

```python
def _flatten_scores(scores: dict[str, Any] | None) -> dict[str, Any]:
    """Flatten sample.scores into <scorer>__<key> columns.

    Dict-valued scores fan out to one column per key. Scalar-valued scores
    become a single column named <scorer>. Scores with value=None are skipped.
    """
    if not scores:
        return {}
    out: dict[str, Any] = {}
    for scorer_name, score in scores.items():
        value = getattr(score, "value", None)
        if value is None:
            continue
        if isinstance(value, dict):
            for k, v in value.items():
                out[f"{scorer_name}__{k}"] = v
        else:
            out[scorer_name] = value
    return out
```

- [ ] **Step 4: Run tests, verify pass**

Run: `pytest tests/test_eval_logs_to_csv.py -v`
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add paper/cross_task/scripts/eval_logs_to_csv.py tests/test_eval_logs_to_csv.py
git commit -m "Flatten sample.scores into <scorer>__<key> columns"
```

---

## Task 5: Implement extra setup-field extraction

**Files:**
- Modify: `paper/cross_task/scripts/eval_logs_to_csv.py`
- Modify: `tests/test_eval_logs_to_csv.py`

`_row_from_sample` from `load.py` produces 9 columns. We need additional setup fields not in that base row: `epoch`, `scenario_id`, `manipulator`, `num_agents`, `topology`, `topic`, `model_mapping` (JSON-stringified).

- [ ] **Step 1: Write failing tests**

Append to `tests/test_eval_logs_to_csv.py`:

```python
def test_extra_setup_full():
    md = {
        "scenario_id": "S-42",
        "manipulator": "alice",
        "num_agents": 6,
        "topology": "all_to_all",
        "topic": "carbon tax",
        "model_mapping": {"alice": "claude", "bob": "gpt5"},
    }
    sample = SimpleNamespace(epoch=3)
    out = elt._extra_setup_fields(sample, md)
    assert out["epoch"] == 3
    assert out["scenario_id"] == "S-42"
    assert out["manipulator"] == "alice"
    assert out["num_agents"] == 6
    assert out["topology"] == "all_to_all"
    assert out["topic"] == "carbon tax"
    # JSON-stringified, parseable
    import json as _json
    assert _json.loads(out["model_mapping"]) == {"alice": "claude", "bob": "gpt5"}


def test_extra_setup_missing_fields_become_none():
    sample = SimpleNamespace(epoch=None)
    out = elt._extra_setup_fields(sample, {})
    for key in ("scenario_id", "manipulator", "num_agents", "topology", "topic", "model_mapping"):
        assert out[key] is None
    assert out["epoch"] is None


def test_extra_setup_non_dict_model_mapping_passes_through_as_string():
    md = {"model_mapping": "claude"}  # malformed but seen in some logs
    out = elt._extra_setup_fields(SimpleNamespace(epoch=0), md)
    assert out["model_mapping"] == '"claude"'
```

- [ ] **Step 2: Run tests, verify failure**

Run: `pytest tests/test_eval_logs_to_csv.py -v`
Expected: 3 new tests fail.

- [ ] **Step 3: Add `_extra_setup_fields`**

Add this function to `eval_logs_to_csv.py`:

```python
EXTRA_SETUP_KEYS = ("scenario_id", "manipulator", "num_agents", "topology", "topic")


def _extra_setup_fields(sample: Any, md: dict[str, Any]) -> dict[str, Any]:
    """Pull setup columns beyond what _row_from_sample already produces.

    Returns a dict with: epoch, scenario_id, manipulator, num_agents,
    topology, topic, model_mapping (JSON string). Missing values are None.
    """
    out: dict[str, Any] = {"epoch": getattr(sample, "epoch", None)}
    for k in EXTRA_SETUP_KEYS:
        out[k] = md.get(k)
    mm = md.get("model_mapping")
    out["model_mapping"] = json.dumps(mm) if mm is not None else None
    return out
```

- [ ] **Step 4: Run tests, verify pass**

Run: `pytest tests/test_eval_logs_to_csv.py -v`
Expected: 15 passed.

- [ ] **Step 5: Commit**

```bash
git add paper/cross_task/scripts/eval_logs_to_csv.py tests/test_eval_logs_to_csv.py
git commit -m "Add extra setup-field extraction (epoch, scenario_id, etc.)"
```

---

## Task 6: Implement `_rows_from_log` (per-log driver)

**Files:**
- Modify: `paper/cross_task/scripts/eval_logs_to_csv.py`
- Modify: `tests/test_eval_logs_to_csv.py`

This task wires steps 2-5 together: read a log, infer task/variant, iterate samples, build full rows. Tests use a fake log object — no real `.eval` file needed.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_eval_logs_to_csv.py`:

```python
def _make_fake_sample(*, sid="s1", epoch=0, error=None, scores=None, store_md=None, top_md=None):
    """Build an object with the shape _row_from_sample expects."""
    store = {"InteractionState:scenario": {"metadata": store_md or {}}}
    return SimpleNamespace(
        id=sid,
        epoch=epoch,
        error=error,
        scores=scores or {},
        store=SimpleNamespace(get=store.get),
        metadata=top_md or {},
    )


def test_rows_from_log_sales_smoke(monkeypatch, tmp_path):
    """End-to-end: fake sales log -> rows with identity + scorer + extra fields."""
    sample = _make_fake_sample(
        sid="sales-1",
        epoch=2,
        scores={
            "sales_classifier": SimpleNamespace(value={
                "accurate": 0.6, "misleading": 0.3, "false": 0.1,
                "manipulation_rate": 0.4, "manipulation_occurred": 1.0,
            }),
        },
        top_md={
            "frame": "minimal", "incentive": "moderate", "difficulty": "high",
            "model": "claude", "scenario_id": "prod-7",
            "manipulator": "seller", "num_agents": 1,
            "model_mapping": {"seller": "claude"},
        },
    )
    fake_log = SimpleNamespace(samples=[sample])

    fake_path = tmp_path / "task4_sales" / "eval_log.eval"
    fake_path.parent.mkdir(parents=True)
    fake_path.touch()

    monkeypatch.setattr(elt, "read_eval_log", lambda p: fake_log)

    rows = elt._rows_from_log(fake_path)
    assert len(rows) == 1
    r = rows[0]
    assert r["task"] == "sales"
    assert r["variant"] == "canonical"
    assert r["sample_id"] == "sales-1"
    assert r["epoch"] == 2
    assert r["model"] == "Claude-Opus-4.7"
    assert r["frame"] == "minimal"
    assert r["incentive"] == "moderate"
    assert r["difficulty"] == "high"
    assert r["scenario_id"] == "prod-7"
    assert r["manipulator"] == "seller"
    assert r["sales_classifier__accurate"] == 0.6
    assert r["sales_classifier__manipulation_rate"] == 0.4
    assert r["manipulation_metric"] == 0.4  # normalized headline
    assert r["log_path"].endswith("task4_sales/eval_log.eval")


def test_rows_from_log_skips_errored_samples(monkeypatch, tmp_path):
    bad = _make_fake_sample(sid="bad", error="boom")
    good = _make_fake_sample(
        sid="good",
        scores={"sales_classifier": SimpleNamespace(value={
            "manipulation_rate": 0.1, "manipulation_occurred": 0.0,
        })},
        top_md={"frame": "minimal", "incentive": "none", "difficulty": "low", "model": "claude"},
    )
    fake_log = SimpleNamespace(samples=[bad, good])

    fake_path = tmp_path / "task4_sales" / "eval_log.eval"
    fake_path.parent.mkdir(parents=True)
    fake_path.touch()
    monkeypatch.setattr(elt, "read_eval_log", lambda p: fake_log)

    rows = elt._rows_from_log(fake_path)
    assert [r["sample_id"] for r in rows] == ["good"]


def test_rows_from_log_unknown_task_returns_empty(monkeypatch, tmp_path):
    """If we can't infer the task, _row_from_sample can't pick a metric -> 0 rows."""
    sample = _make_fake_sample(sid="s", scores={"x": SimpleNamespace(value={"v": 1})})
    fake_log = SimpleNamespace(samples=[sample])
    fake_path = tmp_path / "random.eval"
    fake_path.touch()
    monkeypatch.setattr(elt, "read_eval_log", lambda p: fake_log)
    rows = elt._rows_from_log(fake_path)
    assert rows == []
```

- [ ] **Step 2: Run tests, verify failure**

Run: `pytest tests/test_eval_logs_to_csv.py -v`
Expected: 3 new tests fail (the stub returns `[]`).

- [ ] **Step 3: Implement `_rows_from_log`**

Replace the `_rows_from_log` stub in `eval_logs_to_csv.py` with:

```python
def _rows_from_log(path: Path) -> list[dict[str, Any]]:
    """Read one .eval log and produce one row per scored, non-errored sample."""
    task, variant = _infer_task_variant(path)
    if task == "unknown":
        # Without a known task, _row_from_sample doesn't know which scorer to
        # treat as the headline. Skip — the user's --logs glob hit something
        # outside the 5-task universe.
        print(f"[eval_logs_to_csv] {path}: unknown task, skipping", file=sys.stderr)
        return []

    log = read_eval_log(str(path))
    rows: list[dict[str, Any]] = []
    for sample in log.samples or []:
        base = _row_from_sample(sample, task)
        if base is None:
            continue

        md = _flatten_metadata(sample)
        row: dict[str, Any] = {
            "task": task,
            "variant": variant,
            "log_path": str(path),
            "sample_id": base["sample_id"],
            "model": base["model"],
            "frame": base["frame"],
            "incentive": base["incentive"],
            "difficulty": base["difficulty"],
            "cluster_id": base["cluster_id"],
            "manipulation_metric": base["metric"],
            "manipulation_occurred": base["manipulation_occurred"],
        }
        row.update(_extra_setup_fields(sample, md))
        row.update(_flatten_scores(sample.scores))
        rows.append(row)
    print(f"[eval_logs_to_csv] {path.name}: {len(rows)} rows", file=sys.stderr)
    return rows
```

Note: the `task` key in `base` (from `_row_from_sample`) is overwritten here with the path-inferred task — they should match, but path inference is the authoritative source for our `task` column.

- [ ] **Step 4: Run tests, verify pass**

Run: `pytest tests/test_eval_logs_to_csv.py -v`
Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
git add paper/cross_task/scripts/eval_logs_to_csv.py tests/test_eval_logs_to_csv.py
git commit -m "Implement _rows_from_log driver (identity + setup + scores)"
```

---

## Task 7: Implement column ordering

**Files:**
- Modify: `paper/cross_task/scripts/eval_logs_to_csv.py`
- Modify: `tests/test_eval_logs_to_csv.py`

The DataFrame from a dict-of-records has columns in insertion order, but unioned across rows that order can be inconsistent. Pin a deterministic prefix (identity → setup → normalized metric → flattened scorer columns alphabetized).

- [ ] **Step 1: Write failing tests**

Append to `tests/test_eval_logs_to_csv.py`:

```python
def test_order_columns_pins_identity_prefix():
    df = pd.DataFrame([
        {"sales_classifier__false": 0.1, "frame": "minimal", "task": "sales",
         "manipulation_metric": 0.4, "model": "Claude-Opus-4.7", "sample_id": "s1",
         "variant": "canonical", "incentive": "none", "difficulty": "low",
         "cluster_id": None, "log_path": "/x", "epoch": 0, "scenario_id": None,
         "manipulator": None, "num_agents": None, "topology": None, "topic": None,
         "model_mapping": None, "manipulation_occurred": 1.0,
         "sales_classifier__accurate": 0.5},
    ])
    out = elt._order_columns(df)
    cols = list(out.columns)
    # First 6 must be the identity block in this order
    assert cols[:6] == ["task", "variant", "log_path", "sample_id", "epoch", "scenario_id"]
    # manipulation_metric and manipulation_occurred come before scorer columns
    mm_idx = cols.index("manipulation_metric")
    mo_idx = cols.index("manipulation_occurred")
    sc_idx = cols.index("sales_classifier__accurate")
    assert mm_idx < sc_idx
    assert mo_idx < sc_idx
    # Scorer columns are alphabetized
    scorer_cols = [c for c in cols if "__" in c]
    assert scorer_cols == sorted(scorer_cols)
```

- [ ] **Step 2: Run test, verify failure**

Run: `pytest tests/test_eval_logs_to_csv.py::test_order_columns_pins_identity_prefix -v`
Expected: FAIL — stub returns df unchanged.

- [ ] **Step 3: Implement `_order_columns`**

Replace the `_order_columns` stub:

```python
IDENTITY_COLUMNS = [
    "task", "variant", "log_path",
    "sample_id", "epoch", "scenario_id", "cluster_id",
    "model", "manipulator",
    "frame", "incentive", "difficulty",
    "num_agents", "topology", "topic", "model_mapping",
]

NORMALIZED_METRIC_COLUMNS = ["manipulation_metric", "manipulation_occurred"]


def _order_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Pin identity prefix, then normalized metric, then alphabetized scorer cols."""
    present = list(df.columns)
    leading = [c for c in IDENTITY_COLUMNS if c in present]
    metric = [c for c in NORMALIZED_METRIC_COLUMNS if c in present]
    leading_set = set(leading) | set(metric)
    rest = sorted(c for c in present if c not in leading_set)
    return df[leading + metric + rest]
```

- [ ] **Step 4: Run tests, verify pass**

Run: `pytest tests/test_eval_logs_to_csv.py -v`
Expected: 19 passed.

- [ ] **Step 5: Commit**

```bash
git add paper/cross_task/scripts/eval_logs_to_csv.py tests/test_eval_logs_to_csv.py
git commit -m "Order columns: identity, normalized metric, sorted scorers"
```

---

## Task 8: End-to-end smoke test against real eval logs

**Files:**
- Modify: `tests/test_eval_logs_to_csv.py`

- [ ] **Step 1: Write the smoke test**

Append to `tests/test_eval_logs_to_csv.py`:

```python
@pytest.mark.slow
def test_main_writes_real_csv(tmp_path):
    """Smoke test against actual paper eval logs. Slow — reads real .eval files."""
    real_canonical = REPO_ROOT / "paper/task4_sales/eval_log.eval"
    if not real_canonical.exists():
        pytest.skip("paper eval logs not present (LFS not pulled?)")

    out = tmp_path / "results.csv"
    sys_argv = sys.argv
    sys.argv = ["eval_logs_to_csv", "-o", str(out),
                "--logs", str(real_canonical)]
    try:
        elt.main()
    finally:
        sys.argv = sys_argv

    assert out.exists()
    df = pd.read_csv(out)
    assert len(df) > 0
    # Identity columns present and populated
    for col in ["task", "variant", "sample_id", "model", "frame", "incentive", "difficulty"]:
        assert col in df.columns
        assert df[col].notna().any()
    # Sales-specific scorer column present
    assert "sales_classifier__manipulation_rate" in df.columns
    # Normalized metric populated
    assert df["manipulation_metric"].notna().sum() > 0
    # task and variant correct
    assert set(df["task"].unique()) == {"sales"}
    assert set(df["variant"].unique()) == {"canonical"}
```

- [ ] **Step 2: Run the smoke test**

Run: `pytest tests/test_eval_logs_to_csv.py::test_main_writes_real_csv -v -m slow`

Note: pytest may not register the `slow` marker — if the test is auto-skipped, run without the marker filter:
`pytest tests/test_eval_logs_to_csv.py::test_main_writes_real_csv -v`

Expected: PASS, or SKIP with "paper eval logs not present" if LFS hasn't been pulled.

- [ ] **Step 3: Run the script for real to produce the CSV**

Run: `python paper/cross_task/scripts/eval_logs_to_csv.py`
Expected: prints `[eval_logs_to_csv] wrote N rows × M cols -> .../paper/cross_task/results.csv` where N is in the thousands. No tracebacks.

- [ ] **Step 4: Quick sanity check on the produced CSV**

Run:
```bash
python -c "
import pandas as pd
df = pd.read_csv('paper/cross_task/results.csv')
print(f'Total rows: {len(df)}')
print(f'Total cols: {len(df.columns)}')
print()
print('Per task × variant:')
print(df.groupby(['task','variant']).size().unstack(fill_value=0))
print()
print('manipulation_metric non-null per task:')
print(df.groupby('task')['manipulation_metric'].apply(lambda s: f\"{s.notna().sum()}/{len(s)}\"))
print()
print('Models:')
print(df['model'].value_counts())
"
```

Expected: thousands of rows, 5 task keys present, manipulation_metric mostly populated, 6 canonical models.

- [ ] **Step 5: Commit the CSV and the smoke test**

```bash
git add tests/test_eval_logs_to_csv.py paper/cross_task/results.csv
git commit -m "Add end-to-end smoke test and produce results.csv"
```

---

## Task 9: Run full test suite and final cleanup

**Files:** none modified

- [ ] **Step 1: Run the full test suite**

Run: `pytest tests/ -v`
Expected: all tests pass (existing + 19 new tests for `eval_logs_to_csv`).

- [ ] **Step 2: Lint check the new file (if a linter is configured)**

Run: `ruff check paper/cross_task/scripts/eval_logs_to_csv.py tests/test_eval_logs_to_csv.py 2>/dev/null || echo "ruff not configured, skipping"`
Expected: no errors, or "skipping" message.

- [ ] **Step 3: Verify the script is idempotent**

Run twice in a row:
```bash
python paper/cross_task/scripts/eval_logs_to_csv.py
md5sum paper/cross_task/results.csv
python paper/cross_task/scripts/eval_logs_to_csv.py
md5sum paper/cross_task/results.csv
```
Expected: same hash both times.

- [ ] **Step 4: Final commit if anything changed**

If only `results.csv` was already committed and nothing new shows up in `git status`, this step is a no-op. Otherwise:

```bash
git status
git add -p   # review and stage as appropriate
git commit -m "Final cleanup for eval_logs_to_csv"
```

---

## Self-review notes (already addressed inline)

- ✅ Spec coverage: identity (T6), variant (T3), all-scorer flatten (T4), extra setup (T5), normalized metric (T6 via `_row_from_sample`), default + glob CLI (T1, T2), output path (T1).
- ✅ No placeholders.
- ✅ Type/name consistency: `_resolve_log_paths`, `_infer_task_variant`, `_flatten_scores`, `_extra_setup_fields`, `_rows_from_log`, `_order_columns` all match across tasks. Column names in tests match `_order_columns` constants.
- ✅ Scope: single flattener script, one test file, one CSV output. No analysis logic.
