"""Test whether task × model interaction is statistically significant.

Fits two OLS models on manipulation_occurred and compares via F-test:
  M0:  ~ C(model) + C(task)            (additive)
  M1:  ~ C(model) * C(task)            (with interaction)

Also reports per-cell residuals (model × task) under the additive model
to identify which cells drive the interaction.

Outputs:
- out/02_interaction_test.txt   (F-test result)
- out/02_cell_residuals.csv     (additive-model residual per model×task cell)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm

ROOT = Path(__file__).resolve().parents[2]  # paper/cross_task
CSV = ROOT / "data" / "results.csv"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV, low_memory=False)
df = df.dropna(subset=["manipulation_occurred", "model", "task"])
df["manipulation_occurred"] = df["manipulation_occurred"].astype(float)

CANONICAL = {
    "Claude-Opus-4.7", "GPT-5.5", "Gemini-3.1-Pro",
    "Grok-4", "Llama-3.3-70B", "DeepSeek-V4-Pro",
}
df = df[df["model"].isin(CANONICAL)].copy()
print(f"Canonical-roster rows: {len(df):,}")
print(f"Models: {sorted(df['model'].unique())}")
print(f"Tasks:  {sorted(df['task'].unique())}")

m0 = smf.ols("manipulation_occurred ~ C(model) + C(task)", data=df).fit()
m1 = smf.ols("manipulation_occurred ~ C(model) * C(task)", data=df).fit()

print("\n=== M0 (additive) ===")
print(f"R² = {m0.rsquared:.4f}, AIC = {m0.aic:.1f}")
print("\n=== M1 (with interaction) ===")
print(f"R² = {m1.rsquared:.4f}, AIC = {m1.aic:.1f}")

# F-test (nested model comparison)
ftest = anova_lm(m0, m1)
print("\n=== F-test: M0 vs M1 ===")
print(ftest)

# Effect-size: how much of the variance is explained by interaction alone?
ss_int = ftest["ss_diff"].iloc[1]
ss_total = ((df["manipulation_occurred"] - df["manipulation_occurred"].mean())**2).sum()
print(f"\nIncremental R² from interaction: {ss_int/ss_total:.4f}")

with open(OUT / "02_interaction_test.txt", "w") as f:
    f.write("Model comparison: M0 (additive) vs M1 (with interaction)\n")
    f.write(f"M0: manipulation_occurred ~ C(model) + C(task)   | R² = {m0.rsquared:.4f}, AIC = {m0.aic:.1f}\n")
    f.write(f"M1: manipulation_occurred ~ C(model) * C(task)   | R² = {m1.rsquared:.4f}, AIC = {m1.aic:.1f}\n\n")
    f.write(str(ftest))
    f.write(f"\n\nIncremental R² from interaction: {ss_int/ss_total:.4f}\n")

# Per-cell residuals from M0 (where does the additive model fail?)
df["pred_additive"] = m0.predict(df)
cell = (df.groupby(["model", "task"])
          .agg(mean_actual=("manipulation_occurred", "mean"),
               mean_pred=("pred_additive", "mean"),
               n=("manipulation_occurred", "size"))
          .reset_index())
cell["residual"] = cell["mean_actual"] - cell["mean_pred"]
cell = cell.sort_values("residual", key=abs, ascending=False)
cell.to_csv(OUT / "02_cell_residuals.csv", index=False)
print("\n=== Cells where additive model fails most (top 10 by |residual|) ===")
print(cell.head(10).to_string(index=False))
print(f"\nWrote {OUT / '02_interaction_test.txt'}")
print(f"Wrote {OUT / '02_cell_residuals.csv'}")
