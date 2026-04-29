"""Cross-task model archetype clustering.

Build a 15-dim profile vector per model (5 tasks × 3 axis slopes),
z-score across the 6 models per dimension, then run hierarchical
clustering. Outputs:

  paper/cross_task/figures/fig_dendrogram.svg
  paper/cross_task/figures/fig_cluster_heatmap.svg  (clustered profile matrix)
  paper/cross_task/clusters.json
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from scipy.spatial.distance import pdist, squareform

PROFILES = "paper/cross_task/cross_task_profiles.json"
OUT_DIR = Path("paper/cross_task")

DISPLAY = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5": "GPT-5.5",
    "Gemini-3.1-Pro": "Gemini 3.1 Pro",
    "Grok-4": "Grok 4",
    "Llama-3.3-70B": "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
}
TASKS = ["task1_bargaining", "task2_debate", "task3_village", "task4_sales", "task5_committee"]
AXES = ["frame", "incentive", "difficulty"]


def main():
    d = json.load(open(PROFILES))
    profiles = d["profiles"]
    models = list(profiles.keys())

    # Build 15-dim vectors
    cols = [f"{t.split('_')[0]}_{a}" for t in TASKS for a in AXES]
    X = np.zeros((len(models), len(cols)))
    for mi, m in enumerate(models):
        for ti, t in enumerate(TASKS):
            for ai, a in enumerate(AXES):
                X[mi, ti * 3 + ai] = profiles[m][t][a]

    # z-score per column (so high-variance T5-difficulty doesn't dominate)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd < 1e-9] = 1.0
    Xz = (X - mu) / sd

    # Hierarchical clustering — cosine + ward seems too mixed; use euclidean+ward
    dists = pdist(Xz, metric="euclidean")
    Z = linkage(dists, method="ward")

    # Dendrogram
    fig, ax = plt.subplots(figsize=(8, 5))
    dn = dendrogram(Z, labels=[DISPLAY.get(m, m) for m in models], leaf_rotation=20, ax=ax)
    ax.set_title(
        "Cross-task model clustering — Ward linkage on z-scored 15-dim profiles", fontsize=11
    )
    ax.set_ylabel("Distance")
    fig.tight_layout()
    fig_path = OUT_DIR / "figures" / "fig_dendrogram.svg"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {fig_path}")

    # Cluster assignments at k=2, 3
    clusters_k2 = fcluster(Z, t=2, criterion="maxclust")
    clusters_k3 = fcluster(Z, t=3, criterion="maxclust")
    out = {
        "models": models,
        "axis_columns": cols,
        "z_scored_profile": Xz.tolist(),
        "clusters_k2": {DISPLAY.get(m, m): int(c) for m, c in zip(models, clusters_k2)},
        "clusters_k3": {DISPLAY.get(m, m): int(c) for m, c in zip(models, clusters_k3)},
    }
    out_path = OUT_DIR / "clusters.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {out_path}")

    # Reordered profile heatmap (rows reordered per dendrogram leaf order)
    leaf_order = dn["leaves"]
    fig, ax = plt.subplots(figsize=(12, 4.5))
    Xz_ord = Xz[leaf_order, :]
    vmax = np.nanmax(np.abs(Xz_ord))
    im = ax.imshow(Xz_ord, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(leaf_order)))
    ax.set_yticklabels([DISPLAY.get(models[i], models[i]) for i in leaf_order])
    for ri, mi in enumerate(leaf_order):
        for ci in range(len(cols)):
            v = Xz[mi, ci]
            ax.text(
                ci,
                ri,
                f"{v:+.1f}",
                ha="center",
                va="center",
                fontsize=6,
                color="white" if abs(v) > vmax * 0.6 else "black",
            )
    fig.colorbar(im, ax=ax, label="z-score")
    ax.set_title(
        "Cross-task model profile heatmap — rows reordered by dendrogram\n"
        "(positive = more sensitive than the 6-model mean on this axis × task)",
        fontsize=11,
    )
    fig.tight_layout()
    fig_path = OUT_DIR / "figures" / "fig_cluster_heatmap.svg"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {fig_path}")

    # Pairwise euclidean dist matrix figure
    D = squareform(dists)
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(D, cmap="viridis_r", aspect="auto")
    ax.set_xticks(range(len(models)))
    ax.set_yticks(range(len(models)))
    ax.set_xticklabels([DISPLAY.get(m, m) for m in models], rotation=30, ha="right", fontsize=8)
    ax.set_yticklabels([DISPLAY.get(m, m) for m in models], fontsize=8)
    for i in range(len(models)):
        for j in range(len(models)):
            ax.text(
                j,
                i,
                f"{D[i, j]:.1f}",
                ha="center",
                va="center",
                fontsize=7,
                color="white" if D[i, j] > D.max() * 0.55 else "black",
            )
    fig.colorbar(im, ax=ax, label="Euclidean dist (z-scored profiles)")
    ax.set_title("Cross-task model distance matrix (15-dim profile, z-scored)", fontsize=11)
    fig.tight_layout()
    fig_path = OUT_DIR / "figures" / "fig_distance_matrix.svg"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {fig_path}")

    print("\n=== k=2 clusters ===")
    for m, c in zip(models, clusters_k2):
        print(f"  {DISPLAY[m]:25s} -> cluster {c}")
    print("\n=== k=3 clusters ===")
    for m, c in zip(models, clusters_k3):
        print(f"  {DISPLAY[m]:25s} -> cluster {c}")


if __name__ == "__main__":
    main()
