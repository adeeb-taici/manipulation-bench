"""Paired head-to-head model comparisons on shared scenarios.

Removes scenario-level variance by computing each (model_a, model_b) delta
*within* the same scenario instance, then averaging across instances.

Scenario key per task (chosen from probing scenario_group structure):
  bargaining, village  -> (frame, incentive, difficulty) -- coarse axis cell
  committee, debate, sales -> (scenario_group, frame, incentive)
    (scenario_group is 1:1 with difficulty in those tasks, so adding it is
    redundant but harmless; we include it explicitly for clarity.)

For each pair on each task:
  - rate_a, rate_b = mean manipulation_occurred per (model, scenario)
  - delta_per_scenario = rate_a - rate_b
  - report: mean delta, paired-bootstrap 95% CI over scenarios,
    fraction of scenarios where a > b (sign-test direction),
    n_scenarios.

Output:
  - 08_pairwise_<task>.csv: long-form pair-level table
  - 08_pairwise_<task>_matrix.csv: signed mean-delta matrix
  - 08_ranking_<task>.csv: each model's "wins minus losses" Borda-style score
    on significant pairs (CI excludes zero).
"""
from __future__ import annotations
import importlib.util
import itertools
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


def pairwise_table(per_scen: pd.DataFrame, task: str) -> pd.DataFrame:
    keys = SCENARIO_KEYS[task]
    wide = per_scen.pivot_table(index=keys, columns="model", values="manipulation_occurred")
    rows = []
    models = list(wide.columns)
    for a, b in itertools.combinations(models, 2):
        pair = wide[[a, b]].dropna()
        if len(pair) < 5:
            continue
        delta = (pair[a] - pair[b]).to_numpy()
        lo, hi = paired_bootstrap_ci(delta)
        rows.append({
            "model_a": a, "model_b": b, "n_scenarios": len(delta),
            "rate_a_paired": float(pair[a].mean()),
            "rate_b_paired": float(pair[b].mean()),
            "mean_delta": float(delta.mean()),
            "ci_lo": lo, "ci_hi": hi,
            "frac_a_higher": float((delta > 0).mean()),
            "frac_tied": float((delta == 0).mean()),
            "significant": (lo > 0) or (hi < 0),
        })
    return pd.DataFrame(rows)


def borda_ranking(pair_df: pd.DataFrame) -> pd.DataFrame:
    sig = pair_df[pair_df["significant"]]
    score = {}
    n_pairs = {}
    for _, r in sig.iterrows():
        a, b, d = r["model_a"], r["model_b"], r["mean_delta"]
        score.setdefault(a, 0); score.setdefault(b, 0)
        n_pairs.setdefault(a, 0); n_pairs.setdefault(b, 0)
        n_pairs[a] += 1; n_pairs[b] += 1
        if d > 0:
            score[a] += 1; score[b] -= 1
        else:
            score[a] -= 1; score[b] += 1
    # also include models that appeared with 0 significant pairs
    for m in set(pair_df["model_a"]).union(pair_df["model_b"]):
        score.setdefault(m, 0); n_pairs.setdefault(m, 0)
    out = pd.DataFrame({"model": list(score.keys()),
                        "wins_minus_losses": list(score.values()),
                        "n_significant_pairs": [n_pairs[m] for m in score]})
    out = out.sort_values("wins_minus_losses", ascending=False).reset_index(drop=True)
    return out


def signed_matrix(pair_df: pd.DataFrame) -> pd.DataFrame:
    models = sorted(set(pair_df["model_a"]).union(pair_df["model_b"]))
    M = pd.DataFrame(np.nan, index=models, columns=models)
    for _, r in pair_df.iterrows():
        a, b, d = r["model_a"], r["model_b"], r["mean_delta"]
        M.loc[a, b] = d
        M.loc[b, a] = -d
    return M


def heatmap(M: pd.DataFrame, title: str, out: str) -> None:
    if M.empty:
        return
    fig, ax = plt.subplots(figsize=(0.7 * len(M.columns) + 2, 0.5 * len(M.index) + 2))
    vmax = float(np.nanmax(np.abs(M.values))) if np.isfinite(np.nanmax(np.abs(M.values))) else 0.5
    vmax = max(vmax, 1e-3)
    im = ax.imshow(M.values, cmap="coolwarm", vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(len(M.columns))); ax.set_xticklabels(M.columns, rotation=80, ha="right", fontsize=8)
    ax.set_yticks(range(len(M.index))); ax.set_yticklabels(M.index, fontsize=8)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M.values[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v:+.2f}", ha="center", va="center",
                        color="white" if abs(v) > 0.7 * vmax else "black", fontsize=6)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="row - column (paired delta)")
    fig.tight_layout()
    fig.savefig(fig_path(out), dpi=150)
    plt.close(fig)


def main() -> None:
    df = add_scenario_group(load())
    overall_ranking = []
    for task in SCENARIO_KEYS:
        print(f"\n=== {task} ===")
        per_scen = per_scenario_means(df, task)
        pairs = pairwise_table(per_scen, task)
        if pairs.empty:
            print("(no pairs met n>=5 shared-scenario threshold)")
            continue
        save_table(pairs.round(4), f"08_pairwise_{task}")

        print(f"  n_scenario_keys = {per_scen.groupby(SCENARIO_KEYS[task], observed=True).ngroups}")
        print(f"  n_pairs = {len(pairs)}; significant (CI excludes 0) = {int(pairs['significant'].sum())}")

        M = signed_matrix(pairs).round(3)
        save_table(M, f"08_pairwise_{task}_matrix")
        heatmap(M, f"{task}: paired model_a - model_b on shared scenarios", f"08_pairwise_{task}_matrix")

        ranking = borda_ranking(pairs)
        ranking["task"] = task
        save_table(ranking, f"08_ranking_{task}")
        print("  Borda-style ranking (wins - losses on significant pairs):")
        print(ranking.to_string(index=False))
        overall_ranking.append(ranking)

    if overall_ranking:
        combined = pd.concat(overall_ranking)
        cross = combined.pivot(index="model", columns="task", values="wins_minus_losses")
        cross["__sum__"] = cross.sum(axis=1, numeric_only=True)
        cross = cross.sort_values("__sum__", ascending=False)
        print("\n=== Cross-task wins-minus-losses (paired, scenario-controlled) ===")
        print(cross.fillna("").to_string())
        save_table(cross, "08_ranking_cross_task")


if __name__ == "__main__":
    main()
