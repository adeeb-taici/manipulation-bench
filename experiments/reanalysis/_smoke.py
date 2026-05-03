"""Smoke-test gate for the reanalysis pipeline.

Runs three things end-to-end before launching expensive analyses:
  1. Loader sanity check: row counts per task, cluster-id presence.
  2. Regression on a single (task=T1, model=Claude, axis=frame) cell:
     - statsmodels OLS for omnibus F + per-task eta^2
     - scipy.stats.dunnett for contrasts vs prohibitive baseline
  3. Ranking-stability 50-rep bootstrap of cross-task rho matrix.

Prints results to stdout. No file outputs.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import dunnett, spearmanr
import statsmodels.formula.api as smf

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from experiments.reanalysis.load import load_corpus, CANONICAL_MODELS  # noqa: E402

FRAME_LEVELS = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")


def _format_rows(df: pd.DataFrame) -> None:
    print(f"\n[1] Loader sanity")
    print(f"  total rows: {len(df)}")
    print(f"  per-task counts:")
    for t, n in df.groupby("task").size().items():
        print(f"    {t:11s} {n}")
    print(f"  cluster-id presence:")
    for t in df["task"].unique():
        sub = df[df["task"] == t]
        n_with = sub["cluster_id"].notna().sum()
        print(f"    {t:11s} {n_with}/{len(sub)}")
    print(f"  models present: {sorted(df['model'].unique())}")


def _regression_smoke(df: pd.DataFrame) -> None:
    print(f"\n[2] Regression smoke: T1 Bargaining, Claude-Opus-4.7, frame axis")
    cell = df[(df["task"] == "bargaining") & (df["model"] == "Claude-Opus-4.7")].copy()
    cell = cell.dropna(subset=["metric", "frame"])
    cell["frame"] = pd.Categorical(cell["frame"], categories=FRAME_LEVELS, ordered=False)
    print(f"  n = {len(cell)}; per-frame counts:")
    print("   ", cell.groupby("frame", observed=False).size().to_dict())

    # Omnibus F-test via OLS w/ HC3
    model = smf.ols('metric ~ C(frame, Treatment(reference="prohibitive"))', data=cell).fit(cov_type="HC3")
    f_test = model.f_test('C(frame, Treatment(reference="prohibitive"))[T.pro_social] = 0,'
                          'C(frame, Treatment(reference="prohibitive"))[T.minimal] = 0,'
                          'C(frame, Treatment(reference="prohibitive"))[T.selfish] = 0,'
                          'C(frame, Treatment(reference="prohibitive"))[T.permissive] = 0')
    f_stat = float(f_test.fvalue)
    f_p = float(f_test.pvalue)
    # eta^2 = SS_between / SS_total (for one-factor model, equivalent to R^2)
    eta2 = float(model.rsquared)
    print(f"  OLS+HC3:  F = {f_stat:.3f}, p = {f_p:.3e}, eta^2 = {eta2:.4f}")

    # Dunnett contrasts vs prohibitive baseline
    samples = [cell.loc[cell["frame"] == lvl, "metric"].values for lvl in FRAME_LEVELS]
    control = samples[0]  # prohibitive
    treatments = samples[1:]
    res = dunnett(*treatments, control=control)
    print(f"  Dunnett vs prohibitive (one-sided=False, 95% CI):")
    ci = res.confidence_interval(confidence_level=0.95)
    for lvl, stat, pval, lo, hi in zip(FRAME_LEVELS[1:], res.statistic, res.pvalue, ci.low, ci.high):
        diff = treatments[FRAME_LEVELS[1:].index(lvl)].mean() - control.mean()
        print(f"    {lvl:11s}  diff={diff:+.4f}  95% CI=[{lo:+.4f}, {hi:+.4f}]  p={pval:.3e}")


def _ranking_stability_smoke(df: pd.DataFrame, n_boot: int = 50) -> None:
    print(f"\n[3] Ranking-stability smoke: cross-task rho bootstrap, n_boot={n_boot}")
    print(f"  ranking definition: per-task model order by mean primary metric at frame=permissive")

    tasks_in_corpus = ["bargaining", "debate", "village", "sales", "committee"]
    perm = df[df["frame"] == "permissive"].copy()
    perm = perm.dropna(subset=["metric"])

    # Original (point) ranking per task
    point_ranks = {}
    for t in tasks_in_corpus:
        sub = perm[perm["task"] == t]
        means = sub.groupby("model", observed=False)["metric"].mean()
        means = means.reindex(CANONICAL_MODELS)
        point_ranks[t] = means

    print(f"  point estimate per-task means at permissive:")
    for t in tasks_in_corpus:
        print(f"    {t:11s}", {m: f"{v:.3f}" if pd.notna(v) else "nan" for m, v in point_ranks[t].items()})

    # Stratify groups: (task, model, frame, incentive, difficulty)
    groups = list(df.groupby(["task", "model", "frame", "incentive", "difficulty"], observed=True))
    print(f"  resampling strata: {len(groups)} cells")

    seed_seq = np.random.SeedSequence(20260430)
    seeds = seed_seq.spawn(n_boot)

    pair_index = [(a, b) for i, a in enumerate(tasks_in_corpus) for b in tasks_in_corpus[i+1:]]
    rhos = {pair: [] for pair in pair_index}

    t0 = time.time()
    for boot_idx, child in enumerate(seeds):
        rng = np.random.default_rng(child)
        # Resample within each cell
        sampled_chunks = []
        for _, group_df in groups:
            n = len(group_df)
            idx = rng.integers(0, n, size=n)
            sampled_chunks.append(group_df.iloc[idx])
        boot_df = pd.concat(sampled_chunks, ignore_index=True)
        boot_perm = boot_df[boot_df["frame"] == "permissive"]
        means_per_task = {}
        for t in tasks_in_corpus:
            sub = boot_perm[boot_perm["task"] == t]
            means = sub.groupby("model", observed=False)["metric"].mean().reindex(CANONICAL_MODELS)
            means_per_task[t] = means
        for a, b in pair_index:
            ma, mb = means_per_task[a], means_per_task[b]
            common = ma.dropna().index.intersection(mb.dropna().index)
            if len(common) < 3:
                rhos[(a, b)].append(np.nan)
                continue
            r, _ = spearmanr(ma.loc[common], mb.loc[common])
            rhos[(a, b)].append(r)
    elapsed = time.time() - t0
    print(f"  elapsed: {elapsed:.1f}s for {n_boot} reps -> ~{elapsed/n_boot*2000:.0f}s for full 2000-rep run")

    print(f"\n  bootstrap median rho with [2.5, 97.5] percentile CI per task pair:")
    for pair, vals in rhos.items():
        arr = np.array(vals, dtype=float)
        med = np.nanmedian(arr)
        lo = np.nanpercentile(arr, 2.5)
        hi = np.nanpercentile(arr, 97.5)
        # Compare against point estimate
        ma, mb = point_ranks[pair[0]].dropna(), point_ranks[pair[1]].dropna()
        common = ma.index.intersection(mb.index)
        point = spearmanr(ma.loc[common], mb.loc[common])[0] if len(common) >= 3 else np.nan
        print(f"    {pair[0]:11s} vs {pair[1]:11s}  point={point:+.3f}  boot_median={med:+.3f}  CI=[{lo:+.3f}, {hi:+.3f}]")


def main() -> None:
    df = load_corpus(verbose=False)
    _format_rows(df)
    _regression_smoke(df)
    _ranking_stability_smoke(df, n_boot=50)


if __name__ == "__main__":
    main()
