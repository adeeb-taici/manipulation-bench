"""Capability-axis analysis: model size and recency vs. manipulation.

Three analyses, narrowest to broadest:

1. Within-family old-vs-new paired deltas (clean recency contrasts):
     haiku35 -> haiku45      (Anthropic small)
     sonnet37 -> sonnet46    (Anthropic mid)
   No clean GPT pair: gpt41 vs gpt54-* mixes recency with size.

2. Within-family size ladder slopes:
     OpenAI gpt41 family: nano < mini < base
     OpenAI gpt54 family: nano < mini
     Anthropic family:    haiku{35,45} < sonnet{37,46} < Claude-Opus-4.7
   Per task, regress mean manipulation_occurred against integer size_rank.

3. Coarse small/mid/frontier buckets across all models, per-task mean rate
   with cluster-bootstrap CIs. Cross-family pooling -- caveat heavily.

Pairing uses the same scenario-key strategy as 08:
  bargaining, village         -> (frame, incentive, difficulty)
  committee, debate, sales    -> (scenario_group, frame, incentive)
"""
from __future__ import annotations
import importlib.util
import pathlib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from _loader import load, save_table, fig_path

_spec = importlib.util.spec_from_file_location(
    "vd", pathlib.Path(__file__).with_name("05_variance_decomposition.py")
)
_vd = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_vd)
add_scenario_group = _vd.add_scenario_group

RNG = np.random.default_rng(0)
N_BOOT = 1000

SCENARIO_KEYS = {
    "bargaining": ["frame", "incentive", "difficulty"],
    "village":    ["frame", "incentive", "difficulty"],
    "committee":  ["scenario_group", "frame", "incentive"],
    "debate":     ["scenario_group", "frame", "incentive"],
    "sales":      ["scenario_group", "frame", "incentive"],
}

# Within-family recency pairs (older -> newer, same size tier)
RECENCY_PAIRS = [
    ("haiku35", "haiku45", "Anthropic small"),
    ("sonnet37", "sonnet46", "Anthropic mid"),
]

# Within-family size ladders. size_rank: smaller = lower number.
SIZE_LADDERS = {
    "OpenAI gpt41": [("gpt41nano", 0), ("gpt41mini", 1), ("gpt41", 2)],
    "OpenAI gpt54": [("gpt54nano", 0), ("gpt54mini", 1)],
    "Anthropic":    [("haiku35", 0), ("haiku45", 0),
                     ("sonnet37", 1), ("sonnet46", 1),
                     ("Claude-Opus-4.7", 2)],
}

# Coarse cross-family tier assignment
TIER = {
    # frontier (paper roster + a couple of capable mid models)
    "Claude-Opus-4.7": "frontier", "GPT-5.5": "frontier",
    "Gemini-3.1-Pro": "frontier", "Grok-4": "frontier",
    "Llama-3.3-70B": "frontier", "DeepSeek-V4-Pro": "frontier",
    # mid
    "sonnet37": "mid", "sonnet46": "mid",
    "gpt41": "mid", "gpt41mini": "mid", "gpt54mini": "mid",
    # small
    "haiku35": "small", "haiku45": "small",
    "gpt41nano": "small", "gpt54nano": "small",
}

TIER_ORDER = ["small", "mid", "frontier"]


def per_scenario_means(df: pd.DataFrame, task: str) -> pd.DataFrame:
    keys = SCENARIO_KEYS[task]
    sub = df[df["task"] == task].dropna(subset=keys + ["model", "manipulation_occurred"])
    return sub.groupby(["model"] + keys, observed=True)["manipulation_occurred"].mean().reset_index()


