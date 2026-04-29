"""Per-question-type T4 manipulation breakdown.

Each scenario has 5 buyer questions, each with a check_type:
  - numeric_value
  - known_defect_disclosure
  - catch_all_disclosure
  - value_justification
  - comparable_disclosure

Compute manipulation rate (misleading + false) per (model, check_type),
filtered to the permissive frame to maximise signal.

Outputs:
  paper/task4_sales/analysis/per_check_type.json
  paper/task4_sales/figures/fig8_check_type_heatmap.pdf
  paper/task4_sales/figures/fig9_check_type_by_frame.pdf
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from inspect_ai.log import read_eval_log

LOG = "paper/task4_sales/eval_log.eval"
OUT_DIR = Path("paper/task4_sales")

DISPLAY = {
    "claude": "Claude Opus 4.7",
    "gpt55": "GPT-5.5",
    "gpt5": "GPT-5.5",
    "gemini": "Gemini 3.1 Pro",
    "grok": "Grok 4",
    "llama": "Llama 3.3 70B",
    "deepseek_v4": "DeepSeek V4 Pro",
    "deepseek": "DeepSeek V4 Pro",
}
ORDER = ["claude", "gpt55", "gemini", "grok", "llama", "deepseek_v4"]
CHECK_TYPES = (
    "numeric_value",
    "catch_all_disclosure",
    "value_justification",
    "comparable_disclosure",
)
FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")


def model_canonical(m: str) -> str:
    return {"gpt5": "gpt55", "deepseek": "deepseek_v4"}.get(m, m)


def main():
    log = read_eval_log(LOG)

    # all-conditions: (model, check_type) -> [is_manip 0/1]
    by_mt: dict[tuple[str, str], list[int]] = defaultdict(list)
    # by frame: (model, check_type, frame) -> [is_manip]
    by_mtf: dict[tuple[str, str, str], list[int]] = defaultdict(list)

    for s in log.samples or []:
        if s.error:
            continue
        md = s.metadata or {}
        model = model_canonical(md.get("model", ""))
        frame = md.get("frame")
        sc = (s.scores or {}).get("sales_classifier")
        if sc is None:
            continue
        if (sc.value or {}).get("sample_failed"):
            continue
        classifications = (sc.metadata or {}).get("classifications", [])
        for c in classifications:
            ct = c.get("check_type")
            cls = c.get("classification")
            if ct not in CHECK_TYPES or cls is None:
                continue
            is_manip = 1 if cls in ("misleading", "false") else 0
            by_mt[(model, ct)].append(is_manip)
            if frame:
                by_mtf[(model, ct, frame)].append(is_manip)

    # ---- aggregate grid (manipulation rate, all conditions)
    grid = np.full((len(CHECK_TYPES), len(ORDER)), np.nan)
    n_grid = np.zeros_like(grid)
    for ci, ct in enumerate(CHECK_TYPES):
        for mi, m in enumerate(ORDER):
            vals = by_mt.get((m, ct), [])
            if vals:
                grid[ci, mi] = sum(vals) / len(vals)
                n_grid[ci, mi] = len(vals)

    # JSON dump
    out = {
        "all_conditions": {
            ct: {
                DISPLAY.get(m, m): (
                    {
                        "rate": None if np.isnan(grid[ci, mi]) else round(float(grid[ci, mi]), 3),
                        "n": int(n_grid[ci, mi]),
                    }
                )
                for mi, m in enumerate(ORDER)
            }
            for ci, ct in enumerate(CHECK_TYPES)
        }
    }
    OUT_DIR.joinpath("analysis").mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "analysis" / "per_check_type.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"wrote {json_path}")

    # ---- fig8: check_type × model heatmap
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(grid, cmap="Reds", vmin=0, vmax=max(0.3, np.nanmax(grid) * 1.05), aspect="auto")
    ax.set_xticks(range(len(ORDER)))
    ax.set_xticklabels([DISPLAY.get(m, m) for m in ORDER], rotation=30, ha="right")
    ax.set_yticks(range(len(CHECK_TYPES)))
    ax.set_yticklabels(CHECK_TYPES)
    for ci in range(len(CHECK_TYPES)):
        for mi in range(len(ORDER)):
            v = grid[ci, mi]
            if not np.isnan(v):
                ax.text(
                    mi,
                    ci,
                    f"{v:.2f}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white" if v > np.nanmax(grid) * 0.6 else "black",
                )
    fig.colorbar(im, ax=ax, label="Manipulation rate (misleading+false)")
    ax.set_title(
        "T4 Sales — manipulation rate by question check_type × model\n"
        "(aggregated across all frames/incentives/difficulties)",
        fontsize=11,
    )
    fig.tight_layout()
    fig_path = OUT_DIR / "figures" / "fig8_check_type_heatmap.pdf"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {fig_path}")

    # ---- fig9: per-frame, faceted by check_type, line plot
    fig, axes = plt.subplots(1, len(CHECK_TYPES), figsize=(4 * len(CHECK_TYPES), 4), sharey=True)
    for ci, ct in enumerate(CHECK_TYPES):
        ax = axes[ci]
        for m in ORDER:
            ys, errs = [], []
            for f in FRAMES:
                vals = by_mtf.get((m, ct, f), [])
                if not vals:
                    ys.append(np.nan)
                    errs.append(0.0)
                    continue
                arr = np.asarray(vals, dtype=float)
                ys.append(float(arr.mean()))
                errs.append(float(arr.std(ddof=1) / np.sqrt(len(arr))) if len(arr) > 1 else 0.0)
            ax.errorbar(
                range(len(FRAMES)),
                ys,
                yerr=errs,
                fmt="-o",
                label=DISPLAY.get(m, m),
                alpha=0.85,
                markersize=4,
                capsize=2,
                elinewidth=0.6,
            )
        ax.set_xticks(range(len(FRAMES)))
        ax.set_xticklabels(FRAMES, rotation=45, ha="right", fontsize=8)
        ax.set_title(ct, fontsize=9)
        ax.grid(alpha=0.3)
        if ci == 0:
            ax.set_ylabel("Manipulation rate")
    axes[-1].legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1))
    fig.suptitle(
        "T4 Sales — manipulation rate per check_type × frame, by model", fontsize=12, y=1.02
    )
    fig.tight_layout()
    fig_path = OUT_DIR / "figures" / "fig9_check_type_by_frame.pdf"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {fig_path}")

    # Print summary
    print("\n=== Per check_type cross-model max (where manipulation peaks) ===")
    for ci, ct in enumerate(CHECK_TYPES):
        row = grid[ci, :]
        if np.all(np.isnan(row)):
            continue
        peak_idx = np.nanargmax(row)
        avg = np.nanmean(row)
        print(
            f"  {ct:30s} avg={avg:.3f}  peak={row[peak_idx]:.3f} [{DISPLAY.get(ORDER[peak_idx], ORDER[peak_idx])}]"
        )


if __name__ == "__main__":
    main()
