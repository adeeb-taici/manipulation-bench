#!/usr/bin/env bash
# Run one model's environments sequentially, as an independent stream.
#
# GPT-5.6 Luna (OpenAI) and Tencent Hy3 (DeepInfra) sit on different providers,
# so the two streams can run concurrently without contending for the same
# endpoint. Within a stream environments run one at a time.
#
# usage: launch_stream.sh <luna|hy3> <max_connections> <env> [env ...]
#        env in {t1,t2,t3,t4,t5,t6}
#
# Reasoning is toggled via the OpenRouter reasoning.enabled parameter; provider
# routing is pinned with allow_fallbacks=false so quantization cannot drift
# (Hy3 on DeepInfra/fp8 per prereg Amendment A1).

set -uo pipefail
export PYTHONIOENCODING=utf-8   # inspect's rich display crashes on cp1252

TAG="${1:?usage: launch_stream.sh <luna|hy3> <conns> <env...>}"; shift
CONNS="${1:?need max_connections}"; shift

WT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCEN="$WT/paper/expanded_roster/scenarios"
LOGROOT="$WT/../../../logs/tier1_expanded"
mkdir -p "$LOGROOT"

bind() { printf '{"model":"openrouter/%s","model_args":{"reasoning_enabled":%s,"provider":{"order":["%s"],"allow_fallbacks":false}}}' "$1" "$2" "$3"; }

case "$TAG" in
  luna)
    UT=(--model-role "model_luna_on=$(bind  'openai/gpt-5.6-luna' true  OpenAI)"
        --model-role "model_luna_off=$(bind 'openai/gpt-5.6-luna' false OpenAI)")
    PRIMARY='openrouter/openai/gpt-5.6-luna'
    ;;
  hy3)
    UT=(--model-role "model_hy3_on=$(bind  'tencent/hy3' true  DeepInfra)"
        --model-role "model_hy3_off=$(bind 'tencent/hy3' false DeepInfra)")
    PRIMARY='openrouter/tencent/hy3'
    ;;
  *) echo "unknown tag: $TAG" >&2; exit 2 ;;
esac

OPUS='openrouter/anthropic/claude-opus-4.7'
HAIKU='openrouter/anthropic/claude-haiku-4.5'
GPT5MINI='openrouter/openai/gpt-5-mini'
GEMFLASH='openrouter/google/gemini-3-flash-preview'
DSCHAT='openrouter/deepseek/deepseek-chat'

COMMON=(--temperature 0.7 --max-connections "$CONNS" --no-fail-on-error --display plain)

# Short env key -> scenario-file stem written by split_scenarios_by_model.py
stem_for() {
  case "$1" in
    t1) echo t1_bargaining ;; t2) echo t2_debate ;; t3) echo t3_village ;;
    t4) echo t4_sales ;;      t5) echo t5_committee ;; t6) echo t6_inbox ;;
    *)  echo "" ;;
  esac
}

run_env() {
  local env="$1"
  local stem
  stem="$(stem_for "$env")"
  if [ -z "$stem" ]; then echo "[stream:$TAG] unknown env $env" >&2; return 1; fi
  local sc="$SCEN/tier1_${stem}_${TAG}.jsonl"
  local ld="$LOGROOT/${stem}_${TAG}"
  if [ ! -f "$sc" ]; then echo "[stream:$TAG] missing $sc — skipping $env" >&2; return 1; fi
  echo "[stream:$TAG] === $env start $(date -u +%H:%M:%S) ==="
  case "$env" in
    t1) inspect eval "$WT/src/manipulation_bench/bargaining_task.py@bargaining_commit_bench" \
          -T scenarios="$sc" -T max_action_retries=4 --max-tokens 16384 \
          --model "$PRIMARY" "${UT[@]}" --log-dir "$ld" "${COMMON[@]}" ;;
    t2) inspect eval "$WT/src/manipulation_bench/task.py@manipulation_bench" -T scenarios="$sc" \
          --model "$PRIMARY" "${UT[@]}" \
          --model-role "truthful_debater=$OPUS" --model-role "juror_a=$GEMFLASH" \
          --model-role "juror_b=$HAIKU" --model-role "juror_c=$GPT5MINI" \
          --model-role "judge=$HAIKU" --log-dir "$ld" "${COMMON[@]}" ;;
    t3) inspect eval "$WT/src/manipulation_bench/village_task.py@village_bench" -T scenarios="$sc" \
          --model "$PRIMARY" "${UT[@]}" \
          --model-role "bystander_haiku=$HAIKU" --model-role "bystander_gpt5mini=$GPT5MINI" \
          --model-role "bystander_gemflash=$GEMFLASH" --model-role "bystander_dschat=$DSCHAT" \
          --log-dir "$ld" "${COMMON[@]}" ;;
    t4) inspect eval "$WT/src/manipulation_bench/sales_task.py@sales_bench" -T scenarios="$sc" \
          --model "$PRIMARY" "${UT[@]}" --log-dir "$ld" "${COMMON[@]}" ;;
    t5) inspect eval "$WT/src/manipulation_bench/committee_task.py@committee_bench" -T scenarios="$sc" \
          --model "$PRIMARY" "${UT[@]}" \
          --model-role "model_neutral_anthropic=$HAIKU" --model-role "model_neutral_openai=$GPT5MINI" \
          --model-role "model_neutral_google=$GEMFLASH" --model-role "model_neutral_deepseek=$DSCHAT" \
          --log-dir "$ld" "${COMMON[@]}" ;;
    t6) inspect eval "$WT/src/manipulation_bench/inbox_task.py@inbox_bench" -T scenarios="$sc" \
          --model "$PRIMARY" "${UT[@]}" --log-dir "$ld" "${COMMON[@]}" ;;
    *)  echo "[stream:$TAG] unknown env $env" >&2; return 1 ;;
  esac
  local rc=$?
  echo "[stream:$TAG] === $env done  $(date -u +%H:%M:%S) rc=$rc ==="
}

for e in "$@"; do run_env "$e"; done
echo "[stream:$TAG] ALL DONE $(date -u +%H:%M:%S)"
