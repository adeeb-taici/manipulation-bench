"""Leave-one-model-out (LOMO) robustness analysis.

Reviewer objection: six models is too few to support the paper's conclusions.
This script drops each cohort model in turn and recomputes the paper's four
headline claims on the remaining five, reusing the committed analysis
functions rather than reimplementing them.

Run from the repo root:
    python analysis_lomo/lomo_robustness.py

Sections
--------
A. Section 4.3 assertive/commissive partition (Delta_D + task-cluster-robust
   OLS). Reuses paper/cross_task/scripts/cross_task/model_task_axis_sensitivity.py
   verbatim -- load_rows / ols_coefficients / simple_ols / task_cluster_robust.
B. Per-environment dominant axis + dominance ratios. Reuses
   paper/cross_task/scripts/cross_task/aggregate.py (load_task_slopes,
   T5_SLOPES). T6 is NOT in that script's TASKS list; it is added here as a
   labelled extension (see T6_IS_AN_EXTENSION below).
C. Cross-environment Spearman rank instability. Reuses
   ranking_stability_v2.py's _per_task_means (the version the paper cites);
   point estimates only, no bootstrap.
D. Fisher exact on the 6-environment 2x2. RECONSTRUCTION, not a reproduction
   -- no committed code computes this.
E. Bootstrap CI widths on per-(model, axis) slopes, read from the committed
   bootstrap_cis.json artifacts. T5/T6 reported as gaps, not filled.

Nothing in the repo is modified. All outputs land in analysis_lomo/.
"""

from __future__ import annotations

import csv
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
SCRIPTS = REPO / "paper/cross_task/scripts/cross_task"

# ---------------------------------------------------------------------------
# Import the committed analysis modules by file path. We deliberately do NOT
# copy their logic -- the LOMO numbers must be computed by the same code that
# produced the published numbers, or the comparison is meaningless.
# ---------------------------------------------------------------------------

sys.path.insert(0, str(SCRIPTS))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


mtas = _load("mtas", SCRIPTS / "model_task_axis_sensitivity.py")
aggregate = _load("aggregate_mod", SCRIPTS / "aggregate.py")

MODELS = list(mtas.PAPER_MODELS)
DISPLAY = dict(mtas.DISPLAY)
AXES = ("frame", "incentive", "difficulty")

# Section 4.3 environment -> speech-act class. Taken verbatim from
# model_task_axis_sensitivity.py:TASK_TYPE.
TASK_TYPE = dict(mtas.TASK_TYPE)

# Environment order for reporting (T1..T6).
ENV_ORDER = ["bargaining", "debate", "village", "sales", "committee", "inbox"]
ENV_LABEL = {
    "bargaining": "T1 Bargaining",
    "debate": "T2 Debate",
    "village": "T3 Village",
    "sales": "T4 Sales",
    "committee": "T5 Committee",
    "inbox": "T6 Inbox",
}
# aggregate.py task_dir <-> corpus task name
TASK_DIR = {
    "bargaining": "task1_bargaining",
    "debate": "task2_debate",
    "village": "task3_village",
    "sales": "task4_sales",
    "committee": "task5_committee",
    "inbox": "task6_inbox",
}

# aggregate.py's TASKS list stops at T5, so T6's dominance numbers are not a
# published quantity. Table 2 in the paper is a 5-environment table. Anything
# reported here for T6 dominance is our extension of the same estimator.
T6_IS_AN_EXTENSION = True

# T6's prereg_results.json keys GPT-5.5 as 'gpt5' where T4 uses 'gpt55' -- a
# naming inconsistency, not a different model (T6 prereg.md:30 locks the same
# six models).
#
# REDUNDANT, kept as an explicit assertion: aggregate.py's T4_MODEL_MAP is
# load.MODEL_REMAP, which already contains 'gpt5' -> 'GPT-5.5'. Verified that
# aggregate.load_task_slopes("task6_inbox") returns all six canonical models
# without this map. It resolves to the same value either way and changes no
# number. (An earlier revision of this file claimed the remap lacked the key;
# that was true only of the pre-consolidation cross_task_analysis.py.)
T6_KEY_FIX = {"gpt5": "GPT-5.5"}


