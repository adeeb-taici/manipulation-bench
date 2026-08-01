"""Retrospective test of the staged reduced-design protocol on the frozen data.

No model calls. This filters the frozen six-model results to the cells a staged
protocol would have run, recomputes the published quantities on that subset, and
asks whether the reduced design recovers the full-sweep conclusions.

Protocol under test (as posted)
-------------------------------
  full design      5 frames x 3 incentives x 3 difficulties = 45 cells
  commissive arm   all 5 frames x incentive endpoints x difficulty endpoints
                   = 5 x 2 x 2 = 20 of 45      -> T1 Bargaining, T3 Village, T6 Inbox
  assertive arm    all 3 difficulties x frame endpoints x incentive endpoints
                   = 3 x 2 x 2 = 12 of 45      -> T2 Debate, T4 Sales, T5 Committee

Endpoint mapping (part of the protocol's definition; stated because it is a choice)
  frame       prohibitive, permissive     (indices 0 and 4 of 5 ordered levels)
  incentive   none, high                  (indices 0 and 2)
  difficulty  low, high                   (indices 0 and 2)

Estimator reuse
---------------
The published per-task `model_sensitivity_slopes(rows)` is called verbatim for
T1-T4 and T6, with only the module-level level tuples restricted to the retained
levels. T5 has no such function and no prereg_results.json (cross_task_analysis.py
carries a hardcoded map), so T5 uses the estimator from task5_prereg_analysis.py
(OLS over marginal means / per-model pooled SD), gated on reproducing the
committed T5_SLOPES.

**Index-span rescaling, and why it is required.** The published `slope()` regresses
on *positions* (`xs = list(range(n))`). Handing it a 2-element endpoint list would
return a raw difference, which is 2x (incentive/difficulty) or 4x (frame) larger
than the full-design per-step slope. Left uncorrected that inflates exactly the
axes the protocol reduced, biasing the dominant-axis test toward them. So each
endpoint-reduced slope is divided by the original index span.

A consequence worth stating: for a 3-level evenly spaced axis, the full-design OLS
slope is exactly (y_high - y_none)/2 -- it does not depend on the middle level. So
reducing incentive or difficulty to endpoints is **slope-preserving in estimator
form**; only the cell means change (fewer cells are averaged). Frame is 5 levels and
its OLS slope weights all five, so frame reduction genuinely discards information.

T5 scale correction is applied per-sample (max rating <= 10 => x2) before any
cross-model T5 quantity.

Run: python paper/cross_task/scripts/reduced_protocol_retrospective.py
"""

from __future__ import annotations

import importlib.util
import json
import statistics
import sys
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[3]

MODELS = [
    "Claude-Opus-4.7",
    "GPT-5.5",
    "Gemini-3.1-Pro",
    "Grok-4",
    "Llama-3.3-70B",
    "DeepSeek-V4-Pro",
]
AXES = ("frame", "incentive", "difficulty")

FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
FRAME_ENDPOINTS = ("prohibitive", "permissive")  # indices 0, 4 -> span 4
INC_ENDPOINTS_IDX = (0, 2)  # none, high  -> span 2
DIFF_ENDPOINTS = ("low", "high")  # indices 0, 2 -> span 2

# env key -> (task dir, module stem, arm)
ENVS = [
    ("T1 Bargaining", "task1_bargaining", "task1", "commissive"),
    ("T2 Debate", "task2_debate", "task2", "assertive"),
    ("T3 Village", "task3_village", "task3", "commissive"),
    ("T4 Sales", "task4_sales", "task4", "assertive"),
    ("T5 Committee", "task5_committee", "task5", "assertive"),
    ("T6 Inbox", "task6_inbox", "task6", "commissive"),
]

ALIAS = {
    "claude": "Claude-Opus-4.7",
    "gpt5": "GPT-5.5",
    "gpt55": "GPT-5.5",
    "gemini": "Gemini-3.1-Pro",
    "grok": "Grok-4",
    "llama": "Llama-3.3-70B",
    "deepseek": "DeepSeek-V4-Pro",
}

