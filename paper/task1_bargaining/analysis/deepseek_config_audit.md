# Task 1 Bargaining — DeepSeek configuration audit

Purpose: confirm definitively which DeepSeek configuration produced the 900 DeepSeek samples in the Task 1 Bargaining sweep, so any paper-level interpretation of DeepSeek results carries the correct caveat.

## Verdict

**All 900 Task 1 Bargaining DeepSeek samples were produced with `reasoning_enabled=false`**, per PREREG amendment A1 ([../prereg.md §10](../prereg.md)). Retries did not recover the reasoning-on config; the reasoning-on path is structurally broken for Bargaining's `commit_valuation` tool schema and was never used for the paper's production data.

## Evidence

Model-role `args` field from each Task 1 eval log's `eval.model_roles.model_f` entry:

| Log | Tag | DS args | n DS samples | DS sample_failed count |
|---|---|---|---:|---:|
| `logs/task1_fullsweep_20260422/...fs5xJTVak5W4Z63tCpDg9R.eval` | original sweep | `{"reasoning_enabled": false}` | 0 | 0 |
| `logs/task1_fullsweep_20260422_batch1/...GKdyCWTAFHmA7vCs7xbdEJ.eval` | batch1 (Llama + DeepSeek + Gemini straggler) | `{"reasoning_enabled": false}` | **900** | **0** |
| `logs/task1_fullsweep_20260422_llama_retry/...` | Llama retry | — (no model_f role) | 0 | 0 |
| `logs/task1_fullsweep_20260422_grok/...` | Grok run | — (no model_f role) | 0 | 0 |
| `logs/task1_v61_dsdiag/...` | Diagnostic (reasoning-on, proving it fails) | `{"reasoning_enabled": true}` | 3 | **3** |
| `logs/task1_v61_dsverify/...` | Verification (reasoning-off, proving it works) | `{"reasoning_enabled": false}` | 3 | 0 |

The original full-sweep launch (18:57 2026-04-22) dispatched all 6 roster models with the v6.1 bindings but stalled after completing Claude, GPT-5, Gemini, and 1 Grok sample (2,700 scored, zero DeepSeek reached). DeepSeek's 900 samples were produced in batch1 when the remaining-work split launched with the A1-locked reasoning-off config.

The two diagnostic logs independently confirm the A1 rationale:
- Reasoning-on (diag): 3 of 3 scenarios failed both-agent commits across 11 retry attempts each; 1 of 6 per-agent commits succeeded.
- Reasoning-off (verify): 3 of 3 scenarios produced both-agent commits, all on attempt 0.

## Cross-task caveat for the paper

- **Task 5 Committee**: DeepSeek was run with `reasoning_enabled=true`.
- **Task 1 Bargaining**: DeepSeek was run with `reasoning_enabled=false`.

Any claim that compares DeepSeek's behavior across Tasks 1 and 5 must flag this config difference. In particular:

- The non-monotonic penalty response on Task 1 (`E=250 > E=80` for 4/5 non-prohibitive frames) might be a reasoning-off artifact — the reasoning-on version, had it worked, might have computed the expected-value math more completely at E=250 and shown a monotonic response. The diagnostic logs do not resolve this because reasoning-on never produced valid commits to compare.
- The cross-task per-model sensitivity profile vector (5 tasks × 3 axes = 15 dims, per PREREG §8 "Cross-task positioning") for DeepSeek contains one dimension-set measured under a different config from the other four tasks. This is a known limitation of the paper's DeepSeek row; should be flagged in Methods and Limitations.

Alternative framings considered and rejected during PREREG drafting:
- Swap DeepSeek-v3.2 for DeepSeek-chat (non-reasoning) on Task 1: rejected because it introduces a different model in the profile-vector slot, which is a worse confound than a config change on the same model.
- Drop DeepSeek from Task 1 entirely: rejected because the 5-task profile would then have one row with a missing-value slice.

The current approach (same model, different config) is documented as PREREG Amendment A1 with the tool-call-refusal diagnostic as evidence, and is the least bad option of the three.

## Not pipeline-log-worthy (nothing to log)

No retries recovered reasoning-on; the diagnostic deliberately ran reasoning-on to demonstrate failure, not production-sweep-adjacent. No reasoning-on DeepSeek samples contributed to paper data. Amendment A1 was the config decision for Bargaining-only before the full sweep dispatched.