# ===========================================================================
# A. Section 4.3 -- assertive/commissive partition, task-cluster-robust OLS
# ===========================================================================


def build_delta_d_rows() -> list[dict]:
    """The 36 (model, environment) Delta_D rows, exactly as mtas.main() does."""
    by_cell = mtas.load_rows()
    expected = len(mtas.PAPER_MODELS) * len(mtas.TASKS)
    if len(by_cell) != expected:
        raise RuntimeError(f"Expected {expected} model-task cells, found {len(by_cell)}.")
    rows = []
    for task in mtas.TASKS:
        for model in mtas.PAPER_MODELS:
            cell = by_cell[(model, task)]
            beta, se = mtas.ols_coefficients(cell)
            b_f, b_i, b_d = float(beta[1]), float(beta[2]), float(beta[3])
            rows.append(
                {
                    "model": model,
                    "task": task,
                    "task_type": mtas.TASK_TYPE[task],
                    "n": len(cell),
                    "beta_f": b_f,
                    "beta_i": b_i,
                    "beta_d": b_d,
                    "delta_d": abs(b_d) - max(abs(b_f), abs(b_i)),
                }
            )
    return rows


def partition_test(rows: list[dict]) -> dict:
    """Re-run mtas's Delta_D ~ 1 + assertive OLS with task-cluster-robust SEs.

    Cluster unit is the *environment*, so dropping a model leaves G unchanged
    at 6 and df at G-1 = 5. Only the row count changes (36 -> 30).
    """
    y = np.array([r["delta_d"] for r in rows], dtype=float)
    x = np.array([1.0 if r["task_type"] == "assertive" else 0.0 for r in rows], dtype=float)
    beta, se, t, p, resid, X = mtas.simple_ols(y, x)
    task_labels = np.array([r["task"] for r in rows], dtype=object)
    _cov_cl, se_cl = mtas.task_cluster_robust(resid, X, task_labels)
    g = len(set(task_labels.tolist()))
    t_cl = beta / se_cl
    p_cl = 2 * (1 - stats.t.cdf(np.abs(t_cl), df=g - 1))

    assertive = [r for r in rows if r["task_type"] == "assertive"]
    commissive = [r for r in rows if r["task_type"] == "commissive"]
    a_vals = np.array([r["delta_d"] for r in assertive])
    c_vals = np.array([r["delta_d"] for r in commissive])
    return {
        "n_rows": len(rows),
        "n_clusters": g,
        "assertive_gt0": int((a_vals > 0).sum()),
        "assertive_n": len(a_vals),
        "assertive_mean": float(a_vals.mean()),
        "commissive_lt0": int((c_vals < 0).sum()),
        "commissive_n": len(c_vals),
        "commissive_mean": float(c_vals.mean()),
        "coef": float(beta[1]),
        "se_iid": float(se[1]),
        "p_iid": float(p[1]),
        "se_cluster": float(se_cl[1]),
        "t_cluster": float(t_cl[1]),
        "p_cluster": float(p_cl[1]),
        "directional_holds": bool(a_vals.mean() > 0 > c_vals.mean()),
    }


# ===========================================================================
# B. Dominant axis + dominance ratios
# ===========================================================================


def load_all_slopes() -> dict[str, dict[str, dict[str, float]]]:
    """{env: {canonical_model: {axis: signed slope}}} via aggregate.load_task_slopes."""
    out = {}
    for env in ENV_ORDER:
        task_dir = TASK_DIR[env]
        slopes = aggregate.load_task_slopes(task_dir)
        if env == "inbox":
            # aggregate.load_task_slopes drops T6's 'gpt5' key because the
            # shared remap has no entry for it. Re-read and patch.
            p = REPO / "paper" / task_dir / "analysis" / "prereg_results.json"
            raw = json.load(open(p, encoding="utf-8"))["sensitivity_slopes"]
            slopes = {}
            for key, s in raw.items():
                canon = T6_KEY_FIX.get(key, aggregate.T4_MODEL_MAP.get(key, key))
                if canon not in aggregate.CANONICAL_MODELS:
                    continue
                slopes[canon] = {a: s.get(f"{a}_slope", float("nan")) for a in AXES}
        out[env] = slopes
    return out


