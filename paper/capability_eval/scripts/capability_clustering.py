"""K-means clustering of models in their cross-task manipulation profile,
annotated by capability tier and generation.

Each model is represented as a vector of mean manipulation rates across
(task, frame) combinations (or just task, if frame is missing). We then
project to 2D via PCA, color by tier, mark generation by shape.

Outputs:
  paper/capability_eval/figures/capability_clustering_pca.png
  paper/capability_eval/analysis/capability_clustering.json
"""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from _capability_io import ANALYSIS_DIR, FIG_DIR, FRAMES, TASKS, ensure_dirs, load_joined


N_CLUSTERS = 3


def build_profile(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    sub = df[df["frame"].isin(FRAMES)].copy()
    pivot = sub.groupby(["model", "task", "frame"], observed=True)["manipulation_metric"].mean().unstack(["task", "frame"])
    pivot.columns = [f"{t}__{f}" for t, f in pivot.columns]
    pivot = pivot.dropna(axis=1, thresh=int(0.5 * len(pivot)))
    pivot = pivot.fillna(pivot.mean())
    return pivot, list(pivot.columns)


def main() -> None:
    ensure_dirs()
    df = load_joined()
    profile, feature_cols = build_profile(df)

    if len(profile) < N_CLUSTERS + 1:
        print(f"Insufficient models ({len(profile)}) for clustering")
        return

    cap = df[["model", "tier", "generation", "elo", "family"]].drop_duplicates(subset=["model"]).set_index("model")
    profile = profile.join(cap, how="inner")

    feature_matrix = profile[feature_cols].to_numpy()
    scaler = StandardScaler()
    X = scaler.fit_transform(feature_matrix)

    km = KMeans(n_clusters=N_CLUSTERS, random_state=0, n_init=10)
    labels = km.fit_predict(X)
    profile["cluster"] = labels

    pca = PCA(n_components=2, random_state=0)
    coords = pca.fit_transform(X)

    fig, ax = plt.subplots(figsize=(9, 7), constrained_layout=True)
    tier_colors = {"small": "#7fb3d5", "average": "#f5b041", "flagship": "#cb4335"}
    gen_markers = {"prev": "o", "current": "s"}
    for i, (model, row) in enumerate(profile.iterrows()):
        ax.scatter(coords[i, 0], coords[i, 1],
                   color=tier_colors.get(row["tier"], "gray"),
                   marker=gen_markers.get(row["generation"], "x"),
                   s=160, edgecolors="black", linewidths=0.8)
        ax.annotate(model, (coords[i, 0], coords[i, 1]), fontsize=7,
                    xytext=(5, 5), textcoords="offset points")

    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", label="prev gen", markerfacecolor="gray", markersize=10, markeredgecolor="black"),
        plt.Line2D([0], [0], marker="s", color="w", label="current gen", markerfacecolor="gray", markersize=10, markeredgecolor="black"),
    ] + [
        plt.Line2D([0], [0], marker="o", color="w", label=f"tier: {tier}", markerfacecolor=color, markersize=10, markeredgecolor="black")
        for tier, color in tier_colors.items()
    ]
    ax.legend(handles=legend_handles, fontsize=8, loc="best")
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% var)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% var)")
    ax.set_title("Model manipulation profiles in PCA space, colored by capability tier")
    ax.grid(True, alpha=0.3)
    fig.savefig(FIG_DIR / "capability_clustering_pca.png", dpi=150)
    plt.close(fig)

    summary = {
        "n_models": int(len(profile)),
        "n_features": len(feature_cols),
        "explained_variance_pc1_pc2": [float(v) for v in pca.explained_variance_ratio_[:2]],
        "cluster_assignments": {model: int(profile.loc[model, "cluster"]) for model in profile.index},
        "tier_by_cluster": (
            profile.groupby("cluster")["tier"].value_counts().unstack(fill_value=0).to_dict()
        ),
        "gen_by_cluster": (
            profile.groupby("cluster")["generation"].value_counts().unstack(fill_value=0).to_dict()
        ),
    }
    with open(ANALYSIS_DIR / "capability_clustering.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Wrote {FIG_DIR / 'capability_clustering_pca.png'}")
    print(f"Wrote {ANALYSIS_DIR / 'capability_clustering.json'}")
    print(f"PCA: PC1={pca.explained_variance_ratio_[0]*100:.1f}% PC2={pca.explained_variance_ratio_[1]*100:.1f}%")
    print(f"Tier composition by cluster: {summary['tier_by_cluster']}")
    print(f"Generation composition by cluster: {summary['gen_by_cluster']}")


if __name__ == "__main__":
    main()
