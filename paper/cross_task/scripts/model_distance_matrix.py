"""Pairwise distance matrix over per-model cross-task slope vectors.

Why this exists
---------------
`cross_task_clustering.py` already computes a distance matrix internally and
renders `figures/fig_distance_matrix.pdf`, but it (a) never writes the numbers
out in machine-readable form and (b) builds a **15**-dimensional vector from
five tasks, omitting T6 Inbox. This script produces the **18**-dimensional
version (6 environments x 3 axes) and commits the numbers.

Method, chosen to match the committed pipeline rather than invent one
-------------------------------------------------------------------
  vector      per model: {frame, incentive, difficulty} slope for each of the
              six environments = 18 numbers
  T1-T4, T6   slopes read from each task's published
              `analysis/prereg_results.json` -> `sensitivity_slopes`
  T5          recomputed from the combined eval log, because T5 has no
              prereg_results.json (cross_task_analysis.py carries a hardcoded
              T5_SLOPES map instead). The estimator is the published one from
              task5_prereg_analysis.py: OLS slope over axis-level marginal
              means, divided by that model's pooled SD of bias. A reproduction
              gate requires the uncorrected recomputation to match the
              committed T5_SLOPES before the corrected version is used.
  T5 scale    the per-sample 0-10 vs 0-20 correction is applied before T5
              enters any cross-model quantity (max rating <= 10 => x2).
  scaling     z-score each of the 18 columns across the 6 models, exactly as
              cross_task_clustering.py does, so that T5's standardized-bias
              units do not dominate the rate-based columns.
  metric      Euclidean, matching `pdist(Xz, metric="euclidean")` in
              cross_task_clustering.py. No new metric is introduced.

Run: python paper/cross_task/scripts/model_distance_matrix.py
"""

from __future__ import annotations

import json
import statistics
import sys
import zipfile
from pathlib import Path

import numpy as np
from scipy.spatial.distance import pdist, squareform

# Resolve against this file's own location so the script reads and writes inside
# whichever checkout it lives in (worktree or main), never across them.
REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "paper/cross_task/model_distance_matrix.json"

MODELS = [
    "Claude-Opus-4.7",
    "GPT-5.5",
    "Gemini-3.1-Pro",
    "Grok-4",
    "Llama-3.3-70B",
    "DeepSeek-V4-Pro",
]
AXES = ("frame", "incentive", "difficulty")
ENVS = [
    "task1_bargaining",
    "task2_debate",
    "task3_village",
    "task4_sales",
    "task5_committee",
    "task6_inbox",
]
SHORT = {
    "task1_bargaining": "T1",
    "task2_debate": "T2",
    "task3_village": "T3",
    "task4_sales": "T4",
    "task5_committee": "T5",
    "task6_inbox": "T6",
}

# Per-task model-key conventions in the committed prereg_results.json files.
ALIAS = {
    "claude": "Claude-Opus-4.7",
    "gpt5": "GPT-5.5",
    "gpt55": "GPT-5.5",
    "gemini": "Gemini-3.1-Pro",
    "grok": "Grok-4",
    "llama": "Llama-3.3-70B",
    "deepseek": "DeepSeek-V4-Pro",
}

# cross_task_analysis.py's hardcoded T5 map -- used only as the reproduction gate.
T5_COMMITTED = {
    "Claude-Opus-4.7": {"frame": 0.281, "incentive": 0.117, "difficulty": -0.911},
    "GPT-5.5": {"frame": 0.307, "incentive": 0.202, "difficulty": -0.676},
    "Gemini-3.1-Pro": {"frame": 0.434, "incentive": 0.430, "difficulty": 0.016},
    "Grok-4": {"frame": 0.372, "incentive": 0.135, "difficulty": -0.537},
    "Llama-3.3-70B": {"frame": 0.287, "incentive": 0.018, "difficulty": -0.713},
    "DeepSeek-V4-Pro": {"frame": 0.280, "incentive": 0.181, "difficulty": -0.765},
}

FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
INCS = ("none", "moderate", "high")
DIFFS = ("low", "medium", "high")


def slope_ols(xs, ys):
    if len(xs) < 2:
        return float("nan")
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else float("nan")


def published_slopes(task: str) -> dict:
    p = REPO / "paper" / task / "analysis" / "prereg_results.json"
    d = json.load(open(p, encoding="utf-8"))
    out = {}
    for k, v in d["sensitivity_slopes"].items():
        m = ALIAS.get(k, k)
        out[m] = {a: float(v[f"{a}_slope"]) for a in AXES}
    return out


def t5_rows():
    """Per-sample T5 rows from the combined eval log, with scale flag."""
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
        on10 = bool(vals) and max(vals) <= 10
        rows.append(
            {
                "model": ALIAS.get(
                    md.get("interested_model_label"), md.get("interested_model_label")
                ),
                "frame": md.get("frame"),
                "inc": md.get("incentive"),
                "diff": md.get("difficulty"),
                "bias": float(v["initial_bias"]),
                "on10": on10,
            }
        )
    return rows


