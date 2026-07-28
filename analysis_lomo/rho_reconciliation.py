"""Reconcile the three cross-environment Spearman rho statistics, and LOMO each.

The abstract states two rho figures: a mean off-diagonal of 0.055 and "one pair
(sales vs. debate) reaching -0.77". Those come from DIFFERENT pipelines. This
script computes all three candidates from the committed code paths and reports
the leave-one-model-out swing for each, so the LOMO range can be quoted against
whichever figure the paper actually cites.

Definitions (all: Spearman across the 6 models, per environment pair, then the
mean of the SIGNED off-diagonal; 5 environments -> 10 unique pairs):

  v1      ranking_stability_v1.py    per-model mean of each env's primary metric
                                     at frame=permissive; T2 ranked by
                                     `manipulation_occurred`.        -> 0.055
  v2      ranking_stability_v2.py    identical, except T2 ranked by
                                     `belief_shift` (its stated primary
                                     metric).                        -> 0.329
  corpus  corpus/02_model_ranking.py per-model `manipulation_occurred` rate over
                                     ALL canonical rows (not permissive-only).
                                                                     -> 0.194

v1 and v2 differ in exactly one input column (T2's metric). Every non-T2 cell is
identical; every T2 cell flips sign. Confirmed independently by
findings/reanalysis_notes.md and by analysis/ranking_stability_v2_v1compat.json,
which runs the v2 code with v1's metric and returns 0.0552.

Run from the repo root:
    python analysis_lomo/rho_reconciliation.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "analysis_lomo"
XT = REPO / "paper/cross_task/scripts/cross_task"
CORPUS = REPO / "paper/cross_task/scripts/corpus"

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


def _load(name: str, path: Path, extra_syspath: Path | None = None):
    if extra_syspath:
        sys.path.insert(0, str(extra_syspath))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def mean_offdiag(per_env: dict[str, dict[str, float]], envs: list[str], keep: list[str]):
    """Full matrix + mean of signed off-diagonal, Spearman across `keep`."""
    n = len(envs)
    M = np.full((n, n), np.nan)
    for i, a in enumerate(envs):
        for j, b in enumerate(envs):
            xs = [per_env[a][m] for m in keep]
            ys = [per_env[b][m] for m in keep]
            M[i, j] = spearmanr(xs, ys).statistic
    off = [M[i, j] for i in range(n) for j in range(n) if i != j]
    return M, float(np.nanmean(off))


def main() -> None:
    sys.path.insert(0, str(XT))
    rs2 = _load("rs2_mod", XT / "ranking_stability_v2.py")
    load_mod = _load("load_mod", XT / "load.py")

    print("Loading corpus (six eval logs) ...")
    df = load_mod.load_corpus()

    # --- v1 and v2: reuse ranking_stability_v2's own per-task mean function ---
    envs_v = list(rs2.TASKS)
    means_v1 = rs2._per_task_means(df, ranking="permissive", use_v1_metric=True)
    means_v2 = rs2._per_task_means(df, ranking="permissive", use_v1_metric=False)
    per_v1 = {t: {m: float(means_v1[t][m]) for m in MODELS} for t in envs_v}
    per_v2 = {t: {m: float(means_v2[t][m]) for m in MODELS} for t in envs_v}

    # --- corpus: per-model manipulation_occurred rate on canonical rows only ---
    corpus_loader = _load("corpus_loader", CORPUS / "_loader.py", extra_syspath=CORPUS)
    cdf = corpus_loader.load(variant="canonical")
    envs_c = sorted(set(cdf["task"].unique()) & set(envs_v))
    per_c = {}
    for t in envs_c:
        sub = cdf[cdf["task"] == t]
        per_c[t] = {
            m: float(sub[sub["model"] == m]["manipulation_occurred"].astype(float).mean())
            for m in MODELS
        }

    defs = {
        "v1 (paper headline / abstract 0.055)": (per_v1, envs_v),
        "v2 (belief_shift for T2)": (per_v2, envs_v),
        "corpus (manipulation_occurred, all canonical rows)": (per_c, envs_c),
    }

    out = {}
    for label, (per_env, envs) in defs.items():
        M, mo = mean_offdiag(per_env, envs, MODELS)
        n = len(envs)
        pairs = {
            f"{envs[i]}__vs__{envs[j]}": float(M[i, j]) for i in range(n) for j in range(i + 1, n)
        }
        worst = min(pairs.items(), key=lambda kv: kv[1])
        print(f"\n=== {label} ===")
        print(f"  environments: {envs}")
        print(f"  mean signed off-diag rho = {mo:+.4f}")
        print(
            f"  mean |off-diag|          = "
            f"{float(np.nanmean([abs(M[i, j]) for i in range(n) for j in range(n) if i != j])):+.4f}"
        )
        print(f"  most negative pair       = {worst[0]} = {worst[1]:+.4f}")
        sd = pairs.get("debate__vs__sales", pairs.get("sales__vs__debate"))
        print(f"  debate-vs-sales          = {sd:+.4f}" if sd is not None else "")
        lomo = {}
        print("  LOMO (mean signed off-diag):")
        for x in MODELS:
            keep = [m for m in MODELS if m != x]
            _, mo_x = mean_offdiag(per_env, envs, keep)
            lomo[DISPLAY[x]] = mo_x
            print(f"    drop {DISPLAY[x]:16s} {mo_x:+.4f}")
        lo, hi = min(lomo.values()), max(lomo.values())
        print(
            f"  LOMO range = {lo:+.4f} .. {hi:+.4f}   (straddles zero: "
            f"{'YES' if lo < 0 < hi else 'NO'})"
        )
        out[label] = {
            "environments": envs,
            "full_roster_mean_offdiag": mo,
            "pairs": pairs,
            "most_negative_pair": {"pair": worst[0], "rho": worst[1]},
            "debate_vs_sales": sd,
            "lomo_mean_offdiag": lomo,
            "lomo_min": lo,
            "lomo_max": hi,
            "lomo_straddles_zero": bool(lo < 0 < hi),
            "matrix": [[None if np.isnan(v) else float(v) for v in r] for r in M],
        }

    path = OUT_DIR / "rho_reconciliation.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
