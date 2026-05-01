# Eval Logs → CSV Design

**Date:** 2026-05-01
**Status:** Approved (pending user review of spec)

## Goal

Compile the per-sample (per-rollout) results from the paper's Inspect AI eval logs into a single tidy CSV for downstream analysis. The script must be re-runnable as new logs are produced. It does not modify or delete any source data.

## Inputs

By default the script ingests the canonical paper eval logs and their `_extended` companions:

- `paper/task1_bargaining/eval_log.eval` + `eval_log_extended.eval`
- `paper/task2_debate/eval_log.eval` (no extended)
- `paper/task3_village/eval_log.eval` + `eval_log_extended.eval`
- `paper/task4_sales/eval_log.eval` + `eval_log_extended.eval`
- `paper/task5_committee/eval_log.eval` + `eval_log_extended.eval`

Total: 9 logs across 5 tasks. Each log contains thousands of samples (rollouts).

## Output

Single CSV at `paper/cross_task/results.csv`, committed to the repo.

One row per sample. Both canonical and extended logs are mixed in the same CSV, distinguished by a `variant` column (`canonical` | `extended`).

## CLI

```bash
python paper/cross_task/scripts/eval_logs_to_csv.py              # default: 9 paper logs → paper/cross_task/results.csv
python paper/cross_task/scripts/eval_logs_to_csv.py -o foo.csv   # custom output path
python paper/cross_task/scripts/eval_logs_to_csv.py --logs 'logs/*.eval'  # arbitrary glob, overrides default
```

When `--logs` is passed, the script does its best to infer `task` and `variant` from the path (`task<N>_*`, `_extended` suffix); falls back to `task=unknown, variant=other` if inference fails.

## Columns

### Identity / setup

| Column | Source | Notes |
|---|---|---|
| `task` | path inference | `task1_bargaining` … `task5_committee` |
| `variant` | path inference | `canonical` / `extended` |
| `log_path` | input | absolute path of source log, for provenance |
| `sample_id` | `sample.id` | |
| `epoch` | `sample.epoch` | |
| `scenario_id` | scenario metadata | scenario file id |
| `cluster_id` | task-specific | `claim_id` (T2), `scenario_id` (T4), `slate_id` (T5), null otherwise |
| `model` | `load.py` remapped | under-test model, post-canonicalization (e.g. DeepSeek-v3.2 → DeepSeek-V4-Pro) |
| `manipulator` | metadata | which agent was instructed to manipulate; empty for baseline |
| `frame` | `axes.canonical_frame` | one of 5 canonical levels |
| `incentive` | `axes.canonical_incentive` | one of 3 canonical levels |
| `difficulty` | metadata | low / medium / high |
| `num_agents` | metadata | when present |
| `topology` | metadata | when present |
| `topic` | metadata | when present |
| `model_mapping` | metadata | JSON-stringified `{agent_name: model}` dict for full provenance |

### Normalized cross-task metric

| Column | Source |
|---|---|
| `manipulation_metric` | the headline metric per task, as currently produced by `experiments/reanalysis/load.py` |
| `manipulation_occurred` | binary, from same source |

These are the columns to use for cross-task plotting/regression where a single comparable scalar per sample is needed.

### All scorer scores flattened

For each scorer in `sample.scores`, every key in `score.value` (when value is a dict) becomes a column named `<scorer>__<key>`. Scalar-valued scorers become a single column `<scorer>` with the value.

This produces a sparse wide table — scorers that only fire for one task leave NaN in rows from other tasks. That is intentional and expected. Pandas handles it cleanly.

Examples (non-exhaustive):
- `sales_classifier__accurate`, `sales_classifier__misleading`, `sales_classifier__false`, `sales_classifier__manipulation_rate`
- `bargaining_commit__manipulation_rate`, `bargaining_commit__log_deviation_mean`
- `exploitation_rate__agent_1` … `exploitation_rate__agent_6`, `exploitation_rate__exploitation_rate`
- `promise_action_gap__gap`, `village_fairness__gini`, `village_fairness__detection_rate`
- `initial_rating_bias__initial_bias`, `post_discussion_rating_change__neutral_shift_toward_interested`, `discussion_polarity__*`, `decision_outcome__*`
- `ground_truth_persuasion__belief_shift`, `manipulation_detection__*`, `argument_quality__*`

The exact set of columns is determined dynamically from the logs at runtime (union across all samples).

## Implementation approach

Thin wrapper that reuses existing infrastructure:

1. Resolve input log paths from `--logs` glob, or use the 9 default paths.
2. For each log, read with `inspect_ai.log.read_eval_log`.
3. Per sample:
   - Skip samples with `sample.error`.
   - Call `experiments.reanalysis.load._row_from_sample(...)` (or equivalent extracted helper) to get the normalized identity + `manipulation_metric` + `manipulation_occurred`. This already applies axis canonicalization via `axes.py` and model remapping.
   - Walk `sample.scores` and flatten every dict-valued or scalar score into `<scorer>__<key>` / `<scorer>` columns.
   - Pull additional setup fields (`scenario_id`, `manipulator`, `num_agents`, `topology`, `topic`, `model_mapping` JSON) from scenario metadata where present.
   - Tag the row with `task`, `variant`, `log_path` derived from the log path.
4. Concatenate all rows with `pandas.DataFrame.from_records`, write to CSV with `index=False`.

The script does not delete or modify any source data. It only reads the eval logs and writes the CSV.

## Non-goals

- No re-computation of metrics from raw transcripts — we read the scores already in the eval logs as-is.
- No automatic re-binding of model labels beyond what `load.py` already does.
- No analysis logic (regression, bootstraps, plotting). This script is purely a flattener.
- No JSONL scenario files involved — they are scenario *inputs*, not results.

## Open questions

None at design time. Edge cases (missing metadata fields, unknown scorer shapes) are handled by emitting NaN/empty values rather than failing.
