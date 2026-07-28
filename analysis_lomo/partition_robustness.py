"""Pre-specified robustness battery for the Section 4.3 partition coefficient.

Pre-specified BEFORE seeing results, and reported in full regardless of what
they show. Three tests, all on the same regression the paper reports:

    Delta_D ~ 1 + assertive        (36 rows = 6 models x 6 environments)

with Delta_D = |beta_difficulty| - max(|beta_frame|, |beta_incentive|) from the
per-(model, environment) three-axis OLS, exactly as
paper/cross_task/scripts/cross_task/model_task_axis_sensitivity.py computes it.
That module is imported, not reimplemented.

  (1) Wild cluster bootstrap-t, Webb six-point weights, null imposed,
      B = 9,999, seed 20260728. Clusters = environment (G = 6). Webb weights
      are the standard choice for G < 10 because Rademacher admits only
      2^G = 64 distinct draws at G = 6, which floors the bootstrap p-value at
      1/64; Webb gives 6^6 = 46,656.

  (2) Randomization inference: enumerate all C(6,3) = 20 partitions of the six
      environments into two groups of three, recompute the coefficient under
      each, and locate the observed assignment in that exact distribution. The
      attainable one-sided minimum is 1/20 = 0.05 -- a hard ceiling on this
      design's power, independent of effect size or sample size.

  (3) Leverage and variance decomposition: per-environment cluster leverage,
      leave-one-cluster-out coefficients, and the between- vs within-cluster
      split of Delta_D.

STRUCTURAL NOTE, which is the real power story: `assertive` is a deterministic
function of environment, so it does not vary within cluster. The design is
cluster-randomized with 6 clusters and a 3-vs-3 split; the effective sample
size for this contrast is 6, not 36. Adding models adds rows but no clusters
and cannot raise the RI floor below 0.05.

Run from the repo root:
    python analysis_lomo/partition_robustness.py
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy import stats

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "analysis_lomo"
XT = REPO / "paper/cross_task/scripts/cross_task"

SEED = 20260728
B = 9999
WEBB = np.array([-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)])

sys.path.insert(0, str(XT))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mtas = _load("mtas_rb", XT / "model_task_axis_sensitivity.py")
MODELS = list(mtas.PAPER_MODELS)
DISPLAY = dict(mtas.DISPLAY)
ENVS = list(mtas.TASKS)
TASK_TYPE = dict(mtas.TASK_TYPE)


def delta_d_rows() -> list[dict]:
    by_cell = mtas.load_rows()
    rows = []
    for env in ENVS:
        for model in MODELS:
            beta, _se = mtas.ols_coefficients(by_cell[(model, env)])
            b_f, b_i, b_d = float(beta[1]), float(beta[2]), float(beta[3])
            rows.append(
                {
                    "model": model,
                    "env": env,
                    "assertive": 1.0 if TASK_TYPE[env] == "assertive" else 0.0,
                    "delta_d": abs(b_d) - max(abs(b_f), abs(b_i)),
                }
            )
    return rows


def _cr1(X: np.ndarray, resid: np.ndarray, groups: np.ndarray) -> np.ndarray:
    """CR1 cluster-robust covariance -- same estimator as mtas.task_cluster_robust."""
    n, k = X.shape
    uniq = sorted(set(groups.tolist()))
    g = len(uniq)
    xtx_inv = np.linalg.inv(X.T @ X)
    meat = np.zeros((k, k))
    for cl in uniq:
        idx = np.where(groups == cl)[0]
        score = X[idx, :].T @ resid[idx]
        meat += np.outer(score, score)
    cov = xtx_inv @ meat @ xtx_inv
    cov *= (g / (g - 1)) * ((n - 1) / (n - k))
    return cov


def fit(y: np.ndarray, x: np.ndarray, groups: np.ndarray) -> dict:
    X = np.column_stack([np.ones(len(y)), x])
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta
    cov = _cr1(X, resid, groups)
    se = math.sqrt(cov[1, 1])
    g = len(set(groups.tolist()))
    t = beta[1] / se
    return {
        "beta": float(beta[1]),
        "se_cluster": float(se),
        "t": float(t),
        "p_cluster": float(2 * (1 - stats.t.cdf(abs(t), df=g - 1))),
        "X": X,
        "resid": resid,
        "beta_full": beta,
    }


# ── (1) wild cluster bootstrap-t, Webb weights, null imposed ───────────────


def wild_cluster_bootstrap(y, x, groups, b=B, seed=SEED) -> dict:
    obs = fit(y, x, groups)
    t_obs = obs["t"]

    # Restricted fit: impose beta_assertive = 0 -> intercept-only model.
    Xr = np.ones((len(y), 1))
    beta_r = np.linalg.inv(Xr.T @ Xr) @ Xr.T @ y
    fitted_r = Xr @ beta_r
    resid_r = y - fitted_r

    uniq = sorted(set(groups.tolist()))
    rng = np.random.default_rng(seed)
    t_star = np.empty(b)
    for i in range(b):
        w = {cl: WEBB[rng.integers(0, 6)] for cl in uniq}
        wvec = np.array([w[c] for c in groups], dtype=float)
        y_star = fitted_r + wvec * resid_r
        try:
            t_star[i] = fit(y_star, x, groups)["t"]
        except np.linalg.LinAlgError:
            t_star[i] = np.nan

    valid = t_star[~np.isnan(t_star)]
    # Symmetric (two-sided) bootstrap-t p-value.
    p_two = (1 + int(np.sum(np.abs(valid) >= abs(t_obs)))) / (len(valid) + 1)
    p_one = (1 + int(np.sum(valid >= t_obs))) / (len(valid) + 1)
    return {
        "t_observed": t_obs,
        "B_valid": int(len(valid)),
        "p_two_sided": float(p_two),
        "p_one_sided": float(p_one),
        "t_star_q": {q: float(np.quantile(valid, q / 100)) for q in (2.5, 25, 50, 75, 97.5)},
        "weights": "Webb 6-point",
        "null_imposed": True,
        "seed": seed,
    }


# ── (2) randomization inference over all C(6,3) = 20 partitions ────────────


def randomization_inference(rows: list[dict], keep_models: list[str]) -> dict:
    """Coefficient under every 3-vs-3 assignment of environments."""
    env_means = {
        e: float(
            np.mean([r["delta_d"] for r in rows if r["env"] == e and r["model"] in keep_models])
        )
        for e in ENVS
    }
    observed = tuple(sorted(e for e in ENVS if TASK_TYPE[e] == "assertive"))
    draws = []
    for combo in combinations(sorted(ENVS), 3):
        grp = set(combo)
        # Coefficient of a cluster-level dummy = difference of group means of
        # the cluster means (balanced: 6 models per environment).
        coef = np.mean([env_means[e] for e in combo]) - np.mean(
            [env_means[e] for e in ENVS if e not in grp]
        )
        draws.append(
            {
                "assertive_set": list(combo),
                "coef": float(coef),
                "is_observed": tuple(sorted(combo)) == observed,
            }
        )
    coefs = np.array([d["coef"] for d in draws])
    obs_coef = float([d["coef"] for d in draws if d["is_observed"]][0])
    n_ge = int(np.sum(coefs >= obs_coef))
    rank = int(np.sum(coefs > obs_coef)) + 1
    return {
        "n_assignments": len(draws),
        "observed_assertive_set": list(observed),
        "observed_coef": obs_coef,
        "rank_of_observed_desc": rank,
        "p_one_sided_exact": n_ge / len(draws),
        "p_two_sided_exact": float(np.sum(np.abs(coefs) >= abs(obs_coef)) / len(draws)),
        "attainable_minimum_p": 1 / len(draws),
        "is_most_extreme": bool(rank == 1),
        "env_cluster_means": env_means,
        "all_assignments": sorted(draws, key=lambda d: -d["coef"]),
    }


# ── (3) leverage + variance decomposition ─────────────────────────────────


def diagnostics(rows: list[dict], keep_models: list[str]) -> dict:
    sub = [r for r in rows if r["model"] in keep_models]
    y = np.array([r["delta_d"] for r in sub])
    x = np.array([r["assertive"] for r in sub])
    groups = np.array([r["env"] for r in sub], dtype=object)
    X = np.column_stack([np.ones(len(y)), x])
    xtx_inv = np.linalg.inv(X.T @ X)

    base = fit(y, x, groups)
    lev, loo = {}, {}
    for e in ENVS:
        idx = np.where(groups == e)[0]
        Xg = X[idx, :]
        lev[e] = float(np.trace(Xg @ xtx_inv @ Xg.T))
        m = np.array([r["model"] for r in sub], dtype=object)
        keep = groups != e
        try:
            f = fit(y[keep], x[keep], groups[keep])
            loo[e] = {
                "beta": f["beta"],
                "p_cluster": f["p_cluster"],
                "delta_beta": f["beta"] - base["beta"],
            }
        except Exception:  # noqa: BLE001
            loo[e] = None

    # between- vs within-cluster variance of Delta_D
    grand = float(np.mean(y))
    env_means = {e: float(np.mean(y[groups == e])) for e in ENVS}
    ss_total = float(np.sum((y - grand) ** 2))
    ss_between = float(sum(np.sum(groups == e) * (env_means[e] - grand) ** 2 for e in ENVS))
    ss_within = ss_total - ss_between

    return {
        "cluster_leverage_trace": lev,
        "leverage_note": "assertive does not vary within cluster, so every "
        "environment contributes identical leverage 1.0; the "
        "contrast is identified purely between clusters.",
        "leave_one_environment_out": loo,
        "variance_decomposition": {
            "ss_total": ss_total,
            "ss_between_cluster": ss_between,
            "ss_within_cluster": ss_within,
            "share_between": ss_between / ss_total if ss_total else float("nan"),
            "share_within": ss_within / ss_total if ss_total else float("nan"),
        },
        "env_cluster_means": env_means,
        "effective_n_for_contrast": len(ENVS),
        "rows": len(y),
    }


# ── main ──────────────────────────────────────────────────────────────────


def main() -> None:
    rows = delta_d_rows()
    out = {
        "prespecified": True,
        "spec": {
            "regression": "Delta_D ~ 1 + assertive",
            "cluster_unit": "environment (G=6)",
            "wild_bootstrap": {
                "weights": "Webb 6-point",
                "B": B,
                "null_imposed": True,
                "seed": SEED,
            },
            "randomization_inference": "exact over all C(6,3)=20 partitions",
            "power_ceiling": "RI attainable minimum one-sided p = 1/20 = 0.05",
        },
        "structural_note": (
            "assertive is a deterministic function of environment and does not "
            "vary within cluster. The contrast is cluster-level with G=6 and a "
            "3-vs-3 split; effective n = 6, not 36. Additional models add rows "
            "but no clusters and cannot lower the RI floor below 0.05."
        ),
    }

    print("=" * 78)
    print("SECTION 4.3 PARTITION -- PRE-SPECIFIED ROBUSTNESS BATTERY")
    print("=" * 78)

    rosters = [("(full roster)", MODELS)] + [
        (DISPLAY[x], [m for m in MODELS if m != x]) for x in MODELS
    ]

    results = {}
    for label, keep in rosters:
        sub = [r for r in rows if r["model"] in keep]
        y = np.array([r["delta_d"] for r in sub])
        x = np.array([r["assertive"] for r in sub])
        g = np.array([r["env"] for r in sub], dtype=object)

        base = fit(y, x, g)
        wcb = wild_cluster_bootstrap(y, x, g)
        ri = randomization_inference(rows, keep)
        results[label] = {
            "n_rows": len(y),
            "coef": base["beta"],
            "se_cr1": base["se_cluster"],
            "t": base["t"],
            "p_cr1_sandwich": base["p_cluster"],
            "p_wild_cluster_webb_two_sided": wcb["p_two_sided"],
            "p_wild_cluster_webb_one_sided": wcb["p_one_sided"],
            "wild_detail": wcb,
            "randomization_inference": ri,
        }
        print(f"\n--- exclude: {label}")
        print(
            f"    rows={len(y)}  coef={base['beta']:+.4f}  CR1 SE={base['se_cluster']:.4f}  "
            f"t={base['t']:+.3f}"
        )
        print(f"    p (CR1 sandwich, df=5) .............. {base['p_cluster']:.4f}")
        print(f"    p (wild cluster, Webb, 2-sided) ..... {wcb['p_two_sided']:.4f}")
        print(f"    p (wild cluster, Webb, 1-sided) ..... {wcb['p_one_sided']:.4f}")
        print(
            f"    p (randomization, exact 1-sided) .... {ri['p_one_sided_exact']:.4f}  "
            f"(rank {ri['rank_of_observed_desc']}/20, floor {ri['attainable_minimum_p']:.2f})"
        )

    diag = diagnostics(rows, MODELS)
    out["results"] = results
    out["diagnostics_full_roster"] = diag

    print("\n" + "=" * 78)
    print("LEVERAGE / VARIANCE DECOMPOSITION (full roster)")
    print("=" * 78)
    vd = diag["variance_decomposition"]
    print(f"  Delta_D between-cluster share of SS: {vd['share_between']:.4f}")
    print(f"  Delta_D within-cluster  share of SS: {vd['share_within']:.4f}")
    print(
        f"  effective n for the contrast: {diag['effective_n_for_contrast']} clusters "
        f"({diag['rows']} rows)"
    )
    print("\n  environment cluster means of Delta_D:")
    for e, v in sorted(diag["env_cluster_means"].items(), key=lambda kv: -kv[1]):
        print(f"    {e:12s} {v:+.4f}   ({TASK_TYPE[e]})")
    print("\n  leave-one-ENVIRONMENT-out (not model) coefficient:")
    for e, d in diag["leave_one_environment_out"].items():
        if d:
            print(
                f"    drop {e:12s} coef={d['beta']:+.4f} (delta {d['delta_beta']:+.4f})  "
                f"p_cr1={d['p_cluster']:.4f}"
            )

    print("\n  RI distribution, full roster (top 6 of 20 assignments by coef):")
    for d in out["results"]["(full roster)"]["randomization_inference"]["all_assignments"][:6]:
        mark = "  <== OBSERVED" if d["is_observed"] else ""
        print(f"    {'+'.join(d['assertive_set']):40s} {d['coef']:+.4f}{mark}")

    def jsafe(o):
        if isinstance(o, dict):
            return {k: jsafe(v) for k, v in o.items() if k not in ("X", "resid", "beta_full")}
        if isinstance(o, (list, tuple)):
            return [jsafe(v) for v in o]
        if isinstance(o, (np.integer, np.floating)):
            return float(o)
        if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
            return None
        return o

    p = OUT_DIR / "partition_robustness.json"
    p.write_text(json.dumps(jsafe(out), indent=2), encoding="utf-8")
    print(f"\nwrote {p.relative_to(REPO)}")


if __name__ == "__main__":
    main()
