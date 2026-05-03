"""Redraw fig 2/3/4/7 + Table 3 (v2).

Reads the JSONs produced by regression / ranking_stability /
variance_decomposition and emits PDFs
with `_v2` suffix, alongside the v1 originals (which stay untouched).

Figures:
  fig2_ranking_stability_v2.pdf  — task-pair rho heatmap with bootstrap CIs
  fig3_per_task_aggregate_v2.pdf — per-task eta^2 (replaces "mean |slope|")
  fig4_per_model_profile_v2.pdf  — per-model max |Dunnett contrast| heatmap
  fig7_cross_task_rho_v2.pdf     — same as fig2 but with hatching for non-sig
                                   (different audience: paper §7 vs §3.4)
  table3_v2.md                   — per-task F + eta^2 table
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

TASKS = ("bargaining", "debate", "village", "sales", "committee")
TASK_LABELS = {
    "bargaining": "T1 Bargaining",
    "debate":     "T2 Debate",
    "village":    "T3 Village",
    "sales":      "T4 Sales",
    "committee":  "T5 Committee",
}
MODELS = (
    "Claude-Opus-4.7", "GPT-5.5", "Gemini-3.1-Pro",
    "Grok-4", "Llama-3.3-70B", "DeepSeek-V4-Pro",
)
MODEL_LABELS = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5":         "GPT-5.5",
    "Gemini-3.1-Pro":  "Gemini 3.1 Pro",
    "Grok-4":          "Grok 4",
    "Llama-3.3-70B":   "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
}

PER_TASK_REGRESSION = {
    "bargaining": REPO / "paper/task1_bargaining/analysis/regression_v2.json",
    "debate":     REPO / "paper/task2_debate/analysis/regression_v2.json",
    "village":    REPO / "paper/task3_village/analysis/regression_v2.json",
    "sales":      REPO / "paper/task4_sales/analysis/regression_v2.json",
    "committee":  REPO / "paper/task5_committee/analysis/regression_v2.json",
}
RANKING_STAB = REPO / "paper/cross_task/analysis/ranking_stability_v2.json"
VARIANCE_DECOMP = REPO / "paper/cross_task/analysis/variance_decomp_v2.json"

OUT_DIR = REPO / "paper/cross_task/figures"


# ── fig2 / fig7: cross-task rho matrix with bootstrap CIs ────────────────

def _build_rho_matrix(rs: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (medians, ci_lo, ci_hi) symmetric matrices in TASKS order."""
    n = len(TASKS)
    med = np.full((n, n), np.nan)
    lo = np.full((n, n), np.nan)
    hi = np.full((n, n), np.nan)
    for i, ti in enumerate(TASKS):
        med[i, i] = 1.0
        lo[i, i] = 1.0
        hi[i, i] = 1.0
    for key, entry in rs["rho"].items():
        a, b = entry["task_a"], entry["task_b"]
        i, j = TASKS.index(a), TASKS.index(b)
        med[i, j] = med[j, i] = entry["boot_median"]
        lo[i, j] = lo[j, i] = entry["ci_lo"]
        hi[i, j] = hi[j, i] = entry["ci_hi"]
    return med, lo, hi


def _draw_rho_heatmap(med: np.ndarray, lo: np.ndarray, hi: np.ndarray,
                      title: str, out_path: Path, hatch_nonsig: bool = True) -> None:
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(med, cmap="RdBu_r", vmin=-1, vmax=1, aspect="equal")
    n = len(TASKS)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels([TASK_LABELS[t] for t in TASKS], rotation=30, ha="right")
    ax.set_yticklabels([TASK_LABELS[t] for t in TASKS])

    for i in range(n):
        for j in range(n):
            v = med[i, j]
            if np.isnan(v):
                continue
            ci_lo, ci_hi = lo[i, j], hi[i, j]
            ci_excludes_zero = (ci_lo > 0) or (ci_hi < 0) or i == j
            if i == j:
                cell_txt = "1.00"
            else:
                cell_txt = f"{v:+.2f}\n[{ci_lo:+.2f},{ci_hi:+.2f}]"
            color = "white" if abs(v) > 0.6 else "black"
            ax.text(j, i, cell_txt, ha="center", va="center", fontsize=8, color=color)
            # Hatch cells whose CI spans zero (non-significant)
            if hatch_nonsig and not ci_excludes_zero and i != j:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                           fill=False, hatch="///",
                                           edgecolor="gray", linewidth=0,
                                           alpha=0.4))

    fig.colorbar(im, ax=ax, label="Spearman ρ (bootstrap median)")
    ax.set_title(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path}")


