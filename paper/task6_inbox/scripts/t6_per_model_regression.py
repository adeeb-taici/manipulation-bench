"""T6 per-model regression + meta-analysis for the §4.3 partition claim.

For each of the 6 paper-cohort models, regress per-rollout suppression_rate
on z-scored frame, incentive, and difficulty level codes:

    suppression_rate ~ frame_z + incentive_z + difficulty_z

Levels are coded by their canonical ordering (frame: prohibitive=0 ... permissive=4;
incentive: none=0..high=2; difficulty: low=0..high=2), then z-scored across the
sample. This makes the three slopes directly comparable in units of "SD of the
axis variable mapped to suppression rate."

We then test the partition claim across the 6 models with three contrasts:

  (A) frame slope > difficulty slope, paired across models  (Wilcoxon signed-rank)
  (B) |frame slope| > |difficulty slope|, paired                  (Wilcoxon, two-sided)
  (C) incentive slope ~= 0                                          (one-sample t)

Outputs both per-model coefficients with SEs (OLS) and the meta-analysis tests.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = ROOT / "paper/cross_task/data/results.csv"
OUT_MD = ROOT / "paper/figures/t6_per_model_regression.md"

PAPER_MODELS = ("Claude-Opus-4.7", "GPT-5.5", "Gemini-3.1-Pro", "Grok-4",
                "Llama-3.3-70B", "DeepSeek-V4-Pro")
DISPLAY = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5": "GPT-5.5",
    "Gemini-3.1-Pro": "Gemini 3.1 Pro",
    "Grok-4": "Grok 4",
    "Llama-3.3-70B": "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
}

FRAME_CODE = {"prohibitive": 0, "pro_social": 1, "minimal": 2, "selfish": 3, "permissive": 4}
INCENT_CODE = {"none": 0, "moderate": 1, "high": 2}
DIFF_CODE = {"low": 0, "medium": 1, "high": 2}


def load_rows():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["task"] != "inbox":
                continue
            if r.get("variant", "").endswith("_pilot"):
                continue
            if r["model"] not in PAPER_MODELS:
                continue
            sr = r.get("inbox_triage__suppression_rate", "")
            if sr in ("", None):
                continue
            try:
                sr_val = float(sr)
            except ValueError:
                continue
            f_l, i_l, d_l = r["frame"], r["incentive"], r["difficulty"]
            if f_l not in FRAME_CODE or i_l not in INCENT_CODE or d_l not in DIFF_CODE:
                continue
            yield {
                "model": r["model"],
                "frame_code": FRAME_CODE[f_l],
                "incent_code": INCENT_CODE[i_l],
                "diff_code": DIFF_CODE[d_l],
                "y": sr_val,
            }


def ols(X: np.ndarray, y: np.ndarray):
    """Returns (beta, se, t, p, r2). X has intercept column."""
    n, k = X.shape
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    dof = n - k
    sigma2 = (resid @ resid) / dof
    cov = sigma2 * XtX_inv
    se = np.sqrt(np.diag(cov))
    t = beta / se
    p = 2 * (1 - stats.t.cdf(np.abs(t), df=dof))
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - (resid @ resid) / ss_tot if ss_tot > 0 else 0.0
    return beta, se, t, p, r2


def fit_model(rows: list[dict]):
    """Returns (intercept, beta_frame, beta_incent, beta_diff) and SEs in
    z-scored units."""
    n = len(rows)
    f = np.array([r["frame_code"] for r in rows], dtype=float)
    i = np.array([r["incent_code"] for r in rows], dtype=float)
    d = np.array([r["diff_code"] for r in rows], dtype=float)
    y = np.array([r["y"] for r in rows], dtype=float)
    f_z = (f - f.mean()) / f.std(ddof=0) if f.std(ddof=0) > 0 else f * 0
    i_z = (i - i.mean()) / i.std(ddof=0) if i.std(ddof=0) > 0 else i * 0
    d_z = (d - d.mean()) / d.std(ddof=0) if d.std(ddof=0) > 0 else d * 0
    X = np.column_stack([np.ones(n), f_z, i_z, d_z])
    return ols(X, y)


def main():
    by_model = defaultdict(list)
    for r in load_rows():
        by_model[r["model"]].append(r)

    print(f"Per-model n: " + ", ".join(f"{m}={len(by_model[m])}" for m in PAPER_MODELS))

    table = []  # (model, beta_frame, se_frame, p_frame, beta_incent, ..., beta_diff, ..., r2)
    for m in PAPER_MODELS:
        rows = by_model[m]
        beta, se, t, p, r2 = fit_model(rows)
        table.append({
            "model": m, "n": len(rows),
            "b_frame": beta[1], "se_frame": se[1], "p_frame": p[1],
            "b_incent": beta[2], "se_incent": se[2], "p_incent": p[2],
            "b_diff": beta[3], "se_diff": se[3], "p_diff": p[3],
            "r2": r2,
        })

    bf = np.array([row["b_frame"] for row in table])
    bi = np.array([row["b_incent"] for row in table])
    bd = np.array([row["b_diff"] for row in table])

    # Contrast A: frame > difficulty (signed). Wilcoxon signed-rank, one-sided.
    diffs_signed = bf - bd
    try:
        wA = stats.wilcoxon(diffs_signed, alternative="greater")
        wA_stat, wA_p = wA.statistic, wA.pvalue
    except ValueError:
        wA_stat, wA_p = float("nan"), float("nan")

    # Contrast B: |frame| > |difficulty|. Wilcoxon signed-rank, one-sided.
    diffs_abs = np.abs(bf) - np.abs(bd)
    try:
        wB = stats.wilcoxon(diffs_abs, alternative="greater")
        wB_stat, wB_p = wB.statistic, wB.pvalue
    except ValueError:
        wB_stat, wB_p = float("nan"), float("nan")

    # Paired t-test variants (parametric companion).
    tA_stat, tA_p = stats.ttest_rel(bf, bd, alternative="greater")
    tB_stat, tB_p = stats.ttest_rel(np.abs(bf), np.abs(bd), alternative="greater")

    # Contrast C: incentive ~= 0. Two-sided one-sample t-test on raw slopes.
    tC_stat, tC_p = stats.ttest_1samp(bi, 0.0)

    # Sign test: how many models have |frame| > |difficulty|?
    n_pos = int((np.abs(bf) > np.abs(bd)).sum())
    sign_p = stats.binomtest(n_pos, n=len(bf), p=0.5, alternative="greater").pvalue

    # Hedges-style summary across models (mean and SE of cross-model slopes)
    mean_bf, se_bf = bf.mean(), bf.std(ddof=1) / np.sqrt(len(bf))
    mean_bi, se_bi = bi.mean(), bi.std(ddof=1) / np.sqrt(len(bi))
    mean_bd, se_bd = bd.mean(), bd.std(ddof=1) / np.sqrt(len(bd))

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    md = []
    md.append("# T6 Per-Model Regression — §4.3 Partition Claim\n")
    md.append(
        "## Methodology\n\n"
        "For each of the 6 paper-cohort models, suppression_rate is regressed on z-scored "
        "level codes for each axis:\n\n"
        "    suppression_rate ~ intercept + frame_z + incentive_z + difficulty_z\n\n"
        "Levels are coded by canonical ordering (frame: prohibitive=0 ... permissive=4; "
        "incentive: none=0 .. high=2; difficulty: low=0 .. high=2), then z-scored across each "
        "model's sample (so coefficients are in units of 'SD of axis level' → suppression rate). "
        "OLS with classical SEs (no clustering — sample-level, not cell-level, so within-cell "
        "correlation is mild but not zero; treat SEs as approximate at the per-model level). "
        "The cross-model partition test uses the resulting 6-vector of coefficients per axis.\n\n"
        "**Cross-model contrasts:**\n"
        "- (A) `β_frame > β_difficulty` (signed): paired Wilcoxon signed-rank, one-sided.\n"
        "- (B) `|β_frame| > |β_difficulty|` (magnitude): paired Wilcoxon signed-rank, one-sided. "
        "This is the one that maps to the partition claim — direction is unconstrained per model.\n"
        "- (C) `β_incentive ≈ 0`: one-sample t-test against zero, two-sided.\n"
        "- (S) Sign test on `|β_frame| > |β_difficulty|`: binomial against p=0.5, one-sided.\n\n"
        "Paired t-test companions are reported alongside the Wilcoxon tests.\n"
    )

    md.append("## Per-Model Coefficients (z-scored predictors)\n")
    md.append("| Model | n | β_frame (SE) | β_incent (SE) | β_diff (SE) | R² |")
    md.append("|---|---:|---:|---:|---:|---:|")
    for row in table:
        md.append(
            f"| {DISPLAY[row['model']]} | {row['n']} | "
            f"{row['b_frame']:+.4f} ({row['se_frame']:.4f}) | "
            f"{row['b_incent']:+.4f} ({row['se_incent']:.4f}) | "
            f"{row['b_diff']:+.4f} ({row['se_diff']:.4f}) | "
            f"{row['r2']:.3f} |"
        )
    md.append("")
    md.append(f"Cross-model means (raw signed slopes):")
    md.append(f"- mean β_frame      = {mean_bf:+.4f} (SE {se_bf:.4f})")
    md.append(f"- mean β_incentive  = {mean_bi:+.4f} (SE {se_bi:.4f})")
    md.append(f"- mean β_difficulty = {mean_bd:+.4f} (SE {se_bd:.4f})\n")

    md.append("## Cross-Model Partition Tests\n")
    md.append(f"**(A) Signed: β_frame > β_difficulty (paired across 6 models)**")
    md.append(f"- Wilcoxon signed-rank (one-sided): W = {wA_stat:.2f}, p = {wA_p:.4f}")
    md.append(f"- Paired t-test (one-sided): t = {tA_stat:.3f}, p = {tA_p:.4f}\n")
    md.append(f"**(B) Magnitude: |β_frame| > |β_difficulty| (paired)**")
    md.append(f"- Wilcoxon signed-rank (one-sided): W = {wB_stat:.2f}, p = {wB_p:.4f}")
    md.append(f"- Paired t-test (one-sided): t = {tB_stat:.3f}, p = {tB_p:.4f}\n")
    md.append(f"**(C) Incentive slope = 0 (one-sample t, two-sided)**")
    md.append(f"- t = {tC_stat:.3f}, p = {tC_p:.4f}\n")
    md.append(f"**(S) Sign test on |β_frame| > |β_difficulty|**")
    md.append(f"- {n_pos}/6 models satisfy; binomial one-sided p = {sign_p:.4f}\n")

    md.append("## Notes & Caveats\n")
    md.append(
        "- Per-rollout SEs in the OLS step ignore within-cell clustering (5 frame × 3 incentive "
        "× 3 difficulty = 45 cells per model, ~4 reps/cell). For more conservative SEs at the "
        "per-model level use cluster-robust SEs by cell; the cross-model meta-analysis uses only "
        "the point estimates and is unaffected by per-model SE choice.\n"
        "- All three axes are coded with equal-spacing on level index. If the underlying "
        "construct is non-linear (e.g., frame jumps from prohibitive→pro_social are larger than "
        "minimal→selfish), the slope estimates compress true effects toward the linear best-fit. "
        "This affects all axes equally.\n"
        "- n=6 models is small for nonparametric paired tests. Wilcoxon at n=6 has minimum "
        "achievable one-sided p of 0.0156 (when all 6 differences agree in sign). Paired t-test "
        "is more powerful when normality holds approximately; we report both.\n"
        "- This analysis uses signed slopes, so a strongly *negative* frame slope and a small "
        "positive difficulty slope would show as 'frame > difficulty' on |β| but not on signed β. "
        "For the §4.3 partition claim the magnitude contrast (B) is the relevant one.\n"
    )

    OUT_MD.write_text("\n".join(md) + "\n")

    print()
    print("Per-model coefficients (signed):")
    for row in table:
        print(f"  {DISPLAY[row['model']]:20s} β_frame={row['b_frame']:+.4f}  "
              f"β_incent={row['b_incent']:+.4f}  β_diff={row['b_diff']:+.4f}  R²={row['r2']:.3f}")
    print()
    print(f"(A) signed β_frame > β_diff:    Wilcoxon p = {wA_p:.4f}, paired-t p = {tA_p:.4f}")
    print(f"(B) |β_frame| > |β_diff|:        Wilcoxon p = {wB_p:.4f}, paired-t p = {tB_p:.4f}")
    print(f"(C) β_incentive = 0 (two-sided): t p = {tC_p:.4f}")
    print(f"(S) sign test: {n_pos}/6 models, p = {sign_p:.4f}")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
