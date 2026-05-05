"""Model × axis interactions and surprise residuals.

A surprise residual is what's left after subtracting the model's overall
manipulation rate and the cell's pooled rate from the observed cell rate.
Positive = this model manipulates MORE in this cell than its baseline + the
cell's baseline would predict. Negative = this model resists this cell.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from _loader import load, save_table, fig_path, FRAME_ORDER


def model_axis_pivot(df: pd.DataFrame, task: str, axis: str) -> pd.DataFrame:
    sub = df[df["task"] == task]
    return (sub.groupby(["model", axis], observed=True)["manipulation_occurred"]
              .mean().unstack(axis))


def residuals(pivot: pd.DataFrame) -> pd.DataFrame:
    grand = pivot.values[~np.isnan(pivot.values)].mean() if pivot.size else np.nan
    row_means = pivot.mean(axis=1)
    col_means = pivot.mean(axis=0)
    res = pivot.subtract(row_means, axis=0).subtract(col_means, axis=1) + grand
    return res


def heatmap(pivot: pd.DataFrame, title: str, out: str, *, diverging: bool, vlim: float | None = None) -> None:
    if pivot.empty:
        return
    fig, ax = plt.subplots(figsize=(1.0 * pivot.shape[1] + 3, 0.4 * pivot.shape[0] + 2))
    if diverging:
        if vlim is None:
            vlim = float(np.nanmax(np.abs(pivot.values))) or 1e-6
        im = ax.imshow(pivot.values, aspect="auto", cmap="coolwarm", vmin=-vlim, vmax=vlim)
    else:
        im = ax.imshow(pivot.values, aspect="auto", cmap="magma_r", vmin=0, vmax=1)
    ax.set_xticks(range(pivot.shape[1])); ax.set_xticklabels(pivot.columns, rotation=20, ha="right")
    ax.set_yticks(range(pivot.shape[0])); ax.set_yticklabels(pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if np.isnan(v):
                continue
            if diverging:
                color = "white" if abs(v) > (vlim * 0.7) else "black"
                ax.text(j, i, f"{v:+.2f}", ha="center", va="center", color=color, fontsize=8)
            else:
                color = "white" if v > 0.55 else "black"
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", color=color, fontsize=8)
    ax.set_title(title)
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(fig_path(out), dpi=150)
    plt.close(fig)


def main() -> None:
    df = load()
    tasks = sorted(df["task"].unique())

    all_top, all_bot = [], []
    for task in tasks:
        for axis in ("frame", "incentive", "difficulty"):
            piv = model_axis_pivot(df, task, axis)
            if piv.empty:
                continue
            piv = piv.dropna(how="all")
            piv = piv.reindex(piv.mean(axis=1).sort_values(ascending=False).index)
            heatmap(piv, f"{task}: model × {axis}", f"04_{task}_model_{axis}", diverging=False)
            save_table(piv.round(4), f"04_{task}_model_{axis}_rate")

            res = residuals(piv).round(4)
            heatmap(res, f"{task}: model × {axis} residuals", f"04_{task}_model_{axis}_resid",
                    diverging=True)
            save_table(res, f"04_{task}_model_{axis}_resid")

            stacked = res.stack().reset_index()
            stacked.columns = ["model", axis, "residual"]
            stacked["task"] = task; stacked["axis"] = axis
            stacked = stacked.rename(columns={axis: "level"})
            all_top.append(stacked.nlargest(3, "residual"))
            all_bot.append(stacked.nsmallest(3, "residual"))

    top = pd.concat(all_top, ignore_index=True).sort_values("residual", ascending=False).head(20)
    bot = pd.concat(all_bot, ignore_index=True).sort_values("residual").head(20)

    print("=== Top 20 surprise residuals (model manipulates MORE than expected) ===")
    print(top.to_string(index=False), "\n")
    save_table(top, "04_top_positive_residuals")

    print("=== Top 20 negative residuals (model RESISTS more than expected) ===")
    print(bot.to_string(index=False), "\n")
    save_table(bot, "04_top_negative_residuals")

    print("=== Per-model frame slope (permissive - prohibitive) per task ===")
    slope_rows = []
    for task in tasks:
        piv = model_axis_pivot(df, task, "frame")
        if "permissive" in piv.columns and "prohibitive" in piv.columns:
            slope = (piv["permissive"] - piv["prohibitive"]).rename("slope")
            for model, v in slope.items():
                slope_rows.append({"task": task, "model": model, "slope": v})
    slopes = pd.DataFrame(slope_rows).pivot(index="model", columns="task", values="slope")
    slopes["__mean__"] = slopes.mean(axis=1)
    slopes = slopes.sort_values("__mean__", ascending=False).round(3)
    print(slopes, "\n")
    save_table(slopes, "04_frame_slope_by_model")


if __name__ == "__main__":
    main()
