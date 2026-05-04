"""Two-way ANOVA: tier x frame, tier x difficulty, tier x incentive (per task).

Uses Type II sum of squares (recommended for unbalanced designs without
significant interactions) and Type III for the interaction-aware report.
The interaction term is the main scientific question — does frame-sensitivity
differ by capability tier?

Outputs:
  paper/capability_eval/analysis/capability_anova.json
"""

from __future__ import annotations

import json

import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm

from _capability_io import ANALYSIS_DIR, ensure_dirs, load_joined, TASKS


PAIRS = [("tier", "frame"), ("tier", "incentive"), ("tier", "difficulty")]


def two_way(df: pd.DataFrame, a: str, b: str) -> dict | None:
    sub = df.dropna(subset=[a, b]).copy()
    if sub[a].nunique() < 2 or sub[b].nunique() < 2 or len(sub) < 30:
        return None
    formula = f"manipulation_metric ~ C({a}) * C({b})"
    model = smf.ols(formula, data=sub).fit()
    table = anova_lm(model, typ=2)
    out = {"n": int(len(sub)), "r_squared": float(model.rsquared), "terms": {}}
    for term, row in table.iterrows():
        out["terms"][term] = {
            "sum_sq": float(row["sum_sq"]),
            "df": float(row["df"]),
            "F": float(row["F"]) if pd.notna(row["F"]) else None,
            "p": float(row["PR(>F)"]) if pd.notna(row["PR(>F)"]) else None,
        }
    return out


def main() -> None:
    ensure_dirs()
    df = load_joined()

    summary: dict = {"per_task": {}, "pooled": {}}
    for task in TASKS:
        sub = df[df["task"] == task]
        per = {}
        for a, b in PAIRS:
            res = two_way(sub, a, b)
            if res is not None:
                per[f"{a}_x_{b}"] = res
        summary["per_task"][task] = per

    for a, b in PAIRS:
        res = two_way(df, a, b)
        if res is not None:
            summary["pooled"][f"{a}_x_{b}"] = res

    with open(ANALYSIS_DIR / "capability_anova.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote {ANALYSIS_DIR / 'capability_anova.json'}")
    print()
    print("Pooled two-way ANOVA (Type II SS) - interaction p-values:")
    for key, res in summary["pooled"].items():
        interaction_term = next((t for t in res["terms"] if ":" in t), None)
        if interaction_term:
            p = res["terms"][interaction_term]["p"]
            sig = " *" if (p is not None and p < 0.05) else ""
            print(f"  {key:25s}  interaction p={p:.4f}{sig}  (n={res['n']})")
    print()
    print("Per-task tier x frame interaction p-values:")
    for task in TASKS:
        per = summary["per_task"].get(task, {})
        res = per.get("tier_x_frame")
        if res is None:
            print(f"  {task:12s}  insufficient data")
            continue
        interaction_term = next((t for t in res["terms"] if ":" in t), None)
        p = res["terms"][interaction_term]["p"] if interaction_term else None
        sig = " *" if (p is not None and p < 0.05) else ""
        print(f"  {task:12s}  p={p:.4f}{sig}  (n={res['n']})")


if __name__ == "__main__":
    main()
