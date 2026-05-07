"""Variance decomposition: how much of `manipulation_occurred` is explained by
model, scenario, axes, topology, vs. residual?

We use the linear-probability-model interpretation (OLS on a 0/1 outcome) for
variance attribution. For each grouping factor we compute eta-squared as

    eta2(g) = SS_between_groups(g) / SS_total

where SS_between is the standard one-way between-group sum of squares. This is
the marginal (Type I in the limit of orthogonal data) variance attribution. It
double-counts when factors are correlated — e.g. if Gemini disproportionately
drew permissive scenarios, eta2(model) and eta2(frame) overlap. We surface that
by also reporting partial omega-squared on the axis subset and by checking
factor balance per task.

The CANARY: if eta2(scenario_group) >= eta2(model), the per-model rankings in
02_model_ranking.py are partly a topic-coverage artifact, not a model property.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from _loader import load, save_table, fig_path

FACTORS = ["model", "frame", "incentive", "difficulty", "scenario_group"]


def add_scenario_group(df: pd.DataFrame) -> pd.DataFrame:
    """Pick the best-populated scenario-identifying column per task.

    The CSV's identifier columns are inconsistent:
      bargaining, village -> no scenario/cluster column populated
      committee, debate   -> cluster_id is populated
      sales               -> scenario_group and cluster_id both populated
    """
    out = df.copy()
    out["scenario_group"] = pd.NA
    for task, sub in df.groupby("task", observed=True):
        for col in ("scenario_group", "cluster_id"):
            if col in sub and sub[col].notna().any():
                out.loc[sub.index, "scenario_group"] = sub[col].astype("string")
                break
    return out


def eta_squared(y: np.ndarray, group: np.ndarray) -> tuple[float, int]:
    """One-way eta^2 of y by group. Returns (eta2, num_groups)."""
    if len(y) == 0:
        return (np.nan, 0)
    grand = y.mean()
    ss_total = float(((y - grand) ** 2).sum())
    if ss_total == 0:
        return (0.0, 0)
    df = pd.DataFrame({"y": y, "g": group})
    means = df.groupby("g", observed=True)["y"].agg(["mean", "count"])
    ss_between = float((means["count"] * (means["mean"] - grand) ** 2).sum())
    return (ss_between / ss_total, int(len(means)))


def omega_squared(y: np.ndarray, group: np.ndarray) -> float:
    """Less biased than eta^2 for high-cardinality factors. One-way only."""
    if len(y) == 0:
        return np.nan
    grand = y.mean()
    df = pd.DataFrame({"y": y, "g": group})
    means = df.groupby("g", observed=True)["y"].agg(["mean", "count"])
    k = len(means)
    n = len(y)
    if k <= 1 or n <= k:
        return np.nan
    ss_between = float((means["count"] * (means["mean"] - grand) ** 2).sum())
    ss_total = float(((y - grand) ** 2).sum())
    if ss_total == 0:
        return 0.0
    ss_within = ss_total - ss_between
    ms_within = ss_within / (n - k)
    omega2 = (ss_between - (k - 1) * ms_within) / (ss_total + ms_within)
    return float(max(omega2, 0.0))


def main() -> None:
    df = add_scenario_group(load())
    rows_eta, rows_omega, rows_levels = [], [], []
    for task, sub in df.groupby("task", observed=True):
        y = sub["manipulation_occurred"].to_numpy(dtype=float)
        for f in FACTORS:
            if f not in sub.columns or sub[f].nunique(dropna=True) < 2:
                rows_eta.append({"task": task, "factor": f, "eta2": np.nan})
                rows_omega.append({"task": task, "factor": f, "omega2": np.nan})
                rows_levels.append({"task": task, "factor": f, "n_levels": sub[f].nunique(dropna=True) if f in sub else 0})
                continue
            g = sub[f].astype("string").fillna("__NA__").to_numpy()
            e2, k = eta_squared(y, g)
            rows_eta.append({"task": task, "factor": f, "eta2": e2})
            rows_omega.append({"task": task, "factor": f, "omega2": omega_squared(y, g)})
            rows_levels.append({"task": task, "factor": f, "n_levels": k})

    eta = pd.DataFrame(rows_eta).pivot(index="factor", columns="task", values="eta2").reindex(FACTORS)
    omega = pd.DataFrame(rows_omega).pivot(index="factor", columns="task", values="omega2").reindex(FACTORS)
    levels = pd.DataFrame(rows_levels).pivot(index="factor", columns="task", values="n_levels").reindex(FACTORS)

    print("=== eta^2 per factor (marginal one-way) ===")
    print(eta.round(3), "\n")
    save_table(eta.round(4), "05_eta_squared")

    print("=== omega^2 per factor (less biased for high-cardinality factors) ===")
    print(omega.round(3), "\n")
    save_table(omega.round(4), "05_omega_squared")

    print("=== Factor levels per task ===")
    print(levels.fillna(0).astype(int), "\n")
    save_table(levels, "05_factor_levels")

    print("=== CANARY: scenario_group vs model variance share (eta^2) ===")
    canary = pd.DataFrame({
        "eta2_model": eta.loc["model"],
        "eta2_scenario_group": eta.loc["scenario_group"],
    })
    canary["scenario_dominates"] = canary["eta2_scenario_group"] >= canary["eta2_model"]
    canary["ratio_scenario_over_model"] = canary["eta2_scenario_group"] / canary["eta2_model"]
    print(canary.round(3), "\n")
    save_table(canary, "05_canary_scenario_vs_model")

    omega_canary = pd.DataFrame({
        "omega2_model": omega.loc["model"],
        "omega2_scenario_group": omega.loc["scenario_group"],
    })
    omega_canary["scenario_dominates"] = omega_canary["omega2_scenario_group"] >= omega_canary["omega2_model"]
    print("=== Same canary using omega^2 (preferred for fairness given scenario_group has many levels) ===")
    print(omega_canary.round(3), "\n")
    save_table(omega_canary, "05_canary_scenario_vs_model_omega")

    fig, ax = plt.subplots(figsize=(8, 5))
    plot_df = eta.fillna(0).T
    bottom = np.zeros(len(plot_df))
    for f in FACTORS:
        if f in plot_df.columns:
            ax.bar(plot_df.index, plot_df[f].values, bottom=bottom, label=f)
            bottom = bottom + plot_df[f].values
    ax.set_ylabel("eta^2 (marginal, sum may exceed 1 when factors are correlated)")
    ax.set_title("Variance attribution per task (manipulation_occurred)")
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(fig_path("05_variance_stacked"), dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
