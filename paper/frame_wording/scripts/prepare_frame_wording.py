"""Cell selection + cost/wall-clock estimate for the T5/T6 frame-wording check.

Follows the Appendix F precedent (paper/paraphrase_robustness):
  * pick the (incentive, difficulty) cell whose |frame slope| is closest to the
    per-task mean, and hold it fixed for the sweep
  * vary only the frame-axis wording; everything else byte-identical

Coverage rationale: the registered question is whether the FRAME SLOPE and the
resulting dominance ordering move under rewording. The frame slope needs all five
frame levels at a fixed (incentive, difficulty) slice, so that slice is what runs.
The incentive and difficulty slopes are NOT recomputed -- they are unchanged by
construction, since no incentive or difficulty text is touched, and the published
full-design values are used as the comparison anchors.

Run: python paper/frame_wording/scripts/prepare_frame_wording.py
"""

from __future__ import annotations

import importlib.util
import json
import statistics
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "paper/frame_wording"

MODELS = [
    "Claude-Opus-4.7",
    "GPT-5.5",
    "Gemini-3.1-Pro",
    "Grok-4",
    "Llama-3.3-70B",
    "DeepSeek-V4-Pro",
]
FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
INCS = ("none", "moderate", "high")
DIFFS = ("low", "medium", "high")
ALIAS = {
    "claude": "Claude-Opus-4.7",
    "gpt5": "GPT-5.5",
    "gpt55": "GPT-5.5",
    "gemini": "Gemini-3.1-Pro",
    "grok": "Grok-4",
    "llama": "Llama-3.3-70B",
    "deepseek": "DeepSeek-V4-Pro",
}


def ols(ys):
    ys = [y for y in ys]
    n = len(ys)
    if n < 2 or any(y is None for y in ys):
        return float("nan")
    xs = list(range(n))
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else float("nan")


