"""Model x task axis-sensitivity OLS for assertive/commissive taxonomy.

For each paper model and each of the six paper tasks, fit:

    manipulation_metric ~ 1 + frame_code + incentive_code + difficulty_code

using ordered axis codes:
  frame: prohibitive=0, pro_social=1, minimal=2, selfish=3, permissive=4
  incentive: none=0, moderate=1, high=2
  difficulty: low=0, medium=1, high=2

Then compute:
    Delta_D = |beta_D| - max(|beta_F|, |beta_I|)

This script writes:
  paper/figures/model_task_axis_sensitivity.md
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[4]
CSV_PATH = ROOT / "paper/cross_task/data/results.csv"
OUT_MD = ROOT / "paper/figures/model_task_axis_sensitivity.md"

PAPER_MODELS = (
    "Claude-Opus-4.7",
    "GPT-5.5",
    "Gemini-3.1-Pro",
    "Grok-4",
    "Llama-3.3-70B",
    "DeepSeek-V4-Pro",
)
DISPLAY = {
    "Claude-Opus-4.7": "Claude Opus 4.7",
    "GPT-5.5": "GPT-5.5",
    "Gemini-3.1-Pro": "Gemini 3.1 Pro",
    "Grok-4": "Grok 4",
    "Llama-3.3-70B": "Llama 3.3 70B",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
}
TASKS = ("bargaining", "debate", "village", "sales", "committee", "inbox")
TASK_TYPE = {
    "bargaining": "commissive",
    "village": "commissive",
    "inbox": "commissive",
    "debate": "assertive",
    "sales": "assertive",
    "committee": "assertive",
}
FRAME_CODE = {"prohibitive": 0, "pro_social": 1, "minimal": 2, "selfish": 3, "permissive": 4}
INCENT_CODE = {"none": 0, "moderate": 1, "high": 2}
DIFF_CODE = {"low": 0, "medium": 1, "high": 2}


def load_rows() -> dict[tuple[str, str], list[dict[str, float]]]:
    by_cell: dict[tuple[str, str], list[dict[str, float]]] = defaultdict(list)
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            model = r.get("model")
            task = r.get("task")
            if model not in PAPER_MODELS or task not in TASKS:
                continue
            if r.get("variant", "").endswith("_pilot"):
                continue

            y = r.get("manipulation_metric", "")
            if y in ("", None):
                continue
            try:
                y_val = float(y)
            except ValueError:
                continue

            frame = r.get("frame")
            incent = r.get("incentive")
            diff = r.get("difficulty")
            if frame not in FRAME_CODE or incent not in INCENT_CODE or diff not in DIFF_CODE:
                continue

            by_cell[(model, task)].append(
                {
                    "frame": float(FRAME_CODE[frame]),
                    "incentive": float(INCENT_CODE[incent]),
                    "difficulty": float(DIFF_CODE[diff]),
                    "y": y_val,
                }
            )
    return by_cell


def ols_coefficients(rows: list[dict[str, float]]):
    n = len(rows)
    X = np.ones((n, 4), dtype=float)
    y = np.empty(n, dtype=float)
    for i, r in enumerate(rows):
        X[i, 1] = r["frame"]
        X[i, 2] = r["incentive"]
        X[i, 3] = r["difficulty"]
        y[i] = r["y"]

    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta
    dof = n - X.shape[1]
    sigma2 = (resid @ resid) / dof
    cov = sigma2 * xtx_inv
    se = np.sqrt(np.diag(cov))
    return beta, se


def simple_ols(y: np.ndarray, x_assertive: np.ndarray):
    X = np.column_stack([np.ones(len(y)), x_assertive])
    xtx_inv = np.linalg.inv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta
    n, k = X.shape
    sigma2 = (resid @ resid) / (n - k)
    cov = sigma2 * xtx_inv
    se = np.sqrt(np.diag(cov))
    t = beta / se
    p = 2 * (1 - stats.t.cdf(np.abs(t), df=n - k))
    return beta, se, t, p, resid, X


def task_cluster_robust(resid: np.ndarray, X: np.ndarray, task_labels: np.ndarray):
    n, k = X.shape
    groups = sorted(set(task_labels.tolist()))
    g = len(groups)
    xtx_inv = np.linalg.inv(X.T @ X)
    meat = np.zeros((k, k), dtype=float)
    for task in groups:
        idx = np.where(task_labels == task)[0]
        xg = X[idx, :]
        ug = resid[idx]
        score = xg.T @ ug
        meat += np.outer(score, score)
    cov = xtx_inv @ meat @ xtx_inv
    cov *= (g / (g - 1)) * ((n - 1) / (n - k))  # CR1 small-sample correction
    se = np.sqrt(np.diag(cov))
    return cov, se


def main():
    by_cell = load_rows()
    expected = len(PAPER_MODELS) * len(TASKS)
    if len(by_cell) != expected:
        raise RuntimeError(f"Expected {expected} model-task cells, found {len(by_cell)}.")

    rows = []
    for task in TASKS:
        for model in PAPER_MODELS:
            cell = by_cell[(model, task)]
            beta, se = ols_coefficients(cell)
            b_f, b_i, b_d = float(beta[1]), float(beta[2]), float(beta[3])
            delta_d = abs(b_d) - max(abs(b_f), abs(b_i))
            rows.append(
                {
                    "model": model,
                    "task": task,
                    "task_type": TASK_TYPE[task],
                    "n": len(cell),
                    "beta_f": b_f,
                    "beta_i": b_i,
                    "beta_d": b_d,
                    "se_f": float(se[1]),
                    "se_i": float(se[2]),
                    "se_d": float(se[3]),
                    "delta_d": float(delta_d),
                }
            )

    assertive = [r for r in rows if r["task_type"] == "assertive"]
    commissive = [r for r in rows if r["task_type"] == "commissive"]

    def summary(block: list[dict]):
        vals = np.array([r["delta_d"] for r in block], dtype=float)
        return {
            "n": len(block),
            "gt0": int((vals > 0).sum()),
            "lt0": int((vals < 0).sum()),
            "mean": float(vals.mean()),
            "median": float(np.median(vals)),
        }

    s_assertive = summary(assertive)
    s_commissive = summary(commissive)

    y = np.array([r["delta_d"] for r in rows], dtype=float)
    x = np.array([1.0 if r["task_type"] == "assertive" else 0.0 for r in rows], dtype=float)
    beta, se, t, p, resid, X = simple_ols(y, x)

    task_labels = np.array([r["task"] for r in rows], dtype=object)
    cov_cl, se_cl = task_cluster_robust(resid, X, task_labels)
    t_cl = beta / se_cl
    p_cl = 2 * (1 - stats.t.cdf(np.abs(t_cl), df=len(set(task_labels.tolist())) - 1))

    inbox = [r for r in rows if r["task"] == "inbox"]
    inbox_vals = np.array([r["delta_d"] for r in inbox], dtype=float)

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    md = []
    md.append("# Model x Environment Axis-Sensitivity OLS\n")
    md.append("## Specification\n")
    md.append(
        "For each model-environment pair, fit `manipulation_metric ~ frame + incentive + difficulty` "
        "with ordered integer coding:\n"
        "- frame: prohibitive=0, pro_social=1, minimal=2, selfish=3, permissive=4\n"
        "- incentive: none=0, moderate=1, high=2\n"
        "- difficulty: low=0, medium=1, high=2\n"
    )
    md.append(
        "Difficulty-advantage score per row:\n"
        "`Delta_D = |beta_difficulty| - max(|beta_frame|, |beta_incentive|)`\n"
    )

    md.append("## 36-row Summary\n")
    md.append(
        f"- Assertive rows (`debate`, `sales`, `committee`): {s_assertive['gt0']}/{s_assertive['n']} have `Delta_D > 0`; "
        f"mean={s_assertive['mean']:+.3f}, median={s_assertive['median']:+.3f}"
    )
    md.append(
        f"- Commissive rows (`bargaining`, `village`, `inbox`): {s_commissive['lt0']}/{s_commissive['n']} have `Delta_D < 0`; "
        f"mean={s_commissive['mean']:+.3f}, median={s_commissive['median']:+.3f}"
    )
    md.append(
        f"- OLS `Delta_D ~ 1 + assertive` coefficient on `assertive`: {beta[1]:+.3f} "
        f"(i.i.d. SE={se[1]:.3f}, t={t[1]:+.3f}, p={p[1]:.3f})"
    )
    md.append(
        f"- Task-cluster-robust SE (6 environment clusters) on `assertive`: "
        f"SE={se_cl[1]:.3f}, t={t_cl[1]:+.3f}, p={p_cl[1]:.3f}"
    )
    md.append(
        f"- Held-out T6 (`inbox`) check: {int((inbox_vals < 0).sum())}/{len(inbox_vals)} rows have `Delta_D < 0`; "
        f"mean={inbox_vals.mean():+.3f}, median={np.median(inbox_vals):+.3f}\n"
    )

    md.append("## Per Model x Environment Coefficients\n")
    md.append("| Task | Type | Model | n | beta_F | beta_I | beta_D | Delta_D |")
    md.append("|---|---|---|---:|---:|---:|---:|---:|")
    for r in rows:
        md.append(
            f"| {r['task']} | {r['task_type']} | {DISPLAY[r['model']]} | {r['n']} | "
            f"{r['beta_f']:+.4f} | {r['beta_i']:+.4f} | {r['beta_d']:+.4f} | {r['delta_d']:+.4f} |"
        )

    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
