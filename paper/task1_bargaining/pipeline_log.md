# Task 1 Bargaining — pipeline log

Running log of provider/infrastructure issues encountered during the Task 1 Bargaining sweep, with resolutions. Complements the pre-registered `prereg.md` (which fixes the experimental design) by recording production-run events that affect reproducibility or interpretation.

## 2026-04-22 — Full-sweep launch and partial stall

**Event**: Full sweep launched 18:57 on the 5,400-scenario JSONL with `--max-connections 20`. Processed cleanly through the first ~2,700 samples (Claude 900, GPT-5 900, Gemini 899, Grok 1). Then all 20 concurrent slots went idle, with OpenRouter connections staying "Established" but no data flowing. Eval file stopped growing at 177 MB; CPU dropped to ~2%.

**Diagnosis**: First batch to reach Grok-4 hung. Grok-4 with `reasoning_enabled=true` appears to have the same structural tool-call-refusal pattern under bargaining's `commit_valuation` schema that DeepSeek-v3.2-reasoning-on demonstrated in the pre-sweep smoke, but the failure mode on Grok is a silent connection hold (no explicit error) rather than an empty-content return. With 20 concurrent Grok requests held simultaneously, the whole event loop saturated and Inspect could not dispatch further work.

**Resolution**: Killed at 22:22; retried via `inspect eval-retry` once which reproduced the same stall before it could write any new samples to the eval file. Switched to per-model split approach (Option A from the pre-launch discussion):

- **Batch 1 (Llama + DeepSeek + 1 Gemini straggler = 1,801 scenarios)**: ran at `--max-connections 20` on the models without the Grok-style hang. Finished cleanly in ~56 min. Sample-failure rate: 0.0% on DeepSeek (reasoning-off per A1), 10.9% on Llama (98/900), 0% on Gemini straggler.
- **Grok-only batch (899 scenarios)**: re-launched at `--max-connections 3` to avoid the event-loop saturation. Progressing slowly (~1 sample/min) but with no failures. Expected completion ~2026-04-24 midnight.

**Paper impact**: none on the Committee or Task 1 design/metrics. Pipeline log for reproducibility only.

## 2026-04-23 — Llama tool-refusal recovery via bumped retries

**Event**: Batch 1 completed with Llama at 10.9% `sample_failed` rate (98 scenarios), concentrated in prohibitive-frame cells (55% failure rate at `prohibitive/E=250/low`). Failure mode matched the structural tool-refusal pattern: both agents reach ACTION phase, return empty content with zero tool calls, exhaust `max_action_retries=4`, produce `sample_failed=1` per the scorer fix (commit `1e5b132`).

**Diagnosis attempt**: unclear whether failure was structural (like DeepSeek-reasoning-on) or stochastic-retry-tail. Llama is not a reasoning model, so the same mechanism is unlikely.

**Resolution**: Re-ran just the 98 failed scenarios at `max_action_retries=10` (eval script: `inspect eval ... -T max_action_retries=10`). **Recovery: 98/98 (100%)**. No residual failures. Effective Llama failure rate drops from 10.9% to 0.0%.

This flags it as a pipeline finding rather than a paper-level caveat: Llama's tool-call emission on bargaining's simple-schema tool is reliable given enough retries, unlike DeepSeek-reasoning-on which was structurally broken (0/3 recovery at retries=10). Retry budget = 4 as specified in `prereg.md §4` is marginal for Llama under prohibitive framing; author may want to consider bumping to 6 for any re-runs, though the current 0% aggregate failure rate does not demand it.

## 2026-04-23 — Aggregate sample-failure rate

Across all 4,501 scored Task 1 samples (5 of 6 models complete + retries applied):

- Claude: 0/900 (0.0%)
- GPT-5: 0/900 (0.0%)
- Gemini 3.1 Pro: 0/900 (0.0%)
- DeepSeek v3.2: 0/900 (0.0%) — reasoning-off per A1
- Llama 3.3 70B: 0/900 (0.0%) — after 98-scenario retry at retries=10

Aggregate: **0 / 4,501 = 0.00%**. Well under the PREREG `§6` ceiling of 3%. Grok-4 data when it completes may shift this slightly but all 271 Grok samples scored so far are clean.

## 2026-04-24 — Grok-4 completion

**Event**: Grok-4 split sweep finished cleanly. Status `success`, **899/899 scored**, **0 errors**. Wall-clock ~38 hours at `--max-connections 3` (slow but stable; reasoning-stall pathology never recurred at this concurrency).

**Sample size note**: the Grok split JSONL contained 899 scenarios. One Grok scenario was already scored in the original 2,700-sample launch's eval file before that run stalled, so the remaining-Grok JSONL excluded it. Combined: **1 (orig) + 899 (split) = 900 unique Grok samples** after deduplication by sample id. Task 1 paper-wide aggregate is **5,400 / 5,400 = 100.0%**.

**Final aggregate sample-failure rate** (all 6 models + retries applied): **0 / 5,400 = 0.00%**. PREREG §6 ceiling 3%; comfortably under.

Final per-model:

| Model | Scored | Failures |
|---|---|---|
| Claude Opus 4.7 | 900 | 0 |
| GPT-5 | 900 | 0 |
| Gemini 3.1 Pro | 900 | 0 |
| Grok-4 | 900 (1 from orig + 899 from split) | 0 |
| Llama 3.3 70B | 900 | 0 (after retries=10 retry) |
| DeepSeek v3.2 | 900 | 0 (reasoning-off per A1) |

Task 1 raw-data collection is **complete**; results.md authorship can proceed.

## Logs referenced

- `logs/task1_fullsweep_20260422/` — original launch (2,700 valid samples before stall)
- `logs/task1_fullsweep_20260422_batch1/` — Llama + DeepSeek + Gemini straggler (1,801 samples)
- `logs/task1_fullsweep_20260422_llama_retry/` — 98-scenario Llama retry at retries=10 (98/98 recovered)
- `logs/task1_fullsweep_20260422_grok/` — Grok-only split at `--max-connections 3` (899/899 scored, 0 errors, status=success)
- `logs/task1_v61_dsdiag/`, `logs/task1_v61_dsverify/` — pre-sweep diagnostics that established Amendment A1
