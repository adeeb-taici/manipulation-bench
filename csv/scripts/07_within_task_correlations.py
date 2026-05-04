"""Within-task scorer correlations: does `manipulation_occurred` capture all
the manipulation signal, or are the per-task derived columns orthogonal?

For each task, identify the columns in the `<scorer>__*` namespace populated
on that task's rows, compute Spearman correlations with `manipulation_occurred`
and `manipulation_metric`, and classify each derived column as:

  redundant     |rho| > 0.9 with one of the headlines (same signal)
  partial       0.3 <= |rho| <= 0.9
  complementary |rho| < 0.3 with both headlines (orthogonal — left on the table)

Outputs per-task correlation heatmap + summary CSV.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from _loader import load, save_table, fig_path

# Columns to ignore (identifiers, axis vars, headline metrics themselves)
IGNORE = {
    "task", "variant", "log_path", "sample_id", "epoch", "scenario_id", "cluster_id",
    "model", "manipulator", "frame", "incentive", "difficulty",
    "num_agents", "topology", "topic", "model_mapping",
    "manipulation_metric", "manipulation_occurred",
}


def numeric_scorer_cols(sub: pd.DataFrame, min_coverage: float = 0.05) -> list[str]:
    cols = []
    for c in sub.columns:
        if c in IGNORE:
            continue
        if "__" not in c:
            continue
        # Must be numeric and have at least min_coverage non-null on this task
        coerced = pd.to_numeric(sub[c], errors="coerce")
        if coerced.notna().mean() >= min_coverage and coerced.nunique(dropna=True) > 1:
            cols.append(c)
    return cols


def classify(r_occ: float, r_met: float) -> str:
    best = max(abs(r_occ) if pd.notna(r_occ) else 0, abs(r_met) if pd.notna(r_met) else 0)
    if best > 0.9:
        return "redundant"
    if best < 0.3:
        return "complementary"
    return "partial"


def heatmap(corr: pd.DataFrame, title: str, out: str) -> None:
    if corr.empty:
        return
    fig, ax = plt.subplots(figsize=(0.4 * corr.shape[1] + 3, 0.4 * corr.shape[0] + 3))
    im = ax.imshow(corr.values, aspect="auto", cmap="coolwarm", vmin=-1, vmax=1)
    ax.set_xticks(range(corr.shape[1])); ax.set_xticklabels(corr.columns, rotation=80, ha="right", fontsize=7)
    ax.set_yticks(range(corr.shape[0])); ax.set_yticklabels(corr.index, fontsize=7)
    for i in range(corr.shape[0]):
        for j in range(corr.shape[1]):
            v = corr.values[i, j]
            if pd.notna(v) and abs(v) >= 0.5:
                ax.text(j, i, f"{v:.1f}", ha="center", va="center",
                        color="white" if abs(v) > 0.7 else "black", fontsize=6)
    ax.set_title(title)
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(fig_path(out), dpi=150)
    plt.close(fig)


def main() -> None:
    df = load()
    summary_rows = []

    for task, sub in df.groupby("task", observed=True):
        cols = numeric_scorer_cols(sub)
        if not cols:
            print(f"[{task}] no scorer columns met coverage threshold; skip")
            continue
        block = sub[cols + ["manipulation_metric", "manipulation_occurred"]].apply(pd.to_numeric, errors="coerce")
        corr = block.corr(method="spearman")
        save_table(corr.round(4), f"07_corr_{task}")
        heatmap(corr, f"{task}: Spearman correlations between scorer columns", f"07_corr_{task}")

        for c in cols:
            r_occ = corr.loc[c, "manipulation_occurred"] if "manipulation_occurred" in corr else np.nan
            r_met = corr.loc[c, "manipulation_metric"] if "manipulation_metric" in corr else np.nan
            summary_rows.append({
                "task": task, "column": c,
                "non_null": int(block[c].notna().sum()),
                "rho_occurred": r_occ, "rho_metric": r_met,
                "classification": classify(r_occ, r_met),
            })

    summary = pd.DataFrame(summary_rows).round(3)
    summary = summary.sort_values(["task", "classification", "rho_occurred"], ascending=[True, True, False])
    save_table(summary, "07_scorer_classification")

    print("=== Scorer column classification per task ===")
    for task, g in summary.groupby("task", observed=True):
        print(f"\n--- {task} ---")
        print(g[["column", "non_null", "rho_occurred", "rho_metric", "classification"]].to_string(index=False))

    print("\n=== COMPLEMENTARY columns (orthogonal signal not captured by headline metrics) ===")
    comp = summary[summary["classification"] == "complementary"]
    print(comp.to_string(index=False) if len(comp) else "(none)")
    save_table(comp, "07_complementary_columns")


if __name__ == "__main__":
    main()
