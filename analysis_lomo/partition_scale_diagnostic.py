"""POST-HOC diagnostic: is the Section 4.3 coefficient a metric-scale artifact?

NOT pre-specified. Added after the pre-specified leverage analysis in
partition_robustness.py revealed the problem, and reported for that reason
rather than selected from a menu of options.

The problem
-----------
Section 4.3 regresses `Delta_D = |beta_D| - max(|beta_F|, |beta_I|)` on an
`assertive` dummy, pooling all six environments. But Delta_D carries the units
of each environment's outcome metric, and those units are not common:

    T5 Committee   initial_bias on a 0-20 rating scale
    all others     rates in [0, 1]

Empirically the T5 coefficients are 10-25x larger in absolute value, so T5's
Delta_D (+0.771) is ~13x the next-largest assertive environment (sales, +0.061)
and dominates the between-cluster signal that identifies the contrast.

What is and is not affected
---------------------------
NOT affected: the sign of Delta_D per (model, environment). Delta_D compares
|beta_D| against max(|beta_F|, |beta_I|) *within* one environment, so its sign is
invariant to any positive rescaling of that environment's metric. The 17/18 and
18/18 sign-agreement counts, the 6/6 dominant-axis LOMO stability, and the
randomization-inference rank are all therefore scale-free.

Affected: the magnitude of the pooled coefficient and every SE/p-value derived
from it.

The scale-free variant
----------------------
    Delta_rel = (|beta_D| - max(|beta_F|,|beta_I|)) / (|beta_D| + max(|beta_F|,|beta_I|))

in [-1, +1], invariant to positive rescaling of the environment's metric, and
sign-identical to Delta_D by construction. The same regression is refit on it.

Run from the repo root:
    python analysis_lomo/partition_scale_diagnostic.py
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
sys.path.insert(0, str(XT))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mtas = _load("mtas_sd", XT / "model_task_axis_sensitivity.py")
rb = _load("rb_mod", REPO / "analysis_lomo/partition_robustness.py")

MODELS = list(mtas.PAPER_MODELS)
DISPLAY = dict(mtas.DISPLAY)
ENVS = list(mtas.TASKS)
TASK_TYPE = dict(mtas.TASK_TYPE)


def rows_both() -> list[dict]:
    by_cell = mtas.load_rows()
    out = []
    for env in ENVS:
        for model in MODELS:
            beta, _ = mtas.ols_coefficients(by_cell[(model, env)])
            bf, bi, bd = abs(float(beta[1])), abs(float(beta[2])), abs(float(beta[3]))
            other = max(bf, bi)
            denom = bd + other
            out.append(
                {
                    "model": model,
                    "env": env,
                    "assertive": 1.0 if TASK_TYPE[env] == "assertive" else 0.0,
                    "delta_d": bd - other,
                    "delta_rel": (bd - other) / denom if denom > 0 else 0.0,
                    "scale_proxy": denom,
                }
            )
    return out


def main() -> None:
    rows = rows_both()

    print("=" * 78)
    print("POST-HOC SCALE DIAGNOSTIC (not pre-specified)")
    print("=" * 78)

    print("\nPer-environment scale proxy  mean(|beta_D| + max(|beta_F|,|beta_I|)):")
    for e in sorted(
        ENVS, key=lambda e: -np.mean([r["scale_proxy"] for r in rows if r["env"] == e])
    ):
        sp = np.mean([r["scale_proxy"] for r in rows if r["env"] == e])
        dd = np.mean([r["delta_d"] for r in rows if r["env"] == e])
        dr = np.mean([r["delta_rel"] for r in rows if r["env"] == e])
        print(
            f"  {e:12s} scale={sp:7.4f}   mean Delta_D={dd:+.4f}   "
            f"mean Delta_rel={dr:+.4f}   ({TASK_TYPE[e]})"
        )

    sp = {e: float(np.mean([r["scale_proxy"] for r in rows if r["env"] == e])) for e in ENVS}
    ratio = max(sp.values()) / min(sp.values())
    print(f"\n  largest/smallest environment scale ratio = {ratio:.1f}x")

    out = {
        "not_prespecified": True,
        "scale_proxy_by_env": sp,
        "max_min_scale_ratio": ratio,
        "results": {},
    }

    # sign agreement is scale-free -- verify identical under both
    for key in ("delta_d", "delta_rel"):
        a = [r for r in rows if r["assertive"] == 1.0]
        c = [r for r in rows if r["assertive"] == 0.0]
        print(
            f"\n  sign agreement on {key}: assertive "
            f"{sum(1 for r in a if r[key] > 0)}/{len(a)} >0, "
            f"commissive {sum(1 for r in c if r[key] < 0)}/{len(c)} <0"
        )

    for key, label in (
        ("delta_d", "Delta_D (as published)"),
        ("delta_rel", "Delta_rel (scale-free)"),
    ):
        print(f"\n--- regression on {label}")
        res = {}
        for lbl, keep in [("(full roster)", MODELS)] + [
            (DISPLAY[x], [m for m in MODELS if m != x]) for x in MODELS
        ]:
            sub = [r for r in rows if r["model"] in keep]
            y = np.array([r[key] for r in sub])
            x = np.array([r["assertive"] for r in sub])
            g = np.array([r["env"] for r in sub], dtype=object)
            base = rb.fit(y, x, g)
            wcb = rb.wild_cluster_bootstrap(y, x, g)

            env_means = {e: float(np.mean([r[key] for r in sub if r["env"] == e])) for e in ENVS}
            observed = tuple(sorted(e for e in ENVS if TASK_TYPE[e] == "assertive"))
            coefs, obs = [], None
            for combo in combinations(sorted(ENVS), 3):
                c_ = np.mean([env_means[e] for e in combo]) - np.mean(
                    [env_means[e] for e in ENVS if e not in combo]
                )
                coefs.append(c_)
                if tuple(sorted(combo)) == observed:
                    obs = c_
            coefs = np.array(coefs)
            rank = int(np.sum(coefs > obs)) + 1
            res[lbl] = {
                "coef": base["beta"],
                "se_cr1": base["se_cluster"],
                "t": base["t"],
                "p_cr1": base["p_cluster"],
                "p_wild_two_sided": wcb["p_two_sided"],
                "ri_rank": rank,
                "ri_p_one_sided": float(np.sum(coefs >= obs) / len(coefs)),
            }
            print(
                f"    {lbl:20s} coef={base['beta']:+.4f} CR1 p={base['p_cluster']:.4f} "
                f"wild p={wcb['p_two_sided']:.4f} RI rank={rank}/20"
            )
        out["results"][key] = res

    # how much of the published coefficient is committee?
    sub = rows
    y = np.array([r["delta_d"] for r in sub])
    x = np.array([r["assertive"] for r in sub])
    g = np.array([r["env"] for r in sub], dtype=object)
    full = rb.fit(y, x, g)["beta"]
    keep = g != "committee"
    nocom = rb.fit(y[keep], x[keep], g[keep])["beta"]
    print(
        f"\n  Delta_D coefficient: full={full:+.4f}  without committee={nocom:+.4f}  "
        f"({100 * (nocom - full) / full:+.1f}%)"
    )
    out["committee_share"] = {
        "coef_full": full,
        "coef_without_committee": nocom,
        "pct_change": 100 * (nocom - full) / full,
    }

    def jsafe(o):
        if isinstance(o, dict):
            return {k: jsafe(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [jsafe(v) for v in o]
        if isinstance(o, (np.integer, np.floating)):
            return float(o)
        return o

    p = OUT_DIR / "partition_scale_diagnostic.json"
    p.write_text(json.dumps(jsafe(out), indent=2), encoding="utf-8")
    print(f"\nwrote {p.relative_to(REPO)}")


if __name__ == "__main__":
    main()
