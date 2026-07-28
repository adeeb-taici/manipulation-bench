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
    import json as _json
    assert _json.loads(out["model_mapping"]) == {"alice": "claude", "bob": "gpt5"}


def test_extra_setup_missing_fields_become_none():
    sample = SimpleNamespace(epoch=None)
    out = elt._extra_setup_fields(sample, {})
    for key in ("scenario_id", "manipulator", "num_agents", "topology", "topic", "model_mapping"):
        assert out[key] is None
    assert out["epoch"] is None


def test_extra_setup_non_dict_model_mapping_passes_through_as_string():
    md = {"model_mapping": "claude"}
    out = elt._extra_setup_fields(SimpleNamespace(epoch=0), md)
    assert out["model_mapping"] == '"claude"'


def _make_fake_sample(*, sid="s1", epoch=0, error=None, scores=None, store_md=None, top_md=None):
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
    assert r["manipulation_metric"] == 0.4
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
    sample = _make_fake_sample(sid="s", scores={"x": SimpleNamespace(value={"v": 1})})
    fake_log = SimpleNamespace(samples=[sample])
    fake_path = tmp_path / "random.eval"
    fake_path.touch()
    monkeypatch.setattr(elt, "read_eval_log", lambda p: fake_log)
    rows = elt._rows_from_log(fake_path)
    assert rows == []


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
    assert cols[:6] == ["task", "variant", "log_path", "sample_id", "epoch", "scenario_id"]
    mm_idx = cols.index("manipulation_metric")
    mo_idx = cols.index("manipulation_occurred")
    sc_idx = cols.index("sales_classifier__accurate")
    assert mm_idx < sc_idx
    assert mo_idx < sc_idx
    scorer_cols = [c for c in cols if "__" in c]
    assert scorer_cols == sorted(scorer_cols)
