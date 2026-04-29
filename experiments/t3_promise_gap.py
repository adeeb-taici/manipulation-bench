"""T3 Village promise-action gap analysis.

`promise_action_gap` per scenario gives, per agent, the cumulative
overpromise (pledged_total − actual_total) over the 8-round game.
Positive = over-promised then short-changed (deceptive); 0 = honest;
negative = under-promised then over-delivered (rare).

We focus on agent_1 = the designated manipulator. Aggregate by
(model, frame).

Outputs:
  paper/task3_village/analysis/promise_gap.json
  paper/task3_village/figures/fig8_promise_gap.pdf
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

LOG = "paper/task3_village/eval_log.eval"
OUT_DIR = Path("paper/task3_village")

DISPLAY = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5": "GPT-5.5",
    "Gemini-3.1-Pro": "Gemini 3.1 Pro",
    "Grok-4": "Grok 4",
    "Llama-3.3-70B": "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
}
MODEL_REMAP = {"DeepSeek-v3.2": "DeepSeek-V4-Pro", "GPT-5": "GPT-5.5"}
FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")


def main():
    log = read_eval_log(LOG)
    obs: dict[tuple[str, str], list[float]] = defaultdict(list)
    er_obs: dict[tuple[str, str], list[float]] = defaultdict(list)
    for s in log.samples or []:
        if s.error:
            continue
        md = (s.metadata or {}).get("scenario", {}).get("metadata", {})
        sc_pag = (s.scores or {}).get("promise_action_gap")
        sc_er = (s.scores or {}).get("exploitation_rate")
        if sc_pag is None or not isinstance(sc_pag.value, dict):
            continue
        if sc_er is None or not isinstance(sc_er.value, dict):
            continue
        gap = sc_pag.value.get("agent_1")
        er = sc_er.value.get("agent_1")
        if gap is None or er is None:
            continue
        frame = md.get("frame")
        model = md.get("manipulator_model")
        model = MODEL_REMAP.get(model, model)
        if model is None or frame not in FRAMES:
            continue
        obs[(model, frame)].append(float(gap))
        er_obs[(model, frame)].append(float(er))

    models = sorted(
        {m for (m, _) in obs.keys()},
        key=lambda x: list(DISPLAY).index(x) if x in DISPLAY else 999,
    )

    # Means per (model, frame)
    pag_grid = np.full((len(models), len(FRAMES)), np.nan)
    er_grid = np.full((len(models), len(FRAMES)), np.nan)
    for mi, m in enumerate(models):
        for fi, f in enumerate(FRAMES):
            v = obs.get((m, f), [])
            if v:
                pag_grid[mi, fi] = sum(v) / len(v)
            er = er_obs.get((m, f), [])
            if er:
                er_grid[mi, fi] = sum(er) / len(er)

    summary = {
        DISPLAY.get(m, m): {
            f: {
                "n": len(obs.get((m, f), [])),
                "mean_promise_gap": (
                    None if np.isnan(pag_grid[mi, fi]) else round(float(pag_grid[mi, fi]), 2)
                ),
                "median_promise_gap": (
                    None if not obs.get((m, f), []) else round(float(np.median(obs[(m, f)])), 2)
                ),
                "mean_exploitation_rate": (
                    None if np.isnan(er_grid[mi, fi]) else round(float(er_grid[mi, fi]), 3)
                ),
            }
            for fi, f in enumerate(FRAMES)
        }
        for mi, m in enumerate(models)
    }
    OUT_DIR.joinpath("analysis").mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "analysis" / "promise_gap.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"wrote {json_path}")

    # Figure
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    pag_max = float(np.nanmax(np.abs(pag_grid))) if np.any(~np.isnan(pag_grid)) else 1.0
    for ax, M, label, cmap, vmin, vmax in (
        (
            axes[0],
            pag_grid,
            "Mean promise-action gap (pledged − actual)",
            "RdBu_r",
            -pag_max,
            pag_max,
        ),
        (axes[1], er_grid, "Mean exploitation rate (1 − contribution/20)", "Reds", 0.0, 1.0),
    ):
        im = ax.imshow(M, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_xticks(range(len(FRAMES)))
        ax.set_xticklabels(FRAMES, rotation=30, ha="right")
        ax.set_yticks(range(len(models)))
        ax.set_yticklabels([DISPLAY.get(m, m) for m in models])
        for mi in range(len(models)):
            for fi in range(len(FRAMES)):
                v = M[mi, fi]
                if not np.isnan(v):
                    ax.text(
                        fi,
                        mi,
                        f"{v:.2f}",
                        ha="center",
                        va="center",
                        fontsize=8,
                        color="white" if abs(v) > (vmax - vmin) * 0.35 else "black",
                    )
        ax.set_title(label, fontsize=10)
        fig.colorbar(im, ax=ax, shrink=0.7)
    fig.suptitle(
        "T3 Village manipulator (agent_1): promise-action gap vs exploitation rate, per (model × frame)",
        fontsize=12,
        y=1.02,
    )
    fig.tight_layout()
    fig_path = OUT_DIR / "figures" / "fig8_promise_gap.pdf"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {fig_path}")

    # Top-line summary
    print("\n=== Per model: gap (mean across all frames) ===")
    for mi, m in enumerate(models):
        all_v = []
        for f in FRAMES:
            all_v.extend(obs.get((m, f), []))
        if not all_v:
            continue
        med = float(np.median(all_v))
        mn = float(np.mean(all_v))
        n_nonzero = sum(1 for x in all_v if abs(x) > 0.01)
        pct = n_nonzero / len(all_v) * 100
        print(
            f"  {DISPLAY.get(m, m):20s} mean={mn:6.2f}  median={med:5.2f}  n_games={len(all_v)}  "
            f"%games_with_gap={pct:.0f}%"
        )


if __name__ == "__main__":
    main()
