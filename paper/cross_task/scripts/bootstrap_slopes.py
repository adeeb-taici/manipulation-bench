"""Bootstrap CIs for per-model per-axis slopes.

Generic helper: takes a list of (model, axis_level, metric) tuples and
returns a {model: {axis_level: ... slope CI ...}} structure.

Used by per-task analysis scripts. PREREG specifies N=1000 resamples,
seed per task (date-of-commit).

Usage:
    from experiments.bootstrap_slopes import bootstrap_slope_cis
    cis = bootstrap_slope_cis(rows, metric_key, axes_spec, seed=20260422, n=1000)
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Iterable


def _slope(values: list[float]) -> float:
    """OLS slope of ``values`` against axis index 0..n-1."""
    valid = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if len(valid) < 2:
        return float("nan")
    n = len(values)
    xs = list(range(n))
    xbar = sum(xs) / n
    ybar = sum(values) / n
    num = sum((xs[i] - xbar) * (values[i] - ybar) for i in range(n))
    den = sum((xs[i] - xbar) ** 2 for i in range(n))
    return num / den if den else float("nan")


def _safe_mean(xs: Iterable) -> float:
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float("nan") if not xs else sum(xs) / len(xs)


def bootstrap_slope_cis(
    rows: list[dict],
    metric_key: str,
    model_key: str,
    axes_spec: dict[str, tuple],
    seed: int = 20260422,
    n: int = 1000,
    ci: float = 0.95,
) -> dict:
    """Compute bootstrap CIs on per-model per-axis slopes.

    Args:
        rows: list of dicts each with at least ``model_key``, the metric
            ``metric_key``, and the axis keys named in ``axes_spec``.
        metric_key: which dict key holds the per-row metric.
        model_key: which dict key holds the per-row model id.
        axes_spec: ``{axis_name: (level1, level2, ...)}`` — the levels
            ordered by ascending index (0, 1, 2, ...).
        seed: RNG seed (per-task PREREG bootstrap seed).
        n: number of bootstrap resamples.
        ci: confidence level (0.95 → 95% CI).

    Returns:
        ``{model: {axis: {"point": float, "lo": float, "hi": float, "se": float}}}``
    """
    # Group by model for efficient resampling
    by_model = defaultdict(list)
    for r in rows:
        m = r.get(model_key)
        if m is None:
            continue
        v = r.get(metric_key)
        if v is None:
            continue
        by_model[m].append(r)

    out: dict[str, dict] = {}
    rng = random.Random(seed)
    lo_q = (1 - ci) / 2
    hi_q = 1 - lo_q

    for model, model_rows in by_model.items():
        out[model] = {}
        N = len(model_rows)
        for axis_name, levels in axes_spec.items():
            # Compute point estimate slope on the full sample
            level_means = []
            for lvl in levels:
                xs = [r[metric_key] for r in model_rows if r.get(axis_name) == lvl]
                level_means.append(_safe_mean(xs))
            point = _slope(level_means)

            # Bootstrap
            slopes = []
            for _ in range(n):
                # Resample with replacement
                sample = [model_rows[rng.randrange(N)] for _ in range(N)]
                level_means_b = []
                ok = True
                for lvl in levels:
                    xs = [r[metric_key] for r in sample if r.get(axis_name) == lvl]
                    if not xs:
                        ok = False
                        break
                    level_means_b.append(_safe_mean(xs))
                if not ok:
                    continue
                if any(math.isnan(m) for m in level_means_b):
                    continue
                slopes.append(_slope(level_means_b))

            if not slopes:
                out[model][axis_name] = {
                    "point": point,
                    "lo": float("nan"),
                    "hi": float("nan"),
                    "se": float("nan"),
                    "n_resamples": 0,
                }
                continue

            slopes.sort()
            lo = slopes[int(lo_q * len(slopes))]
            hi = slopes[min(int(hi_q * len(slopes)), len(slopes) - 1)]
            mean_b = sum(slopes) / len(slopes)
            var_b = sum((s - mean_b) ** 2 for s in slopes) / max(1, len(slopes) - 1)
            se = math.sqrt(var_b)
            out[model][axis_name] = {
                "point": point,
                "lo": lo,
                "hi": hi,
                "se": se,
                "n_resamples": len(slopes),
            }

    return out


def bootstrap_aggregate_cis(
    rows: list[dict],
    metric_key: str,
    axes_spec: dict[str, tuple],
    seed: int = 20260422,
    n: int = 1000,
    ci: float = 0.95,
) -> dict:
    """Bootstrap CIs on the aggregate (mean across models) |slope| per axis.

    Treats each model's rows as a unit — resamples *which* rows go into
    each model's slope, then takes the mean of |slope| across the 6 models
    on each resample.
    """
    by_model = defaultdict(list)
    for r in rows:
        m = r.get("model")
        if m is None or r.get(metric_key) is None:
            continue
        by_model[m].append(r)

    rng = random.Random(seed)
    lo_q = (1 - ci) / 2
    hi_q = 1 - lo_q

    out = {}
    for axis_name, levels in axes_spec.items():
        # Point estimate: |slope| averaged across models
        point_slopes = []
        for m, model_rows in by_model.items():
            level_means = [
                _safe_mean([r[metric_key] for r in model_rows if r.get(axis_name) == lvl])
                for lvl in levels
            ]
            s = _slope(level_means)
            if not math.isnan(s):
                point_slopes.append(abs(s))
        point = _safe_mean(point_slopes)

        agg_slopes = []
        for _ in range(n):
            per_model_slopes = []
            ok = True
            for m, model_rows in by_model.items():
                N = len(model_rows)
                sample = [model_rows[rng.randrange(N)] for _ in range(N)]
                level_means = []
                for lvl in levels:
                    xs = [r[metric_key] for r in sample if r.get(axis_name) == lvl]
                    if not xs:
                        ok = False
                        break
                    level_means.append(_safe_mean(xs))
                if not ok:
                    break
                if any(math.isnan(v) for v in level_means):
                    ok = False
                    break
                per_model_slopes.append(abs(_slope(level_means)))
            if not ok:
                continue
            agg_slopes.append(_safe_mean(per_model_slopes))

        if agg_slopes:
            agg_slopes.sort()
            lo = agg_slopes[int(lo_q * len(agg_slopes))]
            hi = agg_slopes[min(int(hi_q * len(agg_slopes)), len(agg_slopes) - 1)]
            out[axis_name] = {"point": point, "lo": lo, "hi": hi, "n_resamples": len(agg_slopes)}
        else:
            out[axis_name] = {
                "point": point,
                "lo": float("nan"),
                "hi": float("nan"),
                "n_resamples": 0,
            }

    return out
