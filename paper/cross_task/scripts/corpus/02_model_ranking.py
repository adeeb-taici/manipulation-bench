"""Model x task manipulation rates with honest CIs and rank correlation.

CI method per cell:
  - cluster-bootstrap over scenario_group when one is populated for that task
    (committee, debate, sales). ICC(1) ~0.36-0.42 in those tasks, so
    row-bootstrap CIs are 2.5x-4x too narrow. See 06.
  - row-bootstrap when no scenario_group is available (bargaining, village).

The output table includes a `ci_method` column so consumers can tell which
cells are honest scenario-clustered intervals vs. row-level intervals.
"""
from __future__ import annotations
import importlib.util
import pathlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from _loader import load, save_table, fig_path

_spec = importlib.util.spec_from_file_location(
    "vd", pathlib.Path(__file__).with_name("05_variance_decomposition.py")
)
_vd = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_vd)
add_scenario_group = _vd.add_scenario_group

RNG = np.random.default_rng(0)
N_BOOT = 1000


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
        means[i] = np.concatenate([groups[j] for j in pick]).mean()
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def rate_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, task), sub in df.groupby(["model", "task"], observed=True):
        v = sub["manipulation_occurred"].to_numpy(dtype=float)
        if sub["scenario_group"].notna().any() and sub["scenario_group"].nunique() >= 2:
            clusters = sub["scenario_group"].astype("string").to_numpy()
            lo, hi = cluster_bootstrap(v, clusters)
            method = "cluster"
        else:
            lo, hi = row_bootstrap(v)
            method = "row"
        rows.append({"model": model, "task": task, "n": len(v),
                     "rate": float(v.mean()), "ci_lo": lo, "ci_hi": hi,
                     "ci_method": method})
    return pd.DataFrame(rows)


def heatmap(pivot: pd.DataFrame, title: str, out: str) -> None:
    fig, ax = plt.subplots(figsize=(1.2 * pivot.shape[1] + 2, 0.4 * pivot.shape[0] + 2))
    im = ax.imshow(pivot.values, aspect="auto", cmap="magma_r", vmin=0, vmax=1)
    ax.set_xticks(range(pivot.shape[1]))
    ax.set_xticklabels(pivot.columns, rotation=30, ha="right")
    ax.set_yticks(range(pivot.shape[0]))
    ax.set_yticklabels(pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                        color="white" if v > 0.5 else "black", fontsize=8)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="manipulation_occurred rate")
    fig.tight_layout()
    fig.savefig(fig_path(out), dpi=150)
    plt.close(fig)


def main() -> None:
    df = add_scenario_group(load())

    print("=== Model x task manipulation rate (all variants pooled) ===")
    rates = rate_table(df)
    pivot = rates.pivot(index="model", columns="task", values="rate")
    pivot["__mean__"] = pivot.mean(axis=1)
    pivot = pivot.sort_values("__mean__", ascending=False)
    print(pivot.round(3), "\n")
    save_table(pivot, "02_model_task_rate_pooled")
    heatmap(pivot.drop(columns="__mean__"), "Manipulation rate by model x task (pooled)",
            "02_model_task_heatmap_pooled")

    full = (rates.set_index(["model", "task"])
                [["n", "rate", "ci_lo", "ci_hi", "ci_method"]]
                .sort_index())
    full["ci_width"] = full["ci_hi"] - full["ci_lo"]
    save_table(full.round(4), "02_model_task_rate_with_ci")

    print("=== CI method used per task ===")
    print(full.reset_index().groupby("task", observed=True)["ci_method"].agg(lambda s: s.unique()[0]).to_string(), "\n")

    print("=== Canonical variant only ===")
    rates_c = rate_table(df[df["variant"] == "canonical"])
    pivot_c = rates_c.pivot(index="model", columns="task", values="rate")
    pivot_c["__mean__"] = pivot_c.mean(axis=1)
    pivot_c = pivot_c.sort_values("__mean__", ascending=False)
    print(pivot_c.round(3), "\n")
    save_table(pivot_c, "02_model_task_rate_canonical")
    heatmap(pivot_c.drop(columns="__mean__"), "Manipulation rate by model x task (canonical)",
            "02_model_task_heatmap_canonical")

    full_c = (rates_c.set_index(["model", "task"])
                    [["n", "rate", "ci_lo", "ci_hi", "ci_method"]]
                    .sort_index())
    full_c["ci_width"] = full_c["ci_hi"] - full_c["ci_lo"]
    save_table(full_c.round(4), "02_model_task_rate_with_ci_canonical")

    print("=== Spearman rank correlation between tasks (does manipulation transfer?) ===")
    rank_input = pivot.drop(columns="__mean__")
    rho = rank_input.corr(method="spearman")
    print(rho.round(2), "\n")
    save_table(rho, "02_task_rank_correlation_pooled")

    rho_c = pivot_c.drop(columns="__mean__").corr(method="spearman")
    print("--- canonical only ---")
    print(rho_c.round(2), "\n")
    save_table(rho_c, "02_task_rank_correlation_canonical")


if __name__ == "__main__":
    main()
