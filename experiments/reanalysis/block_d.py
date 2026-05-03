"""Block D: variance decomposition with bootstrap CI on the eta^2 difference.

Pooled OLS fit across all trajectories with within-task z-scoring:

    y_z ~ C(model) + C(task) + C(model):C(task)
        + C(frame) + C(incentive) + C(difficulty)

Headline: eta^2(model:task) - eta^2(model), with percentile bootstrap CI.

Why difference, not ratio: with eta^2(model) ~ 0.02-0.05, ratios have heavy-
tailed bootstrap distributions. Differences are well-behaved and interpretable
on the original scale.

Why z-score: T5 Committee uses a 0-20 bias scale; T1-T4 use [0,1] rates.
Pooling raw outcomes lets T5 dominate SS_total. Z-scoring within-task forces
each task to contribute equally to the pool, which is the right framing for
the rank-instability question (does model rank order across tasks come from
a stable trait?).

Output: paper/cross_task/analysis/variance_decomp_v2.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from joblib import Parallel, delayed
from statsmodels.stats.anova import anova_lm

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from experiments.reanalysis.load import load_corpus  # noqa: E402

MASTER_SEED = 20260430
N_BOOT_DEFAULT = 1000


def _zscore_within_task(df: pd.DataFrame) -> pd.DataFrame:
    """Add a `metric_z` column z-scored within each task.

    Uses positional indexing because bootstrap samples can have duplicate
    integer indices, which would break label-based assignment.
    """
    out = df.reset_index(drop=True).copy()
    metric_z = np.full(len(out), np.nan)
    tasks = out["task"].values
    metric = out["metric"].values.astype(float)
    for task in pd.unique(tasks):
        mask = tasks == task
        vals = metric[mask]
        finite = vals[np.isfinite(vals)]
        if len(finite) < 2:
            continue
        mu = finite.mean()
        sd = finite.std(ddof=0)
        if sd <= 0:
            continue
        metric_z[mask] = (vals - mu) / sd
    out["metric_z"] = metric_z
    return out


def _eta_squared(df_zscored: pd.DataFrame) -> dict[str, float]:
    """Fit the pooled GLM and return eta^2 per term.

    Type II ANOVA SS / total SS.
    """
    sub = df_zscored.dropna(subset=["metric_z", "model", "task",
                                    "frame", "incentive", "difficulty"]).copy()
    for col in ("model", "task", "frame", "incentive", "difficulty"):
        sub[col] = sub[col].astype("category")
    formula = ("metric_z ~ C(model) + C(task) + C(model):C(task) "
               "+ C(frame) + C(incentive) + C(difficulty)")
    fit = smf.ols(formula, data=sub).fit()
    anova = anova_lm(fit, typ=2)
    ss_total = float(anova["sum_sq"].sum())
    out = {}
    for term in anova.index:
        out[term] = float(anova.loc[term, "sum_sq"]) / ss_total if ss_total > 0 else 0.0
    return out


def _one_boot_replicate(seed: np.random.SeedSequence, df: pd.DataFrame) -> dict[str, float]:
    """Resample trajectories with replacement (full corpus), refit, return eta^2."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(df), size=len(df))
    boot_df = df.iloc[idx]
    # Re-z-score within each task on the bootstrap sample (matches the point fit).
    boot_z = _zscore_within_task(boot_df)
    try:
        return _eta_squared(boot_z)
    except Exception:
        return {}


def run_block_d(df: pd.DataFrame, n_boot: int = N_BOOT_DEFAULT, n_jobs: int = -1) -> dict[str, Any]:
    df = df.dropna(subset=["task", "model", "frame", "incentive", "difficulty", "metric"]).copy()
    df = df.reset_index(drop=True)

    # Point estimate
    df_z = _zscore_within_task(df)
    point_eta = _eta_squared(df_z)
    print(f"[block_d] point eta^2:", file=sys.stderr)
    for term, v in point_eta.items():
        print(f"  {term:35s}  {v:.4f}", file=sys.stderr)

    # Bootstrap
    ss = np.random.SeedSequence(MASTER_SEED)
    children = ss.spawn(n_boot)
    print(f"[block_d] running {n_boot} bootstrap replicates (n_jobs={n_jobs})", file=sys.stderr)
    t0 = time.time()
    boot_results = Parallel(n_jobs=n_jobs, verbose=0, batch_size="auto")(
        delayed(_one_boot_replicate)(child, df) for child in children
    )
    elapsed = time.time() - t0
    print(f"[block_d] done in {elapsed:.1f}s ({elapsed/n_boot:.2f} s/rep)", file=sys.stderr)

    # Collect bootstrap distribution per term
    all_terms = sorted({k for r in boot_results for k in r.keys()})
    boot_dist: dict[str, np.ndarray] = {}
    for term in all_terms:
        vals = np.array([r.get(term, np.nan) for r in boot_results], dtype=float)
        boot_dist[term] = vals

    # Headline: eta^2(model:task) - eta^2(model)
    diff_dist = boot_dist.get("C(model):C(task)", np.array([])) - boot_dist.get("C(model)", np.array([]))
    diff_valid = diff_dist[np.isfinite(diff_dist)]
    diff_summary = None
    if len(diff_valid) >= 10:
        diff_summary = {
            "point": float(point_eta.get("C(model):C(task)", 0) - point_eta.get("C(model)", 0)),
            "boot_median": float(np.median(diff_valid)),
            "ci_lo": float(np.percentile(diff_valid, 2.5)),
            "ci_hi": float(np.percentile(diff_valid, 97.5)),
            "n_valid_reps": int(len(diff_valid)),
            "ci_excludes_zero": bool(
                np.percentile(diff_valid, 2.5) > 0 or np.percentile(diff_valid, 97.5) < 0
            ),
        }

    # Descriptive ratio (no CI)
    ratio_point = None
    eta_model = point_eta.get("C(model)", 0)
    eta_inter = point_eta.get("C(model):C(task)", 0)
    if eta_model > 0:
        ratio_point = float(eta_inter / eta_model)

    return {
        "n_boot": n_boot,
        "elapsed_seconds": elapsed,
        "n_rows": int(len(df)),
        "point_eta_squared": {k: float(v) for k, v in point_eta.items()},
        "headline_difference": diff_summary,
        "descriptive_ratio_point": ratio_point,
        "per_term_bootstrap": {
            term: {
                "boot_median": float(np.nanmedian(arr)),
                "ci_lo": float(np.nanpercentile(arr, 2.5)),
                "ci_hi": float(np.nanpercentile(arr, 97.5)),
                "n_valid_reps": int(np.isfinite(arr).sum()),
            }
            for term, arr in boot_dist.items()
        },
        "master_seed": MASTER_SEED,
        "note": (
            "Outcome z-scored within task before pooling, so absolute eta^2 "
            "values are interpretable only relative to each other (task main "
            "effect is forced to ~0 by construction). Headline: difference "
            "between eta^2(model:task) and eta^2(model)."
        ),
    }


def main() -> None:
    df = load_corpus(verbose=False)
    print(f"[block_d] loaded {len(df)} rows", file=sys.stderr)
    out = run_block_d(df, n_boot=N_BOOT_DEFAULT)

    out_path = REPO / "paper/cross_task/analysis/variance_decomp_v2.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"[block_d] wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