def dominance(slopes_env: dict, keep: list[str], eligible: tuple[str, ...] = AXES) -> dict:
    """mean(|slope|) per axis across `keep`, then dominant axis + ratios.

    Mirrors aggregate.task_aggregate()'s arithmetic (plain mean of absolute
    per-model slopes, largest wins) but over an arbitrary model subset.
    """
    means = {}
    for axis in AXES:
        vals = [
            abs(slopes_env[m][axis])
            for m in keep
            if m in slopes_env
            and slopes_env[m].get(axis) is not None
            and not math.isnan(slopes_env[m][axis])
        ]
        means[axis] = sum(vals) / len(vals) if vals else float("nan")
    ranked = sorted(((means[a], a) for a in eligible), reverse=True)
    top_v, top_a = ranked[0]
    second_v, second_a = ranked[1]
    ratio = top_v / second_v if second_v > 0 else float("inf")
    fd = means["frame"] / means["difficulty"] if means["difficulty"] > 0 else float("inf")
    return {
        **{f"mean_abs_{a}": means[a] for a in AXES},
        "dominant_axis": top_a,
        "dominant_value": top_v,
        "second_axis": second_a,
        "second_value": second_v,
        "ratio_top_second": ratio,
        "ratio_frame_difficulty": fd,
    }


# ===========================================================================
# C. Cross-environment Spearman rank instability (v2 definition)
# ===========================================================================


def rho_lomo():
    """Mean off-diagonal pairwise Spearman rho, v2 definition, point estimates.

    Returns (per_task_means, {excluded_or_None: (matrix, mean_offdiag)}) or
    None if the corpus cannot be loaded.
    """
    try:
        rs2 = _load("rs2", SCRIPTS / "ranking_stability_v2.py")
        load_mod = _load("load_mod", SCRIPTS / "load.py")
        df = load_mod.load_corpus()
        means = rs2._per_task_means(df, ranking="permissive", use_v1_metric=False)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] rank-stability section skipped: {type(e).__name__}: {e}")
        return None, None

    tasks = list(rs2.TASKS)

    def matrix(keep):
        n = len(tasks)
        M = np.full((n, n), np.nan)
        for i, a in enumerate(tasks):
            for j, b in enumerate(tasks):
                xs = [means[a][m] for m in keep]
                ys = [means[b][m] for m in keep]
                M[i, j] = stats.spearmanr(xs, ys).statistic
        off = [M[i, j] for i in range(n) for j in range(n) if i != j]
        return M, float(np.nanmean(off))

    res = {None: matrix(MODELS)}
    for x in MODELS:
        res[x] = matrix([m for m in MODELS if m != x])
    return (tasks, means), res


# ===========================================================================
# D. Fisher exact on the 6-environment 2x2 (RECONSTRUCTION)
# ===========================================================================


def fisher_partition(dom_by_env: dict[str, str]) -> dict:
    """One-sided Fisher exact on {commissive, assertive} x {frame-or-incentive
    dominant, difficulty dominant}.

    RECONSTRUCTION. No committed script computes this. The '~0.011' in
    task6_inbox/prereg.md:132 and results.md:276 is explicitly retracted by
    paper/figures/t6_permutation_test.md as methodologically problematic
    (partition was built by inspecting T1-T5, then treated as ex ante).
    """
    a = b = c = d = 0
    for env, dom in dom_by_env.items():
        prompt_side = dom in ("frame", "incentive")
        if TASK_TYPE[env] == "commissive":
            if prompt_side:
                a += 1
            else:
                b += 1
        else:
            if prompt_side:
                c += 1
            else:
                d += 1
    table = [[a, b], [c, d]]
    _odds, p_two = stats.fisher_exact(table)
    p_one = stats.fisher_exact(table, alternative="greater")[1]
    return {
        "table": table,
        "p_one_sided": float(p_one),
        "p_two_sided": float(p_two),
        "perfect_split": (a == 3 and b == 0 and c == 0 and d == 3),
        "floor_note": "A perfect 3/3-vs-3/3 split floors at 1/C(6,3) = 0.05 one-sided.",
    }


