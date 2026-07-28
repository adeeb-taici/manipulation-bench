#!/usr/bin/env bash
# Sweep 4 Claude models across the cheap-tier paper tasks (T1, T4, T5).
#
# Models:
#   sonnet46 -> anthropic/claude-sonnet-4.6   (current gen)
#   sonnet37 -> anthropic/claude-3.7-sonnet   (prev gen sonnet)
#   haiku45  -> anthropic/claude-haiku-4.5    (current gen)
#   haiku35  -> anthropic/claude-3.5-haiku    (prev gen haiku)
#
# No reasoning_enabled flag — Anthropic models default to no extended thinking;
# matches paper convention for non-Opus Claude bindings.
#
# Tasks: T1 (Bargaining), T4 (Sales), T5 (Committee).
#   - T1/T4/T5 have no LLM judge in paper. Mathematical/rule-based scorers only.
#   - T2 (Debate) skipped: Opus-as-judge cost ~$600/run, paper-faithful but expensive.
#   - T3 (Village) skipped: pending entrypoint fix (game_task.py vs village_task.py)
#                           and missing bystander_gemflash binding.
#
# Logs land in logs/claude_sweep/<label>_<task>/<eval_id>.eval

set -u
mkdir -p logs/claude_sweep

PY="$(pwd)/.venv/bin/python"
INSPECT="$(pwd)/.venv/bin/inspect"
[ -x "$INSPECT" ] || INSPECT="$HOME/.local/bin/inspect"

declare -A BINDING=(
  [sonnet46]='openrouter/anthropic/claude-sonnet-4.6'
  [sonnet37]='openrouter/anthropic/claude-3.7-sonnet'
  [haiku45]='openrouter/anthropic/claude-haiku-4.5'
  [haiku35]='openrouter/anthropic/claude-3.5-haiku'
)

LABELS=(haiku35 haiku45 sonnet37 sonnet46)

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
    --log-dir "logs/claude_sweep/${label}_t1" \
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
    --log-dir "logs/claude_sweep/${label}_t3" \
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
    --log-dir "logs/claude_sweep/${label}_t4" \
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
    --log-dir "logs/claude_sweep/${label}_t5" \
    $COMMON_FLAGS
}

# Drive the sweep: by task (T1 → T4 → T5), all labels per task before next.
# T3 runs in a separate sweep after T1/T4/T5 complete — more expensive
# (5 LLM-driven bystanders), and we want the cheap clean tasks finished first.
for label in "${LABELS[@]}"; do run_t1 "$label" || echo "  T1 $label FAILED"; done
for label in "${LABELS[@]}"; do run_t4 "$label" || echo "  T4 $label FAILED"; done
for label in "${LABELS[@]}"; do run_t5 "$label" || echo "  T5 $label FAILED"; done
# T3 (Village) is intentionally NOT in this sweep — kick off separately:
#   for label in "${LABELS[@]}"; do run_t3 "$label" || echo "  T3 $label FAILED"; done

echo
echo "Sweep complete. Logs under logs/claude_sweep/"