def fig2_and_fig7(rs: dict) -> None:
    """fig2 + fig7 share the same data; both get hatching for non-significant cells."""
    med, lo, hi = _build_rho_matrix(rs)

    title2 = ("Cross-task model-ranking stability (v2)\n"
              "ρ between per-task model orderings, with bootstrap 95% CI\n"
              "(hatched cells: CI spans zero — rankings statistically indistinguishable)")
    _draw_rho_heatmap(med, lo, hi, title2, OUT_DIR / "fig2_ranking_stability_v2.pdf",
                      hatch_nonsig=True)

    title7 = ("Cross-task ρ matrix (v2)\n"
              "Trajectory bootstrap with 95% percentile CI; B=2000\n"
              "Hatched: CI brackets zero")
    _draw_rho_heatmap(med, lo, hi, title7, OUT_DIR / "fig7_cross_task_rho_v2.pdf",
                      hatch_nonsig=True)


# ── fig3: per-task η² ────────────────────────────────────────────────────

def fig3_per_task_aggregate(per_task_jsons: dict) -> None:
    """Stacked bar: per-task eta^2 for model + frame + incentive + difficulty + residual."""
    terms_order = ("C(model)", "C(frame)", "C(incentive)", "C(difficulty)", "Residual")
    term_labels = ["Model", "Frame", "Incentive", "Difficulty", "Residual"]
    colors = ["#4C72B0", "#DD8452", "#55A467", "#C44E52", "#CCCCCC"]

    matrix = np.zeros((len(TASKS), len(terms_order)))
    for i, t in enumerate(TASKS):
        d = json.loads(per_task_jsons[t].read_text())
        eta = d["per_task_eta"]["eta_squared"]
        for j, term in enumerate(terms_order):
            matrix[i, j] = eta.get(term, 0.0) or 0.0

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bottom = np.zeros(len(TASKS))
    x = np.arange(len(TASKS))
    for j, (label, color) in enumerate(zip(term_labels, colors)):
        ax.bar(x, matrix[:, j], bottom=bottom, label=label, color=color, edgecolor="white")
        # Annotate non-trivial slices
        for i, val in enumerate(matrix[:, j]):
            if val >= 0.04 and label != "Residual":
                ax.text(i, bottom[i] + val / 2, f"{val:.2f}",
                        ha="center", va="center", fontsize=8, color="white")
        bottom += matrix[:, j]
    ax.set_xticks(x)
    ax.set_xticklabels([TASK_LABELS[t] for t in TASKS], rotation=15, ha="right")
    ax.set_ylabel("η² (proportion of variance)")
    ax.set_ylim(0, 1.0)
    ax.set_title("Per-task variance decomposition (v2)\n"
                 "Type II ANOVA: y ~ C(model) + C(frame) + C(incentive) + C(difficulty)",
                 fontsize=11)
    ax.legend(loc="upper right", framealpha=0.95)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    out_path = OUT_DIR / "fig3_per_task_aggregate_v2.pdf"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path}")


# ── fig4: per-model profile heatmap ───────────────────────────────────────

def fig4_per_model_profile(per_task_jsons: dict) -> None:
    """Per-model 5×3 grid: max |Dunnett contrast| per (task, axis).

    For each (model, task, axis), pick the max |diff_vs_baseline| across the
    Dunnett contrasts (i.e. the most extreme cell-vs-baseline shift).
    Saturated baseline cells are still included (the contrast values are
    meaningful even when baseline is exactly zero).
    """
    axes_order = ("frame", "incentive", "difficulty")
    n_rows = len(MODELS)
    n_cols = len(TASKS) * len(axes_order)

    matrix = np.full((n_rows, n_cols), np.nan)
    for col_t, t in enumerate(TASKS):
        d = json.loads(per_task_jsons[t].read_text())
        for col_a, axis in enumerate(axes_order):
            col = col_t * len(axes_order) + col_a
            for row, model in enumerate(MODELS):
                cell = d.get("per_model", {}).get(model, {}).get(axis, {})
                contrasts = cell.get("dunnett") or []
                if not contrasts:
                    continue
                max_abs = max(abs(c.get("diff_vs_baseline", 0.0) or 0.0) for c in contrasts)
                matrix[row, col] = max_abs

    # Per-task within-task scaling so T5 (0-20) doesn't dominate the colormap.
    scaled = matrix.copy()
    for col_t, t in enumerate(TASKS):
        cols = slice(col_t * 3, col_t * 3 + 3)
        block = scaled[:, cols]
        finite = block[np.isfinite(block)]
        if len(finite) > 0:
            mx = finite.max() if finite.max() > 0 else 1.0
            scaled[:, cols] = block / mx

    fig, ax = plt.subplots(figsize=(11, 5))
    im = ax.imshow(scaled, cmap="YlOrRd", vmin=0, vmax=1, aspect="auto")
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([MODEL_LABELS[m] for m in MODELS])

    # Two-tier x labels: task on top, axis below
    ax.set_xticks(range(n_cols))
    xlabels = []
    for t in TASKS:
        for axis in axes_order:
            xlabels.append(axis[:4])
    ax.set_xticklabels(xlabels, rotation=0, fontsize=8)
    # Top header for task names
    for col_t, t in enumerate(TASKS):
        center = col_t * 3 + 1
        ax.text(center, -0.7, TASK_LABELS[t], ha="center", va="bottom",
                fontsize=10, fontweight="bold")
        # vertical separators
        if col_t > 0:
            ax.axvline(col_t * 3 - 0.5, color="white", linewidth=2)
    # Annotate raw values
    for r in range(n_rows):
        for c in range(n_cols):
            raw = matrix[r, c]
            if np.isnan(raw):
                continue
            txt = f"{raw:.2f}"
            color = "white" if scaled[r, c] > 0.5 else "black"
            ax.text(c, r, txt, ha="center", va="center", fontsize=7, color=color)

    fig.colorbar(im, ax=ax, label="max |contrast vs baseline| (per-task scaled)")
    ax.set_title("Per-model response profile (v2)\n"
                 "Max |Dunnett contrast| per (task × axis), scaled within task",
                 fontsize=11, pad=20)
    fig.tight_layout()
    out_path = OUT_DIR / "fig4_per_model_profile_v2.pdf"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {out_path}")


