#!/usr/bin/env bash
# Sweep 5 OpenAI models across the 5 paper tasks (full sweep).
#
# Models:
#   gpt-5.4-nano, gpt-5.4-mini, gpt-4.1-nano, gpt-4.1-mini, gpt-4.1
# (gpt-5.4 standard already run separately.)
#
# Reasoning:
#   gpt-5.4 family -> reasoning_enabled=true (matches paper convention)
#   gpt-4.1 family -> no reasoning flag (model doesn't support it)
#
# Per task:
#   1. Generate one JSONL per model via experiments/generate_taskN_*.py --models <label>
#   2. Run inspect eval with --model-role bindings filled in
#
# Logs land in logs/openai_sweep/<model>_<task>.eval
# Sequential, --no-fail-on-error so a flaky model doesn't kill the sweep.

set -u
mkdir -p logs/openai_sweep

# Use the project venv's python + inspect (PATH may not have them in non-login shells).
PY="$(pwd)/.venv/bin/python"
INSPECT="$(pwd)/.venv/bin/inspect"
[ -x "$INSPECT" ] || INSPECT="$HOME/.local/bin/inspect"

# -----------------------------------------------------------------------------
# Model roster: label, OpenRouter slug, model_args JSON (or "" if none)
# -----------------------------------------------------------------------------
# Each binding is a JSON string passed to --model-role <role>=<binding>.
# 5.4 family gets reasoning_enabled=true (paper convention); 4.1 family is bare.
declare -A BINDING=(
  [gpt54nano]='{"model":"openrouter/openai/gpt-5.4-nano","model_args":{"reasoning_enabled":true}}'
  [gpt54mini]='{"model":"openrouter/openai/gpt-5.4-mini","model_args":{"reasoning_enabled":true}}'
  [gpt41nano]='openrouter/openai/gpt-4.1-nano'
  [gpt41mini]='openrouter/openai/gpt-4.1-mini'
  [gpt41]='openrouter/openai/gpt-4.1'
)

LABELS=(gpt54nano gpt54mini gpt41nano gpt41mini gpt41)

JUDGE='openrouter/anthropic/claude-opus-4.7'
COMMON_FLAGS='--temperature 0.7 --max-tokens 16384 --max-connections 20 --no-fail-on-error'

# -----------------------------------------------------------------------------
# Bind a single role for tasks that have a single under-test slot.
#   T1: model_a (+ model_b for self-play counterparty)
#   T4: model_a
#   T5: model_<label>  (committee uses model_<label> roles)
# T2 / T3 use manipulator_<label>.
# -----------------------------------------------------------------------------

run_t1() {
  local label=$1 binding=${BINDING[$1]}
  echo "=== T1 BARGAINING [$label] ==="
  "$PY" paper/task1_bargaining/scripts/generate_task1_bargaining.py \
    --models "$label" \
    -o "src/manipulation_bench/scenarios/task1_bargaining_${label}.jsonl" || return 1
  "$INSPECT" eval src/manipulation_bench/bargaining_task.py@bargaining_commit_bench \
    -T scenarios=task1_bargaining_${label}.jsonl \
    -T max_action_retries=4 \
    --model "$JUDGE" \
    --model-role model_a="$binding" \
    --model-role model_b="$binding" \
    --log-dir "logs/openai_sweep/${label}_t1" \
    $COMMON_FLAGS
}

run_t2() {
  local label=$1 binding=${BINDING[$1]}
  echo "=== T2 DEBATE [$label] ==="
  "$PY" paper/task2_debate/scripts/generate_task2_debate_full.py \
    --models "$label" \
    -o "src/manipulation_bench/scenarios/task2_debate_${label}.jsonl" || return 1
  "$INSPECT" eval src/manipulation_bench/task.py \
    -T scenarios=task2_debate_${label}.jsonl \
    --model "$JUDGE" \
    --model-role manipulator_${label}="$binding" \
    --model-role truthful_debater=openrouter/anthropic/claude-opus-4.7 \
    --model-role juror_a=openrouter/google/gemini-3-flash-preview \
    --model-role juror_b=openrouter/anthropic/claude-haiku-4.5 \
    --model-role juror_c=openrouter/openai/gpt-5-mini \
    --model-role judge=openrouter/anthropic/claude-opus-4.7 \
    --log-dir "logs/openai_sweep/${label}_t2" \
    $COMMON_FLAGS
}

