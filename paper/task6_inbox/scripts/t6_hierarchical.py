"""T6 hierarchical analysis — two principled approaches side-by-side.

Approach (1): Mixed-effects with reduced random-effects structure.
  Three increasingly simple specifications, each tried until one converges
  cleanly:
    1a. Uncorrelated random slopes (random intercept + 3 independent slopes)
    1b. Random intercept + random slope on frame_z only
    1c. Random intercept only

Approach (2): OLS on all 1080 rollouts with model dummies, plus model-by-axis
  interactions. Standard errors are cluster-robust by model.

Both approaches test the same three contrasts on the population-level slopes:
  (A) frame > difficulty           one-sided
  (B) incentive ≠ 0                 two-sided
  (C) frame > incentive             one-sided

The two-stage paired-t result from t6_per_model_regression.py is reproduced
in the report for comparison.
"""

from __future__ import annotations

import csv
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as _s
import statsmodels.formula.api as smf
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = ROOT / "paper/cross_task/data/results.csv"
OUT_MD = ROOT / "paper/figures/t6_hierarchical.md"

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


def load_dataframe() -> pd.DataFrame:
    rows = []
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
                y = float(sr)
            except ValueError:
                continue
            f_l, i_l, d_l = r["frame"], r["incentive"], r["difficulty"]
            if f_l not in FRAME_CODE or i_l not in INCENT_CODE or d_l not in DIFF_CODE:
                continue
            rows.append({
                "model": r["model"],
                "frame_code": FRAME_CODE[f_l],
                "incent_code": INCENT_CODE[i_l],
                "diff_code": DIFF_CODE[d_l],
                "y": y,
            })
    df = pd.DataFrame(rows)
    for col, src in [("frame_z", "frame_code"), ("incent_z", "incent_code"), ("diff_z", "diff_code")]:
        df[col] = (df[src] - df[src].mean()) / df[src].std(ddof=0)
    return df


def fe_contrasts(beta: np.ndarray, cov: np.ndarray, names: list[str]):
    """Compute the three partition contrasts. Returns dict of (est, se, z, p2, p1)."""
    idx = {n: i for i, n in enumerate(names)}
    n_fe = len(names)

    def vec(**kwargs):
        v = np.zeros(n_fe)
        for k, val in kwargs.items():
            v[idx[k]] = val
        return v

    def test(c, directional=False):
        est = float(c @ beta)
        se = float(np.sqrt(c @ cov @ c))
        z = est / se if se > 0 else float("nan")
        p2 = 2 * (1 - _s.norm.cdf(abs(z)))
        p1 = (p2 / 2) if est > 0 else (1 - p2 / 2)
        return {"est": est, "se": se, "z": z, "p2": p2, "p1": p1}

    return {
        "A": test(vec(frame_z=1, diff_z=-1), directional=True),
        "B": test(vec(incent_z=1)),
        "C": test(vec(frame_z=1, incent_z=-1), directional=True),
    }


# -------- Approach 1: mixed-effects with reduced random structures --------

def fit_mixed_uncorrelated(df: pd.DataFrame):
    """Random intercept + uncorrelated random slopes for each axis.

    statsmodels MixedLM uses vc_formula for variance-component (uncorrelated)
    random slopes. We pass a dict of group-specific design columns.
    """
    vc = {
        "frame_z": "0 + frame_z",
        "incent_z": "0 + incent_z",
        "diff_z": "0 + diff_z",
    }
    model = smf.mixedlm(
        "y ~ frame_z + incent_z + diff_z",
        df,
        groups=df["model"],
        vc_formula=vc,
    )
    return model.fit(method=["lbfgs"], reml=True)


def fit_mixed_frame_only(df: pd.DataFrame):
    """Random intercept + random slope on frame_z only."""
    model = smf.mixedlm(
        "y ~ frame_z + incent_z + diff_z",
        df,
        groups=df["model"],
        re_formula="~ frame_z",
    )
    return model.fit(method=["lbfgs"], reml=True)


def fit_mixed_intercept_only(df: pd.DataFrame):
    """Random intercept only."""
    model = smf.mixedlm(
        "y ~ frame_z + incent_z + diff_z",
        df,
        groups=df["model"],
    )
    return model.fit(method=["lbfgs"], reml=True)


