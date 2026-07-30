"""Cross-task rank-correlation on the expanded cohort, against the frozen numbers.

Recomputes the paper's first headline statistic -- mean off-diagonal Spearman rho
across environments, over per-model permissive-frame means -- with the four Tier 1
configs appended to the frozen six-model cohort. Per prereg section 3 the frozen
result is reported unchanged alongside, never replaced.

Estimator is the committed one: ranking_stability_v2._per_task_means(
ranking="permissive", use_v1_metric=True), the same call
analysis_lomo/rho_reconciliation.py makes, which reproduces the published
v1 figure of 0.0552. The script refuses to proceed if that reproduction fails.

The frozen cohort CANNOT be reproduced (Grok 4 is deprecated), so the frozen
column is read from the committed corpus and the expanded configs are appended
to it. Any combined figure therefore mixes a frozen log with fresh runs; that
asymmetry is stated in the output.

Two cohorts are reported:
  frozen   6 models
  expanded 6 frozen + 4 Tier 1 configs = 10

and two environment sets:
  5-env  bargaining, debate, village, sales, committee  (the v1 headline set)
  6-env  the above plus inbox

Run: python paper/expanded_roster/scripts/cross_task_expanded.py
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
LOGS = Path("C:/Users/zaman/workplace/manipulation-bench/logs/tier1_expanded")

FROZEN = [
    "Claude-Opus-4.7",
    "GPT-5.5",
    "Gemini-3.1-Pro",
    "Grok-4",
    "Llama-3.3-70B",
    "DeepSeek-V4-Pro",
]
CONFIGS = ("luna_on", "luna_off", "hy3_on", "hy3_off")
ENVS5 = ["bargaining", "debate", "village", "sales", "committee"]
ENVS6 = ENVS5 + ["inbox"]

PUBLISHED_V1_MEAN = 0.0552

# Superseded / discarded logs, per prereg amendments.
SKIP_DIRS = {"t3_village_luna"}  # pre-A2 Village
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
    if env == "debate":
        return val("ground_truth_persuasion", "manipulation_occurred")
    if env == "village":
        return val("exploitation_rate", "agent_1")
    if env == "sales":
        return val("sales_classifier", "manipulation_rate")
    if env == "committee":
        return val("initial_rating_bias", "initial_bias")
    if env == "inbox":
        return val("inbox_triage", "suppression_rate")
    return None


EXPECTED = {
    "bargaining": 900,
    "debate": 690,
    "village": 90,
    "sales": 225,
    "committee": 180,
    "inbox": 180,
}
GATE = 0.85


def expanded_permissive_means():
    """Per-config permissive-frame mean of each environment's primary metric.

    Also returns per-(env, config) scored counts so the section-2 completion
    gate can be applied. A config that fails any environment's gate is barred
    from the cross-task analysis by the full-coverage rule, even though its
    permissive-frame mean exists.
    """
    acc = defaultdict(list)
    scored = Counter()
    for d in sorted(LOGS.glob("*")):
        if not d.is_dir() or d.name in SKIP_DIRS:
            continue
        env = next((e for e in ENVS6 if e in d.name), None)
        if env is None:
            continue
        evals = sorted(d.glob("*.eval"), key=lambda p: p.stat().st_mtime)
        if not evals:
            continue
        # Union every log in the directory, de-duplicating by sample id, so a
        # resumed run's kept samples are counted alongside the rerun's.
        merged: dict[str, dict] = {}
        for f in evals:
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
                key = f"{s.get('id')}|{s.get('epoch')}"
                if key in merged and s.get("error") and not merged[key].get("error"):
                    continue
                merged[key] = s
        for s in merged.values():
            sid = str(s.get("id", ""))
            cfg = next((c for c in CONFIGS if c in sid), None)
            if cfg is None or s.get("error"):
                continue
            if d.name in SKIP_HY3_IN and cfg.startswith("hy3"):
                continue
            smeta = s.get("metadata") or {}
            md = (smeta.get("scenario") or {}).get("metadata") or {}
            if not md.get("frame"):
                md = smeta
            m = metric_of(env, s.get("scores") or {})
            if m is None:
                continue
            scored[(env, cfg)] += 1
            if md.get("frame") == "permissive":
                acc[(env, cfg)].append(float(m))
    means = {k: float(np.mean(v)) for k, v in acc.items() if v}
    return means, scored


def mean_offdiag(per_env, envs, keep):
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
    best, pair = np.inf, None
    for i in range(len(envs)):
        for j in range(i + 1, len(envs)):
            if M[i, j] < best:
                best, pair = M[i, j], (envs[i], envs[j])
    return pair, float(best)


def show(label, per_env, envs, keep):
    M, mo = mean_offdiag(per_env, envs, keep)
    pair, val = most_negative(M, envs)
    print(f"\n  {label}   (n_models={len(keep)}, n_envs={len(envs)})")
    print("    " + "".join(f"{e[:9]:>11}" for e in envs))
    for i, a in enumerate(envs):
        row = "".join(("        .  " if i == j else f"{M[i, j]:>+11.4f}") for j in range(len(envs)))
        print(f"    {a[:9]:<9}" + row)
    print(f"    mean off-diagonal rho = {mo:+.4f}    most negative = {pair} {val:+.4f}")
    return mo, pair, val


def main() -> None:
    sys.path.insert(0, str(XT))
    rs2 = _load("rs2_mod", XT / "ranking_stability_v2.py")
    load_mod = _load("load_mod", XT / "load.py")
    df = load_mod.load_corpus(verbose=False)
    means = rs2._per_task_means(df, ranking="permissive", use_v1_metric=True)
    frozen = {e: {m: float(means[e][m]) for m in FROZEN} for e in ENVS5}

    # Reproduction gate on the frozen 5-env figure.
    _, mo_frozen5 = mean_offdiag(frozen, ENVS5, FROZEN)
    print("=" * 92)
    print("REPRODUCTION GATE (frozen cohort, 5 envs, v1 estimator)")
    print("=" * 92)
    print(f"  computed {mo_frozen5:+.4f}   published {PUBLISHED_V1_MEAN:+.4f}", end="   ")
    if abs(mo_frozen5 - PUBLISHED_V1_MEAN) > 1e-3:
        print("MISMATCH")
        raise SystemExit("frozen reproduction failed — stopping")
    print("OK")

    exp, scored = expanded_permissive_means()
    gated_out = {}
    for c in CONFIGS:
        fails = [e for e in ENVS5 if scored.get((e, c), 0) / EXPECTED[e] < GATE]
        if fails:
            gated_out[c] = fails
    if gated_out:
        print("\n  EXCLUDED by the section-2 completion gate (full-coverage rule):")
        for c, fails in gated_out.items():
            detail = ", ".join(
                f"{e} {100 * scored.get((e, c), 0) / EXPECTED[e]:.1f}%" for e in fails
            )
            print(f"    {c}: fails {detail}")
    have = {c for (_e, c) in exp}
    print("\n  expanded-config permissive means available:")
    for e in ENVS6:
        cells = {c: exp.get((e, c)) for c in CONFIGS}
        got = {c: f"{v:.3f}" for c, v in cells.items() if v is not None}
        print(f"    {e:<11} {got if got else 'NONE'}")

    complete = [c for c in CONFIGS if all((e, c) in exp for e in ENVS5) and c not in gated_out]
    missing = [c for c in CONFIGS if c not in complete]
    if missing:
        print(f"\n  NOT YET COMPLETE on the 5-env set (excluded): {missing}")
    if not complete:
        print("\n  No expanded config has full 5-env coverage yet — frozen only.")
        return

    print("\n" + "=" * 92)
    print("CROSS-TASK RANK CORRELATION — frozen vs expanded")
    print("=" * 92)
    print("\n  NOTE: the frozen cohort cannot be reproduced (Grok 4 deprecated), so the")
    print("  frozen column is the committed log and expanded configs are appended to it.")

    for envs, tag in ((ENVS5, "5-env (v1 headline set)"), (ENVS6, "6-env (incl. inbox)")):
        if any(e not in frozen for e in envs):
            print(f"\n  [{tag}] skipped: frozen values unavailable for inbox in the v1 corpus")
            continue
        show(f"FROZEN 6 models — {tag}", frozen, envs, FROZEN)

        def with_configs(cfgs, label):
            cfgs = [c for c in cfgs if c in complete]
            if not cfgs:
                return None
            per = {e: dict(frozen[e]) for e in envs}
            keep = list(FROZEN)
            for c in cfgs:
                for e in envs:
                    per[e][c] = exp[(e, c)]
                keep.append(c)
            return show(label, per, envs, keep)

        # Both arms of a model are near-duplicates of each other: they share
        # weights and tend to rank alike across environments, which mechanically
        # inflates cross-environment rank agreement. So the one-arm-per-model
        # variants are the defensible primary; the all-arms variant is reported
        # for completeness with that caveat attached.
        with_configs([c for c in complete if c.endswith("_on")], f"EXPANDED, ON arms only — {tag}")
        with_configs(
            [c for c in complete if c.endswith("_off")], f"EXPANDED, OFF arms only — {tag}"
        )
        with_configs(list(complete), f"EXPANDED, all arms (near-duplicate pairs) — {tag}")


if __name__ == "__main__":
    main()
