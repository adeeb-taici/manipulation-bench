# Paraphrase-robustness addendum

Pre-registered rebuttal addendum to the main paper. Addresses a reviewer's concern that the response-surface findings — particularly the claim that frame *dominates* on commissive-channel tasks — could be a partial artifact of the specific prompt wording chosen for each frame level, since each cell uses a single prompt suffix.

## What this directory contains

| File | What it is |
|---|---|
| [`PREREG_paraphrase_robustness.md`](PREREG_paraphrase_robustness.md) | Pre-registration document, locked before any sweep launched. Contains design, paraphrases verbatim, pass criteria, and Amendment 1 (T3 → T1 substitution due to wall-clock infeasibility in the rebuttal window). |
| [`paraphrases.json`](paraphrases.json) | Machine-readable copy of all 30 paraphrases (T1, T3, T4 — 5 frames × 3 versions each). v1 = original production wording; v2 = formal-imperative paraphrase; v3 = conversational paraphrase. |
| [`cell_selection.json`](cell_selection.json) | Output of [`scripts/pick_representative_cells.py`](scripts/pick_representative_cells.py). For each task, ranks the 9 (incentive, difficulty) cells by how close the cell's frame slope is to the per-task aggregate. The closest cell becomes the held-fixed slice for the paraphrase sweep. |
| [`cost_estimate.json`](cost_estimate.json) | Output of [`scripts/cost_estimate.py`](scripts/cost_estimate.py). Per-scenario $-cost averages from the main paper logs, projected to the addendum's scenario count. |
| `eval_log_t1.eval` | T1 Bargaining paraphrase sweep — 450 scenarios (6 models × 5 frames × 3 paraphrases × 5 reps × 1 fixed cell). LFS. |
| `eval_log_t4.eval` | T4 Sales paraphrase sweep — 450 samples (6 models × 5 frames × 3 paraphrases × 5 medium-difficulty products × 1 rep). LFS. |
| [`analysis/results.json`](analysis/results.json) | Per-paraphrase per-model frame slopes, pooled-across-paraphrases magnitudes (with SE), dominance ratios against Table 2 anchors, and pass/fail verdict on PREREG criteria P-T1 / P-B / P-C. |
| [`scripts/`](scripts/) | All scripts: cell selection, cost estimate, paraphrase generator, byte-identity diff-check (v1 ≡ production), analyzer. |
| [`LAUNCH.md`](LAUNCH.md) | Operational runbook documenting the actual `inspect eval` commands used to produce the eval logs. Frozen at sweep-launch time; kept for provenance. |

## Headline result

Both tested tasks PASS all paraphrase-robustness criteria.

| Task | Pooled \|frame slope\| ± SE | Dominance ratio (anchor: Table 2) | Range across paraphrases |
|---|---:|---:|---:|
| **T1 Bargaining** | 0.088 ± 0.005 | 2.83× incentive/frame (anchor 2.3×) | 1.21× |
| **T4 Sales** | 0.031 ± 0.002 | 2.80× difficulty/frame (anchor 3.3×) | 1.19× |

Per-model rankings preserved across all three paraphrase versions on both tasks; no model crosses the frame-sensitivity threshold between v1, v2, v3. The dominance pattern is **not** an artifact of single prompt wording per cell.

## What's deferred to camera-ready

Per PREREG Amendment 1 (2026-05-06), T3 Village paraphrase sweep was deferred because the full T3 design (180 multi-agent scenarios at the production `--max-connections=6`) extrapolates to ~8–10 hours wall-clock, infeasible in the rebuttal window. T3 paraphrase artifacts (paraphrases, scenarios JSONL, single-model smoke at `logs/paraphrase_t3_smoke/`) remain in the addendum directory, ready to launch with the same `inspect eval` command pattern.

## Reproducing the analysis

From the repo root:

```bash
python paper/paraphrase_robustness/scripts/analyze_paraphrase_robustness.py \
    --t1-log paper/paraphrase_robustness/eval_log_t1.eval \
    --t4-log paper/paraphrase_robustness/eval_log_t4.eval \
    --out-dir paper/paraphrase_robustness/analysis
```

The analyzer regenerates `results.json` plus the appendix table and a draft interpretation paragraph. The drafts are emitted on demand and not committed to version control.

To re-launch the sweeps from scratch, see [`LAUNCH.md`](LAUNCH.md) for the exact `inspect eval` commands used.
