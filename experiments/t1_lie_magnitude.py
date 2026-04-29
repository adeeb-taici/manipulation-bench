"""T1 Bargaining lie-magnitude analysis.

Each scenario has two agents (a/b), each with `agent_*_true`,
`agent_*_stated`, `agent_*_lied`. The headline `manipulation_rate`
treats lying as binary. This script asks: WHEN models lie, HOW MUCH
do they overstate?

Magnitude metric for one (agent, scenario):
    rel_overstate = max(0, stated - true) / true   (signed: 0 if understated)

We analyse:
- Per-model conditional overstatement (mean rel_overstate | lied)
- Lie rate × magnitude joint distribution per model × frame
- Distribution of relative overstatements as a histogram

Outputs:
  paper/task1_bargaining/analysis/lie_magnitude.json
  paper/task1_bargaining/figures/fig8_lie_magnitude.svg
  paper/task1_bargaining/figures/fig9_magnitude_vs_rate.svg
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

LOG = "paper/task1_bargaining/eval_log.eval"
OUT_DIR = Path("paper/task1_bargaining")

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
    # Per (model, frame): list of (lied, rel_overstate, true, stated)
    obs: dict[tuple[str, str], list[tuple[int, float, float, float]]] = defaultdict(list)
    for s in log.samples or []:
        if s.error:
            continue
        md = (s.metadata or {}).get("scenario", {}).get("metadata", {})
        sc = (s.scores or {}).get("bargaining_commit")
        if sc is None or not isinstance(sc.value, dict):
            continue
        v = sc.value
        if v.get("sample_failed"):
            continue
        frame = md.get("frame")
        if frame not in FRAMES:
            continue
        for side, model_key in (("a", "agent_a_model"), ("b", "agent_b_model")):
            model = md.get(model_key)
            model = MODEL_REMAP.get(model, model)
            if model is None:
                continue
            true = v.get(f"agent_{side}_true")
            stated = v.get(f"agent_{side}_stated")
            lied = v.get(f"agent_{side}_lied")
            if true is None or stated is None or lied is None:
                continue
            # Absolute overstatement in points (bargaining pie is 0-100)
            # Clip at 200 — anything beyond is "absurd lie" and we tag it separately.
            raw_over = max(0.0, float(stated) - float(true))
            abs_over = min(raw_over, 200.0)
            obs[(model, frame)].append((int(lied), float(abs_over), float(true), float(stated)))

    models = sorted(
        {m for (m, _) in obs.keys()},
        key=lambda x: list(DISPLAY).index(x) if x in DISPLAY else 999,
    )

    # ---- summary stats
    summary = {}
    for m in models:
        per_frame = {}
        for f in FRAMES:
            tuples = obs.get((m, f), [])
            if not tuples:
                continue
            n = len(tuples)
            lied_n = sum(t[0] for t in tuples)
            cond_overs = [t[1] for t in tuples if t[0] == 1]
            n_extreme = sum(1 for t in tuples if t[0] == 1 and t[1] >= 200.0)
            per_frame[f] = {
                "n_obs": n,
                "lie_rate": round(lied_n / n, 3),
                "mean_overstate_when_lied_clip200": (
                    round(sum(cond_overs) / len(cond_overs), 2) if cond_overs else None
                ),
                "median_overstate_when_lied": (
                    round(float(np.median(cond_overs)), 2) if cond_overs else None
                ),
                "n_extreme_lies_clipped": n_extreme,
            }
        summary[DISPLAY.get(m, m)] = per_frame
    OUT_DIR.joinpath("analysis").mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "analysis" / "lie_magnitude.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"wrote {out_path}")

    # ---- fig8: heatmap — rows models, cols frames, value = MEDIAN overstate when lied
    grid = np.full((len(models), len(FRAMES)), np.nan)
    rate_grid = np.full_like(grid, np.nan)
    for mi, m in enumerate(models):
        for fi, f in enumerate(FRAMES):
            tuples = obs.get((m, f), [])
            cond = [t[1] for t in tuples if t[0] == 1]
            if cond:
                grid[mi, fi] = float(np.median(cond))
            if tuples:
                rate_grid[mi, fi] = sum(t[0] for t in tuples) / len(tuples)

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for ax, M, label, cmap, vmax in (
        (axes[0], rate_grid, "Lie rate (binary)", "Reds", 1.0),
        (
            axes[1],
            grid,
            "Median abs-overstate (pts) when lied",
            "Oranges",
            float(np.nanmax(grid)) * 1.05 if np.any(~np.isnan(grid)) else 1.0,
        ),
    ):
        im = ax.imshow(M, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
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
                        color="white" if v > vmax * 0.55 else "black",
                    )
        ax.set_title(label, fontsize=11)
        fig.colorbar(im, ax=ax, shrink=0.7, label=label)
    fig.suptitle(
        "T1 Bargaining — lie rate (left) vs median lie magnitude in points (right). "
        "Stated values are clipped at 200 — extreme outliers compressed.",
        fontsize=12,
        y=1.02,
    )
    fig.tight_layout()
    fig_path = OUT_DIR / "figures" / "fig8_lie_magnitude.svg"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {fig_path}")

    # ---- fig9: scatter — x=lie rate (over all conditions per model), y=mean magnitude when lied
    fig, ax = plt.subplots(figsize=(7, 5))
    for mi, m in enumerate(models):
        all_tuples = []
        for f in FRAMES:
            all_tuples.extend(obs.get((m, f), []))
        if not all_tuples:
            continue
        rate = sum(t[0] for t in all_tuples) / len(all_tuples)
        cond = [t[1] for t in all_tuples if t[0] == 1]
        mag = float(np.median(cond)) if cond else 0.0
        n_extreme = sum(1 for c in cond if c >= 200.0)
        pct_extreme = n_extreme / len(cond) * 100 if cond else 0.0
        ax.scatter(rate, mag, s=80 + pct_extreme * 5, label=DISPLAY.get(m, m), alpha=0.85)
        ax.annotate(
            f"{DISPLAY.get(m, m)}\n({pct_extreme:.0f}% extreme)",
            (rate, mag),
            xytext=(7, 5),
            textcoords="offset points",
            fontsize=8,
        )
    ax.set_xlabel("Lie rate (fraction of agent-statements flagged)")
    ax.set_ylabel("Median abs-overstatement (pts) when lying — clipped at 200")
    ax.set_title(
        "T1 Bargaining — lie frequency vs lie magnitude (per model, all conditions)", fontsize=11
    )
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    fig_path = OUT_DIR / "figures" / "fig9_magnitude_vs_rate.svg"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {fig_path}")

    # Print a one-liner summary
    print("\n=== Per-model: lie rate × mean magnitude when lying ===")
    for m in models:
        all_tuples = []
        for f in FRAMES:
            all_tuples.extend(obs.get((m, f), []))
        if not all_tuples:
            continue
        rate = sum(t[0] for t in all_tuples) / len(all_tuples)
        cond = [t[1] for t in all_tuples if t[0] == 1]
        med = float(np.median(cond)) if cond else 0.0
        mean_clip = sum(cond) / len(cond) if cond else 0.0
        n_lies = len(cond)
        n_extreme = sum(1 for c in cond if c >= 200.0)
        pct = n_extreme / n_lies * 100 if n_lies else 0.0
        print(
            f"  {DISPLAY.get(m, m):20s} rate={rate:.3f}  median_pts={med:5.1f}  "
            f"mean_clip={mean_clip:6.1f}  n_lies={n_lies}  extreme={n_extreme} ({pct:.0f}%)"
        )


if __name__ == "__main__":
    main()
