"""Block C: cross-task ranking-stability bootstrap.

Replaces the n=6-models point estimate of pairwise Spearman rho with
trajectory-level percentile bootstrap CIs.

Method:
  1. Per task, define each model's "manipulation level" as its mean
     primary metric at frame=permissive (matches the v1 ranking
     definition in cross_task_ranking_stability.py). Optionally also
     compute "overall mean" rankings as a secondary view.
  2. For each of B=2000 replicates:
       - Resample trajectories with replacement WITHIN each
         (task, model, frame, incentive, difficulty) cell.
       - Recompute the per-task model means.
       - Compute Spearman rho for every task pair.
  3. Per task pair: percentile 95% CI on rho; modal rank per model
     per task and % stability.

Seeds: numpy.random.SeedSequence(20260430).spawn(B).

Output: paper/cross_task/analysis/ranking_stability_v2.json
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from experiments.reanalysis.load import CANONICAL_MODELS, load_corpus  # noqa: E402

TASKS = ("bargaining", "debate", "village", "sales", "committee")
TASK_PAIRS = [(a, b) for i, a in enumerate(TASKS) for b in TASKS[i+1:]]
MASTER_SEED = 20260430
N_BOOT_DEFAULT = 2000


def _per_task_means(df: pd.DataFrame, ranking: str = "permissive",
                    use_v1_metric: bool = False) -> dict[str, pd.Series]:
    """Per-task model-mean Series indexed by CANONICAL_MODELS order.

    ranking="permissive" -> mean of primary metric at frame=permissive
    ranking="overall"    -> overall mean across all rows

    use_v1_metric=True replaces T2's metric column with manipulation_occurred
    (the binary detected-manipulation rate) to match v1's mixed-metric
    cross_task_ranking_stability.py definition. v2 default uses belief_shift
    for T2 (matches each task's stated primary metric).
    """
    metric_col = "metric"
    out = {}
    for t in TASKS:
        sub = df[df["task"] == t]
        if ranking == "permissive":
            sub = sub[sub["frame"] == "permissive"]
        # v1-compat: T2 ranking by manipulation_occurred (binary), not belief_shift
        col = "manipulation_occurred" if (use_v1_metric and t == "debate") else metric_col
        sub = sub.dropna(subset=[col])
        means = sub.groupby("model", observed=False)[col].mean()
        out[t] = means.reindex(CANONICAL_MODELS)
    return out


def _spearman(a: pd.Series, b: pd.Series) -> float:
    common = a.dropna().index.intersection(b.dropna().index)
    if len(common) < 3:
        return float("nan")
    r, _ = spearmanr(a.loc[common], b.loc[common])
    return float(r)


def _ranks_per_task(per_task_means: dict[str, pd.Series]) -> dict[str, pd.Series]:
    """Rank models 1..N within each task (1 = lowest manipulation)."""
    out = {}
    for t, means in per_task_means.items():
        # rank() returns 1.0..n with NaN preserved
        out[t] = means.rank(method="average")
    return out


def _resample_indices(group_sizes: list[int], seed: np.random.SeedSequence) -> list[np.ndarray]:
    """Generate within-cell resample indices given a SeedSequence."""
    rng = np.random.default_rng(seed)
    return [rng.integers(0, n, size=n) for n in group_sizes]


def _one_replicate(
    seed: np.random.SeedSequence,
    df: pd.DataFrame,
    cell_indices: list[np.ndarray],
    cell_sizes: list[int],
    ranking: str,
    use_v1_metric: bool = False,
) -> tuple[dict[tuple[str, str], float], dict[str, np.ndarray]]:
    """Run one bootstrap replicate, return (rho_per_pair, ranks_per_task).

    cell_indices[i] gives the row positions of cell i in the original df.
    cell_sizes[i] is len(cell_indices[i]).
    """
    rng = np.random.default_rng(seed)
    # Build resampled row positions
    resampled_positions = []
    for idx_arr, n in zip(cell_indices, cell_sizes):
        if n == 0:
            continue
        picks = rng.integers(0, n, size=n)
        resampled_positions.append(idx_arr[picks])
    if not resampled_positions:
        return {p: float("nan") for p in TASK_PAIRS}, {t: np.full(len(CANONICAL_MODELS), np.nan) for t in TASKS}
    flat = np.concatenate(resampled_positions)
    boot = df.iloc[flat]

    per_task_means = _per_task_means(boot, ranking=ranking, use_v1_metric=use_v1_metric)
    rho = {pair: _spearman(per_task_means[pair[0]], per_task_means[pair[1]]) for pair in TASK_PAIRS}

    # Ranks per task as numpy arrays in CANONICAL_MODELS order
    ranks_arrays = {}
    for t, means in per_task_means.items():
        ranks_arrays[t] = means.rank(method="average").reindex(CANONICAL_MODELS).values
    return rho, ranks_arrays


def run_block_c(df: pd.DataFrame, n_boot: int = N_BOOT_DEFAULT,
                ranking: str = "permissive", n_jobs: int = -1,
                use_v1_metric: bool = False) -> dict[str, Any]:
    """Run the trajectory-level bootstrap for cross-task rho.

    Args:
        df: trajectory dataframe (output of load_corpus).
        n_boot: bootstrap replicates (default 2000).
        ranking: "permissive" or "overall".
        n_jobs: joblib n_jobs.

    Returns dict with point estimates, bootstrap medians, percentile CIs,
    and modal-rank stability per (task, model).
    """
    df = df.dropna(subset=["task", "model", "frame", "incentive", "difficulty", "metric"]).copy()

    # Pre-compute per-cell row positions to avoid re-grouping every replicate.
    df = df.reset_index(drop=True)
    cell_groups = df.groupby(
        ["task", "model", "frame", "incentive", "difficulty"], observed=True
    ).indices  # dict: tuple_key -> ndarray of positions

    cell_indices = list(cell_groups.values())
    cell_sizes = [len(a) for a in cell_indices]

    # Point estimate
    point_means = _per_task_means(df, ranking=ranking, use_v1_metric=use_v1_metric)
    point_rho = {pair: _spearman(point_means[pair[0]], point_means[pair[1]]) for pair in TASK_PAIRS}

    # Spawn child seeds
    ss = np.random.SeedSequence(MASTER_SEED)
    children = ss.spawn(n_boot)

    print(f"[block_c] running {n_boot} bootstrap replicates on {len(cell_indices)} strata "
          f"(n_jobs={n_jobs})", file=sys.stderr)
    t0 = time.time()
    results = Parallel(n_jobs=n_jobs, verbose=0, batch_size="auto")(
        delayed(_one_replicate)(child, df, cell_indices, cell_sizes, ranking, use_v1_metric)
        for child in children
    )
    elapsed = time.time() - t0
    print(f"[block_c] done in {elapsed:.1f}s ({elapsed/n_boot*1000:.1f} ms/rep)", file=sys.stderr)

    # Aggregate rho stats
    rho_arrays = {pair: np.array([r[0][pair] for r in results], dtype=float) for pair in TASK_PAIRS}
    rho_summary = {}
    for pair, arr in rho_arrays.items():
        med = float(np.nanmedian(arr))
        lo = float(np.nanpercentile(arr, 2.5))
        hi = float(np.nanpercentile(arr, 97.5))
        n_valid = int(np.isfinite(arr).sum())
        # Two-sided "indistinguishable from zero" if the CI brackets 0
        ci_excludes_zero = (lo > 0) or (hi < 0)
        rho_summary[f"{pair[0]}__vs__{pair[1]}"] = {
            "task_a": pair[0], "task_b": pair[1],
            "point": float(point_rho[pair]) if not np.isnan(point_rho[pair]) else None,
            "boot_median": med,
            "ci_lo": lo,
            "ci_hi": hi,
            "ci_excludes_zero": bool(ci_excludes_zero),
            "n_valid_reps": n_valid,
        }

    # Modal rank per (task, model)
    rank_stability = {}
    n_models = len(CANONICAL_MODELS)
    for t in TASKS:
        ranks_matrix = np.array([r[1][t] for r in results])  # shape (B, n_models)
        per_model: dict[str, dict[str, Any]] = {}
        for m_idx, model in enumerate(CANONICAL_MODELS):
            col = ranks_matrix[:, m_idx]
            valid = col[np.isfinite(col)]
            if len(valid) == 0:
                per_model[model] = {"modal_rank": None, "stability_pct": None,
                                    "rank_distribution": {}}
                continue
            # Round to nearest int for "modal" — averages from .rank(method='average')
            # land on integers when there are no ties (the typical case here).
            rounded = np.round(valid).astype(int)
            counts = Counter(rounded.tolist())
            total = len(rounded)
            mode_rank, mode_count = counts.most_common(1)[0]
            per_model[model] = {
                "modal_rank": int(mode_rank),
                "stability_pct": float(mode_count / total * 100.0),
                "rank_distribution": {str(k): int(v) for k, v in sorted(counts.items())},
                "median_rank": float(np.nanmedian(valid)),
            }
        rank_stability[t] = per_model

    return {
        "n_boot": n_boot,
        "elapsed_seconds": elapsed,
        "ranking_definition": ranking,
        "use_v1_metric": use_v1_metric,
        "n_strata": len(cell_indices),
        "tasks": list(TASKS),
        "models": list(CANONICAL_MODELS),
        "point_means": {t: {m: (None if pd.isna(v) else float(v))
                            for m, v in point_means[t].items()} for t in TASKS},
        "rho": rho_summary,
        "rank_stability": rank_stability,
        "master_seed": MASTER_SEED,
    }


def main() -> None:
    df = load_corpus(verbose=False)
    print(f"[block_c] loaded {len(df)} rows", file=sys.stderr)

    out_dir = REPO / "paper/cross_task/analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Primary: permissive-frame ranking
    primary = run_block_c(df, n_boot=N_BOOT_DEFAULT, ranking="permissive")
    out_path = out_dir / "ranking_stability_v2.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(primary, f, indent=2, default=str)
    print(f"[block_c] wrote {out_path}", file=sys.stderr)

    # Secondary: overall-mean ranking (descriptive sidekick)
    secondary = run_block_c(df, n_boot=N_BOOT_DEFAULT, ranking="overall")
    out_path2 = out_dir / "ranking_stability_v2_overall.json"
    with open(out_path2, "w", encoding="utf-8") as f:
        json.dump(secondary, f, indent=2, default=str)
    print(f"[block_c] wrote {out_path2}", file=sys.stderr)

    # Tertiary: v1-equivalent metric definition (T2 ranked by manipulation_occurred)
    # — for honest apples-to-apples comparison with v1's published rho matrix.
    v1compat = run_block_c(df, n_boot=N_BOOT_DEFAULT, ranking="permissive",
                            use_v1_metric=True)
    out_path3 = out_dir / "ranking_stability_v2_v1compat.json"
    with open(out_path3, "w", encoding="utf-8") as f:
        json.dump(v1compat, f, indent=2, default=str)
    print(f"[block_c] wrote {out_path3}", file=sys.stderr)


if __name__ == "__main__":
    main()