T5_COMMITTED = {
    "Claude-Opus-4.7": {"frame": 0.281, "incentive": 0.117, "difficulty": -0.911},
    "GPT-5.5": {"frame": 0.307, "incentive": 0.202, "difficulty": -0.676},
    "Gemini-3.1-Pro": {"frame": 0.434, "incentive": 0.430, "difficulty": 0.016},
    "Grok-4": {"frame": 0.372, "incentive": 0.135, "difficulty": -0.537},
    "Llama-3.3-70B": {"frame": 0.287, "incentive": 0.018, "difficulty": -0.713},
    "DeepSeek-V4-Pro": {"frame": 0.280, "incentive": 0.181, "difficulty": -0.765},
}

CRITERIA = """
PRE-SPECIFIED RECOVERY CRITERIA  (written before any subset quantity was computed)

  C1 Dominant axis.  The reduced design assigns the SAME dominant axis as the full
     design in all 6 environments. Dominant axis = argmax over axes of the mean
     absolute per-model slope, the aggregation cross_task_analysis.py uses. Slopes
     are recomputed on reduced cells with the published per-task estimator. On
     endpoint-reduced axes the slope becomes a two-point difference, rescaled by the
     original index span so it stays in per-step units.

  C2 Directional partition.  The environment-level Delta_D sign pattern matches the
     full design's 3 positive / 3 negative, where
     Delta_D = mean|difficulty slope| - max(mean|frame slope|, mean|incentive slope|).

  C3 Rank instability.  Mean off-diagonal Spearman rho on the reduced design stays
     within +/-0.15 of the full-design value of +0.055 (i.e. still nowhere near a
     stable trait), AND the most negative pair remains strongly negative.

  C4 Cost.  Report the exact fraction of the full design used, in cells and in
     model-trajectory evaluations, overall and per environment.

  A criterion that fails is reported plainly, with the cells that carried the lost
  information identified. A failed recovery is a finding about the protocol.
"""