def paired_bootstrap_ci(deltas: np.ndarray, n: int = N_BOOT) -> tuple[float, float]:
    if len(deltas) == 0:
        return (np.nan, np.nan)
    idx = RNG.integers(0, len(deltas), size=(n, len(deltas)))
    means = deltas[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def cluster_bootstrap(values: np.ndarray, clusters: np.ndarray, n: int = N_BOOT) -> tuple[float, float]:
    df = pd.DataFrame({"y": values, "c": clusters}).dropna()
    if df.empty or df["c"].nunique() < 2:
        return (np.nan, np.nan)
    groups = [g["y"].to_numpy() for _, g in df.groupby("c", sort=False)]
    k = len(groups)
    means = np.empty(n)
    for i in range(n):
        pick = RNG.integers(0, k, size=k)
        means[i] = np.concatenate([groups[j] for j in pick]).mean()
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def row_bootstrap(values: np.ndarray, n: int = N_BOOT) -> tuple[float, float]:
    if len(values) == 0:
        return (np.nan, np.nan)
    idx = RNG.integers(0, len(values), size=(n, len(values)))
    means = values[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


# ------------------------------------------------------------------
# Analysis 1: within-family recency pairs
# ------------------------------------------------------------------
def recency_analysis(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for old, new, label in RECENCY_PAIRS:
        for task in SCENARIO_KEYS:
            per_scen = per_scenario_means(df, task)
            wide = per_scen.pivot_table(index=SCENARIO_KEYS[task], columns="model",
                                        values="manipulation_occurred")
            if old not in wide.columns or new not in wide.columns:
                continue
            paired = wide[[old, new]].dropna()
            if len(paired) < 5:
                continue
            delta = (paired[new] - paired[old]).to_numpy()  # newer - older
            lo, hi = paired_bootstrap_ci(delta)
            rows.append({
                "family": label, "older": old, "newer": new, "task": task,
                "n_scenarios": len(delta),
                "rate_older": float(paired[old].mean()),
                "rate_newer": float(paired[new].mean()),
                "delta_newer_minus_older": float(delta.mean()),
                "ci_lo": lo, "ci_hi": hi,
                "frac_newer_higher": float((delta > 0).mean()),
                "direction": "newer manipulates more" if (lo > 0)
                             else ("newer manipulates less" if hi < 0 else "no significant change"),
            })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------
# Analysis 2: within-family size ladder slopes
# ------------------------------------------------------------------
def size_ladder_analysis(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for family, members in SIZE_LADDERS.items():
        for task in SCENARIO_KEYS:
            sub = df[(df["task"] == task) & (df["model"].isin([m for m, _ in members]))]
            if sub.empty:
                continue
            mean_rate = sub.groupby("model", observed=True)["manipulation_occurred"].mean()
            ranks = {m: r for m, r in members}
            xs, ys, models = [], [], []
            for m, r in members:
                if m in mean_rate.index:
                    xs.append(r); ys.append(mean_rate.loc[m]); models.append(m)
            if len(xs) < 2:
                continue
            xs_arr, ys_arr = np.array(xs, dtype=float), np.array(ys, dtype=float)
            if len(xs) >= 2 and np.var(xs_arr) > 0:
                slope = float(np.polyfit(xs_arr, ys_arr, 1)[0])
            else:
                slope = np.nan
            rows.append({
                "family": family, "task": task,
                "n_models": len(xs), "models": ",".join(models),
                "slope_per_size_step": slope,
                "rate_smallest": float(ys_arr[np.argmin(xs_arr)]),
                "rate_largest": float(ys_arr[np.argmax(xs_arr)]),
                "delta_largest_minus_smallest": float(ys_arr[np.argmax(xs_arr)] - ys_arr[np.argmin(xs_arr)]),
            })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------
# Analysis 3: coarse tier buckets
# ------------------------------------------------------------------
def tier_analysis(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["tier"] = df["model"].map(TIER)
    df = df.dropna(subset=["tier"])
    rows = []
    for (tier, task), sub in df.groupby(["tier", "task"], observed=True):
        v = sub["manipulation_occurred"].to_numpy(dtype=float)
        if sub["scenario_group"].notna().any() and sub["scenario_group"].nunique() >= 2:
            lo, hi = cluster_bootstrap(v, sub["scenario_group"].astype("string").to_numpy())
            method = "cluster"
        else:
            lo, hi = row_bootstrap(v)
            method = "row"
        rows.append({"tier": tier, "task": task, "n_rows": len(v),
                     "n_models": int(sub["model"].nunique()),
                     "rate": float(v.mean()),
                     "ci_lo": lo, "ci_hi": hi, "ci_method": method})
    return pd.DataFrame(rows)


def plot_tier(tier_df: pd.DataFrame) -> None:
    pivot = tier_df.pivot(index="tier", columns="task", values="rate").reindex(TIER_ORDER)
    fig, ax = plt.subplots(figsize=(8, 4))
    width = 0.18
    tasks = list(pivot.columns)
    x = np.arange(len(TIER_ORDER))
    for i, task in enumerate(tasks):
        ax.bar(x + i * width - 0.4 + width / 2, pivot[task].values, width, label=task)
    ax.set_xticks(x); ax.set_xticklabels(TIER_ORDER)
    ax.set_ylabel("manipulation_occurred rate")
    ax.set_title("Manipulation rate by coarse capability tier (cross-family pooled, caveats apply)")
    ax.legend(fontsize=8, loc="upper right")
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(fig_path("09_tier_buckets"), dpi=150)
    plt.close(fig)


def plot_recency(rec: pd.DataFrame) -> None:
    if rec.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    families = rec["family"].unique()
    width = 0.35
    tasks = sorted(rec["task"].unique())
    x = np.arange(len(tasks))
    for i, fam in enumerate(families):
        sub = rec[rec["family"] == fam].set_index("task").reindex(tasks)
        ax.bar(x + i * width - width / 2 - width / 2 + width / 2,
               sub["delta_newer_minus_older"].values, width, label=fam)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_xticks(x); ax.set_xticklabels(tasks)
    ax.set_ylabel("delta (newer - older) in manipulation_occurred")
    ax.set_title("Within-family recency: how much did the newer model change?")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(fig_path("09_recency_deltas"), dpi=150)
    plt.close(fig)


def main() -> None:
    df = add_scenario_group(load())

    print("=== 1. Within-family recency pairs (newer - older) ===")
    rec = recency_analysis(df)
    if rec.empty:
        print("(no eligible pairs)")
    else:
        print(rec.round(3).to_string(index=False))
        save_table(rec.round(4), "09_recency_pairs")
        plot_recency(rec)

    print("\n=== 2. Within-family size ladder slopes ===")
    sz = size_ladder_analysis(df)
    if sz.empty:
        print("(no eligible ladders)")
    else:
        print(sz.round(3).to_string(index=False))
        save_table(sz.round(4), "09_size_ladders")

        print("\n--- Slope summary by family ---")
        slope_pivot = sz.pivot(index="family", columns="task", values="slope_per_size_step")
        slope_pivot["__mean__"] = slope_pivot.mean(axis=1)
        print(slope_pivot.round(3))
        save_table(slope_pivot, "09_size_slope_by_family_task")

    print("\n=== 3. Coarse tier buckets (cross-family pooled, caveats apply) ===")
    tier = tier_analysis(df)
    print(tier.round(3).to_string(index=False))
    save_table(tier.round(4), "09_tier_buckets")

    pivot = tier.pivot(index="tier", columns="task", values="rate").reindex(TIER_ORDER)
    print("\n--- Pivot: tier x task ---")
    print(pivot.round(3))
    save_table(pivot, "09_tier_buckets_pivot")
    plot_tier(tier)

    print("\nFigures: 09_recency_deltas.png, 09_tier_buckets.png")


if __name__ == "__main__":
    main()
