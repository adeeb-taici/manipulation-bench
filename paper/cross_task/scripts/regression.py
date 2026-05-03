"""Per-(task, model, axis) regression + Dunnett contrasts.

For each task × model × axis cut:
  - Omnibus axis effect: OLS F-test on the categorical-axis term.
  - Per-task eta^2: SS_axis / SS_total on the same fit.
  - Pairwise contrasts vs. baseline level (prohibitive / none / low):
    scipy.stats.dunnett, two-sided, 95% CI.
  - Polynomial sensitivity: linear + quadratic orthogonal-polynomial
    coefficients (statsmodels OLS) — diagnostic only.
  - SE strategy:
      bargaining, village -> HC3
      debate              -> cluster on claim_id
      sales               -> cluster on scenario_id
      committee           -> cluster on slate_id
  - Saturation flag: residual SD < 1e-6 anywhere -> mark cell saturated.

Companion: per-task axis x model interaction LR test (run on the same
data inside the per-task driver).

Outputs go to paper/task<N>/analysis/regression_v2.json (one per task).
The schema is documented at the bottom of this module.
"""

from __future__ import annotations

import json
import math
import sys
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import dunnett

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))

from load import CANONICAL_MODELS, CLUSTER_COL, load_corpus  # noqa: E402

AXES_BY_TASK = {
    "bargaining": ("frame", "incentive", "difficulty"),
    "debate":     ("frame", "incentive", "difficulty"),
    "village":    ("frame", "incentive", "difficulty"),  # incentive included; T3 is verbal-only — flagged
    "sales":      ("frame", "incentive", "difficulty"),
    "committee":  ("frame", "incentive", "difficulty"),
}

AXIS_LEVELS = {
    "frame":      ("prohibitive", "pro_social", "minimal", "selfish", "permissive"),
    "incentive":  ("none", "moderate", "high"),
    "difficulty": ("low", "medium", "high"),
}

OUT_DIR_BY_TASK = {
    "bargaining": "paper/task1_bargaining/analysis/regression_v2.json",
    "debate":     "paper/task2_debate/analysis/regression_v2.json",
    "village":    "paper/task3_village/analysis/regression_v2.json",
    "sales":      "paper/task4_sales/analysis/regression_v2.json",
    "committee":  "paper/task5_committee/analysis/regression_v2.json",
}

LOW_POWER_TASKS = {"village"}  # ~2 traj/cell after full stratification


def _fit_kwargs(task: str, df_chunk: pd.DataFrame) -> tuple[dict, str]:
    """Return statsmodels .fit() kwargs and a label describing the SE strategy.

    Loader stores the per-task cluster id in a uniform 'cluster_id' column;
    CLUSTER_COL[task] tells us which underlying field that came from for labeling.
    """
    cluster_col = CLUSTER_COL.get(task)
    if cluster_col is not None and "cluster_id" in df_chunk.columns:
        groups = df_chunk["cluster_id"]
        if groups.notna().all() and groups.nunique() > 1:
            return ({"cov_type": "cluster", "cov_kwds": {"groups": groups.values}},
                    f"cluster_on_{cluster_col}")
    return ({"cov_type": "HC3"}, "HC3")


def _eta_squared(model_fit: Any, term: str) -> float | None:
    """eta^2 = SS_term / SS_total via Type II ANOVA."""
    from statsmodels.stats.anova import anova_lm
    try:
        anova = anova_lm(model_fit, typ=2)
    except Exception:
        return None
    if term not in anova.index:
        return None
    ss_term = float(anova.loc[term, "sum_sq"])
    ss_resid = float(anova.loc["Residual", "sum_sq"])
    ss_other_terms = float(anova["sum_sq"].sum() - ss_term - ss_resid)
    ss_total = ss_term + ss_resid + ss_other_terms
    return ss_term / ss_total if ss_total > 0 else None


def _per_task_eta(df_task: pd.DataFrame, axes: tuple[str, ...], task: str) -> dict[str, Any]:
    """Per-task partition of variance: eta^2 for each axis with model added.

    Single fit: y ~ C(model) + C(frame) + C(incentive) + C(difficulty)
    eta^2 = SS_term / SS_total (type II) for each term + residual SS proportion.
    """
    sub = df_task.dropna(subset=["metric", "model", *axes]).copy()
    for col in axes + ("model",):
        sub[col] = sub[col].astype("category")
    formula = "metric ~ " + " + ".join(f"C({c})" for c in ("model", *axes))
    fit_kw, se_label = _fit_kwargs(task, sub)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = smf.ols(formula, data=sub).fit(**fit_kw)

    from statsmodels.stats.anova import anova_lm
    try:
        anova = anova_lm(fit, typ=2)
    except Exception:
        return {"se_method": se_label, "n": len(sub), "eta_squared": {}}

    ss_total = float(anova["sum_sq"].sum())
    eta = {}
    for term in anova.index:
        ss = float(anova.loc[term, "sum_sq"])
        eta[term] = ss / ss_total if ss_total > 0 else None
    return {"se_method": se_label, "n": int(len(sub)), "eta_squared": eta, "ss_total": ss_total}


