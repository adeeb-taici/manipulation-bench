#!/usr/bin/env bash
# Run one Tier 2 model's environments sequentially, as an independent stream.
#
# Mistral Large 3 (Mistral first-party) and Ling-2.6-1T (Novita) sit on
# different providers, so the two streams run concurrently without contending
# for the same endpoint. Within a stream environments run one at a time.
#
# usage: launch_tier2.sh <mistral|ling> <max_connections> <env> [env ...]
#        env in {t1,t2,t3,t4,t5,t6}
#
# Concurrency differs by model on purpose. Ling is served by a single provider
# (Novita) with no fallback set available, and returned a RateLimitError during
# a 15-scenario pilot at concurrency 8, so it runs well below Tier 1's 40-60.
#
# Neither model exposes a reasoning parameter (verified against the OpenRouter
# endpoints API 2026-07-30), so no reasoning field is sent -- unlike Tier 1,
# where the toggle was the treatment.

set -uo pipefail
export PYTHONIOENCODING=utf-8   # inspect's rich display crashes on cp1252

TAG="${1:?usage: launch_tier2.sh <mistral|ling> <conns> <env...>}"; shift
CONNS="${1:?need max_connections}"; shift

WT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCEN="$WT/paper/expanded_roster/scenarios"
LOGROOT="$WT/../../../logs/tier2_expanded"
mkdir -p "$LOGROOT"

bind() { printf '{"model":"openrouter/%s","model_args":{"provider":{"order":["%s"],"allow_fallbacks":false}}}' "$1" "$2"; }

case "$TAG" in
  mistral) SLUG='mistralai/mistral-large-2512'; PROV='Mistral' ;;
  ling)    SLUG='inclusionai/ling-2.6-1t';      PROV='Novita'  ;;
  *) echo "unknown tag: $TAG" >&2; exit 2 ;;
esac
UT=(--model-role "model_${TAG}=$(bind "$SLUG" "$PROV")")
PRIMARY="openrouter/$SLUG"

OPUS='openrouter/anthropic/claude-opus-4.7'
HAIKU='openrouter/anthropic/claude-haiku-4.5'
GPT5MINI='openrouter/openai/gpt-5-mini'
GEMFLASH='openrouter/google/gemini-3-flash-preview'
DSCHAT='openrouter/deepseek/deepseek-chat'

# A3, adopted permanently: inspect's --timeout defaults to NO TIMEOUT, so a
# throttled request hangs forever and presents as a silent stall with no errors
# and no retries. This cost three runs in Tier 1.
TIMEOUTS=(--timeout 900 --attempt-timeout 420 --max-retries 3 --retry-on-error=2)
COMMON=(--temperature 0.7 --max-connections "$CONNS" --no-fail-on-error --display plain "${TIMEOUTS[@]}")

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
  if [ -z "$stem" ]; then echo "[tier2:$TAG] unknown env $env" >&2; return 1; fi
  local sc="$SCEN/tier2_${stem}_${TAG}.jsonl"
  local ld="$LOGROOT/${stem}_${TAG}"
  # A restart under changed run parameters keeps the work already scored and
  # re-collects only the rest (build_tier2_remaining.py). Samples from both
  # halves live in the same log dir and are unioned at analysis time.
  if [ -f "$SCEN/tier2_${stem}_${TAG}_remaining.jsonl" ]; then
    sc="$SCEN/tier2_${stem}_${TAG}_remaining.jsonl"
    echo "[tier2:$TAG] $env using remaining-scenarios file ($(wc -l < "$sc") scenarios)"
  fi
  if [ ! -f "$sc" ]; then echo "[tier2:$TAG] missing $sc -- skipping $env" >&2; return 1; fi
  echo "[tier2:$TAG] === $env start $(date -u +%H:%M:%S) ==="
  case "$env" in
    t1) inspect eval "$WT/src/manipulation_bench/bargaining_task.py@bargaining_commit_bench" \
          -T scenarios="$sc" -T max_action_retries=4 --max-tokens 16384 \
          --model "$PRIMARY" "${UT[@]}" --log-dir "$ld" "${COMMON[@]}" ;;
    t2) inspect eval "$WT/src/manipulation_bench/task.py@manipulation_bench" -T scenarios="$sc" \
          --max-tokens 16384 \
          --model "$PRIMARY" "${UT[@]}" \
          --model-role "truthful_debater=$OPUS" --model-role "juror_a=$GEMFLASH" \
          --model-role "juror_b=$HAIKU" --model-role "juror_c=$GPT5MINI" \
          --model-role "judge=$HAIKU" --log-dir "$ld" "${COMMON[@]}" ;;
    t3) inspect eval "$WT/src/manipulation_bench/village_task.py@village_bench" -T scenarios="$sc" \
          --max-tokens 16384 \
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
    *)  echo "[tier2:$TAG] unknown env $env" >&2; return 1 ;;
  esac
  local rc=$?
  echo "[tier2:$TAG] === $env done  $(date -u +%H:%M:%S) rc=$rc ==="
}

for e in "$@"; do run_env "$e"; done
echo "[tier2:$TAG] ALL DONE $(date -u +%H:%M:%S)"
