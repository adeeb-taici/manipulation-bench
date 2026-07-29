"""Does the T5 rating-scale correction propagate to the cross-task rank-instability result?

The paper's first headline claim -- "cross-task model rankings barely correlate,
mean off-diagonal Spearman rho = 0.055" -- ranks models within each environment
by their frame=permissive mean of that environment's primary metric. For T5 that
metric is `initial_rating_bias`, which was recorded on two different scales
(committee.py:187 says 0-10, its tool schema enforces 0-20). Correcting the scale
changes T5's per-model ordering materially, so it can in principle move every
pair involving T5.

This script reuses the committed estimator (`ranking_stability_v2._per_task_means`
with `use_v1_metric=True`, the same call `analysis_lomo/rho_reconciliation.py`
makes), verifies it reproduces the published figures on uncorrected inputs, then
substitutes T5's corrected per-model permissive means and recomputes everything.

Only T5's column changes; all other environments pass through untouched.

Run: python paper/task5_committee/scripts/t5_rank_propagation.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[3]
XT = REPO / "paper/cross_task/scripts/cross_task"

MODELS = [
    "Claude-Opus-4.7",
    "GPT-5.5",
    "Gemini-3.1-Pro",
    "Grok-4",
    "Llama-3.3-70B",
    "DeepSeek-V4-Pro",
]
DISPLAY = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5": "GPT-5.5",
    "Gemini-3.1-Pro": "Gemini 3.1 Pro",
    "Grok-4": "Grok 4",
    "Llama-3.3-70B": "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
}
# t5_rows.jsonl model keys -> corpus model keys
T5_KEY = {
    "claude": "Claude-Opus-4.7",
    "gpt55": "GPT-5.5",
    "gemini": "Gemini-3.1-Pro",
    "grok": "Grok-4",
    "llama": "Llama-3.3-70B",
    "deepseek": "DeepSeek-V4-Pro",
}

ENVS = ["bargaining", "debate", "village", "sales", "committee"]

# Published values to check reproduction against, from
# paper/cross_task/SUMMARY.md and analysis_lomo/FINDINGS.md.
PUBLISHED = {
    "v1_mean_offdiag": 0.0552,
    "v1_most_negative_pair": ("debate", "village"),
    "v1_most_negative_rho": -0.6000,
    "v1_lomo_lo": -0.1300,
    "v1_lomo_hi": +0.1988,
}


def _load(name: str, path: Path, extra_syspath: Path | None = None):
    if extra_syspath:
        sys.path.insert(0, str(extra_syspath))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def mean_offdiag(per_env, envs, keep):
    """Full matrix + mean of signed off-diagonal. Identical to
    analysis_lomo/rho_reconciliation.py:mean_offdiag."""
    n = len(envs)
    M = np.full((n, n), np.nan)
    for i, a in enumerate(envs):
        for j, b in enumerate(envs):
            xs = [per_env[a][m] for m in keep]
            ys = [per_env[b][m] for m in keep]
            M[i, j] = spearmanr(xs, ys).statistic
    off = [M[i, j] for i in range(n) for j in range(n) if i != j]
    return M, float(np.nanmean(off))


def most_negative(M, envs):
    n = len(envs)
    best, pair = np.inf, None
    for i in range(n):
        for j in range(i + 1, n):
            if M[i, j] < best:
                best, pair = M[i, j], (envs[i], envs[j])
    return pair, float(best)


def corrected_committee_means(rows_path: Path):
    """T5 per-model frame=permissive mean on the 0-20-equivalent scale.

    A sample whose interested-party max initial rating is <= 10 was recorded on
    the 0-10 scale; its bias is doubled. See t5_scale_corrected_excess.py for
    the identification argument (per-sample max is perfectly bimodal; the 11-14
    band is empty across all 1,075 samples).
    """
    raw, corr = {}, {}
    acc_raw, acc_corr = {}, {}
    for line in open(rows_path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("frame") != "permissive" or r.get("initial_bias") is None:
            continue
        vals = r.get("interested_initial") or []
        if not vals:
            continue
        m = T5_KEY.get(r["model"])
        if m is None:
            continue
        b = float(r["initial_bias"])
        b20 = b * 2 if max(vals) <= 10 else b
        acc_raw.setdefault(m, []).append(b)
        acc_corr.setdefault(m, []).append(b20)
    for m in MODELS:
        raw[m] = float(np.mean(acc_raw[m]))
        corr[m] = float(np.mean(acc_corr[m]))
    return raw, corr


def ranks(per_env_env: dict[str, float]) -> list[str]:
    return [DISPLAY[m] for m in sorted(MODELS, key=lambda x: -per_env_env[x])]


def print_matrix(label, M, envs):
    print(f"  {label}")
    print("    " + "".join(f"{e[:9]:>11}" for e in envs))
    for i, a in enumerate(envs):
        row = "".join(("        .  " if i == j else f"{M[i, j]:>+11.4f}") for j in range(len(envs)))
        print(f"    {a[:9]:<9}" + row)


def report(tag, per_env):
    M, mo = mean_offdiag(per_env, ENVS, MODELS)
    pair, val = most_negative(M, ENVS)
    lomo = {}
    for x in MODELS:
        keep = [m for m in MODELS if m != x]
        _, mo_x = mean_offdiag(per_env, ENVS, keep)
        lomo[DISPLAY[x]] = mo_x
    lo, hi = min(lomo.values()), max(lomo.values())
    return {
        "M": M,
        "mean_offdiag": mo,
        "most_neg_pair": pair,
        "most_neg_rho": val,
        "lomo": lomo,
        "lomo_lo": lo,
        "lomo_hi": hi,
        "straddles_zero": bool(lo < 0 < hi),
        "tag": tag,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--rows",
        type=Path,
        default=REPO / "paper/task5_committee/analysis/t5_rows.jsonl",
    )
    args = ap.parse_args()

    sys.path.insert(0, str(XT))
    rs2 = _load("rs2_mod", XT / "ranking_stability_v2.py")
    load_mod = _load("load_mod", XT / "load.py")
    df = load_mod.load_corpus(verbose=False)

    means_v1 = rs2._per_task_means(df, ranking="permissive", use_v1_metric=True)
    means_v2 = rs2._per_task_means(df, ranking="permissive", use_v1_metric=False)
    per_v1 = {t: {m: float(means_v1[t][m]) for m in MODELS} for t in ENVS}
    per_v2 = {t: {m: float(means_v2[t][m]) for m in MODELS} for t in ENVS}

    # ── Reproduction gate ──────────────────────────────────────────────
    base_v1 = report("v1 uncorrected", per_v1)
    print("=" * 92)
    print("REPRODUCTION CHECK (uncorrected inputs, v1 = paper headline)")
    print("=" * 92)
    ok = True
    checks = [
        ("mean off-diag rho", base_v1["mean_offdiag"], PUBLISHED["v1_mean_offdiag"], 1e-3),
        ("most negative rho", base_v1["most_neg_rho"], PUBLISHED["v1_most_negative_rho"], 1e-3),
        ("LOMO lo", base_v1["lomo_lo"], PUBLISHED["v1_lomo_lo"], 1e-3),
        ("LOMO hi", base_v1["lomo_hi"], PUBLISHED["v1_lomo_hi"], 1e-3),
    ]
    for name, got, want, tol in checks:
        good = abs(got - want) < tol
        ok &= good
        print(
            f"  {name:<20} computed {got:+.4f}   published {want:+.4f}   {'OK' if good else 'MISMATCH'}"
        )
    pair_ok = set(base_v1["most_neg_pair"]) == set(PUBLISHED["v1_most_negative_pair"])
    ok &= pair_ok
    print(
        f"  {'most negative pair':<20} computed {base_v1['most_neg_pair']}   "
        f"published {PUBLISHED['v1_most_negative_pair']}   {'OK' if pair_ok else 'MISMATCH'}"
    )
    if not ok:
        raise SystemExit("\nREPRODUCTION FAILED -- stopping before computing anything new.")
    print("\n  All published v1 figures reproduced. Proceeding.\n")

    # ── T5 correction ──────────────────────────────────────────────────
    raw_t5, corr_t5 = corrected_committee_means(args.rows)
    print("=" * 92)
    print("T5 PERMISSIVE-FRAME PER-MODEL MEANS")
    print("=" * 92)
    print(f"  {'model':<18}{'corpus':>10}{'recomputed raw':>17}{'corrected':>12}")
    for m in MODELS:
        print(
            f"  {DISPLAY[m]:<18}{per_v1['committee'][m]:>10.3f}{raw_t5[m]:>17.3f}{corr_t5[m]:>12.3f}"
        )
    drift = max(abs(per_v1["committee"][m] - raw_t5[m]) for m in MODELS)
    print(f"\n  max |corpus - recomputed raw| = {drift:.4f} (sanity: should be ~0)")
    print(f"\n  ranking raw       : {' > '.join(ranks(per_v1['committee']))}")
    print(f"  ranking corrected : {' > '.join(ranks(corr_t5))}\n")

    per_v1_corr = {t: dict(v) for t, v in per_v1.items()}
    per_v1_corr["committee"] = corr_t5
    per_v2_corr = {t: dict(v) for t, v in per_v2.items()}
    per_v2_corr["committee"] = corr_t5

    for label, base, corrected in (
        ("v1 (AUTHORITATIVE -- abstract / headline)", per_v1, per_v1_corr),
        ("v2 (secondary -- T2 by belief_shift)", per_v2, per_v2_corr),
    ):
        b = report("uncorrected", base)
        c = report("corrected", corrected)
        print("=" * 92)
        print(f"{label}")
        print("=" * 92)
        print_matrix("UNCORRECTED matrix:", b["M"], ENVS)
        print()
        print_matrix("CORRECTED matrix:", c["M"], ENVS)
        print()
        print(f"  mean off-diagonal rho : {b['mean_offdiag']:+.4f}  ->  {c['mean_offdiag']:+.4f}")
        print(
            f"  most negative pair    : {b['most_neg_pair']} {b['most_neg_rho']:+.4f}"
            f"  ->  {c['most_neg_pair']} {c['most_neg_rho']:+.4f}"
            f"   {'(identity UNCHANGED)' if b['most_neg_pair'] == c['most_neg_pair'] else '(identity CHANGED)'}"
        )
        print()
        print("  Pairs involving committee (the only ones that can move):")
        ci = ENVS.index("committee")
        for j, e in enumerate(ENVS):
            if e == "committee":
                continue
            print(
                f"    committee vs {e:<11} {b['M'][ci, j]:+.4f}  ->  {c['M'][ci, j]:+.4f}"
                f"   (delta {c['M'][ci, j] - b['M'][ci, j]:+.4f})"
            )
        print()
        print("  Leave-one-model-out mean off-diagonal:")
        for m in MODELS:
            print(
                f"    drop {DISPLAY[m]:<18}{b['lomo'][DISPLAY[m]]:>+9.4f}  ->  {c['lomo'][DISPLAY[m]]:>+9.4f}"
            )
        print(
            f"    range              {b['lomo_lo']:+.4f} .. {b['lomo_hi']:+.4f}"
            f"   ->  {c['lomo_lo']:+.4f} .. {c['lomo_hi']:+.4f}"
        )
        print(
            f"    straddles zero     {'YES' if b['straddles_zero'] else 'NO'}"
            f"          ->  {'YES' if c['straddles_zero'] else 'NO'}"
        )
        print()


if __name__ == "__main__":
    main()
