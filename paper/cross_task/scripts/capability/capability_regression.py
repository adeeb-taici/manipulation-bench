"""OLS regression: manipulation_rate ~ ELO + frame + incentive + difficulty.

Fits two specifications:

  1. Per-task: separate OLS for each task. Reports the ELO coefficient
     (per +100 ELO) with HC3 robust standard errors and 95% CI.
  2. Pooled: all tasks stacked, with task fixed effects. Same ELO coefficient
     interpretation, controlling for cross-task differences in baseline rate.

Outputs:
  paper/cross_task/analysis/capability_regression.json
  paper/cross_task/figures/capability/capability_regression_coefs.png
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from _capability_io import ANALYSIS_DIR, FIG_DIR, FRAMES, INCENTIVES, DIFFICULTIES, TASKS, ensure_dirs, load_joined


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["elo_centered_per100"] = (out["elo"] - 1400) / 100
    for col, levels in (("frame", FRAMES), ("incentive", INCENTIVES), ("difficulty", DIFFICULTIES)):
        out[col] = pd.Categorical(out[col], categories=levels, ordered=False)
    return out


def fit_per_task(df: pd.DataFrame) -> dict:
    out = {}
    for task in TASKS:
        sub = df[df["task"] == task].dropna(subset=["frame", "incentive", "difficulty"])
        if len(sub) < 30 or sub["elo"].nunique() < 4:
            out[task] = {"n": int(len(sub)), "skipped": "insufficient data"}
            continue
        terms = ["elo_centered_per100"]
        for col in ("frame", "incentive", "difficulty"):
            if sub[col].nunique() > 1:
                terms.append(f"C({col})")
        formula = "manipulation_metric ~ " + " + ".join(terms)
        model = smf.ols(formula, data=sub).fit(cov_type="HC3")
        ci = model.conf_int().loc["elo_centered_per100"].tolist()
        out[task] = {
            "n": int(len(sub)),
            "elo_coef_per_100elo": float(model.params["elo_centered_per100"]),
            "elo_se": float(model.bse["elo_centered_per100"]),
            "elo_p": float(model.pvalues["elo_centered_per100"]),
            "elo_ci95": [float(ci[0]), float(ci[1])],
            "r_squared": float(model.rsquared),
            "formula": formula,
        }
    return out


def fit_pooled(df: pd.DataFrame) -> dict:
    sub = df.dropna(subset=["frame", "incentive", "difficulty"]).copy()
    sub["task"] = pd.Categorical(sub["task"], categories=TASKS)
    formula = "manipulation_metric ~ elo_centered_per100 + C(task) + C(frame) + C(incentive) + C(difficulty)"
    model = smf.ols(formula, data=sub).fit(cov_type="HC3")
    ci = model.conf_int().loc["elo_centered_per100"].tolist()
    return {
        "n": int(len(sub)),
        "elo_coef_per_100elo": float(model.params["elo_centered_per100"]),
        "elo_se": float(model.bse["elo_centered_per100"]),
        "elo_p": float(model.pvalues["elo_centered_per100"]),
        "elo_ci95": [float(ci[0]), float(ci[1])],
        "r_squared": float(model.rsquared),
        "formula": formula,
    }


def fit_pooled_with_interactions(df: pd.DataFrame) -> dict:
    """Test whether ELO effect varies by task (ELO × task interaction)."""
    sub = df.dropna(subset=["frame", "incentive", "difficulty"]).copy()
    sub["task"] = pd.Categorical(sub["task"], categories=TASKS)
    formula = (
        "manipulation_metric ~ elo_centered_per100 * C(task) "
        "+ C(frame) + C(incentive) + C(difficulty)"
    )
    model = smf.ols(formula, data=sub).fit(cov_type="HC3")
    interaction_terms = [k for k in model.params.index if "elo_centered_per100:" in k]
    return {
        "n": int(len(sub)),
        "r_squared": float(model.rsquared),
        "elo_main_effect": float(model.params["elo_centered_per100"]),
        "elo_main_p": float(model.pvalues["elo_centered_per100"]),
        "interaction_coefs": {k: float(model.params[k]) for k in interaction_terms},
        "interaction_pvalues": {k: float(model.pvalues[k]) for k in interaction_terms},
    }


def plot_per_task_coefs(per_task: dict, out_path) -> None:
    rows = [(t, d) for t, d in per_task.items() if "elo_coef_per_100elo" in d]
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    tasks = [t for t, _ in rows]
    coefs = [d["elo_coef_per_100elo"] for _, d in rows]
    los = [d["elo_ci95"][0] for _, d in rows]
    his = [d["elo_ci95"][1] for _, d in rows]
    yerr = [[c - lo for c, lo in zip(coefs, los)], [hi - c for c, hi in zip(coefs, his)]]
    colors = ["#cb4335" if d["elo_p"] < 0.05 else "#7f8c8d" for _, d in rows]
    ax.errorbar(range(len(tasks)), coefs, yerr=yerr, fmt="o", capsize=4,
                ecolor="black", elinewidth=1, mfc="white", mec="black")
    for i, c in enumerate(colors):
        ax.scatter([i], [coefs[i]], color=c, s=80, zorder=3, edgecolors="black")
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xticks(range(len(tasks)))
    ax.set_xticklabels(tasks, rotation=20, ha="right")
    ax.set_ylabel("ELO coefficient (delta manipulation rate per +100 ELO)")
    ax.set_title("Per-task OLS: ELO effect on manipulation rate, controlling for axis cell")
    ax.grid(True, alpha=0.3, axis="y")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    ensure_dirs()
    df = _prep(load_joined())

    per_task = fit_per_task(df)
    pooled = fit_pooled(df)
    interaction = fit_pooled_with_interactions(df)

    summary = {
        "per_task": per_task,
        "pooled_with_task_fe": pooled,
        "pooled_with_elo_x_task_interaction": interaction,
        "elo_unit": "per +100 ELO points; ELO centered at 1400",
    }
    with open(ANALYSIS_DIR / "capability_regression.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    plot_per_task_coefs(per_task, FIG_DIR / "capability_regression_coefs.png")

    print(f"Wrote {ANALYSIS_DIR / 'capability_regression.json'}")
    print(f"Wrote {FIG_DIR / 'capability_regression_coefs.png'}")
    print()
    print("Per-task OLS: ELO coefficient (delta rate per +100 ELO, HC3 SE, controlling for frame/incentive/difficulty):")
    for t in TASKS:
        d = per_task.get(t, {})
        if "elo_coef_per_100elo" not in d:
            print(f"  {t:12s}  skipped: {d.get('skipped','?')}")
            continue
        sig = " *" if d["elo_p"] < 0.05 else ""
        print(f"  {t:12s}  n={d['n']:5d}  beta={d['elo_coef_per_100elo']:+.4f}  "
              f"SE={d['elo_se']:.4f}  p={d['elo_p']:.3f}  R^2={d['r_squared']:.3f}{sig}")
    print()
    print(f"Pooled (task FE): beta={pooled['elo_coef_per_100elo']:+.4f}  "
          f"95% CI=[{pooled['elo_ci95'][0]:+.4f}, {pooled['elo_ci95'][1]:+.4f}]  "
          f"p={pooled['elo_p']:.3f}  R^2={pooled['r_squared']:.3f}  n={pooled['n']}")


if __name__ == "__main__":
    main()