def _regression_cell(df_cell: pd.DataFrame, task: str, axis: str) -> dict[str, Any]:
    """Run the per-(task, model, axis) regression on one cell."""
    levels = AXIS_LEVELS[axis]
    baseline = levels[0]

    cell = df_cell.dropna(subset=["metric", axis]).copy()
    if len(cell) == 0:
        return {"n": 0, "skipped": "empty"}
    cell[axis] = pd.Categorical(cell[axis], categories=levels, ordered=False)
    levels_present = [lv for lv in levels if (cell[axis] == lv).any()]

    # Saturation check
    per_level_std = {lv: float(cell.loc[cell[axis] == lv, "metric"].std(ddof=1) or 0.0)
                     for lv in levels_present}
    saturated_levels = [lv for lv, s in per_level_std.items() if s < 1e-6]

    out: dict[str, Any] = {
        "n": int(len(cell)),
        "per_level_n": {lv: int((cell[axis] == lv).sum()) for lv in levels_present},
        "per_level_mean": {lv: float(cell.loc[cell[axis] == lv, "metric"].mean()) for lv in levels_present},
        "per_level_std": per_level_std,
        "saturated_levels": saturated_levels,
        "low_power_warning": task in LOW_POWER_TASKS,
    }

    # Need >= 2 levels with at least 2 obs for an F-test
    sufficient_levels = [lv for lv in levels_present if (cell[axis] == lv).sum() >= 2]
    if len(sufficient_levels) < 2 or baseline not in sufficient_levels:
        out["skipped"] = "insufficient_levels"
        return out

    # OLS for omnibus F + eta^2
    formula = f'metric ~ C({axis}, Treatment(reference="{baseline}"))'
    fit_kw, se_label = _fit_kwargs(task, cell)
    out["se_method"] = se_label
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = smf.ols(formula, data=cell).fit(**fit_kw)
        # Omnibus F via robust f_test
        contrast_names = [
            f'C({axis}, Treatment(reference="{baseline}"))[T.{lv}]'
            for lv in sufficient_levels if lv != baseline
        ]
        if contrast_names:
            hyp = ", ".join(f"{cn} = 0" for cn in contrast_names)
            f_test = fit.f_test(hyp)
            out["omnibus_F"] = float(np.asarray(f_test.fvalue).ravel()[0])
            out["omnibus_p"] = float(np.asarray(f_test.pvalue).ravel()[0])
            out["omnibus_df"] = [int(f_test.df_num), int(f_test.df_denom)]
        out["eta_squared"] = float(fit.rsquared)
    except Exception as e:
        out["fit_error"] = str(e)

    # Dunnett contrasts vs baseline (using raw arrays — exact Dunnett, not robust SEs).
    # The per-cell sample size is large enough for OLS+robust SEs to track Dunnett closely;
    # we report Dunnett because the brief explicitly calls for it.
    if baseline in sufficient_levels:
        control = cell.loc[cell[axis] == baseline, "metric"].values.astype(float)
        treatments_data: list[np.ndarray] = []
        treatment_levels: list[str] = []
        for lv in sufficient_levels:
            if lv == baseline:
                continue
            arr = cell.loc[cell[axis] == lv, "metric"].values.astype(float)
            treatments_data.append(arr)
            treatment_levels.append(lv)

        out["dunnett"] = []
        if len(treatments_data) >= 1 and len(control) >= 2:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    res = dunnett(*treatments_data, control=control)
                ci = res.confidence_interval(confidence_level=0.95)
                for lv, t_arr, stat, pval, lo, hi in zip(
                    treatment_levels, treatments_data, res.statistic, res.pvalue, ci.low, ci.high
                ):
                    diff = float(t_arr.mean() - control.mean())
                    out["dunnett"].append({
                        "level": lv,
                        "diff_vs_baseline": diff,
                        "ci_lo": float(lo) if not (isinstance(lo, float) and math.isnan(lo)) else None,
                        "ci_hi": float(hi) if not (isinstance(hi, float) and math.isnan(hi)) else None,
                        "statistic": float(stat),
                        "p_value": float(pval) if not (isinstance(pval, float) and math.isnan(pval)) else None,
                        "saturated_treatment": lv in saturated_levels,
                        "saturated_baseline": baseline in saturated_levels,
                    })
            except Exception as e:
                out["dunnett_error"] = str(e)

    # Polynomial sensitivity: linear + quadratic on level-index encoding
    try:
        idx_map = {lv: i for i, lv in enumerate(levels_present)}
        cell["_idx"] = cell[axis].astype(str).map(idx_map).astype(float)
        # Center the index for cleaner orthogonality
        x = cell["_idx"].values
        x_c = x - x.mean()
        cell["_lin"] = x_c
        cell["_quad"] = x_c ** 2 - (x_c ** 2).mean()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            poly_fit = smf.ols("metric ~ _lin + _quad", data=cell).fit(**fit_kw)
        out["polynomial"] = {
            "linear_coef": float(poly_fit.params.get("_lin", math.nan)),
            "linear_p":    float(poly_fit.pvalues.get("_lin", math.nan)),
            "quadratic_coef": float(poly_fit.params.get("_quad", math.nan)),
            "quadratic_p":    float(poly_fit.pvalues.get("_quad", math.nan)),
        }
    except Exception as e:
        out["polynomial_error"] = str(e)

    return out