def converged_cleanly(result) -> bool:
    """Heuristic: optimizer converged + Hessian is PD + no boundary warnings."""
    try:
        # statsmodels stores convergence info in mle_retvals
        retvals = getattr(result, "mle_retvals", {}) or {}
        if not retvals.get("converged", True):
            return False
        # Boundary check: any random-effect variance pinned at zero
        cov_re = result.cov_re
        diag = np.diag(np.asarray(cov_re))
        if np.any(diag < 1e-8):
            return False
        return True
    except Exception:
        return False


def run_mixed(df: pd.DataFrame):
    """Try the three specifications in order; return (result, label, warnings_caught)."""
    specs = [
        ("uncorrelated random slopes (intercept + 3 indep. slopes)", fit_mixed_uncorrelated),
        ("random intercept + frame slope only", fit_mixed_frame_only),
        ("random intercept only", fit_mixed_intercept_only),
    ]
    last = None
    for label, fitter in specs:
        with warnings.catch_warnings(record=True) as wlist:
            warnings.simplefilter("always")
            try:
                result = fitter(df)
            except Exception as e:
                last = ("failed: " + label, None, [str(e)])
                continue
            wmsgs = [str(w.message) for w in wlist]
            clean = converged_cleanly(result) and not any("not positive definite" in m or "boundary" in m for m in wmsgs)
            print(f"[mixed] tried: {label} → clean={clean}; warnings: {len(wmsgs)}")
            if clean:
                return result, label, wmsgs
            last = (label, result, wmsgs)
    # Fall back to the last one even if not perfectly clean.
    label, result, wmsgs = last
    return result, label + " (warnings retained — see report)", wmsgs


# -------- Approach 2: OLS with cluster-robust SEs --------

def fit_ols_cluster(df: pd.DataFrame):
    """OLS with model dummies, no interactions: pooled fixed slopes.

    Model dummies absorb model-specific intercepts. Slopes are pooled across
    models (the 'fixed effect' question). Cluster-robust SEs by model.
    """
    formula = "y ~ frame_z + incent_z + diff_z + C(model)"
    return smf.ols(formula, df).fit(cov_type="cluster", cov_kwds={"groups": df["model"]})


def fit_ols_cluster_with_interactions(df: pd.DataFrame):
    """OLS with model dummies AND model-by-axis interactions.

    Each model gets its own slope (full interaction). The "average slope across
    models" is recovered as a linear contrast averaging over models. Cluster-
    robust SEs by model.
    """
    formula = (
        "y ~ frame_z + incent_z + diff_z + C(model) "
        "+ C(model):frame_z + C(model):incent_z + C(model):diff_z"
    )
    return smf.ols(formula, df).fit(cov_type="cluster", cov_kwds={"groups": df["model"]})


