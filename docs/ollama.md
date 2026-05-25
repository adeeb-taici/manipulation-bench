# Local models via Ollama

manipulation-bench works against any model that [Inspect AI](https://inspect.aisi.org.uk/) can reach, including local models served by [Ollama](https://ollama.com/). This lets you run the framework offline on a laptop, develop without burning API budget, and exercise the eval pipeline in CI without provider keys.

## Why Ollama

- **No API key, no per-token cost.** A single binary runs an OpenAI-compatible HTTP server on `localhost:11434`.
- **Reproducible.** A pulled model is a content-addressed blob; the same `qwen3:14b` is the same `qwen3:14b` tomorrow.
- **Tool calling works.** Recent open-weights models (Qwen3, Llama 3.1+, Gemma 2+, etc.) emit OpenAI-format tool calls, which the framework's game environments need for ACTION phases.

## Setup

1. **Install Ollama**: download from [ollama.com/download](https://ollama.com/download) (or `brew install ollama` / `winget install Ollama.Ollama`).
2. **Start the daemon**: `ollama serve`, or use the bundled tray / service.
3. **Pull a tool-capable model**:
   ```bash
   ollama pull qwen3:4b-instruct   # small, fast — good for smoke runs
   ollama pull qwen3:14b           # better tool-call reliability
   ```
4. **Verify**: `ollama list` should show the pulled model.

No `.env` change is needed for the localhost case — Inspect's `ollama` provider sets a dummy API key automatically and defaults to `http://localhost:11434/v1`.

## Run via `mb`

The `mb` CLI passes the model ID through to `inspect eval` verbatim, so the Ollama provider prefix is all you need:

```bash
# Smallest tool-capable smoke run
mb run debate --model ollama/qwen3:4b-instruct --limit 1

# Same with explicit per-role bindings (different models per role)
mb run debate --models debater=ollama/qwen3:14b,judge=ollama/qwen3:4b-instruct

# A game environment (ACTION-phase, tool-call-heavy)
mb run village --model ollama/qwen3:14b --limit 1
```

Per-role syntax (`name=provider/model`) splits on `=`, so colons in Ollama tags (`qwen3:4b-instruct`) parse correctly.

## Choosing a model

The framework's environments split into two groups:

| Group | Envs | Tool-call requirement |
|---|---|---|
| **Tool-light** | Debate, Sales | Optional — any instruct model works for the agents; the judge is a normal completion call. |
| **Tool-heavy** | Werewolf, Diplomacy, Village, Committee, Bargaining, Inbox | ACTION phases require structured tool calls; the model must emit OpenAI-format `tool_calls`. |

For tool-heavy envs, filter the Ollama catalog for "Tools" support. Known-good local options: `qwen3:14b`, `qwen3:4b-instruct`, `llama3.1:8b`, `llama3.1:70b`, `gemma2:27b`. Models that *don't* support tool calls will exhaust the solver's retry budget on ACTION phases and the sample will fail cleanly — swap to a tool-capable variant rather than reduce the retry budget.

## Remote daemons

Ollama listens on `localhost` by default. To point at a daemon on another machine (e.g. a GPU box on your LAN), set `OLLAMA_BASE_URL` before running:

```bash
# bash / zsh
export OLLAMA_BASE_URL=http://gpu-box.local:11434/v1
mb run debate --model ollama/qwen3:14b --limit 1
```

```powershell
# PowerShell
$env:OLLAMA_BASE_URL = "http://gpu-box.local:11434/v1"
mb run debate --model ollama/qwen3:14b --limit 1
```

The same `OLLAMA_BASE_URL` syntax works for any Ollama-compatible server (some OpenAI-compatible inference servers also accept the `/v1` path).

## Mixing local and cloud

Different roles can be bound to different providers in the same run — useful when you want a cheap local judge to score frontier-model agents (or vice versa):

```bash
mb run debate --models \
  debater_a=openrouter/anthropic/claude-opus-4.7,\
  debater_b=openrouter/openai/gpt-5.5-20260423,\
  judge=ollama/qwen3:14b
```

## Troubleshooting

- **`connection refused`** — the daemon isn't running. Start `ollama serve` or open the tray app.
- **Slow first response** — Ollama loads the model on first request. Re-run the same command and the second call will be fast.
- **`tool_calls` empty / sample fails after retries** — the model doesn't support tool calling. Swap to a tool-capable model (see table above).
- **`HTTP 404` against `OLLAMA_BASE_URL`** — the URL needs the `/v1` suffix (e.g. `http://host:11434/v1`, not `http://host:11434`).

For framework-side workarounds and the broader provider compatibility table, see [`provider_quirks.md`](provider_quirks.md).
