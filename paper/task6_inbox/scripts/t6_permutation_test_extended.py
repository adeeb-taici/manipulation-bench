"""T6 permutation test, extended cohort (paper 6 + small-model sweep).

Loads per-sample suppression_rate rows from paper/cross_task/data/results.csv
(task=='inbox'), computes per-(model, axis, level) means and per-axis linear
slopes, then runs the same three-condition permutation test as
t6_permutation_test.py — this time across all 15 models (paper cohort + the
OpenAI/Anthropic small-model sweep).

Reports both:
  (a) the original 6-model paper-cohort result, and
  (b) the 15-model extended-cohort result,
side by side, plus marginals and observed test statistics.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = ROOT / "paper/cross_task/data/results.csv"
OUT_MD = ROOT / "paper/figures/t6_permutation_test_extended.md"

PAPER_MODELS = ("Claude-Opus-4.7", "GPT-5.5", "Gemini-3.1-Pro", "Grok-4", "Llama-3.3-70B", "DeepSeek-V4-Pro")
SMALL_MODELS = ("gpt41", "gpt41mini", "gpt41nano", "gpt54mini", "gpt54nano",
                "sonnet46", "sonnet37", "haiku45", "haiku35")
ALL_MODELS = PAPER_MODELS + SMALL_MODELS

DISPLAY = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5": "GPT-5.5",
    "Gemini-3.1-Pro": "Gemini 3.1 Pro",
    "Grok-4": "Grok 4",
    "Llama-3.3-70B": "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
    "gpt41": "GPT-4.1",
    "gpt41mini": "GPT-4.1 mini",
    "gpt41nano": "GPT-4.1 nano",
    "gpt54mini": "GPT-5.4 mini",
    "gpt54nano": "GPT-5.4 nano",
    "sonnet46": "Sonnet 4.6",
    "sonnet37": "Sonnet 3.7",
    "haiku45": "Haiku 4.5",
    "haiku35": "Haiku 3.5",
}

FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
INCENTIVES = ("none", "moderate", "high")
DIFFICULTIES = ("low", "medium", "high")

N_PERM = 100_000
N_BOOT = 10_000
SEED = 42


def load_inbox_rows():
    """Yield dicts of (model, frame, incentive, difficulty, suppression_rate)
    for inbox rows, dropping pilot variants and rows without a numeric score."""
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["task"] != "inbox":
                continue
            if row.get("variant", "").endswith("_pilot"):
                continue
            sr = row.get("inbox_triage__suppression_rate", "")
            if sr in ("", None):
                continue
            try:
                sr_val = float(sr)
            except ValueError:
                continue
            yield {
                "model": row["model"],
                "frame": row["frame"],
                "incentive": row["incentive"],
                "difficulty": row["difficulty"],
                "suppression_rate": sr_val,
            }


def build_cells(rows, models):
    cells = defaultdict(list)
    for r in rows:
        if r["model"] not in models:
            continue
        m = r["model"]
        cells[(m, "frame", r["frame"])].append(r["suppression_rate"])
        cells[(m, "incentive", r["incentive"])].append(r["suppression_rate"])
        cells[(m, "difficulty", r["difficulty"])].append(r["suppression_rate"])
    return {k: np.asarray(v, dtype=float) for k, v in cells.items()}


def slope_from_levels(values):
    x = np.arange(len(values), dtype=float)
    y = np.asarray(values, dtype=float)
    x = x - x.mean()
    y = y - y.mean()
    denom = (x * x).sum()
    return float((x * y).sum() / denom) if denom else 0.0


def abs_slopes_table(cells, models):
    M = np.zeros((len(models), 3))
    for i, model in enumerate(models):
        for j, (axis, levels) in enumerate(
            [("frame", FRAMES), ("incentive", INCENTIVES), ("difficulty", DIFFICULTIES)]
        ):
            level_means = []
            for lvl in levels:
                arr = cells.get((model, axis, lvl))
                level_means.append(float(arr.mean()) if arr is not None and len(arr) else 0.0)
            M[i, j] = abs(slope_from_levels(level_means))
    return M


def conditions(M):
    frame, incent, diff = M[:, 0], M[:, 1], M[:, 2]
    n = M.shape[0]
    cond1 = (frame.mean() / diff.mean()) >= 2.0 if diff.mean() > 0 else False
    threshold = int(np.ceil(2 * n / 3))  # ≥ 2/3 of models, generalizes the "≥4 of 6" rule
    cond2 = int((frame > diff).sum()) >= threshold
    cond3 = incent.mean() < 0.10
    return cond1, cond2, cond3, threshold


def permutation_test(M, n_perm, seed):
    rng = np.random.default_rng(seed)
    n_models = M.shape[0]
    c1 = c2 = c3 = joint = 0
    for _ in range(n_perm):
        perm = np.empty_like(M)
        for i in range(n_models):
            perm[i] = rng.permutation(M[i])
        a, b, c, _ = conditions(perm)
        c1 += a; c2 += b; c3 += c
        if a and b and c:
            joint += 1
    return {"n": n_perm, "p_joint": joint / n_perm, "p_cond1": c1 / n_perm,
            "p_cond2": c2 / n_perm, "p_cond3": c3 / n_perm}


def bootstrap_test(cells, models, n_boot, seed):
    rng = np.random.default_rng(seed)
    c1 = c2 = c3 = joint = 0
    for _ in range(n_boot):
        M = np.zeros((len(models), 3))
        for i, model in enumerate(models):
            for j, (axis, levels) in enumerate(
                [("frame", FRAMES), ("incentive", INCENTIVES), ("difficulty", DIFFICULTIES)]
            ):
                lvl_means = []
                for lvl in levels:
                    arr = cells.get((model, axis, lvl))
                    if arr is None or len(arr) == 0:
                        lvl_means.append(0.0)
                        continue
                    idx = rng.integers(0, len(arr), size=len(arr))
                    lvl_means.append(float(arr[idx].mean()))
                M[i, j] = abs(slope_from_levels(lvl_means))
        a, b, c, _ = conditions(M)
        c1 += a; c2 += b; c3 += c
        if a and b and c:
            joint += 1
    return {"n": n_boot, "p_joint": joint / n_boot, "p_cond1": c1 / n_boot,
            "p_cond2": c2 / n_boot, "p_cond3": c3 / n_boot}


def report_block(label, M, perm, boot, models):
    cond1, cond2, cond3, thr = conditions(M)
    n = M.shape[0]
    out = []
    out.append(f"### {label} (n={n} models)\n")
    out.append("| Model | |Frame| | |Incentive| | |Difficulty| |")
    out.append("|---|---:|---:|---:|")
    for i, m in enumerate(models):
        out.append(f"| {DISPLAY.get(m, m)} | {M[i,0]:.3f} | {M[i,1]:.3f} | {M[i,2]:.3f} |")
    out.append("")
    out.append(f"- mean(|frame|)      = {M[:,0].mean():.4f}")
    out.append(f"- mean(|incentive|)  = {M[:,1].mean():.4f}")
    out.append(f"- mean(|difficulty|) = {M[:,2].mean():.4f}")
    ratio = M[:, 0].mean() / M[:, 2].mean() if M[:, 2].mean() > 0 else float("inf")
    out.append(f"- frame/difficulty ratio = {ratio:.3f}")
    out.append(f"- # models with |frame|>|difficulty| = {(M[:,0]>M[:,2]).sum()}/{n} (need ≥{thr} for cond2)")
    out.append(f"- cond1: {cond1}; cond2: {cond2}; cond3: {cond3}\n")
    out.append("**Permutation test:**")
    out.append(f"- N={perm['n']:,}, joint p = **{perm['p_joint']:.5f}**")
    out.append(f"- marginals — cond1: {perm['p_cond1']:.5f}, cond2: {perm['p_cond2']:.5f}, cond3: {perm['p_cond3']:.5f}\n")
    out.append("**Bootstrap (per-cell rollout resampling):**")
    out.append(f"- N={boot['n']:,}, joint robustness fraction = {boot['p_joint']:.5f}")
    out.append(f"- marginals — cond1: {boot['p_cond1']:.5f}, cond2: {boot['p_cond2']:.5f}, cond3: {boot['p_cond3']:.5f}\n")
    return "\n".join(out)


def main():
    rows = list(load_inbox_rows())
    print(f"Loaded {len(rows)} inbox rows.")
    counts = defaultdict(int)
    for r in rows:
        counts[r["model"]] += 1
    for m in ALL_MODELS:
        print(f"  {m}: n={counts.get(m, 0)}")

    cells_paper = build_cells(rows, set(PAPER_MODELS))
    cells_all = build_cells(rows, set(ALL_MODELS))

    M_paper = abs_slopes_table(cells_paper, PAPER_MODELS)
    M_all = abs_slopes_table(cells_all, ALL_MODELS)

    perm_paper = permutation_test(M_paper, N_PERM, SEED)
    perm_all = permutation_test(M_all, N_PERM, SEED)
    boot_paper = bootstrap_test(cells_paper, PAPER_MODELS, N_BOOT, SEED)
    boot_all = bootstrap_test(cells_all, ALL_MODELS, N_BOOT, SEED)

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    md = []
    md.append("# T6 Permutation Test — Extended Cohort\n")
    md.append(
        "Re-runs the §4.3 partition permutation test on the expanded T6 model set: "
        "the 6 paper-cohort frontier models plus 9 smaller models from the OpenAI "
        "and Anthropic sweeps (GPT-4.1 family, GPT-5.4 mini/nano, Sonnet 3.7 / 4.6, "
        "Haiku 3.5 / 4.5). Methodology is identical to "
        "`paper/figures/t6_permutation_test.md`: within-row axis-label permutation, "
        "three pre-registered conditions (frame/difficulty ≥ 2× aggregate, frame > "
        "difficulty in ≥ ⌈2n/3⌉ models individually, mean |incentive| < 0.10), "
        "100,000 permutations, seed 42.\n"
    )
    md.append("## Paper cohort (n=6, original test)\n")
    md.append(report_block("Paper cohort", M_paper, perm_paper, boot_paper, PAPER_MODELS))
    md.append("## Extended cohort (n=15, paper + small-model sweep)\n")
    md.append(report_block("Extended cohort", M_all, perm_all, boot_all, ALL_MODELS))
    md.append("## Caveats\n")
    md.append(
        "- The cond2 threshold is generalized from \"≥4 of 6\" to \"≥⌈2n/3⌉\" so the per-model "
        "majority condition has the same intent (clear majority of models) at both cohort sizes.\n"
        "- Small-model sweeps may have different per-cell sample counts than the paper cohort "
        "(180 samples/model). The slope estimator is the same linear regression over level means "
        "regardless of cell n; bootstrap accounts for sampling variability per cell.\n"
        "- Extending the cohort post-hoc is itself a researcher-degree-of-freedom decision. "
        "The paper-cohort number remains the canonical pre-registered test; the extended-cohort "
        "number is reported as a sensitivity analysis.\n"
    )
    OUT_MD.write_text("\n".join(md) + "\n")

    print()
    print(f"Paper-cohort permutation joint p = {perm_paper['p_joint']:.5f}")
    print(f"Extended-cohort permutation joint p = {perm_all['p_joint']:.5f}")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
