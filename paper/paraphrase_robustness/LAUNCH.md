# Paraphrase-Robustness Sweep — Launch Instructions

**Status as of 2026-05-06**: PREREG committed (`1533930`); generator + helper +
diff-check + analyzer all built; v1 byte-identity verified. **Sweep not yet
launched** — requires API keys. The user will run the commands below.

## Pre-flight checklist

- [x] PREREG committed before any sweep launch (`1533930`).
- [x] `paraphrase_t3_village.jsonl` (180 scenarios) generated.
- [x] `paraphrase_t4_sales.jsonl` (450 samples) generated.
- [x] v1 byte-identity diff-check PASSED (`scripts/diff_check_v1.py`).
- [x] Analyzer ready (`scripts/analyze_paraphrase_robustness.py`).
- [ ] API keys configured in `.env` at repo root:
      `OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL=https://api.deepseek.com/v1`.

## 1. Smoke test (recommended, ~$12)

Generate a tiny smoke subset and run on the 1-model slice to verify pipeline.

```bash
# Generate smoke JSONLs: T3 = 15 scenarios (Claude × 5 frames × 3 versions);
# T4 = 15 samples (Claude × 1 product × 5 frames × 3 versions).
python paper/paraphrase_robustness/scripts/generate_paraphrase_sweep.py --smoke

# T3 smoke (Claude only)
inspect eval src/manipulation_bench/village_task.py \
    -T scenarios=paraphrase_t3_smoke.jsonl \
    --model openrouter/anthropic/claude-opus-4.7 \
    --model-role manipulator_claude='{"model":"openrouter/anthropic/claude-opus-4.7"}' \
    --model-role bystander_haiku='{"model":"openrouter/anthropic/claude-haiku-4.5"}' \
    --model-role bystander_gpt5mini='{"model":"openrouter/openai/gpt-5-mini"}' \
    --model-role bystander_gemflash='{"model":"openrouter/google/gemini-3-flash-preview"}' \
    --model-role bystander_dschat='{"model":"openrouter/deepseek/deepseek-chat"}' \
    --log-dir logs/paraphrase_t3_smoke \
    --temperature 0.7 --max-tokens 16384 --max-connections 6 --no-fail-on-error

# T4 smoke (Claude only)
inspect eval src/manipulation_bench/sales_task.py \
    -T scenarios=paraphrase_t4_smoke.jsonl \
    --model openrouter/anthropic/claude-opus-4.7 \
    --model-role model_a='{"model":"openrouter/anthropic/claude-opus-4.7"}' \
    --log-dir logs/paraphrase_t4_smoke \
    --temperature 0.7 --max-tokens 16384 --max-connections 10 --no-fail-on-error
```

Verify both logs scored cleanly (no errors, all 15 samples per task scored).

## 2. Full sweep (~$310 expected, $400 ceiling)

Same flags as production T3/T4 sweeps, with the post-Amendment roster
(GPT-5.5 + DeepSeek V4 Pro). Mirrors the launch commands at the bottom of
`paper/task3_village/scripts/generate_task3_village_full.py` and the T4
production-run config (Amendment A3 max_tokens=16384 across the board).

### T3 Village (180 scenarios, ~$245)

```bash
inspect eval src/manipulation_bench/village_task.py \
    -T scenarios=paraphrase_t3_village.jsonl \
    --model openrouter/anthropic/claude-opus-4.7 \
    --model-role manipulator_claude='{"model":"openrouter/anthropic/claude-opus-4.7"}' \
    --model-role manipulator_gpt5='{"model":"openrouter/openai/gpt-5.5-20260423","model_args":{"reasoning_enabled":true}}' \
    --model-role manipulator_gemini='{"model":"openrouter/google/gemini-3.1-pro-preview","model_args":{"reasoning_enabled":true}}' \
    --model-role manipulator_grok='{"model":"openrouter/x-ai/grok-4","model_args":{"reasoning_enabled":true}}' \
    --model-role manipulator_llama='{"model":"openrouter/meta-llama/llama-3.3-70b-instruct"}' \
    --model-role manipulator_deepseek='{"model":"openai-api/deepseek/deepseek-v4-pro","model_args":{"reasoning_enabled":true},"metadata":{"tool_choice_strategy":"auto"}}' \
    --model-role bystander_haiku='{"model":"openrouter/anthropic/claude-haiku-4.5"}' \
    --model-role bystander_gpt5mini='{"model":"openrouter/openai/gpt-5-mini"}' \
    --model-role bystander_gemflash='{"model":"openrouter/google/gemini-3-flash-preview"}' \
    --model-role bystander_dschat='{"model":"openrouter/deepseek/deepseek-chat"}' \
    --log-dir logs/paraphrase_t3_full \
    --temperature 0.7 --max-tokens 16384 --max-connections 6 --no-fail-on-error
```

