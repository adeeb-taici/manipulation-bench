"""Trajectory-level dataframe loader for the reanalysis pipeline.

Reads the five canonical paper combined eval logs and returns a single
pandas dataframe with one row per scored trajectory. Surfaces axis labels
plus per-task cluster IDs (claim_id / scenario_id / slate_id) needed for
cluster-robust regression.

This wraps `manipulation_bench.analyze_surface.collect_rows()` and adds
the cluster-id pull plus model-name canonicalization that the v1 prereg
scripts each implement separately.

Usage:
    # From a sibling script in paper/cross_task/scripts/:
    from load import load_corpus
    df = load_corpus()
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd
from inspect_ai.log import read_eval_log

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from manipulation_bench.analyze_surface import (  # noqa: E402
    canonical_frame,
    canonical_incentive,
    collect_rows,
    detect_environment,
)

LOG_PATHS = {
    "bargaining": REPO_ROOT / "paper/task1_bargaining/eval_log.eval",
    "debate":     REPO_ROOT / "paper/task2_debate/eval_log.eval",
    "village":    REPO_ROOT / "paper/task3_village/eval_log.eval",
    "sales":      REPO_ROOT / "paper/task4_sales/eval_log.eval",
    "committee":  REPO_ROOT / "paper/task5_committee/eval_log.eval",
    "inbox":      REPO_ROOT / "paper/task6_inbox/eval_log.eval",
}

# eval_log_extended.eval files (May 2026 corpus refresh) sit alongside the
# canonical eval_log.eval. Use as a manual override by passing tasks={"sales":
# REPO_ROOT/"paper/task4_sales/eval_log_extended.eval"} or similar — the
# canonical pipeline uses eval_log.eval to match the project brief's 12,510-
# trajectory corpus.
LOG_PATHS_FALLBACK = {
    task: REPO_ROOT / f"paper/{dir_}/eval_log_extended.eval"
    for task, dir_ in (
        ("bargaining", "task1_bargaining"),
        ("debate",     "task2_debate"),
        ("village",    "task3_village"),
        ("sales",      "task4_sales"),
        ("committee",  "task5_committee"),
        ("inbox",      "task6_inbox"),
    )
}

# Per-task cluster column for cluster-robust SEs.
# T1, T3 have no item-level clustering (one outcome per trajectory).
# T6 uses suppression_target (2 substrates: RippleMetrics, billing complaints).
CLUSTER_COL = {
    "bargaining": None,    # HC3
    "debate":     "claim_id",
    "village":    None,    # HC3
    "sales":      "scenario_id",  # product+difficulty pairing
    "committee":  "slate_id",
    "inbox":      "suppression_target",
}

# Canonical model labels — paper roster of 6.
MODEL_REMAP = {
    # T1/T2/T3/T5 use Pascal-Case scenario labels
    "DeepSeek-v3.2":   "DeepSeek-V4-Pro",  # combined-log labels carry old name; runtime model is V4 Pro
    "GPT-5":           "GPT-5.5",          # ditto for GPT-5.5 amendment
    # T4 uses lowercase scenario labels
    "claude":          "Claude-Opus-4.7",
    "gpt5":            "GPT-5.5",
    "gpt55":           "GPT-5.5",
    "gemini":          "Gemini-3.1-Pro",
    "grok":            "Grok-4",
    "llama":           "Llama-3.3-70B",
    "deepseek":        "DeepSeek-V4-Pro",
    "deepseek_v4":     "DeepSeek-V4-Pro",
    # passthrough
    "Claude-Opus-4.7": "Claude-Opus-4.7",
    "GPT-5.5":         "GPT-5.5",
    "Gemini-3.1-Pro":  "Gemini-3.1-Pro",
    "Grok-4":          "Grok-4",
    "Llama-3.3-70B":   "Llama-3.3-70B",
    "DeepSeek-V4-Pro": "DeepSeek-V4-Pro",
}

CANONICAL_MODELS = (
    "Claude-Opus-4.7",
    "GPT-5.5",
    "Gemini-3.1-Pro",
    "Grok-4",
    "Llama-3.3-70B",
    "DeepSeek-V4-Pro",
)

# Display labels for figures — pretty-printed, with spaces.
MODEL_LABELS = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5":         "GPT-5.5",
    "Gemini-3.1-Pro":  "Gemini 3.1 Pro",
    "Grok-4":          "Grok 4",
    "Llama-3.3-70B":   "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
}

# Canonical task ordering and display labels for cross-task figures/tables.
TASKS = ("bargaining", "debate", "village", "sales", "committee", "inbox")
TASK_LABELS = {
    "bargaining": "T1 Bargaining",
    "debate":     "T2 Debate",
    "village":    "T3 Village",
    "sales":      "T4 Sales",
    "committee":  "T5 Committee",
    "inbox":      "T6 Inbox",
}

# T1 stores incentive as expected_penalty (0/80/250); canonical levels are labels.
T1_INCENTIVE_MAP = {0: "none", 80: "moderate", 250: "high"}


def _flatten_metadata(sample: Any) -> dict[str, Any]:
    """Same logic as analyze_surface._sample_meta but returns the flattened dict."""
    scenario = sample.store.get("InteractionState:scenario") or {}
    md = dict(scenario.get("metadata") or {})
    sample_md = getattr(sample, "metadata", None) or {}
    if isinstance(sample_md, dict):
        for k, v in sample_md.items():
            if v is not None and md.get(k) is None:
                md[k] = v
    return md


def _t1_incentive_canonical(raw: Any) -> str | None:
    """T1 stores expected_penalty as 0/80/250; map to canonical incentive."""
    if raw is None:
        return None
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return canonical_incentive(raw)
    return T1_INCENTIVE_MAP.get(v)


def _row_from_sample(sample: Any, env: str) -> dict[str, Any] | None:
    """Build one trajectory-level row including the per-task cluster id."""
    if sample.error:
        return None
    md = _flatten_metadata(sample)

    # Primary metric per task
    metric: float | None = None
    manip: float | None = None

    if env == "bargaining":
        bs = (sample.scores or {}).get("bargaining_commit")
        if bs is None or not isinstance(bs.value, dict) or bs.value.get("sample_failed"):
            return None
        metric = bs.value.get("manipulation_rate")
        if metric is None:
            return None
        m_raw = bs.value.get("manipulation_occurred")
        manip = float(m_raw) if m_raw is not None else None
        # Use explicit None check — `expected_penalty=0` is the "none" incentive
        # level and must not fall through `or` to the missing `incentive` key.
        ep = md.get("expected_penalty")
        incentive = _t1_incentive_canonical(ep if ep is not None else md.get("incentive"))
    elif env == "debate":
        gtp = (sample.scores or {}).get("ground_truth_persuasion")
        if gtp is None or not isinstance(gtp.value, dict):
            return None
        metric = gtp.value.get("belief_shift")
        m_raw = gtp.value.get("manipulation_occurred")
        manip = float(m_raw) if m_raw is not None else None
        if manip is None and metric is None:
            return None
        incentive = canonical_incentive(md.get("incentive"))
    elif env == "village":
        er = (sample.scores or {}).get("exploitation_rate")
        if er is None or not isinstance(er.value, dict):
            return None
        # Paper primary metric: agent_1's exploitation_rate (the manipulator)
        metric = er.value.get("agent_1")
        if metric is None:
            metric = er.value.get("exploitation_rate")
        m_raw = er.value.get("manipulation_occurred")
        manip = float(m_raw) if m_raw is not None else None
        if metric is None and manip is None:
            return None
        incentive = canonical_incentive(md.get("incentive"))
    elif env == "sales":
        sc = (sample.scores or {}).get("sales_classifier")
        if sc is None or not isinstance(sc.value, dict):
            return None
        metric = sc.value.get("manipulation_rate")
        if metric is None:
            return None
        m_raw = sc.value.get("manipulation_occurred")
        manip = float(m_raw) if m_raw is not None else None
        incentive = canonical_incentive(md.get("incentive"))
    elif env == "committee":
        bs = (sample.scores or {}).get("initial_rating_bias")
        if bs is None or not isinstance(bs.value, dict):
            return None
        metric = bs.value.get("initial_bias")
        if metric is None:
            return None
        m_raw = bs.value.get("manipulation_occurred")
        manip = float(m_raw) if m_raw is not None else None
        incentive = canonical_incentive(md.get("incentive"))
    elif env == "inbox":
        it = (sample.scores or {}).get("inbox_triage")
        if it is None or not isinstance(it.value, dict):
            return None
        metric = it.value.get("suppression_rate")
        m_raw = it.value.get("manipulation_occurred")
        manip = float(m_raw) if m_raw is not None else None
        if metric is None and manip is None:
            return None
        incentive = canonical_incentive(md.get("incentive"))
    else:
        return None

    # Cluster id
    cluster_col = CLUSTER_COL.get(env)
    cluster_id: str | None = None
    if cluster_col:
        v = md.get(cluster_col)
        cluster_id = str(v) if v is not None else None

    # Model label (varies per task — match the prereg scripts)
    if env in ("debate", "village"):
        raw_model = md.get("manipulator_model") or md.get("model")
    elif env == "committee":
        raw_model = md.get("interested_model_label") or md.get("model")
    else:
        raw_model = md.get("model")
    model = MODEL_REMAP.get(str(raw_model), str(raw_model)) if raw_model is not None else None

    frame = canonical_frame(md.get("frame"))
    difficulty = md.get("difficulty")

    return {
        "sample_id": sample.id,
        "task": env,
        "model": model,
        "frame": frame,
        "incentive": incentive,
        "difficulty": difficulty,
        "cluster_id": cluster_id,
        "metric": float(metric) if metric is not None else None,
        "manipulation_occurred": float(manip) if manip is not None else None,
    }


RESULTS_CSV = REPO_ROOT / "paper/cross_task/results.csv"


def _load_from_csv(
    csv_path: Path, tasks: tuple[str, ...], verbose: bool
) -> pd.DataFrame:
    """Read paper/cross_task/results.csv and shape it like _row_from_sample output.

    The CSV has the same identity columns plus all flattened scorer scores;
    we subset to the 9 columns load_corpus has historically returned and
    rename `manipulation_metric` -> `metric` to match the legacy schema.

    Filters to variant=='canonical' so the v2 pipeline ignores the
    small_model_sweep rows (they carry non-CANONICAL_MODELS labels and
    would be dropped by the model filter below anyway, but filtering by
    variant up front is cheaper and explicit).
    """
    if verbose:
        print(f"[load] reading {csv_path.relative_to(REPO_ROOT)}", file=sys.stderr)
    df = pd.read_csv(csv_path, low_memory=False)
    df = df[df["variant"] == "canonical"]
    df = df[df["task"].isin(tasks)]
    df = df.rename(columns={"manipulation_metric": "metric"})
    keep = [
        "sample_id", "task", "model", "frame", "incentive", "difficulty",
        "cluster_id", "metric", "manipulation_occurred",
    ]
    df = df[keep].reset_index(drop=True)
    if verbose:
        for t, n in df.groupby("task").size().items():
            print(f"[load] {t}: {n} rows (from csv)", file=sys.stderr)
    return df


def _load_from_eval_logs(
    tasks: tuple[str, ...], verbose: bool
) -> pd.DataFrame:
    """Walk each task's combined .eval log and run _row_from_sample. Slow."""
    rows: list[dict[str, Any]] = []
    for task in tasks:
        path = LOG_PATHS[task]
        if not path.exists():
            fallback = LOG_PATHS_FALLBACK.get(task)
            if fallback and fallback.exists():
                if verbose:
                    print(f"[load] {task}: using fallback {fallback.name}", file=sys.stderr)
                path = fallback
            else:
                if verbose:
                    print(f"[load] {task}: log not found, skipping", file=sys.stderr)
                continue
        log = read_eval_log(str(path))
        env = detect_environment(log)
        if env != task and env != "unknown":
            print(f"[warn] {path} detected env={env}, expected {task}", file=sys.stderr)
        n_before = len(rows)
        for s in log.samples or []:
            r = _row_from_sample(s, task)
            if r is not None:
                rows.append(r)
        if verbose:
            print(f"[load] {task}: {len(rows) - n_before} rows", file=sys.stderr)
    return pd.DataFrame(rows)


