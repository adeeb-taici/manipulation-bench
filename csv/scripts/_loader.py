"""Shared CSV loader for manipulation-bench results.csv analysis."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

CSV_PATH = Path(__file__).resolve().parent.parent / "results.csv"
OUT_DIR = Path(__file__).resolve().parent.parent / "out"
TABLES_DIR = OUT_DIR / "tables"
FIGURES_DIR = OUT_DIR / "figures"

FRAME_ORDER = ["prohibitive", "pro_social", "minimal", "selfish", "permissive"]
INCENTIVE_ORDER = ["none", "moderate", "high"]
DIFFICULTY_ORDER = ["low", "medium", "high"]

DTYPES = {"scenario_id": "string", "cluster_id": "string", "manipulator": "string"}


def load(variant: str | None = None, tasks: list[str] | None = None) -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, dtype=DTYPES, low_memory=False)
    if variant is not None:
        df = df[df["variant"] == variant]
    if tasks is not None:
        df = df[df["task"].isin(tasks)]
    df["frame"] = pd.Categorical(df["frame"], categories=FRAME_ORDER, ordered=True)
    df["incentive"] = pd.Categorical(df["incentive"], categories=INCENTIVE_ORDER, ordered=True)
    df["difficulty"] = pd.Categorical(df["difficulty"], categories=DIFFICULTY_ORDER, ordered=True)
    return df.reset_index(drop=True)


def save_table(df: pd.DataFrame, name: str) -> Path:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    path = TABLES_DIR / f"{name}.csv"
    df.to_csv(path, index=True)
    return path


def fig_path(name: str) -> Path:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIGURES_DIR / f"{name}.png"