# ===========================================================================
# E. Bootstrap CI widths from the committed artifacts (T1-T4; T5/T6 gaps)
# ===========================================================================


def ci_widths() -> tuple[list[dict], list[str]]:
    rows, gaps = [], []
    for env in ENV_ORDER:
        p = REPO / "paper" / TASK_DIR[env] / "analysis" / "bootstrap_cis.json"
        if not p.exists():
            gaps.append(f"{ENV_LABEL[env]}: no bootstrap_cis.json committed -- CI unavailable")
            continue
        d = json.load(open(p, encoding="utf-8"))
        for model, per_axis in (d.get("per_model") or {}).items():
            canon = aggregate.T4_MODEL_MAP.get(model, model)
            canon = T6_KEY_FIX.get(model, canon)
            for axis, info in (per_axis or {}).items():
                lo, hi, pt = info.get("lo"), info.get("hi"), info.get("point")
                rows.append(
                    {
                        "environment": ENV_LABEL[env],
                        "model": DISPLAY.get(canon, canon),
                        "axis": axis,
                        "point": pt,
                        "ci_lo": lo,
                        "ci_hi": hi,
                        "ci_width": (hi - lo) if (lo is not None and hi is not None) else None,
                        "n_resamples": info.get("n_resamples"),
                    }
                )
    return rows, gaps


