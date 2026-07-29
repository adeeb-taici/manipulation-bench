"""Propagate the T5 baseline-relative metric into the assertive/commissive partition.

Replaces Committee's six (model, env) rows in the Section 4.3 Delta_D table with
values recomputed on excess-over-honest (bias - cold_panel_honest[slate]), leaves
the other five environments untouched, and re-runs:

  - per-row sign agreement (assertive Delta_D > 0, commissive < 0)
  - environment-level dominant axis + Fisher exact on the 2x2
  - Delta_D ~ 1 + assertive, with environment-cluster-robust SE
  - the scale-free variant Delta_rel (analysis_lomo/partition_scale_diagnostic.py)

The five non-committee environments' coefficients are transcribed from the
committed paper/figures/model_task_axis_sensitivity.md.

Run: python paper/task5_committee/scripts/t5_partition_propagation.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[3]

# (env, type, model, beta_F, beta_I, beta_D) from
# paper/figures/model_task_axis_sensitivity.md -- committee rows excluded,
# they are recomputed below.
COMMITTED = [
    ("bargaining", "commissive", "claude", 0.0656, 0.1592, -0.0142),
    ("bargaining", "commissive", "gpt55", 0.1611, 0.3408, 0.0533),
    ("bargaining", "commissive", "gemini", 0.1225, 0.3967, 0.0325),
    ("bargaining", "commissive", "grok", 0.1383, 0.2375, 0.0725),
    ("bargaining", "commissive", "llama", 0.0769, 0.0217, -0.0000),
    ("bargaining", "commissive", "deepseek", 0.1063, 0.3463, 0.0297),
    ("debate", "assertive", "claude", 0.0007, -0.0028, 0.0086),
    ("debate", "assertive", "gpt55", -0.0020, -0.0108, 0.0204),
    ("debate", "assertive", "gemini", 0.0042, -0.0024, 0.0152),
    ("debate", "assertive", "grok", 0.0014, 0.0016, 0.0394),
    ("debate", "assertive", "llama", -0.0007, -0.0033, 0.0568),
    ("debate", "assertive", "deepseek", 0.0039, -0.0064, 0.0313),
    ("village", "commissive", "claude", 0.1063, 0.0246, -0.0049),
    ("village", "commissive", "gpt55", 0.1849, 0.1220, -0.0529),
    ("village", "commissive", "gemini", 0.2545, 0.1046, -0.0470),
    ("village", "commissive", "grok", 0.2135, 0.0316, -0.0036),
    ("village", "commissive", "llama", 0.1044, 0.0218, 0.0083),
    ("village", "commissive", "deepseek", 0.1359, 0.0142, 0.0107),
    ("sales", "assertive", "claude", 0.0200, -0.0027, 0.0547),
    ("sales", "assertive", "gpt55", -0.0004, 0.0013, 0.0213),
    ("sales", "assertive", "gemini", 0.0471, 0.0213, 0.1480),
    ("sales", "assertive", "grok", 0.0164, 0.0027, 0.0693),
    ("sales", "assertive", "llama", 0.0347, 0.0107, 0.1133),
    ("sales", "assertive", "deepseek", 0.0378, 0.0187, 0.1147),
    ("inbox", "commissive", "claude", 0.0000, 0.0111, 0.0083),
    ("inbox", "commissive", "gpt55", 0.0066, -0.0003, -0.0042),
    ("inbox", "commissive", "gemini", 0.2104, 0.2031, -0.0475),
    ("inbox", "commissive", "grok", 0.1656, 0.1868, -0.0356),
    ("inbox", "commissive", "llama", 0.1531, 0.0275, -0.0009),
    ("inbox", "commissive", "deepseek", 0.0873, 0.0424, -0.0049),
]

# Committee, committed (raw initial_bias) -- reproduced exactly by
# t5_scale_and_baseline.py, so used here as the control arm.
COMMITTEE_RAW = [
    ("committee", "assertive", "claude", 1.2295, 0.5184, -3.9835),
    ("committee", "assertive", "gpt55", 1.1877, 0.7806, -2.6395),
    ("committee", "assertive", "gemini", 3.6838, 3.6486, 0.1245),
    ("committee", "assertive", "grok", 1.5623, 0.5817, -2.2424),
    ("committee", "assertive", "llama", 0.7826, 0.0493, -1.9364),
    ("committee", "assertive", "deepseek", 1.2213, 0.7917, -3.3662),
]


def delta_d(b_f, b_i, b_d):
    return abs(b_d) - max(abs(b_f), abs(b_i))


def delta_rel(b_f, b_i, b_d):
    num = abs(b_d) - max(abs(b_f), abs(b_i))
    den = abs(b_d) + max(abs(b_f), abs(b_i))
    return num / den if den else 0.0


def committee_excess_rows(rows_path: Path):
    """Recompute committee betas on excess-over-honest."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "t5sb", Path(__file__).resolve().parent / "t5_scale_and_baseline.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows = mod.load(rows_path)
    b = mod.betas(rows, "excess")
    out = []
    for m in mod.MODEL_ORDER:
        if m not in b:
            continue
        out.append(
            (
                "committee",
                "assertive",
                m,
                b[m]["b_frame"],
                b[m]["b_incentive"],
                b[m]["b_difficulty"],
            )
        )
    return out