def t6_rows():
    p = REPO / "paper/task6_inbox/scripts/task6_prereg_analysis.py"
    spec = importlib.util.spec_from_file_location("t6_prep", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    out = []
    for r in mod.load_rows():
        out.append(
            {
                "model": ALIAS.get(r["model"], r["model"]),
                "frame": r["frame"],
                "incentive": r["incentive"],
                "difficulty": r["difficulty"],
                # task6_prereg_analysis.load_rows names suppression_rate "sr"
                "metric": r["sr"],
            }
        )
    return out


def t5_rows():
    z = zipfile.ZipFile(REPO / "paper/task5_committee/eval_log.eval")
    out = []
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
        out.append(
            {
                "model": ALIAS.get(md.get("interested_model_label")),
                "frame": md.get("frame"),
                "incentive": md.get("incentive"),
                "difficulty": md.get("difficulty"),
                "metric": float(v["initial_bias"]) * (2 if (vals and max(vals) <= 10) else 1),
            }
        )
    return out


def pick_cell(rows, standardize: bool):
    """Cell whose |frame slope| is closest to the overall mean |frame slope|."""

    def frame_slope(sub, sd):
        means = []
        for f in FRAMES:
            v = [r["metric"] for r in sub if r["frame"] == f]
            means.append(sum(v) / len(v) / sd if v else None)
        return ols(means)

    per_model_sd = {}
    for m in MODELS:
        vals = [r["metric"] for r in rows if r["model"] == m]
        per_model_sd[m] = (statistics.pstdev(vals) or 1.0) if standardize else 1.0

    overall = statistics.mean(
        [
            abs(frame_slope([r for r in rows if r["model"] == m], per_model_sd[m]))
            for m in MODELS
            if any(r["model"] == m for r in rows)
        ]
    )

    table = []
    for inc in INCS:
        for dif in DIFFS:
            slopes = []
            for m in MODELS:
                sub = [
                    r
                    for r in rows
                    if r["model"] == m and r["incentive"] == inc and r["difficulty"] == dif
                ]
                if sub:
                    slopes.append(abs(frame_slope(sub, per_model_sd[m])))
            if not slopes:
                continue
            avg = statistics.mean(slopes)
            table.append(
                {
                    "incentive": inc,
                    "difficulty": dif,
                    "abs_avg_frame_slope": avg,
                    "dist": abs(avg - overall),
                }
            )
    table.sort(key=lambda r: r["dist"])
    return overall, table


# ---- cost model: measured per-scenario tokens (paper/expanded_roster/cost_model.py)
UT_TOK = {"committee": (7956, 2887), "inbox": (2681, 3786)}
PINNED = {
    "committee": [
        ("claude-haiku-4.5", 8512, 922, 1.00, 5.00),
        ("deepseek-chat", 6900, 823, 0.20, 0.80),
        ("gemini-3-flash", 6721, 708, 0.50, 3.00),
        ("gpt-5-mini", 6587, 3560, 0.25, 2.00),
    ],
    "inbox": [],
}
# $/M in,out -- OpenRouter catalogue, to be re-verified at launch
ROSTER = [
    ("Claude Opus 4.7", "anthropic/claude-opus-4.7", 5.00, 25.00),
    ("GPT-5.5", "openai/gpt-5.5-20260423", 1.25, 10.00),
    ("Gemini 3.1 Pro", "google/gemini-3.1-pro-preview", 1.25, 10.00),
    ("Grok 4.3", "x-ai/grok-4.3", 3.00, 15.00),
    ("Llama 3.3 70B", "meta-llama/llama-3.3-70b-instruct", 0.10, 0.30),
    ("DeepSeek V4 Pro", "deepseek/deepseek-v4-pro", 0.28, 1.14),
]
REPS = 4
VERSIONS = 3


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sel = {}
    for env, loader, std in (("committee", t5_rows, True), ("inbox", t6_rows, False)):
        rows = [r for r in loader() if r["metric"] is not None]
        overall, table = pick_cell(rows, standardize=std)
        sel[env] = {"mean_abs_frame_slope": overall, "chosen": table[0], "per_cell_table": table}
        print("=" * 88)
        print(
            f"{env.upper()} -- representative cell selection (mean |frame slope| = {overall:.4f})"
        )
        print("=" * 88)
        for r in table[:4]:
            mark = "  <== chosen" if r is table[0] else ""
            print(
                f"  incentive={r['incentive']:<9} difficulty={r['difficulty']:<7}"
                f" |frame slope|={r['abs_avg_frame_slope']:.4f}  dist={r['dist']:.4f}{mark}"
            )
        print()

    json.dump(sel, open(OUT / "cell_selection.json", "w", encoding="utf-8"), indent=2)

    print("=" * 88)
    print("SCENARIO COUNT AND COST")
    print("=" * 88)
    n_per_env = len(ROSTER) * len(FRAMES) * VERSIONS * REPS
    print(
        f"  per environment: {len(ROSTER)} models x {len(FRAMES)} frames x "
        f"{VERSIONS} versions x {REPS} reps = {n_per_env}"
    )
    print(f"  two environments: {2 * n_per_env} scenarios\n")

    grand = 0.0
    for env in ("committee", "inbox"):
        ut_in, ut_out = UT_TOK[env]
        n_per_model = len(FRAMES) * VERSIONS * REPS
        pin_per_scen = sum(i * pi / 1e6 + o * po / 1e6 for _n, i, o, pi, po in PINNED[env])
        pin_total = pin_per_scen * n_per_env
        ut_total = 0.0
        for _label, _slug, pi, po in ROSTER:
            ut_total += n_per_model * (ut_in * pi / 1e6 + ut_out * po / 1e6)
        print(
            f"  {env:<10} under-test ${ut_total:>7.2f}   pinned ${pin_total:>7.2f}"
            f"   total ${ut_total + pin_total:>7.2f}"
        )
        grand += ut_total + pin_total
    print(f"  {'TOTAL':<10} {'':>19} {'':>16} ${grand:>7.2f}")

    # Wall clock from measured Tier 1 medians (s/scenario) at modest concurrency
    med = {"committee": 130.8, "inbox": 14.7}
    for conc in (8, 16):
        tot_h = sum(med[e] * n_per_env / 3600 / conc for e in ("committee", "inbox"))
        print(
            f"\n  wall clock at concurrency {conc:>2}: {tot_h:.1f} h "
            f"(committee {med['committee'] * n_per_env / 3600 / conc:.1f} h + "
            f"inbox {med['inbox'] * n_per_env / 3600 / conc:.1f} h)"
        )


if __name__ == "__main__":
    main()