### T4 Sales (450 samples, ~$22)

```bash
inspect eval src/manipulation_bench/sales_task.py \
    -T scenarios=paraphrase_t4_sales.jsonl \
    --model openrouter/anthropic/claude-opus-4.7 \
    --model-role model_a='{"model":"openrouter/anthropic/claude-opus-4.7"}' \
    --model-role model_b='{"model":"openrouter/openai/gpt-5.5-20260423","model_args":{"reasoning_enabled":true}}' \
    --model-role model_c='{"model":"openrouter/google/gemini-3.1-pro-preview","model_args":{"reasoning_enabled":true}}' \
    --model-role model_d='{"model":"openrouter/x-ai/grok-4","model_args":{"reasoning_enabled":true}}' \
    --model-role model_e='{"model":"openrouter/meta-llama/llama-3.3-70b-instruct"}' \
    --model-role model_f='{"model":"openai-api/deepseek/deepseek-v4-pro","model_args":{"reasoning_enabled":true},"metadata":{"tool_choice_strategy":"auto"}}' \
    --log-dir logs/paraphrase_t4_full \
    --temperature 0.7 --max-tokens 16384 --max-connections 10 --no-fail-on-error
```

Note on `--max-tokens 16384` for T4: matches Amendment A3 in
`paper/task4_sales/prereg.md` (raised from 4096 to 16384 to prevent
reasoning-token truncation on Gemini/Grok/DeepSeek). Applying it across
all six models is harmless for the non-reasoning models (Claude default,
Llama, GPT-5.5 light reasoning) and matches the canonical T4 config.

## 3. Combine + analyze

After both eval logs land:

```bash
# Optional: combine into one log per task (mirrors paper/cross_task pattern).
# If you keep the raw logs separate, point --t3-log/--t4-log directly.
python paper/cross_task/scripts/combine_eval_logs.py \
    --inputs 'logs/paraphrase_t3_full/*.eval' \
    --output paper/paraphrase_robustness/eval_log_t3.eval

python paper/cross_task/scripts/combine_eval_logs.py \
    --inputs 'logs/paraphrase_t4_full/*.eval' \
    --output paper/paraphrase_robustness/eval_log_t4.eval

# Run analysis
python paper/paraphrase_robustness/scripts/analyze_paraphrase_robustness.py \
    --t3-log paper/paraphrase_robustness/eval_log_t3.eval \
    --t4-log paper/paraphrase_robustness/eval_log_t4.eval
```

Outputs (under `paper/paraphrase_robustness/analysis/`):
- `results.json` — per-paraphrase per-model frame slopes + aggregate + verdict
- `appendix_table.md` — formatted Markdown table (PASS/FAIL per row)
- `appendix_subsection_draft.md` — 2-3 sentence interpretation auto-drafted
  from the verdict; user edits before pasting into the paper.

## 4. Manual paper edits (after results land)

Two edits to make to the main paper after the analyzer emits its outputs:

### 4a. New appendix subsection

Add `paper/paraphrase_robustness/analysis/appendix_subsection_draft.md` (or
the user-edited final version) as a new subsection
`\subsection{Frame-axis paraphrase robustness}\label{app:frame-robustness}`
in the main appendix. The auto-drafted interpretation paragraph is intended
as a starting point — adjust to taste.

### 4b. Limitations cross-reference

In the main paper's Limitations section, the "Single prompt wording per
cell" paragraph: append the sentence (matching the verdict that comes back):

- **If PASS**: "We address this concern in
  Appendix~\\ref{app:frame-robustness}, where two additional paraphrases per
  frame level on a representative cell of T3 (commissive) and T4
  (assertive) leave the dominance ratios within 2x of the headline values."
- **If PARTIAL FAIL** (direction holds, magnitude varies): "We address
  this concern in Appendix~\\ref{app:frame-robustness}, where two
  additional paraphrases per frame level confirm the direction of
  dominance is robust on both T3 and T4 but show paraphrase-conditioned
  magnitude on [task]; the headline ratios should be read with this
  margin in mind."
- **If DIRECTION FAIL**: "We address this concern in
  Appendix~\\ref{app:frame-robustness}; under [paraphrase], the
  dominance ratio on [task] falls to [X.Xx], indicating the headline
  claim is partly wording-dependent. We discuss the qualification in [§...]."

The analyzer's `appendix_subsection_draft.md` selects the matching variant
automatically based on the computed verdict.
