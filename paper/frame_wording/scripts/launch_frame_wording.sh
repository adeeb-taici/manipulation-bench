#!/usr/bin/env bash
# Frame-wording check: run one environment's sweep.
#
# usage: launch_frame_wording.sh <committee|inbox> <max_connections>
#
# Dated slugs pinned; provider recorded per run. Grok 4 is deprecated, so
# Grok 4.3 substitutes and runs its own v1 arm.
#
# Timeouts are permanent per expanded-roster Amendment A3: inspect's --timeout
# defaults to NO timeout, so a throttled request hangs forever and presents as a
# silent stall with no errors and no retries.

set -uo pipefail
export PYTHONIOENCODING=utf-8

ENV_NAME="${1:?usage: launch_frame_wording.sh <committee|inbox> <conns>}"
CONNS="${2:?need max_connections}"

WT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCEN="$WT/paper/frame_wording/scenarios/frame_wording_${ENV_NAME}.jsonl"
LOGROOT="$WT/../../../logs/frame_wording"
mkdir -p "$LOGROOT"
[ -f "$SCEN" ] || { echo "missing $SCEN" >&2; exit 2; }

# Under-test roster. Access date 2026-07-31, OpenRouter.
UT=(--model-role "model_claude=openrouter/anthropic/claude-opus-4.7"
    --model-role "model_gpt55=openrouter/openai/gpt-5.5-20260423"
    --model-role "model_gemini=openrouter/google/gemini-3.1-pro-preview"
    --model-role "model_grok43=openrouter/x-ai/grok-4.3"
    --model-role "model_llama=openrouter/meta-llama/llama-3.3-70b-instruct"
    --model-role "model_deepseek=openai-api/deepseek/deepseek-v4-pro")

# Pinned neutral panel, byte-identical to the frozen Committee design.
HAIKU='openrouter/anthropic/claude-haiku-4.5'
GPT5MINI='openrouter/openai/gpt-5-mini'
GEMFLASH='openrouter/google/gemini-3-flash-preview'
DSCHAT='openrouter/deepseek/deepseek-chat'

COMMON=(--temperature 0.7 --max-connections "$CONNS" --no-fail-on-error --display plain
        --timeout 900 --attempt-timeout 420 --max-retries 3 --retry-on-error=2)

echo "[fw:$ENV_NAME] start $(date -u +%H:%M:%S) conns=$CONNS"
case "$ENV_NAME" in
  committee)
    inspect eval "$WT/src/manipulation_bench/committee_task.py@committee_bench" \
      -T scenarios="$SCEN" \
      --model openrouter/anthropic/claude-opus-4.7 "${UT[@]}" \
      --model-role "model_neutral_anthropic=$HAIKU" \
      --model-role "model_neutral_openai=$GPT5MINI" \
      --model-role "model_neutral_google=$GEMFLASH" \
      --model-role "model_neutral_deepseek=$DSCHAT" \
      --log-dir "$LOGROOT/$ENV_NAME" "${COMMON[@]}" ;;
  inbox)
    inspect eval "$WT/src/manipulation_bench/inbox_task.py@inbox_bench" \
      -T scenarios="$SCEN" \
      --model openrouter/anthropic/claude-opus-4.7 "${UT[@]}" \
      --log-dir "$LOGROOT/$ENV_NAME" "${COMMON[@]}" ;;
  *) echo "unknown env: $ENV_NAME" >&2; exit 2 ;;
esac
rc=$?
echo "[fw:$ENV_NAME] done $(date -u +%H:%M:%S) rc=$rc"
