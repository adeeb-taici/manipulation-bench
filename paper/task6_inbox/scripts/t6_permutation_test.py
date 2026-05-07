"""T6 permutation test for the assertive/commissive partition claim (paper §4.3).

Replaces the post-hoc joint-probability calculation with a held-out-only
permutation test. For each iteration, axis labels {frame, incentive,
difficulty} are permuted independently within each model row of the
abs-slope table; we then check the three pre-registered conditions:

  cond1: mean(|frame|) / mean(|difficulty|) >= 2
  cond2: at least 4 of 6 models have |frame| > |difficulty|
  cond3: mean(|incentive|) < 0.10

Per-cell bootstrap: also resample scenarios within each (model, axis,
level) cell with replacement, recompute slopes, and check the same
conditions.

Inputs are taken from the canonical prereg JSON at
paper/task6_inbox/analysis/prereg_results.json (matches Table 5 in the paper).
Bootstrap reads the eval log via inspect_ai.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
PREREG = ROOT / "paper/task6_inbox/analysis/prereg_results.json"
OUT_MD = ROOT / "paper/figures/t6_permutation_test.md"

MODELS = ("claude", "gpt5", "gemini", "grok", "llama", "deepseek")
MODEL_DISPLAY = {
    "claude": "Claude Opus 4.7",
    "gpt5": "GPT-5.5",
    "gemini": "Gemini 3.1 Pro",
    "grok": "Grok 4",
    "llama": "Llama 3.3 70B",
    "deepseek": "DeepSeek V4 Pro",
}

N_PERM = 100_000
N_BOOT = 10_000
SEED = 42


def load_abs_slopes() -> np.ndarray:
    d = json.loads(PREREG.read_text())
    rows = []
    for m in MODELS:
        s = d["sensitivity_slopes"][m]
        rows.append([abs(s["frame_slope"]), abs(s["incentive_slope"]), abs(s["difficulty_slope"])])
    return np.asarray(rows)  # shape (6, 3): cols = frame, incentive, difficulty


def conditions(M: np.ndarray) -> tuple[bool, bool, bool]:
    """M is (n_models, 3) with columns [frame, incentive, difficulty]."""
    frame = M[:, 0]
    incent = M[:, 1]
    diff = M[:, 2]
    cond1 = (frame.mean() / diff.mean()) >= 2.0 if diff.mean() > 0 else False
    cond2 = int((frame > diff).sum()) >= 4
    cond3 = incent.mean() < 0.10
    return cond1, cond2, cond3


def permutation_test(M: np.ndarray, n: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    n_models = M.shape[0]
    c1 = c2 = c3 = joint = 0
    for _ in range(n):
        perm = np.empty_like(M)
        for i in range(n_models):
            perm[i] = rng.permutation(M[i])
        a, b, c = conditions(perm)
        c1 += a
        c2 += b
        c3 += c
        if a and b and c:
            joint += 1
    return {
        "n": n,
        "p_joint": joint / n,
        "p_cond1": c1 / n,
        "p_cond2": c2 / n,
        "p_cond3": c3 / n,
    }


def load_per_cell_rollouts() -> dict | None:
    """Returns dict[(model, axis, level)] -> list[float] of suppression rates,
    or None if the eval log can't be loaded."""
    try:
        from inspect_ai.log import read_eval_log
    except Exception:
        return None
    log_path = ROOT / "paper/task6_inbox/eval_log.eval"
    if not log_path.exists():
        return None
    log = read_eval_log(str(log_path))
    cells: dict = defaultdict(list)
    for sample in log.samples or []:
        md = (sample.metadata or {})
        model = md.get("model")
        frame = md.get("frame")
        incent = md.get("incentive")
        diff = md.get("difficulty")
        if not model or model not in MODELS:
            continue
        score = None
        if sample.scores:
            for s in sample.scores.values():
                v = s.value
                if isinstance(v, dict) and "suppression_rate" in v:
                    sr = v["suppression_rate"]
                    if isinstance(sr, (int, float)):
                        score = float(sr)
                        break
        if score is None:
            continue
        if frame:
            cells[(model, "frame", frame)].append(score)
        if incent:
            cells[(model, "incentive", incent)].append(score)
        if diff:
            cells[(model, "difficulty", diff)].append(score)
    return dict(cells) if cells else None


FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
INCENTIVES = ("none", "moderate", "high")
DIFFICULTIES = ("low", "medium", "high")


def slope_from_levels(values: list[float]) -> float:
    """Linear regression slope of mean per ordered level. Encodes levels as 0..k-1."""
    k = len(values)
    x = np.arange(k, dtype=float)
    y = np.asarray(values, dtype=float)
    x = x - x.mean()
    y = y - y.mean()
    denom = (x * x).sum()
    if denom == 0:
        return 0.0
    return float((x * y).sum() / denom)


def bootstrap_test(rollouts: dict, n: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    c1 = c2 = c3 = joint = 0
    cell_arrays = {k: np.asarray(v, dtype=float) for k, v in rollouts.items()}
    for _ in range(n):
        M = np.zeros((len(MODELS), 3))
        for mi, model in enumerate(MODELS):
            for axi, (axis, levels) in enumerate(
                [("frame", FRAMES), ("incentive", INCENTIVES), ("difficulty", DIFFICULTIES)]
            ):
                level_means = []
                for lvl in levels:
                    arr = cell_arrays.get((model, axis, lvl))
                    if arr is None or len(arr) == 0:
                        level_means.append(0.0)
                        continue
                    idx = rng.integers(0, len(arr), size=len(arr))
                    level_means.append(float(arr[idx].mean()))
                M[mi, axi] = abs(slope_from_levels(level_means))
        a, b, c = conditions(M)
        c1 += a
        c2 += b
        c3 += c
        if a and b and c:
            joint += 1
    return {
        "n": n,
        "p_joint": joint / n,
        "p_cond1": c1 / n,
        "p_cond2": c2 / n,
        "p_cond3": c3 / n,
    }


def main() -> None:
    M = load_abs_slopes()
    obs_cond1, obs_cond2, obs_cond3 = conditions(M)
    obs_stats = {
        "frame_mean": float(M[:, 0].mean()),
        "incentive_mean": float(M[:, 1].mean()),
        "difficulty_mean": float(M[:, 2].mean()),
        "frame_over_difficulty_ratio": float(M[:, 0].mean() / M[:, 2].mean()),
        "n_models_frame_gt_difficulty": int((M[:, 0] > M[:, 2]).sum()),
    }

    perm = permutation_test(M, N_PERM, SEED)

    rollouts = load_per_cell_rollouts()
    boot = None
    if rollouts is not None:
        boot = bootstrap_test(rollouts, N_BOOT, SEED)

    # Markdown report
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# T6 Inbox Triage — Permutation Test for the Assertive/Commissive Partition\n")
    lines.append(
        "## Methodology\n\n"
        "The paper's §4.3 partition (assertive vs. commissive manipulation) was constructed by "
        "inspecting T1–T5 outcomes; T6 was pre-registered as a held-out test. The original "
        "joint-probability calculation (~0.016, or 0.011 with T6) treated the partition as if it "
        "were specified ex ante and is therefore methodologically problematic. This note replaces "
        "that calculation with a permutation-based p-value computed *over T6 alone*.\n\n"
        "**Test statistics (pre-registered conditions, evaluated on the absolute slopes from "
        "Table 5):**\n"
        "- `cond1`: aggregate frame dominance over difficulty — `mean(|frame|) / mean(|difficulty|) >= 2`\n"
        "- `cond2`: per-model frame dominance — at least 4 of 6 models have `|frame| > |difficulty|`\n"
        "- `cond3`: incentive inertness — `mean(|incentive|) < 0.10`\n\n"
        "**Null model.** For each of N permutations, axis labels {frame, incentive, difficulty} "
        "are permuted *independently within each model row* of the absolute-slope table; the same "
        "three conditions are then evaluated. The empirical p-value is the fraction of "
        "permutations satisfying all three jointly. Random seed: `np.random.default_rng(42)`.\n\n"
        "**Bootstrap variant.** Where the eval log is available, we additionally resample "
        "scenarios with replacement within each (model, axis, level) cell, recompute per-axis "
        "slopes, and re-evaluate the same three conditions. This addresses sampling variability "
        "in the slope estimates themselves rather than only label assignment.\n"
    )

    lines.append("## Observed Test Statistics (real data)\n")
    lines.append("| Model | |Frame| | |Incentive| | |Difficulty| |")
    lines.append("|---|---:|---:|---:|")
    for i, m in enumerate(MODELS):
        lines.append(
            f"| {MODEL_DISPLAY[m]} | {M[i,0]:.3f} | {M[i,1]:.3f} | {M[i,2]:.3f} |"
        )
    lines.append("")
    lines.append(f"- mean(|frame|)      = {obs_stats['frame_mean']:.4f}")
    lines.append(f"- mean(|incentive|)  = {obs_stats['incentive_mean']:.4f}")
    lines.append(f"- mean(|difficulty|) = {obs_stats['difficulty_mean']:.4f}")
    lines.append(f"- frame/difficulty ratio = {obs_stats['frame_over_difficulty_ratio']:.3f}")
    lines.append(
        f"- # models with |frame| > |difficulty| = {obs_stats['n_models_frame_gt_difficulty']}/6"
    )
    lines.append(
        f"- cond1 satisfied: {obs_cond1}; cond2 satisfied: {obs_cond2}; cond3 satisfied: {obs_cond3}\n"
    )

    lines.append("## Permutation P-Values\n")
    lines.append(f"- N = {perm['n']:,} permutations, seed = {SEED}")
    lines.append(f"- **Joint p-value (cond1 ∧ cond2 ∧ cond3): {perm['p_joint']:.5f}**")
    lines.append(f"- Marginal p(cond1, frame/difficulty ≥ 2×): {perm['p_cond1']:.5f}")
    lines.append(f"- Marginal p(cond2, ≥4/6 models |frame|>|diff|): {perm['p_cond2']:.5f}")
    lines.append(f"- Marginal p(cond3, mean |incentive| < 0.10): {perm['p_cond3']:.5f}\n")

    if boot is not None:
        lines.append("## Bootstrap P-Values (per-cell rollout resampling)\n")
        lines.append(f"- N = {boot['n']:,} bootstrap iterations, seed = {SEED}")
        lines.append(f"- Joint p-value: {boot['p_joint']:.5f}")
        lines.append(f"- Marginal p(cond1): {boot['p_cond1']:.5f}")
        lines.append(f"- Marginal p(cond2): {boot['p_cond2']:.5f}")
        lines.append(f"- Marginal p(cond3): {boot['p_cond3']:.5f}\n")
        lines.append(
            "Note: the bootstrap is *not* a null-hypothesis test — it characterizes the "
            "sampling distribution of the test statistics under the observed data. A small "
            "bootstrap 'p' here reflects that the partition holds robustly under resampling, not "
            "that it is unlikely under chance. The permutation p-value above is the inferential "
            "quantity.\n"
        )
    else:
        lines.append(
            "## Bootstrap P-Values\n\nEval log not available in this run; bootstrap skipped.\n"
        )

    lines.append("## Caveats\n")
    lines.append(
        "- The within-row permutation null assumes the three axes are exchangeable for a given "
        "model. This is a reasonable null for 'is the assertive/commissive partition predicted "
        "by T6?' but does not test whether the *direction* of frame > difficulty is "
        "exogenously meaningful.\n"
        "- The slopes are linear-regression coefficients over ordered levels (5 frame levels, 3 "
        "incentive, 3 difficulty); permuting cells within a row is sensible only because we "
        "compare *absolute* slopes.\n"
        "- The conditions were specified before looking at T6 outcomes (they restate the "
        "assertive/commissive partition derived from T1–T5). Within T6 itself this is a single "
        "pre-registered three-part test; no multiple-comparisons correction is needed.\n"
    )

    OUT_MD.write_text("\n".join(lines) + "\n")

    print(
        f"Empirical p = {perm['p_joint']:.4f} over N={perm['n']:,} permutations. "
        f"Conditions cond1/cond2/cond3 marginal p-values: "
        f"{perm['p_cond1']:.4f} / {perm['p_cond2']:.4f} / {perm['p_cond3']:.4f}."
    )
    if boot is not None:
        print(
            f"Bootstrap joint p = {boot['p_joint']:.4f} over N={boot['n']:,} iterations. "
            f"Marginals: {boot['p_cond1']:.4f} / {boot['p_cond2']:.4f} / {boot['p_cond3']:.4f}."
        )
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
