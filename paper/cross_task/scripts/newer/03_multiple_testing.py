"""Apply Holm and Benjamini-Hochberg FDR corrections to the p-values
reported across paper/cross_task/scripts/capability/FINDINGS.md and paper/cross_task/scripts/corpus/FINDINGS.md.

The p-values below are transcribed from those documents. Update the
table when new tests are added; the script just re-runs the corrections.

Outputs:
- out/03_multiple_testing.csv   (raw p, holm p, BH p, survives@0.05)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from statsmodels.stats.multitest import multipletests

OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

# Transcribed from the four findings docs. Each row: (family, test, p_raw)
# "family" lets us correct within a family if desired (e.g., per-task ELO).
TESTS = [
    # capability-axis: per-task ELO regression (F1)
    ("ELO_per_task", "village β=-0.062",       1e-4),
    ("ELO_per_task", "sales β=-0.020",         1e-4),
    ("ELO_per_task", "debate β=-0.008",        0.005),
    ("ELO_per_task", "bargaining β=-0.004",    0.43),
    ("ELO_per_task", "inbox β=+0.029",         0.015),
    ("ELO_per_task", "committee β=+1.55",      1e-4),

    # capability-axis: tier × frame ANOVA (F2) per task
    ("tier_x_frame", "bargaining",  1e-4),
    ("tier_x_frame", "debate",      0.98),
    ("tier_x_frame", "village",     1e-4),
    ("tier_x_frame", "sales",       0.54),
    ("tier_x_frame", "committee",   1e-4),
    ("tier_x_frame", "inbox",       0.003),
    ("tier_x_frame", "pooled",      1e-4),

    # capability-axis: tier × incentive ANOVA (one row reported)
    ("tier_x_incentive", "pooled",  0.80),

    # csv/FINDINGS variance decomposition: model η² (chi-square against 0
    # is not reported in the doc; we only have the descriptive η²). Skipped
    # from p-value correction — listed here as a comment for the record.
    # ("variance_decomp", "model η²"), no p

    # csv/FINDINGS §5: scorer correlations (committee orthogonal scorers)
    # reported as r values, not p values; skipped.

    # legacy FINDINGS §15 debate frame×incentive: reported as Δ values,
    # no formal p reported. Skipped.

    # csv/FINDINGS §3: per-task scenario η² is descriptive (no p). Skipped.
]

df = pd.DataFrame(TESTS, columns=["family", "test", "p_raw"])

# Global correction across all tests
_, holm_global, _, _ = multipletests(df["p_raw"], method="holm")
_, bh_global, _, _ = multipletests(df["p_raw"], method="fdr_bh")
df["p_holm_global"] = holm_global
df["p_bh_global"] = bh_global
df["survives_holm_0.05"] = df["p_holm_global"] < 0.05
df["survives_bh_0.05"] = df["p_bh_global"] < 0.05

# Within-family correction (more standard for "per-task" panels)
df["p_holm_family"] = float("nan")
df["p_bh_family"] = float("nan")
for fam, idx in df.groupby("family").groups.items():
    if len(idx) <= 1:
        df.loc[idx, "p_holm_family"] = df.loc[idx, "p_raw"].values
        df.loc[idx, "p_bh_family"] = df.loc[idx, "p_raw"].values
        continue
    _, ph, _, _ = multipletests(df.loc[idx, "p_raw"], method="holm")
    _, pb, _, _ = multipletests(df.loc[idx, "p_raw"], method="fdr_bh")
    df.loc[idx, "p_holm_family"] = ph
    df.loc[idx, "p_bh_family"] = pb

df["survives_holm_family_0.05"] = df["p_holm_family"] < 0.05
df["survives_bh_family_0.05"] = df["p_bh_family"] < 0.05

df = df.sort_values("p_raw")
df.to_csv(OUT / "03_multiple_testing.csv", index=False)
print(df.to_string(index=False))
print(f"\nWrote {OUT / '03_multiple_testing.csv'}")

print("\n=== Summary ===")
print(f"Total tests:                  {len(df)}")
print(f"Significant raw at 0.05:      {(df['p_raw']<0.05).sum()}")
print(f"Survives Holm-global:         {df['survives_holm_0.05'].sum()}")
print(f"Survives BH-FDR global:       {df['survives_bh_0.05'].sum()}")
print(f"Survives Holm within-family:  {df['survives_holm_family_0.05'].sum()}")
print(f"Survives BH within-family:    {df['survives_bh_family_0.05'].sum()}")
