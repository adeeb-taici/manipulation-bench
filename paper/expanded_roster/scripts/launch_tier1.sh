#!/usr/bin/env bash
# Tier 1 launch — reasoning-toggle deconfound (see ../prereg.md).
#
# Four configs x six environments x full factorial = 9,060 scenarios.
#   luna_on / luna_off   openai/gpt-5.6-luna     provider OpenAI    (Azure excluded)
#   hy3_on  / hy3_off    tencent/hy3             provider DeepInfra (fp8; Amendment A1)
#
# Provider routing is pinned with allow_fallbacks=false so quantization cannot
# drift within a run or between the ON and OFF arms. Reasoning is toggled with
# the OpenRouter reasoning.enabled parameter (Inspect model_arg
# `reasoning_enabled`), verified to produce R=0 output tokens when false.
#
# Scenario files live in this branch (paper/expanded_roster/scenarios) and are
# passed as ABSOLUTE paths: the editable install resolves `manipulation_bench`
# to the main checkout's src/, so relative filenames would look for scenarios
# there and pollute it.
#
# Usage:  bash paper/expanded_roster/scripts/launch_tier1.sh <env>
#         env in {t1,t2,t3,t4,t5,t6}
#
# Run order is by value-per-hour: t1 first (it carries the penalty-response
# deconfound, and is cheap), then t4/t6 (minutes), t5, then t2 and t3 (long).

set -euo pipefail
export PYTHONIOENCODING=utf-8   # inspect's rich display crashes on cp1252 otherwise

WT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
SCEN="$WT/paper/expanded_roster/scenarios"
LOGROOT="$WT/../../../logs/tier1_expanded"   # logs/ is gitignored
mkdir -p "$LOGROOT"

bind() {  # bind <slug> <reasoning_enabled> <provider>
  printf '{"model":"openrouter/%s","model_args":{"reasoning_enabled":%s,"provider":{"order":["%s"],"allow_fallbacks":false}}}' "$1" "$2" "$3"
}
LUNA_ON=$(bind  "openai/gpt-5.6-luna" true  OpenAI)
LUNA_OFF=$(bind "openai/gpt-5.6-luna" false OpenAI)
HY3_ON=$(bind   "tencent/hy3"          true  DeepInfra)   # Amendment A1: was GMICloud
HY3_OFF=$(bind  "tencent/hy3"          false DeepInfra)   # Amendment A1: was GMICloud

# Under-test roles, identical across every environment.
UT=(
  --model-role "model_luna_on=$LUNA_ON"
  --model-role "model_luna_off=$LUNA_OFF"
  --model-role "model_hy3_on=$HY3_ON"
  --model-role "model_hy3_off=$HY3_OFF"
)

# Pinned support roles, verbatim from each task's canonical run command.
OPUS='openrouter/anthropic/claude-opus-4.7'
HAIKU='openrouter/anthropic/claude-haiku-4.5'
GPT5MINI='openrouter/openai/gpt-5-mini'
GEMFLASH='openrouter/google/gemini-3-flash-preview'
DSCHAT='openrouter/deepseek/deepseek-chat'

# --model is required by inspect but unused by the deterministic scorers; point
# it at the cheapest roster model so an accidental fallback cannot cost much.
CHEAP='openrouter/tencent/hy3'

COMMON=(--temperature 0.7 --max-connections 20 --no-fail-on-error --display plain)

case "${1:?usage: launch_tier1.sh <t1|t2|t3|t4|t5|t6>}" in
  t1|t1_hy3)
    # t1_hy3 re-runs only the Hy3 arms (Amendment A1); Luna's 1,800 samples
    # from the original GMICloud run are complete and are not re-collected.
    SC="$SCEN/tier1_t1_bargaining.jsonl"
    [ "$1" = "t1_hy3" ] && SC="$SCEN/tier1_t1_bargaining_hy3.jsonl"
    inspect eval "$WT/src/manipulation_bench/bargaining_task.py@bargaining_commit_bench" \
      -T scenarios="$SC" -T max_action_retries=4 \
      --model "$CHEAP" "${UT[@]}" --max-tokens 16384 \
      --log-dir "$LOGROOT/${1}_bargaining" "${COMMON[@]}"
    ;;
  t2)
    inspect eval "$WT/src/manipulation_bench/task.py" \
      -T scenarios="$SCEN/tier1_t2_debate.jsonl" \
      --model "$CHEAP" "${UT[@]}" \
      --model-role "truthful_debater=$OPUS" \
      --model-role "juror_a=$GEMFLASH" --model-role "juror_b=$HAIKU" --model-role "juror_c=$GPT5MINI" \
      --model-role "judge=$HAIKU" \
      --log-dir "$LOGROOT/t2_debate" "${COMMON[@]}"
    ;;
  t3)
    inspect eval "$WT/src/manipulation_bench/village_task.py" \
      -T scenarios="$SCEN/tier1_t3_village.jsonl" \
      --model "$CHEAP" "${UT[@]}" \
      --model-role "bystander_haiku=$HAIKU" --model-role "bystander_gpt5mini=$GPT5MINI" \
      --model-role "bystander_gemflash=$GEMFLASH" --model-role "bystander_dschat=$DSCHAT" \
      --log-dir "$LOGROOT/t3_village" "${COMMON[@]}"
    ;;
  t4)
    inspect eval "$WT/src/manipulation_bench/sales_task.py" \
      -T scenarios="$SCEN/tier1_t4_sales.jsonl" \
      --model "$CHEAP" "${UT[@]}" \
      --log-dir "$LOGROOT/t4_sales" "${COMMON[@]}"
    ;;
  t5)
    inspect eval "$WT/src/manipulation_bench/committee_task.py" \
      -T scenarios="$SCEN/tier1_t5_committee.jsonl" \
      --model "$CHEAP" "${UT[@]}" \
      --model-role "model_neutral_anthropic=$HAIKU" --model-role "model_neutral_openai=$GPT5MINI" \
      --model-role "model_neutral_google=$GEMFLASH" --model-role "model_neutral_deepseek=$DSCHAT" \
      --log-dir "$LOGROOT/t5_committee" "${COMMON[@]}"
    ;;
  t6)
    inspect eval "$WT/src/manipulation_bench/inbox_task.py" \
      -T scenarios="$SCEN/tier1_t6_inbox.jsonl" \
      --model "$CHEAP" "${UT[@]}" \
      --log-dir "$LOGROOT/t6_inbox" "${COMMON[@]}"
    ;;
  *) echo "unknown env: $1" >&2; exit 2 ;;
esac
