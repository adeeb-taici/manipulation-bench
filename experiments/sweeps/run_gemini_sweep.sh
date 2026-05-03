#!/usr/bin/env bash
# Sweep 6 Gemini models across the cheap-tier paper tasks (T1, T4, T5).
#
# Models — 2 generations × 3 tiers (Pro, Flash, Flash-Lite):
#   gemini31pro       -> google/gemini-3.1-pro-preview         (current Pro)
#   gemini31flash     -> google/gemini-3-flash-preview         (current Flash; 3.0 — no plain 3.1 flash exists)
#   gemini31flashlite -> google/gemini-3.1-flash-lite-preview  (current Flash-Lite)
#   gemini25pro       -> google/gemini-2.5-pro                 (prev gen Pro)
#   gemini25flash     -> google/gemini-2.5-flash               (prev gen Flash)
#   gemini25flashlite -> google/gemini-2.5-flash-lite          (prev gen Flash-Lite)
#
# No reasoning_enabled flag — paper's gemini-3.1-pro-preview binding used it,
# but 2.5-tier and Flash/Lite tiers don't support it. Keeping default for all
# means a slightly different 3.1-pro behavior than the paper's manipulator_gemini
# slot, which had reasoning_enabled=true. Acceptable: this sweep is intentionally
# under-test of new model rows, not a re-run of the paper roster.
#
# Tasks: T1 (Bargaining), T4 (Sales), T5 (Committee).
# T2/T3 skipped (Opus judge cost / village bystander cost).
#
# Logs land in logs/gemini_sweep/<label>_<task>/<eval_id>.eval

set -u
mkdir -p logs/gemini_sweep

PY="$(pwd)/.venv/bin/python"
INSPECT="$(pwd)/.venv/bin/inspect"
[ -x "$INSPECT" ] || INSPECT="$HOME/.local/bin/inspect"

declare -A BINDING=(
  [gemini31pro]='openrouter/google/gemini-3.1-pro-preview'
  [gemini31flash]='openrouter/google/gemini-3-flash-preview'
  [gemini31flashlite]='openrouter/google/gemini-3.1-flash-lite-preview'
  [gemini25pro]='openrouter/google/gemini-2.5-pro'
  [gemini25flash]='openrouter/google/gemini-2.5-flash'
  [gemini25flashlite]='openrouter/google/gemini-2.5-flash-lite'
)

# Run cheapest first (Lite tiers) so any blowup surfaces with low blast radius.
LABELS=(gemini25flashlite gemini31flashlite gemini25flash gemini31flash gemini25pro gemini31pro)

JUDGE='openrouter/anthropic/claude-opus-4.7'
COMMON_FLAGS='--temperature 0.7 --max-tokens 16384 --max-connections 20 --no-fail-on-error'

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
    --log-dir "logs/gemini_sweep/${label}_t1" \
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
    --log-dir "logs/gemini_sweep/${label}_t4" \
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
    --log-dir "logs/gemini_sweep/${label}_t5" \
    $COMMON_FLAGS
}

# Drive the sweep: by task, all labels per task before next.
for label in "${LABELS[@]}"; do run_t1 "$label" || echo "  T1 $label FAILED"; done
for label in "${LABELS[@]}"; do run_t4 "$label" || echo "  T4 $label FAILED"; done
for label in "${LABELS[@]}"; do run_t5 "$label" || echo "  T5 $label FAILED"; done

echo
echo "Sweep complete. Logs under logs/gemini_sweep/"