def load_module(task_dir: str, stem: str):
    p = REPO / "paper" / task_dir / "scripts" / f"{stem}_prereg_analysis.py"
    spec = importlib.util.spec_from_file_location(f"{stem}_prereg", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- T5 estimator
def t5_rows():
    z = zipfile.ZipFile(REPO / "paper/task5_committee/eval_log.eval")
    rows = []
    for nm in z.namelist():
        if not nm.startswith("samples/"):
            continue
        s = json.loads(z.read(nm))
        if s.get("error"):
            continue
        sc = (s.get("scores") or {}).get("initial_rating_bias")
        v = sc.get("value") if isinstance(sc, dict) else None
        if not isinstance(v, dict) or v.get("initial_bias") is None:
            continue
        md = ((s.get("metadata") or {}).get("scenario") or {}).get("metadata") or {}
        gs = (
            ((s.get("store") or {}).get("InteractionState:scenario") or {}).get("metadata") or {}
        ).get("game_state") or {}
        ip = gs.get("interested_party_name")
        r = (gs.get("initial_ratings") or {}).get(ip) or {}
        vals = [int(x) for c in r.values() if isinstance(c, dict) for x in c.values()]
        rows.append(
            {
                "model": ALIAS.get(md.get("interested_model_label")),
                "frame": md.get("frame"),
                "incentive": md.get("incentive"),
                "difficulty": md.get("difficulty"),
                "metric": float(v["initial_bias"]) * (2 if (vals and max(vals) <= 10) else 1),
            }
        )
    return rows


def ols(xs, ys):
    if len(xs) < 2:
        return float("nan")
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else float("nan")


def t5_slopes(rows, frames, incs, diffs):
    """task5_prereg_analysis.py estimator; levels carry ORIGINAL indices."""
    out = {}
    all_levels = {
        "frame": FRAMES,
        "incentive": ("none", "moderate", "high"),
        "difficulty": ("low", "medium", "high"),
    }
    keep = {"frame": frames, "incentive": incs, "difficulty": diffs}
    for m in MODELS:
        sub = [r for r in rows if r["model"] == m]
        if not sub:
            continue
        sd = statistics.pstdev([r["metric"] for r in sub]) or 1.0
        got = {}
        for axis in AXES:
            xs, ys = [], []
            for lv in keep[axis]:
                idx = all_levels[axis].index(lv)
                sel = [r["metric"] for r in sub if r[axis] == lv]
                if sel:
                    xs.append(idx)
                    ys.append(sum(sel) / len(sel) / sd)
            got[axis] = ols(xs, ys)
        out[m] = got
    return out


# ------------------------------------------------------- generic env slope calc
def env_slopes(mod, rows, frames, incs, diffs):
    """Call the published model_sensitivity_slopes with restricted levels, then
    rescale endpoint-reduced axes back to per-step units."""
    orig = (mod.FRAMES, mod.INCENTIVES, mod.DIFFICULTIES)
    span = {}
    inc_all = list(orig[1])
    # `incs` always carries level VALUES, never positions. T1's incentive levels
    # are (0, 80, 250) -- ints that any value-vs-index heuristic would misread as
    # indices -- so no such heuristic is used here.
    inc_keep = list(incs)
    span["frame"] = FRAMES.index(frames[-1]) - FRAMES.index(frames[0]) if len(frames) == 2 else 1
    span["incentive"] = (
        (inc_all.index(inc_keep[-1]) - inc_all.index(inc_keep[0])) if len(inc_keep) == 2 else 1
    )
    span["difficulty"] = (
        (list(orig[2]).index(diffs[-1]) - list(orig[2]).index(diffs[0])) if len(diffs) == 2 else 1
    )
    try:
        mod.FRAMES, mod.INCENTIVES, mod.DIFFICULTIES = tuple(frames), tuple(inc_keep), tuple(diffs)
        raw = mod.model_sensitivity_slopes(rows)
    finally:
        mod.FRAMES, mod.INCENTIVES, mod.DIFFICULTIES = orig
    out = {}
    for k, v in raw.items():
        m = ALIAS.get(k, k)
        out[m] = {a: (v[f"{a}_slope"] / span[a] if span[a] else float("nan")) for a in AXES}
    return out


def filter_rows(rows, frames, inc_keep, diffs, inc_key="incentive"):
    return [
        r
        for r in rows
        if r["frame"] in frames and r[inc_key] in inc_keep and r["difficulty"] in diffs
    ]


def aggregate(slopes):
    return {a: float(np.mean([abs(slopes[m][a]) for m in MODELS if m in slopes])) for a in AXES}


def dominant(agg):
    order = sorted(AXES, key=lambda a: -agg[a])
    top, second = order[0], order[1]
    ratio = agg[top] / agg[second] if agg[second] else float("inf")
    return top, second, ratio


def criterion_c3():
    """Mean off-diagonal Spearman rho, full vs reduced, via the committed v1 pipeline.

    corpus.csv is per-sample and carries frame/incentive/difficulty, so the same
    estimator (ranking_stability_v2._per_task_means with use_v1_metric=True) can be
    handed a filtered frame. The full-design call is gated on reproducing +0.0552.
    """
    xt = REPO / "paper/cross_task/scripts/cross_task"
    sys.path.insert(0, str(xt))
    spec = importlib.util.spec_from_file_location("rs2_rp", xt / "ranking_stability_v2.py")
    rs2 = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = rs2
    spec.loader.exec_module(rs2)
    spec2 = importlib.util.spec_from_file_location("load_rp", xt / "load.py")
    ld = importlib.util.module_from_spec(spec2)
    sys.modules[spec2.name] = ld
    spec2.loader.exec_module(ld)

    envs5 = ["bargaining", "debate", "village", "sales", "committee"]
    arm_of = {
        "bargaining": "commissive",
        "village": "commissive",
        "inbox": "commissive",
        "debate": "assertive",
        "sales": "assertive",
        "committee": "assertive",
    }

    def offdiag(means, keep):
        n = len(envs5)
        M = np.full((n, n), np.nan)
        for i, a in enumerate(envs5):
            for j, b in enumerate(envs5):
                M[i, j] = spearmanr(
                    [means[a][m] for m in keep], [means[b][m] for m in keep]
                ).statistic
        off = [M[i, j] for i in range(n) for j in range(n) if i != j]
        best, pair = np.inf, None
        for i in range(n):
            for j in range(i + 1, n):
                if M[i, j] < best:
                    best, pair = M[i, j], (envs5[i], envs5[j])
        return float(np.nanmean(off)), pair, float(best)

    df = ld.load_corpus(verbose=False)
    full_means = rs2._per_task_means(df, ranking="permissive", use_v1_metric=True)
    mo_full, pair_full, val_full = offdiag(full_means, MODELS)

    print("\n" + "=" * 100)
    print("C3 -- RANK INSTABILITY (committed v1 pipeline, permissive-frame per-model means)")
    print("=" * 100)
    print(f"  full-design reproduction: {mo_full:+.4f} vs published +0.0552", end="   ")
    if abs(mo_full - 0.0552) > 1e-3:
        raise SystemExit("MISMATCH -- refusing to proceed")
    print("OK")

    # Reduced: keep only the cells that environment's arm would have run.
    def keep_row(r):
        arm = arm_of.get(str(r["task"]))
        if arm is None:
            return True
        inc_ok = str(r["incentive"]) in ("none", "high")
        if arm == "commissive":
            return inc_ok and str(r["difficulty"]) in ("low", "high")
        return inc_ok and str(r["frame"]) in FRAME_ENDPOINTS

    dfr = df[df.apply(keep_row, axis=1)].copy()
    red_means = rs2._per_task_means(dfr, ranking="permissive", use_v1_metric=True)
    mo_red, pair_red, val_red = offdiag(red_means, MODELS)

    print(f"  rows: full {len(df):,} -> reduced {len(dfr):,}")
    print(f"\n  {'':<22}{'mean off-diag rho':>20}{'most negative pair':>28}")
    print(
        f"  {'full design':<22}{mo_full:>+20.4f}"
        f"{pair_full[0] + '-' + pair_full[1] + f' {val_full:+.3f}':>28}"
    )
    print(
        f"  {'reduced design':<22}{mo_red:>+20.4f}"
        f"{pair_red[0] + '-' + pair_red[1] + f' {val_red:+.3f}':>28}"
    )
    within = abs(mo_red - 0.0552) <= 0.15
    strong = val_red <= -0.4
    print(
        f"\n  within +/-0.15 of +0.055 : {'YES' if within else 'NO'} (delta {mo_red - 0.0552:+.4f})"
    )
    print(f"  most negative still strong: {'YES' if strong else 'NO'} ({val_red:+.3f})")
    print(f"  C3 -> {'PASS' if (within and strong) else 'FAIL'}")
    return {
        "full": mo_full,
        "reduced": mo_red,
        "pair_full": list(pair_full),
        "pair_reduced": list(pair_red),
        "val_full": val_full,
        "val_reduced": val_red,
        "pass": bool(within and strong),
    }


def main() -> None:
    print(CRITERIA)
    print("=" * 100)
    print("PROTOCOL AND CELL ARITHMETIC")
    print("=" * 100)
    print(f"  full design      5 frames x 3 incentives x 3 difficulties = {5 * 3 * 3} cells")
    print(
        f"  commissive arm   5 x 2 x 2 = {5 * 2 * 2} of 45  ({100 * 20 / 45:.1f}%)  -> T1, T3, T6"
    )
    print(
        f"  assertive arm    3 x 2 x 2 = {3 * 2 * 2} of 45  ({100 * 12 / 45:.1f}%)  -> T2, T4, T5"
    )
    print(
        "  endpoints        frame=(prohibitive, permissive)  incentive=(none, high)  "
        "difficulty=(low, high)"
    )

    results = []
    cost = []
    full_slopes_all, red_slopes_all = {}, {}

    for label, task_dir, stem, arm in ENVS:
        if stem == "task5":
            rows = t5_rows()
            inc_all = ("none", "moderate", "high")
            if arm == "commissive":
                fr, ic, df = FRAMES, (inc_all[0], inc_all[2]), DIFF_ENDPOINTS
            else:
                fr, ic, df = FRAME_ENDPOINTS, (inc_all[0], inc_all[2]), ("low", "medium", "high")
            full = t5_slopes(rows, FRAMES, inc_all, ("low", "medium", "high"))
            # NOT a reproduction gate: `full` is scale-CORRECTED while T5_COMMITTED
            # is the uncorrected published map, so a non-zero delta is expected and
            # is the size of the correction. (The reproduction gate proper lives in
            # model_distance_matrix.py, which compares uncorrected-to-uncorrected and
            # matches to 0.0005.) The largest entry here is GPT-5.5 difficulty,
            # -0.676 -> -0.737.
            worst = max(abs(full[m][a] - T5_COMMITTED[m][a]) for m in MODELS for a in AXES)
            gate = f"T5 scale-correction delta vs published map: {worst:.4f} (expected, not a gate)"
            red_rows = filter_rows(rows, fr, ic, df)
            red = t5_slopes(red_rows, fr, ic, df)
            n_full, n_red = len(rows), len(red_rows)
            cells_full = len({(r["frame"], r["incentive"], r["difficulty"]) for r in rows})
            cells_red = len({(r["frame"], r["incentive"], r["difficulty"]) for r in red_rows})
        else:
            mod = load_module(task_dir, stem)
            rows = mod.load_rows()
            inc_all = list(mod.INCENTIVES)
            ic = (inc_all[0], inc_all[2])
            if arm == "commissive":
                fr, df = FRAMES, DIFF_ENDPOINTS
            else:
                fr, df = FRAME_ENDPOINTS, tuple(mod.DIFFICULTIES)
            full = env_slopes(mod, rows, FRAMES, tuple(inc_all), tuple(mod.DIFFICULTIES))
            red_rows = filter_rows(rows, fr, ic, df)
            red = env_slopes(mod, red_rows, fr, ic, df)
            n_full, n_red = len(rows), len(red_rows)
            cells_full = len({(r["frame"], r["incentive"], r["difficulty"]) for r in rows})
            cells_red = len({(r["frame"], r["incentive"], r["difficulty"]) for r in red_rows})
            gate = ""

        full_slopes_all[label], red_slopes_all[label] = full, red
        af, ar = aggregate(full), aggregate(red)
        df_top, df_2, df_r = dominant(af)
        rd_top, rd_2, rd_r = dominant(ar)
        results.append(
            {
                "env": label,
                "arm": arm,
                "full_dom": df_top,
                "full_ratio": df_r,
                "red_dom": rd_top,
                "red_ratio": rd_r,
                "match": df_top == rd_top,
                "agg_full": af,
                "agg_red": ar,
                "gate": gate,
            }
        )
        cost.append(
            {
                "env": label,
                "cells_full": cells_full,
                "cells_red": cells_red,
                "evals_full": n_full,
                "evals_red": n_red,
            }
        )

    print("\n" + "=" * 100)
    print("C1 -- DOMINANT AXIS: full vs reduced")
    print("=" * 100)
    print(
        f"{'env':<16}{'arm':<12}{'full dom':>12}{'reduced dom':>13}{'match':>7}"
        f"{'red top:2nd':>13}{'expand?':>9}"
    )
    for r in results:
        trig = "YES" if r["red_ratio"] < 1.5 else "no"
        print(
            f"{r['env']:<16}{r['arm']:<12}{r['full_dom']:>12}{r['red_dom']:>13}"
            f"{'OK' if r['match'] else 'FAIL':>7}{r['red_ratio']:>13.2f}{trig:>9}"
        )
    n_match = sum(r["match"] for r in results)
    print(
        f"\n  C1: {n_match}/6 environments recover the dominant axis "
        f"-> {'PASS' if n_match == 6 else 'FAIL'}"
    )
    for r in results:
        if r["gate"]:
            print(f"  ({r['gate']})")

    print("\n  aggregate mean |slope| per axis (full -> reduced):")
    for r in results:
        print(
            f"    {r['env']:<16}"
            + "  ".join(f"{a[:4]} {r['agg_full'][a]:.4f}->{r['agg_red'][a]:.4f}" for a in AXES)
        )

    print("\n" + "=" * 100)
    print("C2 -- DIRECTIONAL PARTITION (Delta_D sign at environment level)")
    print("=" * 100)
    print(f"{'env':<16}{'arm':<12}{'Delta_D full':>14}{'Delta_D reduced':>17}{'sign match':>12}")
    sign_ok = 0
    for r in results:
        dfull = r["agg_full"]["difficulty"] - max(
            r["agg_full"]["frame"], r["agg_full"]["incentive"]
        )
        dred = r["agg_red"]["difficulty"] - max(r["agg_red"]["frame"], r["agg_red"]["incentive"])
        ok = (dfull > 0) == (dred > 0)
        sign_ok += ok
        print(
            f"{r['env']:<16}{r['arm']:<12}{dfull:>+14.4f}{dred:>+17.4f}{'OK' if ok else 'FAIL':>12}"
        )
    print(f"\n  C2: {sign_ok}/6 signs match -> {'PASS' if sign_ok == 6 else 'FAIL'}")

    print("\n" + "=" * 100)
    print("C4 -- COST")
    print("=" * 100)
    print(f"{'env':<16}{'cells red/full':>18}{'evals red/full':>22}{'eval fraction':>15}")
    tcf = tcr = tef = ter = 0
    for c in cost:
        tcf += c["cells_full"]
        tcr += c["cells_red"]
        tef += c["evals_full"]
        ter += c["evals_red"]
        print(
            f"{c['env']:<16}{c['cells_red']:>8}/{c['cells_full']:<9}"
            f"{c['evals_red']:>13,}/{c['evals_full']:<8,}{100 * c['evals_red'] / c['evals_full']:>14.1f}%"
        )
    print(f"{'TOTAL':<16}{tcr:>8}/{tcf:<9}{ter:>13,}/{tef:<8,}{100 * ter / tef:>14.1f}%")

    rho_out = criterion_c3()

    print("\n" + "=" * 100)
    print("EXPLORATORY -- alternative incentive endpoints (none, MODERATE) not (none, high)")
    print("=" * 100)
    print("  One alternative mapping only. Everything else held fixed.")
    alt = []
    for label, task_dir, stem, arm in ENVS:
        if stem == "task5":
            rows = t5_rows()
            ic = ("none", "moderate")
            fr, df = (
                (FRAMES, DIFF_ENDPOINTS)
                if arm == "commissive"
                else (FRAME_ENDPOINTS, ("low", "medium", "high"))
            )
            red = t5_slopes(filter_rows(rows, fr, ic, df), fr, ic, df)
        else:
            mod = load_module(task_dir, stem)
            rows = mod.load_rows()
            inc_all = list(mod.INCENTIVES)
            ic = (inc_all[0], inc_all[1])
            fr, df = (
                (FRAMES, DIFF_ENDPOINTS)
                if arm == "commissive"
                else (FRAME_ENDPOINTS, tuple(mod.DIFFICULTIES))
            )
            red = env_slopes(mod, filter_rows(rows, fr, ic, df), fr, ic, df)
        top, _s, ratio = dominant(aggregate(red))
        base = next(r for r in results if r["env"] == label)
        alt.append((label, base["red_dom"], top, top == base["red_dom"], ratio))
    print(f"{'env':<16}{'dom (none,high)':>18}{'dom (none,moderate)':>22}{'same':>7}{'ratio':>8}")
    for label, a, b, same, ratio in alt:
        print(f"{label:<16}{a:>18}{b:>22}{'OK' if same else 'FLIP':>7}{ratio:>8.2f}")
    print(f"\n  {sum(1 for x in alt if x[3])}/6 unchanged under the alternative mapping")

    json.dump(
        {
            "results": results,
            "cost": cost,
            "rho": rho_out,
            "exploratory_alt_incentive": [
                {"env": l, "dom_none_high": a, "dom_none_moderate": b, "same": s, "ratio": r}
                for l, a, b, s, r in alt
            ],
        },
        open(REPO / "paper/cross_task/reduced_protocol_retrospective.json", "w", encoding="utf-8"),
        indent=2,
        default=float,
    )


if __name__ == "__main__":
    main()
