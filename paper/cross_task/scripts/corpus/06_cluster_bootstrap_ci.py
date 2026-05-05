"""Cluster bootstrap: are the model-rate CIs from 02 honest, given that rows
within a `scenario_group` aren't independent?

Plan:
  1. ICC per task: fraction of variance in `manipulation_occurred` between
     scenario_groups vs. within. Only computable for tasks where a scenario
     identifier is populated (committee, debate, sales).
  2. Cluster bootstrap: resample whole scenario_groups (not rows), recompute
     each (model, task) rate, take the 2.5/97.5 percentiles. Compare width to
     the row-bootstrap CI.

Skip tasks where no scenario_group is available (bargaining, village).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from _loader import load, save_table

# Reuse the helper from 05
import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location("vd", pathlib.Path(__file__).with_name("05_variance_decomposition.py"))
_vd = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_vd)
add_scenario_group = _vd.add_scenario_group

RNG = np.random.default_rng(0)
N_BOOT = 1000


def icc_oneway(y: np.ndarray, group: np.ndarray) -> float:
    """Population ICC(1) — between-group variance / total variance.

    Estimator from Shrout & Fleiss (1979) one-way random effects.
    """
    df = pd.DataFrame({"y": y, "g": group}).dropna()
    if df["g"].nunique() < 2:
        return float("nan")
    grand = df["y"].mean()
    ms = df.groupby("g", observed=True)["y"].agg(["mean", "count"])
    n_bar = ms["count"].mean()
    ss_b = ((ms["count"] * (ms["mean"] - grand) ** 2)).sum()
    df_b = len(ms) - 1
    ms_b = ss_b / df_b if df_b > 0 else np.nan
    df_w = len(df) - len(ms)
    ss_w = ((df["y"] - df.groupby("g")["y"].transform("mean")) ** 2).sum()
    ms_w = ss_w / df_w if df_w > 0 else np.nan
    if not np.isfinite(ms_b) or not np.isfinite(ms_w) or ms_w == 0:
        return float("nan")
    return float((ms_b - ms_w) / (ms_b + (n_bar - 1) * ms_w))


def row_bootstrap(values: np.ndarray, n: int = N_BOOT) -> tuple[float, float]:
    if len(values) == 0:
        return (np.nan, np.nan)
    idx = RNG.integers(0, len(values), size=(n, len(values)))
    means = values[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def cluster_bootstrap(values: np.ndarray, clusters: np.ndarray, n: int = N_BOOT) -> tuple[float, float]:
    df = pd.DataFrame({"y": values, "c": clusters}).dropna()
    if df.empty:
        return (np.nan, np.nan)
    groups = [g["y"].to_numpy() for _, g in df.groupby("c", sort=False)]
    k = len(groups)
    if k < 2:
        return (np.nan, np.nan)
    means = np.empty(n)
    for i in range(n):
        pick = RNG.integers(0, k, size=k)
        cat = np.concatenate([groups[j] for j in pick])
        means[i] = cat.mean()
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main() -> None:
    df = add_scenario_group(load())

    print("=== ICC(1) per task (scenario_group as cluster) ===")
    icc_rows = []
    for task, sub in df.groupby("task", observed=True):
        if sub["scenario_group"].isna().all():
            icc_rows.append({"task": task, "n": len(sub), "n_clusters": 0, "icc": np.nan})
            continue
        y = sub["manipulation_occurred"].to_numpy(dtype=float)
        g = sub["scenario_group"].astype("string").to_numpy()
        icc = icc_oneway(y, g)
        icc_rows.append({"task": task, "n": len(sub), "n_clusters": int(sub["scenario_group"].nunique()), "icc": icc})
    icc_df = pd.DataFrame(icc_rows).set_index("task").round(4)
    print(icc_df, "\n")
    save_table(icc_df, "06_icc_per_task")

    print("=== Cluster vs. row bootstrap CI per (model, task) ===")
    ci_rows = []
    for (model, task), sub in df.groupby(["model", "task"], observed=True):
        y = sub["manipulation_occurred"].to_numpy(dtype=float)
        rate = float(y.mean()) if len(y) else np.nan
        row_lo, row_hi = row_bootstrap(y)
        if sub["scenario_group"].isna().all():
            cl_lo = cl_hi = np.nan
        else:
            cl_lo, cl_hi = cluster_bootstrap(y, sub["scenario_group"].astype("string").to_numpy())
        ci_rows.append({
            "model": model, "task": task, "n": len(y), "rate": rate,
            "row_ci_lo": row_lo, "row_ci_hi": row_hi, "row_ci_width": row_hi - row_lo,
            "cluster_ci_lo": cl_lo, "cluster_ci_hi": cl_hi, "cluster_ci_width": cl_hi - cl_lo,
        })
    ci_df = pd.DataFrame(ci_rows)
    ci_df["width_ratio"] = ci_df["cluster_ci_width"] / ci_df["row_ci_width"]
    ci_df = ci_df.sort_values(["task", "model"]).reset_index(drop=True)
    save_table(ci_df.round(4), "06_ci_comparison")

    summary = ci_df.dropna(subset=["width_ratio"]).groupby("task", observed=True)["width_ratio"].agg(["mean", "median", "min", "max"]).round(2)
    print("=== CI width inflation factor (cluster / row), per task ===")
    print(summary, "\n")
    save_table(summary, "06_width_ratio_summary")

    too_narrow = ci_df[(ci_df["width_ratio"] >= 1.5)].copy()
    too_narrow = too_narrow[["task", "model", "rate", "row_ci_width", "cluster_ci_width", "width_ratio"]]
    too_narrow = too_narrow.sort_values("width_ratio", ascending=False).round(3)
    print(f"=== Cells where row CI underestimates uncertainty by >=1.5x (n={len(too_narrow)}) ===")
    print(too_narrow.head(25).to_string(index=False), "\n")
    save_table(too_narrow, "06_cells_underestimating_uncertainty")


if __name__ == "__main__":
    main()
