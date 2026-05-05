"""Shared loaders for the capability/ scripts.

Joins paper/cross_task/data/results.csv with paper/cross_task/data/model_capability.csv
into a single tidy pandas DataFrame keyed on
(task, model, frame, incentive, difficulty, sample_id) with capability columns
(elo, tier, generation, family) attached.

All scripts in this directory should import `load_joined()` from here so that
the row-level filters and column types stay consistent.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # paper/cross_task
RESULTS_CSV = ROOT / "data" / "results.csv"
CAPABILITY_CSV = ROOT / "data" / "model_capability.csv"
ANALYSIS_DIR = ROOT / "analysis"
FIG_DIR = ROOT / "figures" / "capability"

TASKS = ["bargaining", "debate", "village", "sales", "committee", "inbox"]
FRAMES = ["prohibitive", "pro_social", "minimal", "selfish", "permissive"]
INCENTIVES = ["none", "moderate", "high"]
DIFFICULTIES = ["low", "medium", "high"]
TIERS = ["small", "average", "flagship"]
GENERATIONS = ["prev", "current"]


def load_capability() -> pd.DataFrame:
    df = pd.read_csv(CAPABILITY_CSV)
    df["elo"] = df["elo"].astype(float)
    return df


def load_joined() -> pd.DataFrame:
    """Row-per-sample DataFrame with capability columns merged in."""
    res = pd.read_csv(RESULTS_CSV, low_memory=False)
    res = res.dropna(subset=["manipulation_metric"]).copy()
    res["manipulation_metric"] = res["manipulation_metric"].astype(float)

    cap = load_capability()
    df = res.merge(cap, on="model", how="inner")
    return df


def aggregate(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Mean manipulation_metric grouped by `by`, with sample count."""
    out = df.groupby(by, observed=True)["manipulation_metric"].agg(["mean", "count"]).reset_index()
    return out.rename(columns={"mean": "rate", "count": "n"})


def ensure_dirs() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
