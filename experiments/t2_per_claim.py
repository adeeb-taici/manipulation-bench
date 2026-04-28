"""Per-claim T2 manipulation rate breakdown.

For each of the 23 contested claims, compute manipulation_occurred mean
per model. Output:
  - paper/task2_debate/analysis/per_claim.json
  - paper/task2_debate/figures/fig8_per_claim.png — heatmap (claim × model)
  - paper/task2_debate/figures/fig9_claim_difficulty.png — claim-difficulty
    distribution (panel_prior buckets vs realised manipulation rate)
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import importlib.util

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

LOG = "paper/task2_debate/eval_log.eval"
OUT_DIR = Path("paper/task2_debate")

DISPLAY = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5": "GPT-5.5",
    "Gemini-3.1-Pro": "Gemini 3.1 Pro",
    "Grok-4": "Grok 4",
    "Llama-3.3-70B": "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
}
MODEL_REMAP = {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"}


def load_claims():
    spec = importlib.util.spec_from_file_location("claims", "experiments/task2_debate_claims.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return {c["claim_id"]: c for c in m.CLAIMS}


def main():
    claims = load_claims()
    log = read_eval_log(LOG)

    by_claim_model: dict[tuple[str, str], list[float]] = defaultdict(list)
    for s in log.samples or []:
        if s.error:
            continue
        md = (s.metadata or {}).get("scenario", {}).get("metadata", {})
        sc = (s.scores or {}).get("ground_truth_persuasion")
        if sc is None or not isinstance(sc.value, dict):
            continue
        v = sc.value.get("manipulation_occurred")
        if v is None:
            continue
        cid = md.get("claim_id")
        model = md.get("manipulator_model")
        model = MODEL_REMAP.get(model, model)
        if not cid or not model:
            continue
        by_claim_model[(cid, model)].append(float(v))

    models = sorted(
        {m for (_, m) in by_claim_model},
        key=lambda x: list(DISPLAY).index(x) if x in DISPLAY else 999,
    )
    cids = sorted(claims.keys())

    grid = np.full((len(cids), len(models)), np.nan)
    for ci, cid in enumerate(cids):
        for mi, m in enumerate(models):
            vals = by_claim_model.get((cid, m), [])
            if vals:
                grid[ci, mi] = sum(vals) / len(vals)

    # ---- per-claim JSON
    out = {
        "claims": [
            {
                "claim_id": cid,
                "topic": claims[cid]["topic"],
                "ground_truth": claims[cid]["ground_truth"],
                "panel_prior": claims[cid]["panel_prior"],
                "difficulty_tier": claims[cid]["difficulty_tier"],
                "per_model": {
                    DISPLAY.get(m, m): (
                        None if np.isnan(grid[ci, mi]) else round(float(grid[ci, mi]), 3)
                    )
                    for mi, m in enumerate(models)
                },
                "mean_across_models": (
                    None
                    if np.all(np.isnan(grid[ci, :]))
                    else round(float(np.nanmean(grid[ci, :])), 3)
                ),
            }
            for ci, cid in enumerate(cids)
        ]
    }
    OUT_DIR.joinpath("analysis").mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "analysis" / "per_claim.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {json_path}")

    # Sort claims by mean rate (easiest = most manipulated, top)
    means = np.nanmean(grid, axis=1)
    order = np.argsort(-means)  # descending
    sorted_cids = [cids[i] for i in order]
    sorted_grid = grid[order, :]

    # ---- fig8 heatmap
    fig, ax = plt.subplots(figsize=(8, 9))
    im = ax.imshow(sorted_grid, cmap="Reds", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels([DISPLAY.get(m, m) for m in models], rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(len(sorted_cids)))
    yticks = []
    for cid in sorted_cids:
        c = claims[cid]
        gt = "T" if c["ground_truth"] == "true" else "F"
        yticks.append(f"{cid} [{gt}|{c['difficulty_tier'][0].upper()}|p={c['panel_prior']:.2f}]")
    ax.set_yticklabels(yticks, fontsize=7)
    for ci in range(len(sorted_cids)):
        for mi in range(len(models)):
            v = sorted_grid[ci, mi]
            if not np.isnan(v):
                ax.text(
                    mi,
                    ci,
                    f"{v:.2f}",
                    ha="center",
                    va="center",
                    fontsize=6,
                    color="white" if v > 0.55 else "black",
                )
    fig.colorbar(im, ax=ax, label="Manipulation rate")
    ax.set_title(
        "T2 Debate — manipulation rate per claim × model\n"
        "(rows sorted by easiest-to-manipulate; tag: GT|difficulty|panel_prior)",
        fontsize=11,
    )
    fig.tight_layout()
    fig_path = OUT_DIR / "figures" / "fig8_per_claim.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {fig_path}")

    # ---- fig9: panel_prior vs realised manipulation rate
    fig, ax = plt.subplots(figsize=(8, 5))
    for mi, m in enumerate(models):
        xs, ys = [], []
        for ci, cid in enumerate(cids):
            v = grid[ci, mi]
            if not np.isnan(v):
                xs.append(claims[cid]["panel_prior"])
                ys.append(v)
        ax.scatter(xs, ys, label=DISPLAY.get(m, m), alpha=0.7, s=40)
    # Aggregate trend (mean across models per claim)
    xs_all = [claims[cid]["panel_prior"] for cid in cids]
    ys_all = [np.nanmean(grid[ci, :]) for ci in range(len(cids))]
    # Sort for line
    pairs = sorted(zip(xs_all, ys_all))
    ax.plot(
        [p[0] for p in pairs], [p[1] for p in pairs], "k--", alpha=0.4, label="cross-model mean"
    )
    ax.set_xlabel("Panel prior P(claim is true)")
    ax.set_ylabel("Manipulation rate (mean across all conditions)")
    ax.set_title("T2 Debate — claim difficulty (panel prior) vs realised manipulation rate")
    ax.legend(fontsize=8, loc="best")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig_path = OUT_DIR / "figures" / "fig9_claim_difficulty.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {fig_path}")

    # Top-3 easiest / hardest claims (cross-model mean)
    print("\n=== Easiest claims to manipulate (top 5) ===")
    for i in order[:5]:
        cid = cids[i]
        print(
            f"  {cid}  rate={means[i]:.3f}  [{claims[cid]['difficulty_tier']}, p={claims[cid]['panel_prior']:.2f}, GT={claims[cid]['ground_truth']}]  {claims[cid]['topic'][:80]}"
        )
    print("\n=== Hardest claims to manipulate (bottom 5) ===")
    for i in order[-5:][::-1]:
        cid = cids[i]
        print(
            f"  {cid}  rate={means[i]:.3f}  [{claims[cid]['difficulty_tier']}, p={claims[cid]['panel_prior']:.2f}, GT={claims[cid]['ground_truth']}]  {claims[cid]['topic'][:80]}"
        )


if __name__ == "__main__":
    main()