# ===========================================================================
# Main
# ===========================================================================


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 78)
    print("LOMO ROBUSTNESS ANALYSIS")
    print("=" * 78)

    # ---- A. Section 4.3 partition -----------------------------------------
    all_rows = build_delta_d_rows()
    full_part = partition_test(all_rows)
    print("\n[A] Section 4.3 partition -- full roster (reproduction check)")
    print(
        f"    assertive {full_part['assertive_gt0']}/{full_part['assertive_n']} Delta_D>0 | "
        f"commissive {full_part['commissive_lt0']}/{full_part['commissive_n']} Delta_D<0 | "
        f"coef={full_part['coef']:+.3f} | cluster SE={full_part['se_cluster']:.3f} "
        f"t={full_part['t_cluster']:+.3f} p={full_part['p_cluster']:.3f}"
    )

    part_lomo = {}
    print("\n[A] Section 4.3 partition -- LOMO")
    for x in MODELS:
        sub = [r for r in all_rows if r["model"] != x]
        res = partition_test(sub)
        part_lomo[x] = res
        print(
            f"    drop {DISPLAY[x]:16s} rows={res['n_rows']} G={res['n_clusters']} "
            f"assertive {res['assertive_gt0']}/{res['assertive_n']} | "
            f"commissive {res['commissive_lt0']}/{res['commissive_n']} | "
            f"coef={res['coef']:+.3f} p_cluster={res['p_cluster']:.3f} "
            f"p_iid={res['p_iid']:.3f} directional={'YES' if res['directional_holds'] else 'NO'}"
        )

    # ---- B. Dominance ------------------------------------------------------
    slopes = load_all_slopes()
    for env in ENV_ORDER:
        missing = [m for m in MODELS if m not in slopes[env]]
        if missing:
            raise RuntimeError(f"{env}: missing slopes for {missing}")

    full_dom = {env: dominance(slopes[env], MODELS) for env in ENV_ORDER}
    print("\n[B] Dominant axis -- full roster")
    for env in ENV_ORDER:
        d = full_dom[env]
        print(
            f"    {ENV_LABEL[env]:16s} f={d['mean_abs_frame']:.4f} i={d['mean_abs_incentive']:.4f} "
            f"d={d['mean_abs_difficulty']:.4f} dom={d['dominant_axis']:10s} "
            f"top/2nd={d['ratio_top_second']:.2f}x  f/d={d['ratio_frame_difficulty']:.2f}x"
        )

    csv_rows = []
    dom_lomo = {}
    print("\n[B] Dominant axis -- LOMO")
    for x in [None] + MODELS:
        keep = MODELS if x is None else [m for m in MODELS if m != x]
        label = "(none - full roster)" if x is None else DISPLAY[x]
        per_env = {}
        for env in ENV_ORDER:
            d = dominance(slopes[env], keep)
            per_env[env] = d
            csv_rows.append(
                {
                    "excluded_model": label,
                    "n_models": len(keep),
                    "environment": ENV_LABEL[env],
                    "speech_act_class": TASK_TYPE[env],
                    "dominant_axis": d["dominant_axis"],
                    "dominant_axis_full_roster": full_dom[env]["dominant_axis"],
                    "dominant_axis_unchanged": (
                        ""
                        if x is None
                        else str(d["dominant_axis"] == full_dom[env]["dominant_axis"])
                    ),
                    "mean_abs_frame_slope": round(d["mean_abs_frame"], 6),
                    "mean_abs_incentive_slope": round(d["mean_abs_incentive"], 6),
                    "mean_abs_difficulty_slope": round(d["mean_abs_difficulty"], 6),
                    "second_axis": d["second_axis"],
                    "ratio_top_over_second": round(d["ratio_top_second"], 4),
                    "ratio_frame_over_difficulty": round(d["ratio_frame_difficulty"], 4),
                    "t6_extension_not_published": (
                        "TRUE (T6 absent from aggregate.py TASKS)" if env == "inbox" else ""
                    ),
                }
            )
        if x is not None:
            dom_lomo[x] = per_env
            n_same = sum(
                1
                for env in ENV_ORDER
                if per_env[env]["dominant_axis"] == full_dom[env]["dominant_axis"]
            )
            flips = [
                f"{ENV_LABEL[env]}:{full_dom[env]['dominant_axis']}->{per_env[env]['dominant_axis']}"
                for env in ENV_ORDER
                if per_env[env]["dominant_axis"] != full_dom[env]["dominant_axis"]
            ]
            print(
                f"    drop {DISPLAY[x]:16s} unchanged={n_same}/6  "
                f"T5={per_env['committee']['ratio_top_second']:.2f}x "
                f"T6={per_env['inbox']['ratio_top_second']:.2f}x  "
                f"flips={flips if flips else 'none'}"
            )

    csv_path = OUT_DIR / "lomo_dominance.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        w.writeheader()
        w.writerows(csv_rows)
    print(f"\n    wrote {csv_path.relative_to(REPO)} ({len(csv_rows)} rows)")

    # ---- B2. T3 sensitivity: incentive eligible or not ---------------------
    print("\n[B2] T3 Village dominance ratio with/without incentive as eligible axis")
    t3_both = {}
    for x in [None] + MODELS:
        keep = MODELS if x is None else [m for m in MODELS if m != x]
        with_inc = dominance(slopes["village"], keep, eligible=AXES)
        no_inc = dominance(slopes["village"], keep, eligible=("frame", "difficulty"))
        t3_both["full" if x is None else x] = (with_inc, no_inc)
        print(
            f"    {'full roster' if x is None else 'drop ' + DISPLAY[x]:21s} "
            f"with incentive: {with_inc['dominant_axis']} {with_inc['ratio_top_second']:.2f}x "
            f"(2nd={with_inc['second_axis']})   "
            f"without: {no_inc['dominant_axis']} {no_inc['ratio_top_second']:.2f}x"
        )

    # ---- C. Rank instability ----------------------------------------------
    print("\n[C] Cross-environment Spearman rank instability (v2 definition)")
    rho_meta, rho_res = rho_lomo()
    rho_out = None
    if rho_res is not None:
        tasks, _means = rho_meta
        print(f"    tasks={tasks}  (T6 excluded by design -- held-out generalization claim)")
        print(f"    full roster mean off-diag rho = {rho_res[None][1]:+.4f}")
        for x in MODELS:
            print(f"      drop {DISPLAY[x]:16s} {rho_res[x][1]:+.4f}")
        rho_out = {
            "tasks": tasks,
            "definition": "v2: permissive-frame mean of each task's primary metric "
            "(T2 = belief_shift), point-estimate Spearman, no bootstrap",
            "full_roster_mean_offdiag": rho_res[None][1],
            "matrix_full": [[None if np.isnan(v) else v for v in r] for r in rho_res[None][0]],
            "lomo_mean_offdiag": {DISPLAY[x]: rho_res[x][1] for x in MODELS},
            "lomo_matrices": {
                DISPLAY[x]: [[None if np.isnan(v) else v for v in r] for r in rho_res[x][0]]
                for x in MODELS
            },
        }

    # ---- D. Fisher reconstruction -----------------------------------------
    print("\n[D] Fisher exact on the 6-environment 2x2 -- RECONSTRUCTION, not a reproduction")
    fisher_full = fisher_partition({env: full_dom[env]["dominant_axis"] for env in ENV_ORDER})
    print(
        f"    full roster table={fisher_full['table']} "
        f"one-sided p={fisher_full['p_one_sided']:.4f} two-sided p={fisher_full['p_two_sided']:.4f}"
    )
    fisher_lomo = {}
    for x in MODELS:
        fr = fisher_partition({env: dom_lomo[x][env]["dominant_axis"] for env in ENV_ORDER})
        fisher_lomo[DISPLAY[x]] = fr
        print(
            f"      drop {DISPLAY[x]:16s} table={fr['table']} "
            f"one-sided p={fr['p_one_sided']:.4f} perfect_3v3={fr['perfect_split']}"
        )

    # ---- E. CI widths -----------------------------------------------------
    print("\n[E] Bootstrap CI widths from committed artifacts")
    ci_rows, gaps = ci_widths()
    ci_path = OUT_DIR / "slope_ci_widths.csv"
    with open(ci_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ci_rows[0].keys()))
        w.writeheader()
        w.writerows(ci_rows)
    print(f"    wrote {ci_path.relative_to(REPO)} ({len(ci_rows)} rows)")
    by_env = {}
    for r in ci_rows:
        if r["ci_width"] is not None:
            by_env.setdefault(r["environment"], []).append(r["ci_width"])
    for env, ws in by_env.items():
        print(f"      {env:16s} median CI width={float(np.median(ws)):.4f}  n={len(ws)}")
    for g in gaps:
        print(f"      GAP: {g}")

    # ---- dump JSON --------------------------------------------------------
    payload = {
        "provenance": {
            "section_4_3_script": "paper/cross_task/scripts/cross_task/model_task_axis_sensitivity.py",
            "section_4_3_input": "paper/cross_task/data/results.csv",
            "dominance_script": "paper/cross_task/scripts/cross_task/aggregate.py",
            "dominance_input": "paper/task<N>/analysis/prereg_results.json (+ hardcoded T5_SLOPES)",
            "rank_stability_script": "paper/cross_task/scripts/cross_task/ranking_stability_v2.py",
            "t6_dominance_is_an_extension": T6_IS_AN_EXTENSION,
            "t5_slopes_hardcoded_3dp": True,
            "fisher_is_reconstruction": True,
        },
        "partition_full": full_part,
        "partition_lomo": {DISPLAY[x]: part_lomo[x] for x in MODELS},
        "dominance_full": {ENV_LABEL[e]: full_dom[e] for e in ENV_ORDER},
        "dominance_lomo": {
            DISPLAY[x]: {ENV_LABEL[e]: dom_lomo[x][e] for e in ENV_ORDER} for x in MODELS
        },
        "t3_incentive_sensitivity": {
            ("full" if k == "full" else DISPLAY[k]): {
                "with_incentive": v[0],
                "without_incentive": v[1],
            }
            for k, v in t3_both.items()
        },
        "rank_stability": rho_out,
        "fisher_reconstruction": {"full": fisher_full, "lomo": fisher_lomo},
        "ci_gaps": gaps,
    }

    def jsafe(o):
        if isinstance(o, dict):
            return {k: jsafe(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [jsafe(v) for v in o]
        if isinstance(o, float) and (math.isnan(o) or math.isinf(o)):
            return None
        if isinstance(o, (np.integer, np.floating)):
            return float(o)
        return o

    json_path = OUT_DIR / "lomo_results.json"
    json_path.write_text(json.dumps(jsafe(payload), indent=2), encoding="utf-8")
    print(f"\n    wrote {json_path.relative_to(REPO)}")
    print("\nDone.")


if __name__ == "__main__":
    main()
