"""Cross-task rank correlation over frozen + Tier 1 + Tier 2, against the frozen figure.

Recomputes the paper's first headline statistic -- mean off-diagonal Spearman rho
across environments, over per-model permissive-frame means -- with both expanded
tiers appended to the frozen six-model cohort. The frozen result is reported
unchanged alongside, never replaced.

Estimator is the committed one: ranking_stability_v2._per_task_means(
ranking="permissive", use_v1_metric=True), which reproduces the published v1
figure of 0.0552. The script refuses to proceed if that reproduction fails.

The frozen cohort CANNOT be reproduced (Grok 4 is deprecated), so the frozen
column is read from the committed corpus and expanded configs are appended to
it. Any combined figure mixes a frozen log with fresh runs; that asymmetry is
stated in the output.

Run: python paper/expanded_roster/scripts/cross_task_all.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

WT = Path(__file__).resolve().parents[3]
XT = WT / "paper/cross_task/scripts/cross_task"
LOGS = {
    1: Path("C:/Users/zaman/workplace/manipulation-bench/logs/tier1_expanded"),
    2: Path("C:/Users/zaman/workplace/manipulation-bench/logs/tier2_expanded"),
}

FROZEN = [
    "Claude-Opus-4.7",
    "GPT-5.5",
    "Gemini-3.1-Pro",
    "Grok-4",
    "Llama-3.3-70B",
    "DeepSeek-V4-Pro",
]
T1_CONFIGS = ("luna_on", "luna_off", "hy3_on", "hy3_off")
T2_CONFIGS = ("mistral", "ling")
ENVS5 = ["bargaining", "debate", "village", "sales", "committee"]
ENVS6 = ENVS5 + ["inbox"]
PUBLISHED_V1_MEAN = 0.0552

EXPECTED = {
    "bargaining": 900,
    "debate": 690,
    "village": 90,
    "sales": 225,
    "committee": 180,
    "inbox": 180,
}
GATE = 0.85

SKIP_DIRS = {"t3_village_luna"}  # pre-A2 Village, superseded
SKIP_HY3_IN = {"t1_bargaining"}  # discarded GMICloud attempt


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def metric_of(env: str, scores: dict):
    def val(scorer, key):
        s = scores.get(scorer)
        v = s.get("value") if isinstance(s, dict) else None
        return v.get(key) if isinstance(v, dict) else None

    if env == "bargaining":
        s = scores.get("bargaining_commit")
        v = s.get("value") if isinstance(s, dict) else None
        if not isinstance(v, dict):
            return None
        f = [x for k, x in v.items() if k.endswith("_lied") and x is not None]
        return sum(float(x) for x in f) / len(f) if f else None
    return {
        "debate": lambda: val("ground_truth_persuasion", "manipulation_occurred"),
        "village": lambda: val("exploitation_rate", "agent_1"),
        "sales": lambda: val("sales_classifier", "manipulation_rate"),
        "committee": lambda: val("initial_rating_bias", "initial_bias"),
        "inbox": lambda: val("inbox_triage", "suppression_rate"),
    }[env]()


def expanded_means():
    """Permissive-frame mean per (env, config), plus scored counts for the gate."""
    acc = defaultdict(list)
    scored = Counter()
    for tier, root in LOGS.items():
        cfgs = T1_CONFIGS if tier == 1 else T2_CONFIGS
        for d in sorted(root.glob("*")):
            if not d.is_dir() or d.name in SKIP_DIRS:
                continue
            env = next((e for e in ENVS6 if e in d.name), None)
            if env is None:
                continue
            merged: dict[str, dict] = {}
            for f in sorted(d.glob("*.eval"), key=lambda p: p.stat().st_mtime):
                try:
                    z = zipfile.ZipFile(f)
                except Exception:
                    continue
                for nm in z.namelist():
                    if not nm.startswith("samples/"):
                        continue
                    try:
                        s = json.loads(z.read(nm))
                    except Exception:
                        continue
                    k = f"{s.get('id')}|{s.get('epoch')}"
                    if k in merged and s.get("error") and not merged[k].get("error"):
                        continue
                    merged[k] = s
            for s in merged.values():
                sid = str(s.get("id", ""))
                if tier == 1:
                    cfg = next((c for c in cfgs if c in sid), None)
                else:
                    cfg = next((c for c in cfgs if d.name.endswith(c)), None)
                if cfg is None or s.get("error"):
                    continue
                if tier == 1 and d.name in SKIP_HY3_IN and cfg.startswith("hy3"):
                    continue
                m = metric_of(env, s.get("scores") or {})
                if m is None:
                    continue
                scored[(env, cfg)] += 1
                smeta = s.get("metadata") or {}
                md = (smeta.get("scenario") or {}).get("metadata") or {}
                if not md.get("frame"):
                    md = smeta
                if md.get("frame") == "permissive":
                    acc[(env, cfg)].append(float(m))
    return {k: float(np.mean(v)) for k, v in acc.items() if v}, scored


def mean_offdiag(per_env, envs, keep):
    n = len(envs)
    M = np.full((n, n), np.nan)
    for i, a in enumerate(envs):
        for j, b in enumerate(envs):
            M[i, j] = spearmanr(
                [per_env[a][m] for m in keep], [per_env[b][m] for m in keep]
            ).statistic
    off = [M[i, j] for i in range(n) for j in range(n) if i != j]
    return M, float(np.nanmean(off))


def most_negative(M, envs):
    best, pair = np.inf, None
    for i in range(len(envs)):
        for j in range(i + 1, len(envs)):
            if M[i, j] < best:
                best, pair = M[i, j], (envs[i], envs[j])
    return pair, float(best)


def show(label, per_env, envs, keep, matrix=False):
    M, mo = mean_offdiag(per_env, envs, keep)
    pair, val = most_negative(M, envs)
    print(f"\n  {label}")
    print(
        f"    n_models={len(keep)}   mean off-diagonal rho = {mo:+.4f}   "
        f"most negative = {pair[0]}-{pair[1]} {val:+.4f}"
    )
    if matrix:
        print("    " + "".join(f"{e[:9]:>11}" for e in envs))
        for i, a in enumerate(envs):
            row = "".join(
                ("        .  " if i == j else f"{M[i, j]:>+11.4f}") for j in range(len(envs))
            )
            print(f"    {a[:9]:<9}" + row)
    return mo


def main() -> None:
    sys.path.insert(0, str(XT))
    rs2 = _load("rs2_mod", XT / "ranking_stability_v2.py")
    load_mod = _load("load_mod", XT / "load.py")
    df = load_mod.load_corpus(verbose=False)
    means = rs2._per_task_means(df, ranking="permissive", use_v1_metric=True)
    frozen = {e: {m: float(means[e][m]) for m in FROZEN} for e in ENVS5}

    print("=" * 96)
    print("REPRODUCTION GATE (frozen cohort, 5 envs, v1 estimator)")
    print("=" * 96)
    _, mo_frozen = mean_offdiag(frozen, ENVS5, FROZEN)
    print(f"  computed {mo_frozen:+.4f}   published {PUBLISHED_V1_MEAN:+.4f}", end="   ")
    if abs(mo_frozen - PUBLISHED_V1_MEAN) > 1e-3:
        raise SystemExit("MISMATCH -- frozen reproduction failed, stopping")
    print("OK")

    exp, scored = expanded_means()
    all_cfgs = list(T1_CONFIGS) + list(T2_CONFIGS)
    gated_out = {}
    for c in all_cfgs:
        fails = [e for e in ENVS5 if scored.get((e, c), 0) / EXPECTED[e] < GATE]
        if fails:
            gated_out[c] = fails

    print("\n  section-2 completion gate (full-coverage rule):")
    for c in all_cfgs:
        pcts = {e: 100 * scored.get((e, c), 0) / EXPECTED[e] for e in ENVS5}
        status = "EXCLUDED " + str(gated_out[c]) if c in gated_out else "eligible"
        print(f"    {c:<10} {status:<28} " + " ".join(f"{e[:4]}={pcts[e]:.0f}%" for e in ENVS5))

    eligible = [c for c in all_cfgs if c not in gated_out and all((e, c) in exp for e in ENVS5)]

    print("\n" + "=" * 96)
    print("CROSS-TASK RANK CORRELATION -- frozen vs expanded")
    print("=" * 96)
    print("\n  NOTE: the frozen cohort cannot be reproduced (Grok 4 deprecated), so the")
    print("  frozen column is the committed log and expanded configs are appended to it.")

    def with_cfgs(cfgs, label, matrix=False):
        cfgs = [c for c in cfgs if c in eligible]
        if not cfgs:
            return None
        per = {e: dict(frozen[e]) for e in ENVS5}
        keep = list(FROZEN)
        for c in cfgs:
            for e in ENVS5:
                per[e][c] = exp[(e, c)]
            keep.append(c)
        return show(label, per, ENVS5, keep, matrix=matrix)

    show("FROZEN 6 models (published)", frozen, ENVS5, FROZEN, matrix=True)
    with_cfgs(list(T2_CONFIGS), "+ Tier 2 only (mistral, ling)", matrix=True)
    with_cfgs(
        [c for c in T1_CONFIGS if c.endswith("_on")] + list(T2_CONFIGS), "+ Tier 1 ON arms + Tier 2"
    )
    with_cfgs(
        [c for c in T1_CONFIGS if c.endswith("_off")] + list(T2_CONFIGS),
        "+ Tier 1 OFF arms + Tier 2",
    )
    with_cfgs(eligible, "+ ALL eligible (Tier 1 + Tier 2; arms are near-duplicates)", matrix=True)

    print("\n  per-config permissive-frame means (5-env set):")
    print(f"    {'config':<10}" + "".join(f"{e[:9]:>11}" for e in ENVS5))
    for c in all_cfgs:
        if not all((e, c) in exp for e in ENVS5):
            continue
        mark = "" if c in eligible else "  (gated out)"
        print(f"    {c:<10}" + "".join(f"{exp[(e, c)]:>11.3f}" for e in ENVS5) + mark)


if __name__ == "__main__":
    main()
