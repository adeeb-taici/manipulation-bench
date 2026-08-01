"""Analyze the T5/T6 frame-wording sweep against paper/frame_wording/CRITERIA.md.

Frame slope is recomputed per version on the swept cell with the published
per-task estimator. Incentive and difficulty slopes are the published
full-design values -- unchanged by construction, since no incentive or
difficulty text was touched -- and serve as the dominance anchors.

T5: per-sample scale correction (max rating <= 10 => x2) applied before any
cross-model quantity; scale adherence is also reported per version.

Run: python paper/frame_wording/scripts/analyze_frame_wording.py
"""

from __future__ import annotations

import json
import statistics
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LOGS = Path("C:/Users/zaman/workplace/manipulation-bench/logs/frame_wording")

FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
VERSIONS = (1, 2, 3)
MODELS = ("claude", "gpt55", "gemini", "grok43", "llama", "deepseek")

# Published full-design aggregate mean |slope| per axis (T5 scale-corrected).
ANCHORS = {
    "committee": {"incentive": 0.1822, "difficulty": 0.6151},
    "inbox": {"incentive": 0.0785, "difficulty": 0.0169},
}
PUBLISHED_FRAME = {"committee": 0.3270, "inbox": 0.1038}
PUBLISHED_DOMINANT = {"committee": "difficulty", "inbox": "frame"}


def ols(ys):
    n = len(ys)
    if n < 2 or any(y is None for y in ys):
        return float("nan")
    xs = list(range(n))
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else float("nan")


def load(env):
    """Union every log in the directory, de-duplicated by sample id.

    Committee's DeepSeek arm was re-run after adding tool_choice_strategy="auto"
    (the documented V4 Pro 'Thinking mode does not support this tool_choice'
    quirk), so the directory holds both the failed originals and the successful
    re-run. A usable sample always wins over an errored one with the same id;
    without this the same 45 scenarios would be counted twice.
    """
    rows, errs = [], Counter()
    d = LOGS / env
    merged: dict[str, dict] = {}
    for f in sorted(d.glob("*.eval"), key=lambda p: p.stat().st_mtime):
        z = zipfile.ZipFile(f)
        for nm in z.namelist():
            if not nm.startswith("samples/"):
                continue
            s = json.loads(z.read(nm))
            key = f"{s.get('id')}|{s.get('epoch')}"
            if key in merged and s.get("error") and not merged[key].get("error"):
                continue
            merged[key] = s
    for s in merged.values():
        if True:
            smeta = s.get("metadata") or {}
            md = (smeta.get("scenario") or {}).get("metadata") or smeta
            model = md.get("model") or (md.get("model_mapping") or {}).get("agent_1")
            ver = md.get("frame_version")
            if s.get("error"):
                errs[(ver, model)] += 1
                continue
            sc = s.get("scores") or {}
            if env == "inbox":
                v = (sc.get("inbox_triage") or {}).get("value")
                metric = v.get("suppression_rate") if isinstance(v, dict) else None
                scale = None
            else:
                v = (sc.get("initial_rating_bias") or {}).get("value")
                metric = v.get("initial_bias") if isinstance(v, dict) else None
                gs = (
                    ((s.get("store") or {}).get("InteractionState:scenario") or {}).get("metadata")
                    or {}
                ).get("game_state") or {}
                ip = gs.get("interested_party_name")
                r = (gs.get("initial_ratings") or {}).get(ip) or {}
                vals = [int(x) for c in r.values() if isinstance(c, dict) for x in c.values()]
                scale = (10 if max(vals) <= 10 else 20) if vals else None
                if metric is not None and scale == 10:
                    metric = float(metric) * 2
            if metric is None:
                errs[(ver, model)] += 1
                continue
            rows.append(
                {
                    "model": model,
                    "frame": md.get("frame"),
                    "version": ver,
                    "metric": float(metric),
                    "scale": scale,
                }
            )
    return rows, errs


