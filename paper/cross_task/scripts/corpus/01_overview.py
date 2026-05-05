"""Sanity check: coverage matrix, missingness, distribution of headline metrics."""
from __future__ import annotations
import pandas as pd
from _loader import load, save_table

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)


def main() -> None:
    df = load()
    print(f"Loaded {len(df):,} rows, {df.shape[1]} columns\n")

    print("=== Rows by task × variant ===")
    cov = df.pivot_table(index="task", columns="variant", values="sample_id", aggfunc="count", fill_value=0)
    print(cov, "\n")
    save_table(cov, "01_coverage_task_variant")

    print("=== Rows by task × model ===")
    tm = df.pivot_table(index="model", columns="task", values="sample_id", aggfunc="count", fill_value=0)
    tm["__total__"] = tm.sum(axis=1)
    tm = tm.sort_values("__total__", ascending=False)
    print(tm, "\n")
    save_table(tm, "01_coverage_task_model")

    print("=== Headline metric coverage per task ===")
    rows = []
    for task, sub in df.groupby("task", observed=True):
        rows.append({
            "task": task,
            "n": len(sub),
            "manipulation_occurred_mean": sub["manipulation_occurred"].mean(),
            "manipulation_occurred_null_rate": sub["manipulation_occurred"].isna().mean(),
            "manipulation_metric_min": sub["manipulation_metric"].min(),
            "manipulation_metric_max": sub["manipulation_metric"].max(),
            "manipulation_metric_mean": sub["manipulation_metric"].mean(),
            "manipulation_metric_null_rate": sub["manipulation_metric"].isna().mean(),
        })
    headline = pd.DataFrame(rows).set_index("task").round(4)
    print(headline, "\n")
    save_table(headline, "01_headline_per_task")

    print("=== Axis balance (counts per level, pooled) ===")
    for axis in ("frame", "incentive", "difficulty"):
        print(f"-- {axis} --")
        print(df[axis].value_counts().reindex(df[axis].cat.categories), "\n")


if __name__ == "__main__":
    main()