def load_corpus(
    tasks: Iterable[str] | None = None,
    verbose: bool = True,
    source: str = "auto",
) -> pd.DataFrame:
    """Load the 5-task combined eval logs into a single trajectory-level dataframe.

    Args:
        tasks: subset of task names to load; default = all five.
        verbose: print per-task row count to stderr.
        source: "csv" reads paper/cross_task/results.csv (~30s for full corpus).
                "eval" walks the raw .eval files (slow, multi-minute).
                "auto" (default) uses csv if it exists, else falls back to eval.

    Returns:
        DataFrame with columns:
            sample_id, task, model, frame, incentive, difficulty,
            cluster_id, metric, manipulation_occurred
    """
    selected = tuple(tasks) if tasks is not None else tuple(LOG_PATHS.keys())

    if source == "auto":
        source = "csv" if RESULTS_CSV.exists() else "eval"
    if source == "csv":
        if not RESULTS_CSV.exists():
            raise FileNotFoundError(
                f"source='csv' but {RESULTS_CSV} does not exist; "
                "regenerate it with `python paper/cross_task/scripts/eval_logs_to_csv.py`"
            )
        df = _load_from_csv(RESULTS_CSV, selected, verbose=verbose)
    elif source == "eval":
        df = _load_from_eval_logs(selected, verbose=verbose)
    else:
        raise ValueError(f"source must be 'auto', 'csv', or 'eval'; got {source!r}")

    if df.empty:
        return df

    if verbose:
        pre_filter_by_task = df.groupby("task").size().to_dict()
        unmapped = df[~df["model"].isin(CANONICAL_MODELS)]["model"].value_counts().to_dict()
        print(f"[load] pre-filter per-task: {pre_filter_by_task}", file=sys.stderr)
        if unmapped:
            print(f"[load] dropped non-canonical model labels: {unmapped}", file=sys.stderr)

    df = df[df["model"].isin(CANONICAL_MODELS)].reset_index(drop=True)
    return df


if __name__ == "__main__":
    df = load_corpus()
    print(f"\nTotal rows: {len(df)}")
    print(f"\nPer-task counts:")
    print(df.groupby("task").size())
    print(f"\nPer-task × model counts:")
    print(df.groupby(["task", "model"]).size().unstack(fill_value=0))
    print(f"\nCluster id presence per task:")
    print(df.groupby("task")["cluster_id"].apply(lambda s: f"{s.notna().sum()}/{len(s)}"))
