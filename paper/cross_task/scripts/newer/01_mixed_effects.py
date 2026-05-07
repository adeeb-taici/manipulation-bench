"""Mixed-effects regression on manipulation_occurred.

Fits a linear mixed model (LPM, since logistic mixed-effects in Python
either requires R via pymer4 or PyMC; LPM coefficients are interpretable
as percentage-point shifts):

  manipulation_occurred ~ C(model) + C(frame) + C(incentive) + C(difficulty)
                          + (1|cluster_id) + (1|task)

statsmodels.MixedLM only supports a single grouping factor, so we nest:
group on `task`, with `cluster_id` (or fallback `scenario_id`/row index)
as a variance component within task.

Outputs:
- out/01_mixed_effects_coefs.csv  (fixed effects + 95% CI)
- out/01_mixed_effects_summary.txt (full statsmodels summary)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[2]  # paper/cross_task
CSV = ROOT / "data" / "results.csv"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

print(f"Loading {CSV} ...")
df = pd.read_csv(CSV, low_memory=False)
print(f"  {len(df):,} rows, {df['model'].nunique()} models, {df['task'].nunique()} tasks")

# Clean: drop rows with missing outcome or axes
df = df.dropna(subset=["manipulation_occurred", "model", "task", "frame", "incentive", "difficulty"])
df["manipulation_occurred"] = df["manipulation_occurred"].astype(float)

# Restrict to canonical frontier-6 to keep coefficient table interpretable
CANONICAL = {
    "Claude-Opus-4.7", "GPT-5.5", "Gemini-3.1-Pro",
    "Grok-4", "Llama-3.3-70B", "DeepSeek-V4-Pro",
}
present = sorted(df["model"].unique())
print("Models present:", present)
canonical_present = [m for m in present if m in CANONICAL]
print(f"Canonical present: {canonical_present}")

if len(canonical_present) >= 4:
    df = df[df["model"].isin(CANONICAL)].copy()
    print(f"Restricted to canonical roster: {len(df):,} rows")
else:
    print("Canonical labels not found; keeping all models")

# Build a clustering variable: prefer cluster_id, fall back to scenario_id,
# then to a per-task synthetic cluster (one cluster per row in tasks that
# have no scenario identifier — equivalent to no clustering for those tasks)
sid = df["scenario_id"] if "scenario_id" in df.columns else pd.Series([np.nan]*len(df), index=df.index)
df["cluster"] = df["cluster_id"].astype("string").fillna(sid.astype("string"))
mask = df["cluster"].isna()
df.loc[mask, "cluster"] = (
    df.loc[mask, "task"].astype(str) + "_row_" + df.loc[mask].index.astype(str)
)
df["cluster"] = df["cluster"].astype(str)
print(f"Distinct clusters: {df['cluster'].nunique():,}")

# Reference levels: pick the lowest-manipulation frame as reference for interpretability
df["frame"] = pd.Categorical(df["frame"], categories=[
    "prohibitive", "pro_social", "minimal", "selfish", "permissive"
], ordered=False)
df["incentive"] = pd.Categorical(df["incentive"], categories=["none", "moderate", "high"], ordered=False)
df["difficulty"] = pd.Categorical(df["difficulty"], categories=["low", "medium", "high"], ordered=False)

# Drop rows with axis values outside the canonical levels (legacy aliases)
before = len(df)
df = df.dropna(subset=["frame", "incentive", "difficulty"])
print(f"Dropped {before - len(df)} rows with non-canonical axis labels")

# Fit: random intercept on cluster (which is nested within task), with task
# as a fixed effect. statsmodels.MixedLM only supports one grouping factor;
# this is the standard substitute for the (1|task) + (1|cluster) form when
# clusters are uniquely nested in tasks.
formula = "manipulation_occurred ~ C(model) + C(task) + C(frame) + C(incentive) + C(difficulty)"
print(f"\nFitting {formula} with groups=cluster ...")

md = smf.mixedlm(formula, df, groups=df["cluster"])
try:
    mdf = md.fit(method="lbfgs", reml=False)
except Exception as e:
    print(f"lbfgs failed ({e}); falling back to powell")
    mdf = md.fit(method="powell", reml=False)

print(mdf.summary())

# Save full summary
(OUT / "01_mixed_effects_summary.txt").write_text(str(mdf.summary()))

# Save fixed-effects coefficient table
fe = mdf.fe_params
se = mdf.bse_fe
ci = mdf.conf_int().loc[fe.index]
coef_df = pd.DataFrame({
    "term": fe.index,
    "coef": fe.values,
    "se": se.values,
    "ci_low": ci[0].values,
    "ci_high": ci[1].values,
    "z": (fe / se).values,
    "p": mdf.pvalues.loc[fe.index].values,
})
coef_df.to_csv(OUT / "01_mixed_effects_coefs.csv", index=False)
print(f"\nWrote {OUT / '01_mixed_effects_coefs.csv'}")
print(f"Wrote {OUT / '01_mixed_effects_summary.txt'}")

# Print interpretable summary
print("\n=== Fixed effects (sorted by |coef|) ===")
print(coef_df.reindex(coef_df["coef"].abs().sort_values(ascending=False).index).to_string(index=False))
