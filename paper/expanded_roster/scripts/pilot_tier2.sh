#!/usr/bin/env bash
# Tier 2 pre-launch feasibility pilot (prereg tier2_prereg.md section 5).
#
# Committee is the binding tool-call gate (Tier 1's only genuine competence
# failure was hy3_on at 127/180 on submit_ratings); Bargaining carries P-T2.1.
# This is a feasibility check, NOT a result -- it is not analysed for
# manipulation rates and its scenarios are re-run in the full sweep.
#
# usage: pilot_tier2.sh <mistral|ling>

set -uo pipefail
export PYTHONIOENCODING=utf-8

TAG="${1:?usage: pilot_tier2.sh <mistral|ling>}"

WT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCEN="$WT/paper/expanded_roster/scenarios"
LOGROOT="$WT/../../../logs/tier2_pilot"
mkdir -p "$LOGROOT"

# Neither Tier 2 model exposes a reasoning parameter, so no reasoning field is
# sent. Both are single-provider, so allow_fallbacks=false pins what exists.
bind() { printf '{"model":"openrouter/%s","model_args":{"provider":{"order":["%s"],"allow_fallbacks":false}}}' "$1" "$2"; }

case "$TAG" in
  mistral) SLUG='mistralai/mistral-large-2512'; PROV='Mistral' ;;
  ling)    SLUG='inclusionai/ling-2.6-1t';      PROV='Novita'  ;;
  *) echo "unknown tag: $TAG" >&2; exit 2 ;;
esac
UT=(--model-role "model_${TAG}=$(bind "$SLUG" "$PROV")")
PRIMARY="openrouter/$SLUG"

HAIKU='openrouter/anthropic/claude-haiku-4.5'
GPT5MINI='openrouter/openai/gpt-5-mini'
GEMFLASH='openrouter/google/gemini-3-flash-preview'
DSCHAT='openrouter/deepseek/deepseek-chat'

# A3: --timeout defaults to NO timeout in inspect; without these a throttled
# request hangs forever and presents as a silent stall.
COMMON=(--temperature 0.7 --max-connections 8 --no-fail-on-error --display plain
        --timeout 900 --attempt-timeout 420 --max-retries 3 --retry-on-error=2)

echo "[pilot:$TAG] === bargaining start $(date -u +%H:%M:%S) ==="
inspect eval "$WT/src/manipulation_bench/bargaining_task.py@bargaining_commit_bench" \
  -T scenarios="$SCEN/pilot2_t1_bargaining_${TAG}.jsonl" -T max_action_retries=4 \
  --max-tokens 16384 --model "$PRIMARY" "${UT[@]}" \
  --log-dir "$LOGROOT/t1_${TAG}" "${COMMON[@]}"
echo "[pilot:$TAG] === bargaining done rc=$? $(date -u +%H:%M:%S) ==="

echo "[pilot:$TAG] === committee start $(date -u +%H:%M:%S) ==="
inspect eval "$WT/src/manipulation_bench/committee_task.py@committee_bench" \
  -T scenarios="$SCEN/pilot2_t5_committee_${TAG}.jsonl" \
  --model "$PRIMARY" "${UT[@]}" \
  --model-role "model_neutral_anthropic=$HAIKU" --model-role "model_neutral_openai=$GPT5MINI" \
  --model-role "model_neutral_google=$GEMFLASH" --model-role "model_neutral_deepseek=$DSCHAT" \
  --log-dir "$LOGROOT/t5_${TAG}" "${COMMON[@]}"
echo "[pilot:$TAG] === committee done rc=$? $(date -u +%H:%M:%S) ==="