def _interaction_lr(df_task: pd.DataFrame, axis: str, task: str) -> dict[str, Any]:
    """F-test for axis x model interaction within a task."""
    sub = df_task.dropna(subset=["metric", "model", axis]).copy()
    if len(sub) == 0 or sub["model"].nunique() < 2:
        return {"skipped": "insufficient_data"}
    sub["model"] = sub["model"].astype("category")
    sub[axis] = pd.Categorical(sub[axis], categories=AXIS_LEVELS[axis], ordered=False)

    fit_kw, se_label = _fit_kwargs(task, sub)
    full_f  = f"metric ~ C(model) * C({axis})"
    main_f  = f"metric ~ C(model) + C({axis})"
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            full = smf.ols(full_f, data=sub).fit(**fit_kw)
            main = smf.ols(main_f, data=sub).fit(**fit_kw)
            # Wald F-test on the interaction coefficients
            interaction_terms = [p for p in full.params.index if ":" in p]
            if not interaction_terms:
                return {"skipped": "no_interaction_terms"}
            hyp = ", ".join(f"{t} = 0" for t in interaction_terms)
            ft = full.f_test(hyp)
        # Detect rank-deficient covariance from statsmodels' ValueWarning.
        # When this fires, the reported F is computed against a rank-deficient
        # covariance and is not meaningful; we report n/a instead.
        rank_def = any(
            "covariance of constraints does not have full rank" in str(w.message)
            for w in caught
        )
        F_val = float(np.asarray(ft.fvalue).ravel()[0])
        p_val = float(np.asarray(ft.pvalue).ravel()[0])
        # Also catch absurd F values (>1e6 or non-finite) that survived warnings:
        absurd = (not np.isfinite(F_val)) or abs(F_val) > 1e6
        out = {
            "se_method": se_label,
            "n": int(len(sub)),
            "interaction_F": F_val,
            "interaction_p": p_val,
            "interaction_df": [int(ft.df_num), int(ft.df_denom)],
            "n_interaction_terms": len(interaction_terms),
        }
        if rank_def or absurd:
            out["rank_deficient"] = True
            out["F_not_estimable"] = True
            out["note"] = (
                "Wald F-test covariance is rank-deficient (some interaction "
                "cell is saturated). F and p values are reported but should "
                "not be interpreted; treat as not estimable."
            )
        return out
    except Exception as e:
        return {"error": str(e), "se_method": se_label}


def run_regression(df: pd.DataFrame, task: str) -> dict[str, Any]:
    """Run per-(model, axis) regression + axis x model interaction LR for one task."""
    df_task = df[df["task"] == task]
    axes = AXES_BY_TASK[task]
    out: dict[str, Any] = {
        "task": task,
        "n_rows": int(len(df_task)),
        "axes": list(axes),
        "models": [m for m in CANONICAL_MODELS if m in set(df_task["model"].unique())],
        "low_power_warning": task in LOW_POWER_TASKS,
        "per_task_eta": _per_task_eta(df_task, axes, task),
        "interaction_lr": {},
        "per_model": defaultdict(dict),
    }
    for axis in axes:
        out["interaction_lr"][axis] = _interaction_lr(df_task, axis, task)
    for model in out["models"]:
        df_cell = df_task[df_task["model"] == model]
        for axis in axes:
            out["per_model"][model][axis] = _regression_cell(df_cell, task, axis)
    out["per_model"] = {k: dict(v) for k, v in out["per_model"].items()}
    return out


def main() -> None:
    df = load_corpus(verbose=False)
    print(f"[regression] loaded {len(df)} rows", file=sys.stderr)

    for task in ("bargaining", "debate", "village", "sales", "committee"):
        result = run_regression(df, task)
        out_path = REPO / OUT_DIR_BY_TASK[task]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"[regression] {task}: wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
