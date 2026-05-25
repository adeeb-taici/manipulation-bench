# Provider quirks

Different model providers expose subtly different APIs even when wrapped
behind a common interface (Inspect AI, OpenRouter, OpenAI-compatible
endpoints). This page catalogs the quirks the framework has had to work
around, and the levers exposed for handling them.

## DeepSeek V4 Pro reasoner

Bound as `model_f` in the canonical 6-model frontier roster.

**Symptoms**:
- OpenRouter: rejects with "no endpoints available matching your guardrail
  restrictions" because DeepSeek's reasoning model isn't surfaced through
  OpenRouter's privacy-guarded endpoints.
- Direct API: rejects `tool_choice="any"` with `"deepseek-reasoner does not
  support this tool_choice"`. Only `{"none", "auto"}` are accepted by the
  reasoner. Specific-function selection (`{"type": "function", ...}`) is
  also rejected.

**Workaround**:
1. Configure DeepSeek's official API directly. Add to `.env`:
   ```
   DEEPSEEK_API_KEY=...
   DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
   ```
   Use Inspect's `openai-api/deepseek/<model>` provider prefix (the
   `openai-api` adapter speaks OpenAI's protocol against DeepSeek's
   compatible endpoint).
2. In each scenario, mark DeepSeek-bound agents with
   `metadata.tool_choice_strategy="auto"`. The game solver
   ([`src/manipulation_bench/game_solver.py`](../src/manipulation_bench/game_solver.py))
   sees this and substitutes `"auto"` for `"any"` on that agent's
   `model.generate()` calls. The existing `max_action_retries` budget
   handles the case where the reasoner doesn't call a tool on the first
   attempt.

This is the only place the framework diverges from its default
tool-choice handling.

## OpenAI / Azure GPT-5 strict-mode tool schemas

**Symptom**: Tool calls get rejected with HTTP 400 if any property is not
listed in the tool's `required` array. Strict mode treats every property
as mandatory; OpenAI's spec for non-strict tools allows optional
properties, but several providers (notably Azure-deployed GPT-5 and
OpenAI's strict adapter) silently flip strict-mode on.

**Workaround**: When you author a `ToolInfo`, declare every property in
`required`. This is best practice anyway — it forces the model to think
about each parameter explicitly. Existing tools across the framework
(Werewolf, Diplomacy, Village, Committee) all already comply.

## Llama 3.3 70B retry sensitivity

**Symptom**: At high concurrency (`--max-connections 20`), individual
samples sporadically fail with empty completions. The same scenarios
re-run sequentially almost always succeed.

**Workaround**: Drop concurrency to `--max-connections 3` or use the
`task_retry` script in `experiments/`. No solver change needed.

## Ollama (local models)

Inspect AI ships a native `ollama` provider that wraps Ollama's
OpenAI-compatible `/v1/chat/completions` endpoint. Model IDs follow the
form `ollama/<model>[:tag]`, e.g. `ollama/qwen3:14b`. Setup, model
selection, and remote-daemon configuration are documented in
[`ollama.md`](ollama.md). The compatibility notes below cover the
framework-side gotchas that go beyond plain "use the provider".

**Tool calling depends on the model**. The framework's game
environments (Werewolf, Diplomacy, Village, Committee, Bargaining,
Inbox) require structured tool calls in ACTION phases. Open-weights
models vary widely in tool-call quality:

- Known-good for tool calls: `qwen3:14b`, `qwen3:4b-instruct`,
  `llama3.1:8b`, `llama3.1:70b`, `gemma2:27b`.
- Models that don't support tool calls will exhaust the solver's
  `max_action_retries` budget on every ACTION phase and the sample will
  fail cleanly. Swap to a tool-capable model rather than raising the
  retry budget — the failure mode is correct and silencing it would hide
  a real capability gap.

**No API key needed for localhost**. Inspect's `ollama` provider
defaults the API key to a dummy `"ollama"` string and the base URL to
`http://localhost:11434/v1`. Nothing in `.env` is required for the
common case.

**Remote daemons** via `OLLAMA_BASE_URL` (mirrors how `DEEPSEEK_BASE_URL`
works for that provider):

```bash
export OLLAMA_BASE_URL=http://gpu-box.local:11434/v1
mb run debate --model ollama/qwen3:14b --limit 1
```

The `/v1` suffix matters — pointing at the bare host without it gives
`HTTP 404`.

## Adding a new quirk

If you discover a provider that needs framework-side handling:

1. Add the symptom + workaround here.
2. Prefer per-agent metadata (like `tool_choice_strategy`) over global
   provider switches so scenarios remain reproducible across provider
   changes.
3. Reference this file from any new comment in
   `src/manipulation_bench/game_solver.py` so future readers can find the
   full context without code archaeology.