def frame_slope(rows, env, version):
    """Mean |frame slope| across models, published estimator."""
    per = []
    for m in MODELS:
        sub = [r for r in rows if r["model"] == m and r["version"] == version]
        if not sub:
            continue
        sd = (statistics.pstdev([r["metric"] for r in sub]) or 1.0) if env == "committee" else 1.0
        means = []
        for f in FRAMES:
            v = [r["metric"] for r in sub if r["frame"] == f]
            means.append(sum(v) / len(v) / sd if v else None)
        s = ols(means)
        if s == s:
            per.append(abs(s))
    return (statistics.mean(per) if per else float("nan")), len(per)


def main() -> None:
    out = {}
    for env in ("inbox", "committee"):
        rows, errs = load(env)
        print("=" * 96)
        print(f"{env.upper()}  --  frame-wording sweep")
        print("=" * 96)

        n_err = sum(errs.values())
        print(f"  usable {len(rows)}   unusable {n_err}")
        if n_err:
            print("  attrition per arm (version, model):")
            per_v = Counter()
            for (v, m), c in sorted(errs.items(), key=lambda kv: (-kv[1],)):
                per_v[v] += c
                print(f"    v{v} {m:<10} {c}")
            print(f"    per-version totals: {dict(sorted(per_v.items()))}")
        usable_v = Counter(r["version"] for r in rows)
        print(f"  usable per version: {dict(sorted(usable_v.items()))}")

        anch = ANCHORS[env]
        print(
            f"\n  {'version':<10}{'frame slope':>14}{'top-vs-2nd':>13}"
            f"{'dominant':>13}{'matches published':>20}"
        )
        res = []
        for v in VERSIONS:
            fs, nmod = frame_slope(rows, env, v)
            axes = {"frame": fs, "incentive": anch["incentive"], "difficulty": anch["difficulty"]}
            order = sorted(axes, key=lambda a: -axes[a])
            ratio = axes[order[0]] / axes[order[1]] if axes[order[1]] else float("inf")
            ok = order[0] == PUBLISHED_DOMINANT[env]
            res.append(
                {
                    "version": v,
                    "frame_slope": fs,
                    "ratio": ratio,
                    "dominant": order[0],
                    "match": ok,
                    "n_models": nmod,
                }
            )
            print(f"  v{v:<9}{fs:>14.4f}{ratio:>13.2f}{order[0]:>13}{('OK' if ok else 'FLIP'):>20}")
        vals = [r["frame_slope"] for r in res if r["frame_slope"] == r["frame_slope"]]
        if vals:
            spread = (max(vals) - min(vals)) / statistics.mean(vals) * 100
            print(
                f"\n  frame-slope spread across versions: {spread:.1f}% of mean "
                f"(min {min(vals):.4f}, max {max(vals):.4f})"
            )
            print(f"  published full-design frame slope (anchor): {PUBLISHED_FRAME[env]:.4f}")

        if env == "committee":
            print("\n  scale adherence per version (per-sample max test):")
            for v in VERSIONS:
                sub = [r for r in rows if r["version"] == v and r["scale"]]
                if not sub:
                    continue
                n10 = sum(1 for r in sub if r["scale"] == 10)
                print(f"    v{v}  n={len(sub):<4} on 0-10: {n10:<4} ({100 * n10 / len(sub):.1f}%)")

        if env == "inbox":
            print("\n  minimal-level negative control (three byte-identical arms):")
            for v in VERSIONS:
                sub = [r["metric"] for r in rows if r["version"] == v and r["frame"] == "minimal"]
                if sub:
                    print(f"    v{v}  mean {statistics.mean(sub):+.4f}  n={len(sub)}")
        out[env] = {
            "results": res,
            "attrition": {f"v{k[0]}_{k[1]}": c for k, c in errs.items()},
            "usable_per_version": dict(usable_v),
        }
        print()

    json.dump(
        out,
        open(REPO / "paper/frame_wording/results.json", "w", encoding="utf-8"),
        indent=2,
        default=float,
    )


if __name__ == "__main__":
    main()
