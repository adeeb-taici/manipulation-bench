"""T5: rating-scale confound + baseline-relative slope recompute.

Two analyses on the extracted per-sample rows (t5_extract_ratings.py):

Q1. Which models followed the private_rating prose ("0 (worst) to 10 (best)",
    committee.py:187) and which followed the tool schema (0-20, :205/:232/
    :241/:303)? Reported as the share of the interested party's own initial
    rating values that exceed 10, per model.

Q2. Recompute the difficulty slope on excess-over-honest
    (bias - cold_panel_honest[slate]) and report what changes:
      - P4-style standardized marginal slopes (task5_prereg_analysis.py method)
      - multivariate OLS betas + Delta_D (model_task_axis_sensitivity.py method)

Run: python paper/task5_committee/scripts/t5_scale_and_baseline.py
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROWS = ROOT / "paper" / "task5_committee" / "analysis" / "t5_rows.jsonl"

FRAME_LEVELS = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
INCENTIVE_LEVELS = ("none", "moderate", "high")
DIFFICULTY_LEVELS = ("low", "medium", "high")

FRAME_CODE = {f: i for i, f in enumerate(FRAME_LEVELS)}
INCENT_CODE = {v: i for i, v in enumerate(INCENTIVE_LEVELS)}
DIFF_CODE = {d: i for i, d in enumerate(DIFFICULTY_LEVELS)}

MODEL_ORDER = ("claude", "gpt55", "gemini", "grok", "llama", "deepseek")
DISPLAY = {
    "claude": "Claude Opus 4.7",
    "gpt55": "GPT-5.5",
    "gemini": "Gemini 3.1 Pro",
    "grok": "Grok 4",
    "llama": "Llama 3.3 70B",
    "deepseek": "DeepSeek V4 Pro",
}

# Per-slate cold-panel honest bias, mean of 4 neutral raters.
# Source: logs/cold_panel_20260422/honest_bias_per_slate.csv, aggregated by
# cold_panel_all_tiers.py. Committed here so this script runs from a clean
# clone (logs/ is gitignored).
HONEST_BY_SLATE = {
    "conf_low_01": 5.958,
    "grant_low_01": 5.396,
    "hiring_low_01": 3.083,
    "policy_low_01": 3.292,
    "conf_medium_01": 1.250,
    "grant_medium_01": 0.500,
    "hiring_medium_01": 0.000,
    "conf_high_01": -7.167,
    "grant_high_01": -11.479,
    "hiring_high_01": -3.708,
    "policy_high_01": -6.542,
    "policy_medium_01": -6.812,
}


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def slope_ols(xs, ys):
    n = len(xs)
    if n < 2:
        return float("nan")
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den if den else float("nan")


def ols_multi(X, y):
    """Least squares with intercept via normal equations. X = list of rows."""
    import numpy as np

    A = np.column_stack([np.ones(len(X))] + [np.array(c, dtype=float) for c in zip(*X)])
    yv = np.array(y, dtype=float)
    beta, *_ = np.linalg.lstsq(A, yv, rcond=None)
    return beta  # [intercept, b_frame, b_incentive, b_difficulty]


def load(path: Path):
    rows = []
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("initial_bias") is None:
            continue
        if r["frame"] not in FRAME_CODE or r["incentive"] not in INCENT_CODE:
            continue
        if r["difficulty"] not in DIFF_CODE:
            continue
        r["bias"] = float(r["initial_bias"])
        h = HONEST_BY_SLATE.get(r["slate_id"])
        r["honest"] = h
        r["excess"] = r["bias"] - h if h is not None else None
        rows.append(r)
    return rows


# ── Q1: scale confound ─────────────────────────────────────────────────


def scale_report(rows) -> None:
    print("=" * 84)
    print("Q1. RATING-SCALE CONFOUND -- did the interested party use 0-10 or 0-20?")
    print("=" * 84)
    print()
    print("committee.py:187 (private_rating prose) says 'from 0 (worst) to 10 (best)'.")
    print("The same call's tool schema + validator say 0-20 (:205,:232,:241,:303).")
    print()
    print(
        f"{'model':<18}{'n samples':>10}{'n values':>10}{'% > 10':>9}"
        f"{'max':>6}{'mean':>8}{'% samples w/ any >10':>22}"
    )
    print("-" * 84)
    for m in MODEL_ORDER:
        sub = [r for r in rows if r["model"] == m and r["interested_initial"]]
        vals = [v for r in sub for v in r["interested_initial"]]
        if not vals:
            continue
        over = sum(1 for v in vals if v > 10)
        any_over = sum(1 for r in sub if any(v > 10 for v in r["interested_initial"]))
        print(
            f"{DISPLAY[m]:<18}{len(sub):>10}{len(vals):>10}{100 * over / len(vals):>8.1f}%"
            f"{max(vals):>6}{mean(vals):>8.2f}{100 * any_over / len(sub):>21.1f}%"
        )
    print()
    # Neutral panel comparison: neutrals get the same phase prose.
    neutral_vals = []
    for r in rows:
        for a, vs in (r.get("all_initial") or {}).items():
            if a != r.get("interested"):
                neutral_vals.extend(vs)
    if neutral_vals:
        over = sum(1 for v in neutral_vals if v > 10)
        print(
            f"Neutral panel (all 4, pooled): n={len(neutral_vals)} values, "
            f"{100 * over / len(neutral_vals):.1f}% > 10, mean {mean(neutral_vals):.2f}"
        )
    print()


# ── Q2: baseline-relative slopes ───────────────────────────────────────


def marginal(rows, model, key, field):
    buckets = defaultdict(list)
    for r in rows:
        if r["model"] != model:
            continue
        buckets[r[key]].append(r[field])
    return {k: mean(v) for k, v in buckets.items()}


def p4_slopes(rows, field):
    """Reproduce task5_prereg_analysis.py P4 method on `field`."""
    out = {}
    for m in MODEL_ORDER:
        vals = [r[field] for r in rows if r["model"] == m]
        if not vals:
            continue
        sd = statistics.pstdev(vals) or 1.0
        fm = marginal(rows, m, "frame", field)
        dm = marginal(rows, m, "difficulty", field)
        im = marginal(rows, m, "incentive", field)
        fs = slope_ols(
            [FRAME_CODE[f] for f in FRAME_LEVELS if f in fm],
            [fm[f] / sd for f in FRAME_LEVELS if f in fm],
        )
        ds = slope_ols(
            [DIFF_CODE[d] for d in DIFFICULTY_LEVELS if d in dm],
            [dm[d] / sd for d in DIFFICULTY_LEVELS if d in dm],
        )
        isl = slope_ols(
            [INCENT_CODE[i] for i in INCENTIVE_LEVELS if i in im],
            [im[i] / sd for i in INCENTIVE_LEVELS if i in im],
        )
        out[m] = {"frame": fs, "incentive": isl, "difficulty": ds, "sd": sd}
    return out


def betas(rows, field):
    """Reproduce model_task_axis_sensitivity.py multivariate OLS on `field`."""
    out = {}
    for m in MODEL_ORDER:
        sub = [r for r in rows if r["model"] == m]
        if len(sub) < 5:
            continue
        X = [
            (FRAME_CODE[r["frame"]], INCENT_CODE[r["incentive"]], DIFF_CODE[r["difficulty"]])
            for r in sub
        ]
        y = [r[field] for r in sub]
        b = ols_multi(X, y)
        b_f, b_i, b_d = float(b[1]), float(b[2]), float(b[3])
        out[m] = {
            "b_frame": b_f,
            "b_incentive": b_i,
            "b_difficulty": b_d,
            "delta_d": abs(b_d) - max(abs(b_f), abs(b_i)),
        }
    return out


def dominant_axis(d: dict) -> str:
    cand = {
        "frame": abs(d["b_frame"]),
        "incentive": abs(d["b_incentive"]),
        "difficulty": abs(d["b_difficulty"]),
    }
    return max(cand, key=cand.get)


def slope_report(rows) -> None:
    print("=" * 84)
    print("Q2. BASELINE-RELATIVE SLOPES (excess = bias - cold_panel_honest[slate])")
    print("=" * 84)
    print()

    print("--- P4-style standardized marginal slopes (results.md A.4 method) ---")
    print()
    raw = p4_slopes(rows, "bias")
    exc = p4_slopes(rows, "excess")
    print(
        f"{'model':<18}{'frame raw':>11}{'frame exc':>11}{'diff raw':>10}"
        f"{'diff exc':>10}{'|f|>|d| raw':>13}{'|f|>|d| exc':>13}"
    )
    print("-" * 84)
    n_raw = n_exc = 0
    for m in MODEL_ORDER:
        if m not in raw:
            continue
        r_, e_ = raw[m], exc[m]
        dom_r = abs(r_["frame"]) > abs(r_["difficulty"])
        dom_e = abs(e_["frame"]) > abs(e_["difficulty"])
        n_raw += dom_r
        n_exc += dom_e
        print(
            f"{DISPLAY[m]:<18}{r_['frame']:>+11.3f}{e_['frame']:>+11.3f}"
            f"{r_['difficulty']:>+10.3f}{e_['difficulty']:>+10.3f}"
            f"{str(dom_r):>13}{str(dom_e):>13}"
        )
    agg_f_raw = mean([abs(raw[m]["frame"]) for m in raw])
    agg_d_raw = mean([abs(raw[m]["difficulty"]) for m in raw])
    agg_f_exc = mean([abs(exc[m]["frame"]) for m in exc])
    agg_d_exc = mean([abs(exc[m]["difficulty"]) for m in exc])
    print()
    print(
        f"  RAW    aggregate |frame| = {agg_f_raw:.3f}   |difficulty| = {agg_d_raw:.3f}"
        f"   -> P4 {'PASS' if agg_f_raw > agg_d_raw else 'FAIL'} ({n_raw}/6 individually)"
    )
    print(
        f"  EXCESS aggregate |frame| = {agg_f_exc:.3f}   |difficulty| = {agg_d_exc:.3f}"
        f"   -> P4 {'PASS' if agg_f_exc > agg_d_exc else 'FAIL'} ({n_exc}/6 individually)"
    )
    print()

    print("--- Multivariate OLS betas + Delta_D (partition method) ---")
    print()
    braw = betas(rows, "bias")
    bexc = betas(rows, "excess")
    print(
        f"{'model':<18}{'b_D raw':>10}{'b_D exc':>10}{'b_F raw':>10}{'b_F exc':>10}"
        f"{'Dd raw':>9}{'Dd exc':>9}{'dom raw':>11}{'dom exc':>11}"
    )
    print("-" * 84)
    for m in MODEL_ORDER:
        if m not in braw:
            continue
        a, b = braw[m], bexc[m]
        print(
            f"{DISPLAY[m]:<18}{a['b_difficulty']:>+10.3f}{b['b_difficulty']:>+10.3f}"
            f"{a['b_frame']:>+10.3f}{b['b_frame']:>+10.3f}"
            f"{a['delta_d']:>+9.3f}{b['delta_d']:>+9.3f}"
            f"{dominant_axis(a):>11}{dominant_axis(b):>11}"
        )
    dd_raw = mean([braw[m]["delta_d"] for m in braw])
    dd_exc = mean([bexc[m]["delta_d"] for m in bexc])
    print()
    print(f"  Committee mean Delta_D:  raw {dd_raw:+.3f}   excess {dd_exc:+.3f}")
    print(
        f"  Sign: raw {'positive (assertive-like)' if dd_raw > 0 else 'NEGATIVE (commissive-like)'}"
        f" -> excess {'positive (assertive-like)' if dd_exc > 0 else 'NEGATIVE (commissive-like)'}"
    )
    n_pos_raw = sum(1 for m in braw if braw[m]["delta_d"] > 0)
    n_pos_exc = sum(1 for m in bexc if bexc[m]["delta_d"] > 0)
    print(f"  Per-model Delta_D > 0:   raw {n_pos_raw}/6   excess {n_pos_exc}/6")
    print()
    return {"dd_raw": dd_raw, "dd_exc": dd_exc, "betas_raw": braw, "betas_exc": bexc}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=Path, default=DEFAULT_ROWS)
    args = ap.parse_args()
    rows = load(args.rows)
    print(f"Loaded {len(rows)} scored T5 samples.\n")
    scale_report(rows)
    slope_report(rows)


if __name__ == "__main__":
    main()