run_t3() {
  local label=$1 binding=${BINDING[$1]}
  echo "=== T3 VILLAGE [$label] ==="
  "$PY" paper/task3_village/scripts/generate_task3_village_full.py \
    --models "$label" \
    -o "src/manipulation_bench/scenarios/task3_village_${label}.jsonl" || return 1
  "$INSPECT" eval src/manipulation_bench/village_task.py@village_bench \
    -T scenarios=task3_village_${label}.jsonl \
    --model "$JUDGE" \
    --model-role manipulator_${label}="$binding" \
    --model-role bystander_haiku=openrouter/anthropic/claude-haiku-4.5 \
    --model-role bystander_gpt5mini=openrouter/openai/gpt-5-mini \
    --model-role bystander_gemflash=openrouter/google/gemini-3-flash-preview \
    --model-role bystander_dschat=openrouter/deepseek/deepseek-chat \
    --log-dir "logs/openai_sweep/${label}_t3" \
    $COMMON_FLAGS
}

run_t4() {
  local label=$1 binding=${BINDING[$1]}
  echo "=== T4 SALES [$label] ==="
  "$PY" paper/task4_sales/scripts/generate_task4_sales.py \
    --models "$label" \
    --output "src/manipulation_bench/scenarios/task4_sales_${label}.jsonl" || return 1
  "$INSPECT" eval src/manipulation_bench/sales_task.py \
    -T scenarios=task4_sales_${label}.jsonl \
    --model "$JUDGE" \
    --model-role model_a="$binding" \
    --log-dir "logs/openai_sweep/${label}_t4" \
    $COMMON_FLAGS
}

run_t5() {
  local label=$1 binding=${BINDING[$1]}
  echo "=== T5 COMMITTEE [$label] ==="
  "$PY" paper/task5_committee/scripts/generate_task5_committee.py \
    --models "$label" \
    --out "src/manipulation_bench/scenarios/task5_committee_${label}.jsonl" || return 1
  "$INSPECT" eval src/manipulation_bench/committee_task.py \
    -T scenarios=task5_committee_${label}.jsonl \
    --model "$JUDGE" \
    --model-role model_${label}="$binding" \
    --model-role model_neutral_anthropic=openrouter/anthropic/claude-haiku-4.5 \
    --model-role model_neutral_openai=openrouter/openai/gpt-5-mini \
    --model-role model_neutral_google=openrouter/google/gemini-3-flash-preview \
    --model-role model_neutral_deepseek=openrouter/deepseek/deepseek-chat \
    --log-dir "logs/openai_sweep/${label}_t5" \
    $COMMON_FLAGS
}

# -----------------------------------------------------------------------------
# Drive the sweep. Order: by task (so all T1s finish before any T2 starts),
# so partial results stay coherent if interrupted.
#
# NOTE: T1 already ran cleanly for all 5 labels (900/900 samples, 0 errors).
# T2 is skipped here — Opus-as-judge makes each T2 run ~$600. Run T2 separately
# (or with a cheaper judge) once OpenRouter credits are topped up.
# -----------------------------------------------------------------------------
# T1 already complete locally. T2 skipped (Opus judge cost). T3/T5 disabled
# pending binding fixes (T3 wrong task entrypoint + missing bystander_gemflash;
# T5 wrong gemini-flash version). T4 is paper-faithful — only model_a is bound,
# single-agent with scripted buyer, no cold panel to mis-bind.
# for label in "${LABELS[@]}"; do run_t1 "$label" || echo "  T1 $label FAILED"; done
# for label in "${LABELS[@]}"; do run_t2 "$label" || echo "  T2 $label FAILED"; done
for label in "${LABELS[@]}"; do run_t3 "$label" || echo "  T3 $label FAILED"; done
# for label in "${LABELS[@]}"; do run_t4 "$label" || echo "  T4 $label FAILED"; done   # done
# for label in "${LABELS[@]}"; do run_t5 "$label" || echo "  T5 $label FAILED"; done   # done

echo
echo "Sweep complete. Logs under logs/openai_sweep/"