def main():
    df = load_dataframe()
    print(f"Loaded {len(df)} rollouts across {df['model'].nunique()} models.")

    # Approach 1: mixed-effects with reduced random structure.
    mixed_result, mixed_label, mixed_warnings = run_mixed(df)
    mixed_beta = np.asarray(mixed_result.fe_params)
    mixed_cov = np.asarray(mixed_result.cov_params())[: len(mixed_beta), : len(mixed_beta)]
    mixed_names = list(mixed_result.fe_params.index)
    mixed_C = fe_contrasts(mixed_beta, mixed_cov, mixed_names)

    # Approach 2: OLS pooled-slopes with cluster-robust SEs.
    ols_pool = fit_ols_cluster(df)
    ols_pool_names = list(ols_pool.params.index)
    ols_pool_beta = np.asarray(ols_pool.params)
    ols_pool_cov = np.asarray(ols_pool.cov_params())
    ols_pool_C = fe_contrasts(ols_pool_beta, ols_pool_cov, ols_pool_names)

    # Approach 2b: OLS with full interactions, then average per-model slopes via contrast.
    ols_int = fit_ols_cluster_with_interactions(df)
    int_names = list(ols_int.params.index)
    n_p = len(int_names)
    idx = {n: i for i, n in enumerate(int_names)}
    n_models = df["model"].nunique()

    def avg_slope_contrast(axis: str):
        """Build a contrast vector that returns the cross-model mean slope on `axis`.
        Each model's slope on `axis` is the main effect plus its interaction term
        (relative to the reference category, which is its own main effect)."""
        c = np.zeros(n_p)
        c[idx[axis]] = 1.0  # baseline (reference model) slope
        # Find all interaction terms C(model)[T.X]:axis
        interaction_terms = [n for n in int_names if n.endswith(":" + axis) and n.startswith("C(model)")]
        # Average is: baseline + (1/k)·sum of interactions, where k = number of models
        # Reference model contributes baseline (no interaction term named for it).
        # Other models contribute baseline + interaction_term.
        # Average across all k models = baseline + (sum of interactions) / k.
        for term in interaction_terms:
            c[idx[term]] = 1.0 / n_models
        return c

    cf = avg_slope_contrast("frame_z")
    ci = avg_slope_contrast("incent_z")
    cd = avg_slope_contrast("diff_z")
    beta = np.asarray(ols_int.params)
    cov = np.asarray(ols_int.cov_params())

    def wald(c):
        est = float(c @ beta)
        se = float(np.sqrt(c @ cov @ c))
        z = est / se if se > 0 else float("nan")
        p2 = 2 * (1 - _s.norm.cdf(abs(z)))
        p1 = (p2 / 2) if est > 0 else (1 - p2 / 2)
        return {"est": est, "se": se, "z": z, "p2": p2, "p1": p1}

    ols_int_C = {
        "A": wald(cf - cd),
        "B": wald(ci),
        "C": wald(cf - ci),
    }

    # Two-stage paired-t (reproduce from t6_per_model_regression.py for the report).
    by_model = defaultdict(list)
    for _, r in df.iterrows():
        by_model[r["model"]].append(r)
    bf, bi, bd = [], [], []
    for m in PAPER_MODELS:
        sub = pd.DataFrame(by_model[m])
        X = sm.add_constant(sub[["frame_z", "incent_z", "diff_z"]].values)
        ymv = sub["y"].values
        b = np.linalg.lstsq(X, ymv, rcond=None)[0]
        bf.append(b[1]); bi.append(b[2]); bd.append(b[3])
    bf, bi, bd = np.array(bf), np.array(bi), np.array(bd)
    ts_A = _s.ttest_rel(bf, bd, alternative="greater")
    ts_C = _s.ttest_rel(bf, bi, alternative="greater")
    ts_B = _s.ttest_1samp(bi, 0.0)

    # Build report.
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    md = []
    md.append("# T6 Hierarchical Analysis — §4.3 Partition Claim\n")
    md.append(
        "Three approaches to the same population-level question — \"is the frame slope larger "
        "than the difficulty slope across the population of models?\" — fit on all 1080 paper-"
        "cohort T6 rollouts. Predictors: z-scored level codes (frame: prohibitive=0..permissive=4; "
        "incentive: none=0..high=2; difficulty: low=0..high=2).\n\n"
        "Three contrasts, identical across approaches:\n"
        "- (A) `β_frame − β_difficulty > 0` (one-sided)\n"
        "- (B) `β_incentive ≠ 0` (two-sided)\n"
        "- (C) `β_frame − β_incentive > 0` (one-sided)\n"
    )

    md.append("## Approach 1 — Mixed-Effects (REML)\n")
    md.append(f"Specification used: **{mixed_label}**.\n")
    if mixed_warnings:
        md.append("Convergence/fit warnings caught:")
        for w in mixed_warnings[:8]:
            md.append(f"- `{w}`")
        md.append("")
    md.append("Fixed effects:\n")
    md.append("| Term | Estimate | SE | z | p (two-sided) |")
    md.append("|---|---:|---:|---:|---:|")
    fe_se = mixed_result.bse_fe
    for nm in mixed_names:
        est = mixed_result.fe_params[nm]
        se = fe_se[nm]
        z = est / se if se > 0 else float("nan")
        pp = 2 * (1 - _s.norm.cdf(abs(z)))
        md.append(f"| {nm} | {est:+.4f} | {se:.4f} | {z:+.3f} | {pp:.4f} |")
    md.append("")
    md.append("Partition contrasts:\n")
    md.append(f"- (A) frame > diff: Δ = {mixed_C['A']['est']:+.4f}, SE = {mixed_C['A']['se']:.4f}, z = {mixed_C['A']['z']:+.3f}, **one-sided p = {mixed_C['A']['p1']:.4f}**")
    md.append(f"- (B) incent ≠ 0: β = {mixed_C['B']['est']:+.4f}, SE = {mixed_C['B']['se']:.4f}, z = {mixed_C['B']['z']:+.3f}, **two-sided p = {mixed_C['B']['p2']:.4f}**")
    md.append(f"- (C) frame > incent: Δ = {mixed_C['C']['est']:+.4f}, SE = {mixed_C['C']['se']:.4f}, z = {mixed_C['C']['z']:+.3f}, **one-sided p = {mixed_C['C']['p1']:.4f}**\n")

    md.append("## Approach 2a — OLS, Pooled Slopes, Cluster-Robust SEs (clusters=model)\n")
    md.append("Single slope per axis, model dummies absorb intercept differences. SEs use the "
              "Liang–Zeger cluster-robust sandwich estimator with model as the cluster variable.\n")
    md.append("Pooled slopes:\n")
    md.append("| Term | Estimate | Cluster SE | z | p (two-sided) |")
    md.append("|---|---:|---:|---:|---:|")
    for axis in ("frame_z", "incent_z", "diff_z"):
        i = ols_pool_names.index(axis)
        est = ols_pool_beta[i]
        se = float(np.sqrt(ols_pool_cov[i, i]))
        z = est / se if se > 0 else float("nan")
        pp = 2 * (1 - _s.norm.cdf(abs(z)))
        md.append(f"| {axis} | {est:+.4f} | {se:.4f} | {z:+.3f} | {pp:.4f} |")
    md.append("")
    md.append("Partition contrasts:\n")
    md.append(f"- (A) frame > diff: Δ = {ols_pool_C['A']['est']:+.4f}, SE = {ols_pool_C['A']['se']:.4f}, z = {ols_pool_C['A']['z']:+.3f}, **one-sided p = {ols_pool_C['A']['p1']:.4f}**")
    md.append(f"- (B) incent ≠ 0: β = {ols_pool_C['B']['est']:+.4f}, SE = {ols_pool_C['B']['se']:.4f}, z = {ols_pool_C['B']['z']:+.3f}, **two-sided p = {ols_pool_C['B']['p2']:.4f}**")
    md.append(f"- (C) frame > incent: Δ = {ols_pool_C['C']['est']:+.4f}, SE = {ols_pool_C['C']['se']:.4f}, z = {ols_pool_C['C']['z']:+.3f}, **one-sided p = {ols_pool_C['C']['p1']:.4f}**\n")

    md.append("## Approach 2b — OLS, Full Model×Axis Interactions, Cluster-Robust SEs\n")
    md.append("Each model gets its own per-axis slope (saturated interaction model). Population-"
              "level slopes are recovered as the unweighted cross-model average via linear "
              "contrasts. Cluster-robust SEs by model.\n")
    md.append("Partition contrasts (cross-model averages):\n")
    md.append(f"- (A) frame > diff: Δ = {ols_int_C['A']['est']:+.4f}, SE = {ols_int_C['A']['se']:.4f}, z = {ols_int_C['A']['z']:+.3f}, **one-sided p = {ols_int_C['A']['p1']:.4f}**")
    md.append(f"- (B) incent ≠ 0: β = {ols_int_C['B']['est']:+.4f}, SE = {ols_int_C['B']['se']:.4f}, z = {ols_int_C['B']['z']:+.3f}, **two-sided p = {ols_int_C['B']['p2']:.4f}**")
    md.append(f"- (C) frame > incent: Δ = {ols_int_C['C']['est']:+.4f}, SE = {ols_int_C['C']['se']:.4f}, z = {ols_int_C['C']['z']:+.3f}, **one-sided p = {ols_int_C['C']['p1']:.4f}**\n")

    md.append("## Comparison: Two-Stage Paired-t (from t6_per_model_regression.py)\n")
    md.append(f"- (A) frame > diff: t = {ts_A.statistic:+.3f}, **one-sided p = {ts_A.pvalue:.4f}**")
    md.append(f"- (B) incent ≠ 0: t = {ts_B.statistic:+.3f}, **two-sided p = {ts_B.pvalue:.4f}**")
    md.append(f"- (C) frame > incent: t = {ts_C.statistic:+.3f}, **one-sided p = {ts_C.pvalue:.4f}**\n")

    md.append("## Summary Table — All Four Approaches\n")
    md.append("| Approach | A: frame>diff | B: incent≠0 | C: frame>incent |")
    md.append("|---|---:|---:|---:|")
    md.append(f"| Mixed-effects ({mixed_label}) | {mixed_C['A']['p1']:.4f} | {mixed_C['B']['p2']:.4f} | {mixed_C['C']['p1']:.4f} |")
    md.append(f"| OLS pooled, cluster-robust SE | {ols_pool_C['A']['p1']:.4f} | {ols_pool_C['B']['p2']:.4f} | {ols_pool_C['C']['p1']:.4f} |")
    md.append(f"| OLS interactions, cluster-robust SE | {ols_int_C['A']['p1']:.4f} | {ols_int_C['B']['p2']:.4f} | {ols_int_C['C']['p1']:.4f} |")
    md.append(f"| Two-stage paired t (n=6) | {ts_A.pvalue:.4f} | {ts_B.pvalue:.4f} | {ts_C.pvalue:.4f} |\n")

    md.append("## Interpretation\n")
    md.append(
        "All four approaches address the same population-level question — whether the partition "
        "claim (frame > difficulty, frame > incentive, incentive small) holds across the model "
        "population — using different machinery for the standard errors. With a balanced design "
        "(180 rollouts × 6 models, fully crossed cells) they should give similar answers, and "
        "the agreement (or disagreement) across them is itself a robustness diagnostic.\n\n"
        "- The **mixed-effects** approach is the textbook reference, but with n=6 groups the "
        "random-effects covariance is hard to estimate; we use a reduced specification.\n"
        "- The **cluster-robust OLS** approaches give the same point estimates as mixed-effects "
        "for the population-mean slopes (the data is balanced) but compute SEs from the "
        "between-cluster variability via a sandwich estimator. No convergence issues.\n"
        "- The **two-stage paired-t** is the simplest and most transparent: fit per-model "
        "regressions, then test the resulting 6-vector of coefficients with paired tests. "
        "Lower power than the cluster-robust approaches but the easiest to defend.\n"
    )

    OUT_MD.write_text("\n".join(md) + "\n")

    print()
    print(f"Mixed-effects ({mixed_label}):")
    print(f"  A frame>diff:    Δ={mixed_C['A']['est']:+.4f}  z={mixed_C['A']['z']:+.3f}  p1={mixed_C['A']['p1']:.4f}")
    print(f"  B incent≠0:       β={mixed_C['B']['est']:+.4f}  z={mixed_C['B']['z']:+.3f}  p2={mixed_C['B']['p2']:.4f}")
    print(f"  C frame>incent:  Δ={mixed_C['C']['est']:+.4f}  z={mixed_C['C']['z']:+.3f}  p1={mixed_C['C']['p1']:.4f}")
    print(f"OLS pooled + cluster-robust SE:")
    print(f"  A: p1={ols_pool_C['A']['p1']:.4f}  B: p2={ols_pool_C['B']['p2']:.4f}  C: p1={ols_pool_C['C']['p1']:.4f}")
    print(f"OLS interactions + cluster-robust SE:")
    print(f"  A: p1={ols_int_C['A']['p1']:.4f}  B: p2={ols_int_C['B']['p2']:.4f}  C: p1={ols_int_C['C']['p1']:.4f}")
    print(f"Two-stage paired-t:")
    print(f"  A: p1={ts_A.pvalue:.4f}  B: p2={ts_B.pvalue:.4f}  C: p1={ts_C.pvalue:.4f}")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