# ── Table 3 v2: per-task F + eta^2 + dominant axis ───────────────────────

def table3_v2(per_task_jsons: dict, out_dir: Path) -> None:
    rows = []
    for t in TASKS:
        d = json.loads(per_task_jsons[t].read_text())
        eta = d["per_task_eta"]["eta_squared"]
        n = d["per_task_eta"]["n"]
        se = d["per_task_eta"]["se_method"]
        # Pull the omnibus F from the per-(model="all") fit if available...
        # Cleanest: use the interaction LR results AND the per-task eta^2 directly.
        eta_frame = eta.get("C(frame)", 0.0) or 0.0
        eta_incentive = eta.get("C(incentive)", 0.0) or 0.0
        eta_difficulty = eta.get("C(difficulty)", 0.0) or 0.0
        eta_model = eta.get("C(model)", 0.0) or 0.0
        eta_residual = eta.get("Residual", 0.0) or 0.0
        # Dominant non-residual term
        axis_etas = {"frame": eta_frame, "incentive": eta_incentive, "difficulty": eta_difficulty}
        dominant_axis = max(axis_etas, key=axis_etas.get)
        rows.append({
            "task":       TASK_LABELS[t],
            "n":          n,
            "se":         se,
            "model":      eta_model,
            "frame":      eta_frame,
            "incentive":  eta_incentive,
            "difficulty": eta_difficulty,
            "residual":   eta_residual,
            "dominant_axis": dominant_axis,
        })

    lines = [
        "# Table 3 (v2) — Per-task variance decomposition",
        "",
        "Replaces the v1 mean-|slope| aggregate. η² = SS_term / SS_total from",
        "Type II ANOVA on `y ~ C(model) + C(frame) + C(incentive) + C(difficulty)`.",
        "Cluster-robust SEs where item structure exists (T2/T4/T5).",
        "",
        "| Task | n | SE | η²(model) | η²(frame) | η²(incentive) | η²(difficulty) | residual | dominant axis |",
        "|---|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in rows:
        # Bold the dominant axis cell
        def fmt(key, value):
            s = f"{value:.4f}"
            return f"**{s}**" if r["dominant_axis"] == key else s
        lines.append(
            f"| {r['task']} | {r['n']} | {r['se']} | {r['model']:.4f} | "
            f"{fmt('frame', r['frame'])} | {fmt('incentive', r['incentive'])} | "
            f"{fmt('difficulty', r['difficulty'])} | {r['residual']:.4f} | "
            f"{r['dominant_axis']} |"
        )
    lines.append("")
    lines.append("**Note**: T2 Debate has 99% residual variance — no axis explains")
    lines.append("more than 0.2% of variance. The 'dominant axis' designation for T2")
    lines.append("is between three nearly-tied near-zero numbers and should not be")
    lines.append("interpreted as a real signal. v1 reported T2 as 'difficulty-dominant'")
    lines.append("based on the 0.061 mean |slope|, which this v2 view does not support.")
    out_path = out_dir / "table3_v2.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  wrote {out_path}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[figures] generating v2 figures...")

    rs = json.loads(RANKING_STAB.read_text())
    fig2_and_fig7(rs)

    fig3_per_task_aggregate(PER_TASK_REGRESSION)

    fig4_per_model_profile(PER_TASK_REGRESSION)

    table3_v2(PER_TASK_REGRESSION, REPO / "paper/cross_task/analysis")

    print("[figures] done.")


if __name__ == "__main__":
    main()