def t5_slopes(rows, corrected: bool) -> dict:
    """Published estimator: OLS over marginal means / per-model pooled SD."""
    out = {}
    for m in MODELS:
        sub = [r for r in rows if r["model"] == m]
        if not sub:
            continue
        vals = [(r["bias"] * 2 if (corrected and r["on10"]) else r["bias"]) for r in sub]
        sd = statistics.pstdev(vals) or 1.0
        got = {}
        for axis, key, levels in (
            ("frame", "frame", FRAMES),
            ("incentive", "inc", INCS),
            ("difficulty", "diff", DIFFS),
        ):
            xs, ys = [], []
            for i, lv in enumerate(levels):
                sel = [v for v, r in zip(vals, sub) if r[key] == lv]
                if sel:
                    xs.append(i)
                    ys.append(sum(sel) / len(sel) / sd)
            got[axis] = slope_ols(xs, ys)
        out[m] = got
    return out


def main() -> None:
    rows = t5_rows()

    print("=" * 88)
    print("REPRODUCTION GATE -- T5 slopes recomputed uncorrected vs committed T5_SLOPES")
    print("=" * 88)
    raw = t5_slopes(rows, corrected=False)
    worst = 0.0
    for m in MODELS:
        for a in AXES:
            d = abs(raw[m][a] - T5_COMMITTED[m][a])
            worst = max(worst, d)
    print(f"  max abs deviation = {worst:.4f}", end="   ")
    if worst > 0.002:
        for m in MODELS:
            print(
                f"    {m:<18}"
                + "".join(f"{a}: {raw[m][a]:+.3f} vs {T5_COMMITTED[m][a]:+.3f}   " for a in AXES)
            )
        raise SystemExit("MISMATCH -- refusing to proceed")
    print("OK")

    corr = t5_slopes(rows, corrected=True)
    n10 = sum(1 for r in rows if r["on10"])
    print(f"\n  T5 scale correction applied: {n10}/{len(rows)} samples on 0-10 doubled")
    print(f"  {'model':<18}{'frame raw->corr':>26}{'inc raw->corr':>26}{'diff raw->corr':>26}")
    for m in MODELS:
        print(
            f"  {m:<18}" + "".join(f"{raw[m][a]:+.3f} -> {corr[m][a]:+.3f}".rjust(26) for a in AXES)
        )

    # Build the 18-dim matrix
    slopes = {}
    for t in ENVS:
        slopes[t] = corr if t == "task5_committee" else published_slopes(t)

    cols = [f"{SHORT[t]}_{a}" for t in ENVS for a in AXES]
    X = np.zeros((len(MODELS), len(cols)))
    for mi, m in enumerate(MODELS):
        for ti, t in enumerate(ENVS):
            for ai, a in enumerate(AXES):
                X[mi, ti * 3 + ai] = slopes[t][m][a]

    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd[sd < 1e-9] = 1.0
    Xz = (X - mu) / sd
    D = squareform(pdist(Xz, metric="euclidean"))

    print("\n" + "=" * 88)
    print("PAIRWISE EUCLIDEAN DISTANCE, z-scored 18-dim slope vectors (6 envs x 3 axes)")
    print("=" * 88)
    print(f"{'':<18}" + "".join(f"{m[:11]:>13}" for m in MODELS))
    for i, m in enumerate(MODELS):
        print(
            f"{m:<18}"
            + "".join(
                ("      .      " if i == j else f"{D[i, j]:>13.3f}") for j in range(len(MODELS))
            )
        )

    pairs = [
        (D[i, j], MODELS[i], MODELS[j])
        for i in range(len(MODELS))
        for j in range(i + 1, len(MODELS))
    ]
    lo, hi = min(pairs), max(pairs)
    print(f"\n  most similar : {lo[1]} & {lo[2]}   d = {lo[0]:.3f}")
    print(f"  least similar: {hi[1]} & {hi[2]}   d = {hi[0]:.3f}")

    json.dump(
        {
            "note": "18-dim per-model slope vectors (6 environments x 3 axes); T5 "
            "scale-corrected per-sample before inclusion; columns z-scored "
            "across models; Euclidean distance (matches cross_task_clustering.py).",
            "models": MODELS,
            "columns": cols,
            "raw_profile": X.tolist(),
            "z_scored_profile": Xz.tolist(),
            "distance_matrix": D.tolist(),
            "most_similar": {"pair": [lo[1], lo[2]], "distance": lo[0]},
            "least_similar": {"pair": [hi[1], hi[2]], "distance": hi[0]},
        },
        open(OUT, "w", encoding="utf-8"),
        indent=2,
    )
    print(f"\n  wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
