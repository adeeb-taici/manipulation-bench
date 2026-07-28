"""Bootstrap the Spearman rank correlation between per-task model rankings.

The paper's headline rank-instability claim (mean off-diagonal Spearman
ρ = 0.055 across the 10 task-pairs on T1-T5) is a correlation between
two 6-element rank vectors, repeated 10 times and averaged. With n=6
models per ranking, the per-pair ρ has high sampling variance even at
fixed rates, and the mean across 10 pairs is itself a small-sample
statistic.

What this script does:
1. Restrict to canonical-6 roster, T1-T5.
2. Resample raw rows. Two schemes:
   - Row bootstrap: independent resample of all rows.
   - Cluster bootstrap: resample scenario_groups within each task
     where cluster_id is populated (committee/debate/sales); fall
     back to row bootstrap on bargaining/village.
3. For each resample, compute per-(task, model) mean
   `manipulation_occurred`. Build a 5×6 ranking matrix. Compute the
   10 pairwise Spearman ρ values and the mean off-diagonal.
4. Repeat B=2000 times. Report:
   - Bootstrap distribution of mean off-diagonal ρ (mean, 2.5/97.5).
   - Bootstrap distribution of each of the 10 pairwise ρ.
   - Permutation null: shuffle model labels within each task,
     compute the same statistic, B=2000 reps. Compare observed mean
     vs null distribution.

Outputs:
- out/05_spearman_bootstrap.csv (per-pair ρ + bootstrap CI)
- out/05_spearman_bootstrap_summary.txt (mean off-diag ρ, CIs, perm p)
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]  # paper/cross_task
CSV = ROOT / "data" / "results.csv"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

CANONICAL = [
    "Claude-Opus-4.7", "GPT-5.5", "Gemini-3.1-Pro",
    "Grok-4", "Llama-3.3-70B", "DeepSeek-V4-Pro",
]
TASKS_T1T5 = ["bargaining", "debate", "village", "sales", "committee"]
B = 2000
RNG = np.random.default_rng(20260504)

print(f"Loading {CSV} ...")
df = pd.read_csv(CSV, low_memory=False)
df = df.dropna(subset=["manipulation_occurred", "model", "task"])
df = df[df["model"].isin(CANONICAL) & df["task"].isin(TASKS_T1T5)].copy()
df["manipulation_occurred"] = df["manipulation_occurred"].astype(float)

# Optional: restrict to permissive frame to match the paper's
# rank-stability figure construction. Reproduce both:
# (a) all-rows pooled rate, (b) permissive-frame rate.
print(f"  {len(df):,} rows; tasks={sorted(df['task'].unique())}")

def per_task_rank_matrix(rows):
    """Return a (5 tasks × 6 models) DataFrame of mean
    manipulation_occurred."""
    g = rows.groupby(["task", "model"])["manipulation_occurred"].mean().unstack("model")
    g = g.reindex(index=TASKS_T1T5, columns=CANONICAL)
    return g

def mean_off_diag_spearman(rate_matrix):
    """Compute the mean of the 10 pairwise Spearman ρ across tasks.

    rate_matrix: 5×6 DataFrame (tasks × models). For each task we have a
    6-element vector of model rates; convert to ranks and correlate
    pairwise across tasks. Returns (mean_rho, list of 10 rhos).
    """
    arr = rate_matrix.values  # (5,6)
    rhos = []
    for i in range(5):
        for j in range(i+1, 5):
            # spearmanr returns nan if either input is constant; that
            # happens at endpoints (e.g., village=1.000 across all models
            # under permissive frame). Skip those pairs rather than
            # poisoning the mean.
            if np.ptp(arr[i]) == 0 or np.ptp(arr[j]) == 0:
                rhos.append(np.nan)
                continue
            r, _ = spearmanr(arr[i], arr[j])
            rhos.append(r)
    valid = [r for r in rhos if not np.isnan(r)]
    return float(np.mean(valid)) if valid else np.nan, rhos

# Indices for cluster bootstrap: per-task, group by cluster_id when present
def make_resample_indices(df, scheme="cluster"):
    out = []
    for task, sub in df.groupby("task"):
        if scheme == "cluster" and sub["cluster_id"].notna().any():
            # cluster-resample: sample groups with replacement, take all rows
            cids = sub["cluster_id"].dropna().unique()
            picked = RNG.choice(cids, size=len(cids), replace=True)
            for cid in picked:
                idx = sub.index[sub["cluster_id"] == cid].to_numpy()
                out.append(idx)
            # also append rows with no cluster_id (untracked) by row bootstrap
            untracked = sub[sub["cluster_id"].isna()].index.to_numpy()
            if len(untracked):
                ridx = RNG.choice(untracked, size=len(untracked), replace=True)
                out.append(ridx)
        else:
            # row bootstrap
            ridx = RNG.choice(sub.index.to_numpy(), size=len(sub), replace=True)
            out.append(ridx)
    return np.concatenate(out)

print("\n=== POINT ESTIMATES ===")
def report(label, frame_filter=None):
    rows = df if frame_filter is None else df[df["frame"] == frame_filter]
    rates = per_task_rank_matrix(rows)
    mr, rhos = mean_off_diag_spearman(rates)
    print(f"\n{label}: mean off-diag ρ = {mr:+.3f}")
    print("  per-task rates:")
    print(rates.round(3).to_string())
    print(f"  10 pairwise ρ: {[round(r,2) for r in rhos]}")
    return rates, mr, rhos

rates_all, mr_all, rhos_all = report("All-rows pooled (T1-T5, canonical-6)")
rates_perm, mr_perm, rhos_perm = report("Permissive frame only", frame_filter="permissive")

# ============== BOOTSTRAP ==============
print(f"\n=== BOOTSTRAP B={B} (cluster-resample) ===")

bootstrap_means_all = np.zeros(B)
bootstrap_means_perm = np.zeros(B)
bootstrap_rhos_all = np.zeros((B, 10))

for b in range(B):
    idx = make_resample_indices(df, scheme="cluster")
    sub = df.loc[idx]
    rates_b = per_task_rank_matrix(sub)
    if rates_b.isna().any().any():
        bootstrap_means_all[b] = np.nan
        bootstrap_rhos_all[b] = np.nan
        bootstrap_means_perm[b] = np.nan
        continue
    mb, rhos_b = mean_off_diag_spearman(rates_b)
    bootstrap_means_all[b] = mb
    bootstrap_rhos_all[b] = rhos_b
    # permissive subset
    sub_p = sub[sub["frame"] == "permissive"]
    rates_pb = per_task_rank_matrix(sub_p)
    if rates_pb.isna().any().any():
        bootstrap_means_perm[b] = np.nan
    else:
        bootstrap_means_perm[b], _ = mean_off_diag_spearman(rates_pb)
    if (b+1) % 200 == 0:
        print(f"  {b+1}/{B}")

def ci(x, low=2.5, high=97.5):
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return float("nan"), float("nan")
    return float(np.percentile(x, low)), float(np.percentile(x, high))

print(f"\nAll-rows pooled mean off-diag ρ:")
print(f"  point estimate: {mr_all:+.3f}")
ci_all = ci(bootstrap_means_all)
print(f"  bootstrap mean: {np.nanmean(bootstrap_means_all):+.3f}")
print(f"  bootstrap 95% CI: [{ci_all[0]:+.3f}, {ci_all[1]:+.3f}]")

print(f"\nPermissive-frame mean off-diag ρ:")
print(f"  point estimate: {mr_perm:+.3f}")
ci_perm = ci(bootstrap_means_perm)
print(f"  bootstrap mean: {np.nanmean(bootstrap_means_perm):+.3f}")
print(f"  bootstrap 95% CI: [{ci_perm[0]:+.3f}, {ci_perm[1]:+.3f}]")

# Per-pair bootstrap CIs
pair_labels = []
for i in range(5):
    for j in range(i+1, 5):
        pair_labels.append(f"{TASKS_T1T5[i]}_vs_{TASKS_T1T5[j]}")
print("\nPer-pair Spearman ρ (all-rows pooled):")
per_pair = []
for k, label in enumerate(pair_labels):
    pt = rhos_all[k]
    col = bootstrap_rhos_all[:, k]
    col = col[~np.isnan(col)]
    if len(col) < 10 or np.isnan(pt):
        per_pair.append((label, pt, np.nan, np.nan))
        print(f"  {label:35s}  ρ = {pt}   (insufficient non-nan resamples)")
        continue
    cl, ch = ci(col)
    per_pair.append((label, pt, cl, ch))
    print(f"  {label:35s}  ρ = {pt:+.3f}  CI [{cl:+.3f}, {ch:+.3f}]")

# ============== PERMUTATION NULL ==============
# Null: model labels carry no cross-task signal — each task's model
# ranking is independent of the others. Shuffle model labels within
# each task (preserving each task's marginal rate distribution) and
# recompute mean off-diag ρ. Compare observed mean to null distribution.
print(f"\n=== PERMUTATION NULL B={B} ===")
null_means = np.zeros(B)
rate_arr_all = rates_all.values  # (5,6)
for b in range(B):
    perm = np.array([RNG.permutation(rate_arr_all[i]) for i in range(5)])
    rhos_n = []
    for i in range(5):
        for j in range(i+1, 5):
            if np.ptp(perm[i]) == 0 or np.ptp(perm[j]) == 0:
                continue
            r, _ = spearmanr(perm[i], perm[j])
            rhos_n.append(r)
    null_means[b] = np.mean(rhos_n) if rhos_n else np.nan

null_low, null_high = ci(null_means)
two_sided_p = float((np.abs(null_means) >= abs(mr_all)).mean())
print(f"Null mean off-diag ρ (model labels shuffled per task):")
print(f"  null mean: {np.nanmean(null_means):+.3f}")
print(f"  null 95% CI: [{null_low:+.3f}, {null_high:+.3f}]")
print(f"  two-sided permutation p (|null| >= |observed {mr_all:+.3f}|): {two_sided_p:.3f}")

# Save outputs
pd.DataFrame(per_pair, columns=["pair", "rho_point", "rho_ci_low", "rho_ci_high"]).to_csv(
    OUT / "05_spearman_bootstrap.csv", index=False
)

with open(OUT / "05_spearman_bootstrap_summary.txt", "w") as f:
    f.write(f"Mean off-diagonal Spearman ρ across T1-T5 task-pairs (canonical-6).\n")
    f.write(f"B = {B}, cluster-resample where cluster_id populated, row-resample otherwise.\n\n")
    f.write(f"All-rows pooled:\n")
    f.write(f"  point:   {mr_all:+.3f}\n")
    f.write(f"  bootstrap mean: {np.nanmean(bootstrap_means_all):+.3f}\n")
    f.write(f"  bootstrap 95% CI: [{ci_all[0]:+.3f}, {ci_all[1]:+.3f}]\n\n")
    f.write(f"Permissive-frame only:\n")
    f.write(f"  point:   {mr_perm:+.3f}\n")
    f.write(f"  bootstrap 95% CI: [{ci_perm[0]:+.3f}, {ci_perm[1]:+.3f}]\n\n")
    f.write(f"Permutation null (shuffle model labels within each task):\n")
    f.write(f"  null mean:   {np.nanmean(null_means):+.3f}\n")
    f.write(f"  null 95% CI: [{null_low:+.3f}, {null_high:+.3f}]\n")
    f.write(f"  two-sided p: {two_sided_p:.3f}\n")
print(f"\nWrote {OUT / '05_spearman_bootstrap.csv'}")
print(f"Wrote {OUT / '05_spearman_bootstrap_summary.txt'}")
