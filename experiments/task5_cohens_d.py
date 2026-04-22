"""Cohen's d secondary analysis for Task 5 Committee per PREREG §8.

For each cell (model × frame × incentive × difficulty):
  1. Identify reference cell: same (model, incentive, difficulty) with frame=prohibitive
  2. Pooled SD across current cell and reference cell
  3. d = (mean_current - mean_reference) / pooled_SD

Saturated cells (within-cell variance near zero) report raw mean difference with a
footnote; per PREREG §8 we do not floor-correct SD across the roster.

Convergence check: Spearman ρ between (a) per-model ranking on raw bias frame-slope
and (b) per-model ranking on Cohen's-d frame-slope. ρ>0.7 threshold.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict

from inspect_ai.log import read_eval_log

LOG = "logs/committee_fullsweep_20260422/2026-04-22T15-20-47-00-00_committee-bench_nMe8xyseb5QPSzdS8rjvE7.eval"

FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
INCS = ("none", "moderate", "high")
DIFFS = ("low", "medium", "high")

SATURATED_VAR_THRESHOLD = 0.25  # SD <0.5 → ~ceiling within cell


def load_rows():
    log = read_eval_log(LOG)
    rows = []
    for s in log.samples:
        if s.error is not None:
            continue
        m = (s.metadata or {}).get("scenario", {}).get("metadata", {})
        bs = (s.scores or {}).get("initial_rating_bias")
        if bs is None or not isinstance(bs.value, dict):
            continue
        bias = bs.value.get("initial_bias")
        if bias is None:
            continue
        rows.append(
            dict(
                model=m.get("interested_model_label"),
                frame=m.get("frame"),
                incentive=m.get("incentive"),
                difficulty=m.get("difficulty"),
                bias=float(bias),
            )
        )
    return rows


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def pooled_sd(a, b):
    """Pooled SD across two samples; returns (sd, degenerate_flag).

    PREREG §8 saturated-cell rule: "within-cell variance near zero" — checked on
    the current cell (a), not the pooled value. A degenerate current cell makes
    Cohen's d unmeaningful as an effect size even if the reference cell has
    variance.
    """
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return float("nan"), True
    va = statistics.variance(a)
    vb = statistics.variance(b)
    pooled_var = ((na - 1) * va + (nb - 1) * vb) / (na + nb - 2)
    sd = math.sqrt(pooled_var) if pooled_var > 0 else 0.0
    degenerate = va < SATURATED_VAR_THRESHOLD  # current-cell variance near zero
    return sd, degenerate


def cell(rows, **kw):
    return [r["bias"] for r in rows if all(r[k] == v for k, v in kw.items())]


def spearman_rho(a, b):
    """Spearman correlation between two rankings on equal-length lists."""

    def ranks(xs):
        idx = sorted(range(len(xs)), key=lambda i: xs[i])
        r = [0.0] * len(xs)
        i = 0
        while i < len(xs):
            j = i
            while j + 1 < len(xs) and xs[idx[j + 1]] == xs[idx[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[idx[k]] = avg
            i = j + 1
        return r

    ra, rb = ranks(a), ranks(b)
    mra, mrb = mean(ra), mean(rb)
    num = sum((x - mra) * (y - mrb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - mra) ** 2 for x in ra))
    db = math.sqrt(sum((y - mrb) ** 2 for y in rb))
    return num / (da * db) if da and db else float("nan")


def slope_ols(xs, ys):
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den if den else float("nan")


def main():
    rows = load_rows()
    models = sorted({r["model"] for r in rows if r["model"]})
    print(f"Scored rows: {len(rows)}")
    print(f"Models: {models}\n")

    # ---- 1) Per-cell Cohen's d table ----
    # For every (model, frame, incentive, difficulty), ref = same (model, prohibitive, incentive, difficulty)
    cell_results = []  # list of dicts
    for model in models:
        for frame in FRAMES:
            for inc in INCS:
                for diff in DIFFS:
                    cur = cell(rows, model=model, frame=frame, incentive=inc, difficulty=diff)
                    ref = cell(
                        rows, model=model, frame="prohibitive", incentive=inc, difficulty=diff
                    )
                    if not cur or not ref:
                        continue
                    m_cur, m_ref = mean(cur), mean(ref)
                    sd, degen = pooled_sd(cur, ref)
                    diff_mean = m_cur - m_ref
                    if sd and sd > 0 and not degen:
                        d = diff_mean / sd
                        d_str = f"{d:.2f}"
                        note = ""
                    else:
                        d = None
                        d_str = "saturated"
                        note = (
                            f"raw Δ={diff_mean:+.2f}, pooled_sd={sd:.3f}"
                            if not math.isnan(sd)
                            else "raw Δ={diff_mean:+.2f}, n too small"
                        )
                    cell_results.append(
                        dict(
                            model=model,
                            frame=frame,
                            incentive=inc,
                            difficulty=diff,
                            n_cur=len(cur),
                            n_ref=len(ref),
                            mean_cur=m_cur,
                            mean_ref=m_ref,
                            diff_mean=diff_mean,
                            pooled_sd=sd,
                            d=d,
                            d_str=d_str,
                            note=note,
                            saturated=degen,
                        )
                    )

    # ---- 2) Per-model, per-frame d-aggregates (averaged over incentive × difficulty) ----
    # For permissive cells where Gemini saturates, report raw mean difference (diff_mean) instead.
    print("## Cohen's d per (model, non-prohibitive frame), averaged over incentive × difficulty\n")
    print(
        f"{'model':12s} {'frame':14s} {'mean d':>8s} {'n_cells':>8s} {'saturated':>10s}  ref-based"
    )
    agg_d_by_model_frame = defaultdict(dict)  # {model: {frame: mean_d}}
    agg_raw_by_model_frame = defaultdict(dict)  # fallback when saturated
    for model in models:
        for frame in FRAMES:
            if frame == "prohibitive":
                continue
            rels = [c for c in cell_results if c["model"] == model and c["frame"] == frame]
            n_sat = sum(1 for r in rels if r["saturated"])
            valid_ds = [r["d"] for r in rels if r["d"] is not None]
            raw_diffs = [r["diff_mean"] for r in rels]
            if valid_ds:
                d_agg = mean(valid_ds)
                agg_d_by_model_frame[model][frame] = d_agg
            else:
                agg_d_by_model_frame[model][frame] = None
            agg_raw_by_model_frame[model][frame] = mean(raw_diffs)
            d_display = (
                f"{agg_d_by_model_frame[model][frame]:+.3f}"
                if agg_d_by_model_frame[model][frame] is not None
                else "all sat"
            )
            print(
                f"{model:12s} {frame:14s} {d_display:>8s} {len(rels):>8d} {f'{n_sat}/{len(rels)}':>10s}"
            )

    # ---- 3) Convergence check: per-model frame-slope on raw bias vs on Cohen's d ----
    # Raw frame-slope: average bias per frame (over incentive × difficulty), slope on frame-index 0-4.
    # Cohen's-d frame-slope: average d per frame (non-prohibitive cells), slope on frame-index 1-4,
    #   with saturated cells replaced by raw_diff / cross-roster median pooled_sd as a fallback
    #   ONLY for slope computation; aggregated d reporting uses saturated flag.
    print("\n## Convergence check: per-model frame-sensitivity ranking\n")
    raw_frame_slope = {}
    d_frame_slope = {}
    for model in models:
        # Raw bias frame slope (5 points: frames 0..4)
        frame_means = []
        for fi, f in enumerate(FRAMES):
            vals = cell(rows, model=model, frame=f)
            frame_means.append(mean(vals) if vals else float("nan"))
        # standardize by per-model pooled SD of bias
        all_bias = [r["bias"] for r in rows if r["model"] == model]
        sd_pool = statistics.pstdev(all_bias) or 1.0
        raw_slope = slope_ols(list(range(5)), [f / sd_pool for f in frame_means])
        raw_frame_slope[model] = raw_slope

        # Cohen's d frame slope: use d when defined; substitute raw_diff / sd_pool fallback
        d_means_per_frame = []
        for fi, f in enumerate(FRAMES):
            if f == "prohibitive":
                d_means_per_frame.append(0.0)
                continue
            rels = [c for c in cell_results if c["model"] == model and c["frame"] == f]
            vals = []
            for r in rels:
                if r["d"] is not None:
                    vals.append(r["d"])
                else:
                    # Saturated fallback: raw_diff / roster median pooled SD
                    roster_sds = [
                        cc["pooled_sd"]
                        for cc in cell_results
                        if cc["frame"] == f
                        and cc["d"] is not None
                        and not math.isnan(cc["pooled_sd"])
                    ]
                    fallback_sd = statistics.median(roster_sds) if roster_sds else 1.0
                    vals.append(r["diff_mean"] / fallback_sd)
            d_means_per_frame.append(mean(vals) if vals else float("nan"))
        d_slope = slope_ols(list(range(5)), d_means_per_frame)
        d_frame_slope[model] = d_slope

        print(f"{model:12s} raw frame-slope = {raw_slope:+.3f}   d frame-slope = {d_slope:+.3f}")

    # Spearman rho on rankings
    ms = sorted(models)
    raw_ranks = [raw_frame_slope[m] for m in ms]
    d_ranks = [d_frame_slope[m] for m in ms]
    rho = spearman_rho(raw_ranks, d_ranks)
    print(f"\nSpearman rho (raw-slope rank vs d-slope rank) = {rho:.3f}")
    print(f"Convergence threshold: rho > 0.7 -> {'PASS' if rho > 0.7 else 'FAIL'}")

    # ---- 4) Dump per-cell table for the report ----
    print("\n## Full per-cell table (printable)\n")
    # Delta symbol for output (avoid unicode issues on cp1252)
    for model in models:
        print(f"\n### {model}")
        print(
            f"{'frame':14s} {'incentive':10s} {'difficulty':10s} {'n_cur':>6s} {'mean_cur':>9s} {'mean_ref':>9s} {'Δ':>7s} {'pooled_sd':>10s} {'d':>10s}"
        )
        for c in cell_results:
            if c["model"] != model or c["frame"] == "prohibitive":
                continue
            print(
                f"{c['frame']:14s} {c['incentive']:10s} {c['difficulty']:10s} "
                f"{c['n_cur']:>6d} {c['mean_cur']:>9.3f} {c['mean_ref']:>9.3f} {c['diff_mean']:>+7.3f} "
                f"{c['pooled_sd']:>10.3f} {c['d_str']:>10s}"
            )

    # Save CSV for the report
    import csv
    from pathlib import Path

    out = Path("analysis/task5_committee/cohens_d_per_cell.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "model",
                "frame",
                "incentive",
                "difficulty",
                "n_cur",
                "n_ref",
                "mean_cur",
                "mean_ref",
                "diff_mean",
                "pooled_sd",
                "cohens_d",
                "saturated",
            ]
        )
        for c in cell_results:
            if c["frame"] == "prohibitive":
                continue
            w.writerow(
                [
                    c["model"],
                    c["frame"],
                    c["incentive"],
                    c["difficulty"],
                    c["n_cur"],
                    c["n_ref"],
                    f"{c['mean_cur']:.3f}",
                    f"{c['mean_ref']:.3f}",
                    f"{c['diff_mean']:.3f}",
                    f"{c['pooled_sd']:.3f}" if not math.isnan(c["pooled_sd"]) else "",
                    f"{c['d']:.3f}" if c["d"] is not None else "saturated",
                    "Y" if c["saturated"] else "N",
                ]
            )
    print(f"\nSaved: {out}")

    # Save summary JSON for downstream report
    import json

    summary_out = Path("analysis/task5_committee/cohens_d_summary.json")
    summary = dict(
        raw_frame_slope=raw_frame_slope,
        d_frame_slope=d_frame_slope,
        convergence_rho=rho,
        agg_d_by_model_frame={
            m: {f: v for f, v in dd.items()} for m, dd in agg_d_by_model_frame.items()
        },
        agg_raw_by_model_frame={
            m: {f: v for f, v in dd.items()} for m, dd in agg_raw_by_model_frame.items()
        },
    )
    with open(summary_out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved: {summary_out}")


if __name__ == "__main__":
    main()