def cluster_robust(rows, field):
    """OLS of field on assertive dummy, SE clustered by environment."""
    y = np.array([r[field] for r in rows], dtype=float)
    a = np.array([1.0 if r["type"] == "assertive" else 0.0 for r in rows])
    X = np.column_stack([np.ones(len(y)), a])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    meat = np.zeros((2, 2))
    for env in sorted({r["env"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["env"] == env]
        Xg, ug = X[idx], resid[idx]
        s = Xg.T @ ug
        meat += np.outer(s, s)
    G = len({r["env"] for r in rows})
    scale = G / (G - 1) * (len(y) - 1) / (len(y) - 2)
    V = XtX_inv @ meat @ XtX_inv * scale
    se = float(np.sqrt(V[1, 1]))
    t = float(beta[1]) / se if se else float("nan")
    p = 2 * (1 - stats.t.cdf(abs(t), df=G - 1))
    return float(beta[1]), se, t, float(p)


def build(committee_rows):
    rows = []
    for env, typ, model, bf, bi, bd in list(COMMITTED) + list(committee_rows):
        rows.append(
            {
                "env": env,
                "type": typ,
                "model": model,
                "delta_d": delta_d(bf, bi, bd),
                "delta_rel": delta_rel(bf, bi, bd),
                "dom": max(
                    {"frame": abs(bf), "incentive": abs(bi), "difficulty": abs(bd)}.items(),
                    key=lambda kv: kv[1],
                )[0],
            }
        )
    return rows


def report(label, rows):
    print("=" * 78)
    print(f"PARTITION -- {label}")
    print("=" * 78)
    assertive = [r for r in rows if r["type"] == "assertive"]
    commissive = [r for r in rows if r["type"] == "commissive"]
    a_pos = sum(1 for r in assertive if r["delta_d"] > 0)
    c_neg = sum(1 for r in commissive if r["delta_d"] < 0)
    print(
        f"  assertive  Delta_D > 0 : {a_pos}/{len(assertive)}   "
        f"mean {np.mean([r['delta_d'] for r in assertive]):+.4f}   "
        f"median {np.median([r['delta_d'] for r in assertive]):+.4f}"
    )
    print(
        f"  commissive Delta_D < 0 : {c_neg}/{len(commissive)}   "
        f"mean {np.mean([r['delta_d'] for r in commissive]):+.4f}   "
        f"median {np.median([r['delta_d'] for r in commissive]):+.4f}"
    )
    # Environment-level dominant axis
    print()
    print("  Environment-level dominant axis (majority of its 6 model rows):")
    tbl = {}
    for env in ("bargaining", "village", "inbox", "debate", "sales", "committee"):
        sub = [r for r in rows if r["env"] == env]
        n_diff = sum(1 for r in sub if r["dom"] == "difficulty")
        dom = "difficulty" if n_diff > len(sub) / 2 else "frame/incentive"
        tbl[env] = dom
        typ = sub[0]["type"]
        print(
            f"    {env:<12} {typ:<11} -> {dom:<16} ({n_diff}/{len(sub)} rows difficulty-dominant)"
        )
    a_diff = sum(
        1 for e, d in tbl.items() if d == "difficulty" and e in ("debate", "sales", "committee")
    )
    c_diff = sum(
        1 for e, d in tbl.items() if d == "difficulty" and e in ("bargaining", "village", "inbox")
    )
    table = [[a_diff, 3 - a_diff], [c_diff, 3 - c_diff]]
    _, p_fisher = stats.fisher_exact(table, alternative="greater")
    print(f"    2x2 = {table}   Fisher one-sided p = {p_fisher:.4f}")
    print()
    for field in ("delta_d", "delta_rel"):
        coef, se, t, p = cluster_robust(rows, field)
        print(
            f"  {field:<10} ~ 1 + assertive :  coef {coef:+.4f}  "
            f"cluster-SE {se:.4f}  t {t:+.3f}  p {p:.4f}"
        )
    print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--rows",
        type=Path,
        default=ROOT / "paper" / "task5_committee" / "analysis" / "t5_rows.jsonl",
    )
    args = ap.parse_args()

    raw_rows = build(COMMITTEE_RAW)
    report("Committee on RAW initial_bias (committed Section 4.3)", raw_rows)

    exc = committee_excess_rows(args.rows)
    exc_rows = build(exc)
    report("Committee on EXCESS-over-honest", exc_rows)

    print("Committee rows, side by side:")
    print(
        f"  {'model':<12}{'Delta_D raw':>13}{'Delta_D exc':>13}{'Delta_rel raw':>15}{'Delta_rel exc':>15}"
    )
    raw_c = {r["model"]: r for r in raw_rows if r["env"] == "committee"}
    exc_c = {r["model"]: r for r in exc_rows if r["env"] == "committee"}
    for m in raw_c:
        print(
            f"  {m:<12}{raw_c[m]['delta_d']:>+13.4f}{exc_c[m]['delta_d']:>+13.4f}"
            f"{raw_c[m]['delta_rel']:>+15.4f}{exc_c[m]['delta_rel']:>+15.4f}"
        )


if __name__ == "__main__":
    main()
