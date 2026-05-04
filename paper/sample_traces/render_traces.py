"""Render full conversation traces (system, user, assistant, tool calls) for one
large + one small model sample per paper task, into Markdown files.

Usage:
    python paper/sample_traces/render_traces.py
    python paper/sample_traces/render_traces.py --task 4

Output: paper/sample_traces/task<N>_<env>_traces.md
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from inspect_ai.log import read_eval_log

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "paper" / "sample_traces"

# Task → (env_name, large_log, small_log, large_pick_model, small_pick_model)
# pick_model is the canonical metadata.model label to filter on.
TASKS = [
    ("task1_bargaining",  "bargaining", "claude",   "gpt41"),
    ("task2_debate",      "debate",     "claude",   "gpt41"),
    ("task3_village",     "village",    "claude",   "gpt41"),
    ("task4_sales",       "sales",      "claude",   "gpt41"),
    ("task5_committee",   "committee",  "claude",   "gpt41"),
    # task6_inbox: only large log exists. Include large only.
    ("task6_inbox",       "inbox",      "claude",   None),
]


def resolve_attachments(text: str, attachments: dict) -> str:
    """Replace attachment://<hash> markers with the actual content."""
    if not isinstance(text, str):
        return text
    def sub(m):
        h = m.group(1)
        return attachments.get(h, f"<missing-attachment:{h}>")
    return re.sub(r"attachment://([a-f0-9]+)", sub, text)


def stringify_content(content, attachments) -> str:
    """ChatMessage.content can be str or list[ContentText|ContentImage|...]."""
    if content is None:
        return ""
    if isinstance(content, str):
        return resolve_attachments(content, attachments)
    if isinstance(content, list):
        parts = []
        for c in content:
            t = getattr(c, "text", None)
            if t is not None:
                parts.append(resolve_attachments(t, attachments))
            else:
                parts.append(f"[{type(c).__name__}]")
        return "\n".join(parts)
    return str(content)


def fence(lang: str, body: str) -> str:
    body = body.rstrip()
    # Avoid colliding with backticks in body
    delim = "```"
    while delim in body:
        delim += "`"
    return f"{delim}{lang}\n{body}\n{delim}"


def render_event(e, attachments) -> str:
    """Render one ModelEvent as Markdown."""
    out = []
    role = getattr(e, "role", None)
    model = getattr(e, "model", None)
    out.append(f"### Model call — role=`{role}`  model=`{model}`")

    tools = getattr(e, "tools", None)
    if tools:
        out.append(f"**Tools available:** " + ", ".join(f"`{t.name}`" for t in tools))

    # Inputs
    inp = getattr(e, "input", None) or []
    out.append("\n**Inputs:**\n")
    for m in inp:
        content = stringify_content(getattr(m, "content", None), attachments)
        tcs = getattr(m, "tool_calls", None)
        if m.role == "system":
            out.append("**[system]**")
            out.append(fence("text", content))
        elif m.role == "user":
            out.append("**[user]**")
            out.append(fence("text", content))
        elif m.role == "assistant":
            label = "**[assistant]**"
            out.append(label)
            if content:
                out.append(fence("text", content))
            if tcs:
                for tc in tcs:
                    out.append(f"_tool call:_ `{tc.function}({tc.arguments})`")
        elif m.role == "tool":
            out.append(f"**[tool result — {getattr(m, 'function', '?')}]**")
            out.append(fence("text", content))
        else:
            out.append(f"**[{m.role}]**")
            out.append(fence("text", content))

    # Output
    o = getattr(e, "output", None)
    out.append("\n**Output (assistant):**\n")
    if o is None:
        out.append("_(no output)_")
    else:
        msg = o.message
        content = stringify_content(getattr(msg, "content", None), attachments)
        if content:
            out.append(fence("text", content))
        tcs = getattr(msg, "tool_calls", None) or []
        for tc in tcs:
            out.append(f"_tool call:_ `{tc.function}({tc.arguments})`")
        if not content and not tcs:
            out.append("_(empty)_")
    out.append("")
    return "\n".join(out)


MODEL_ALIASES = {
    # canonical short label → list of strings any of these tasks store it as
    "claude":    ("claude", "Claude-Opus-4.7", "claude-opus-4.7"),
    "haiku45":   ("haiku45", "Claude-Haiku-4.5", "claude-haiku-4.5"),
    "haiku35":   ("haiku35", "Claude-Haiku-3.5"),
    "sonnet46":  ("sonnet46", "Claude-Sonnet-4.6"),
    "sonnet37":  ("sonnet37", "Claude-Sonnet-3.7"),
    "gpt5":      ("gpt5", "GPT-5", "gpt55", "GPT-5.5"),
    "gpt41":     ("gpt41", "GPT-4.1", "gpt-4.1"),
    "gpt41mini": ("gpt41mini", "GPT-4.1-mini", "gpt-4.1-mini"),
    "gpt41nano": ("gpt41nano", "GPT-4.1-nano", "gpt-4.1-nano"),
    "gpt54mini": ("gpt54mini", "GPT-5.4-mini"),
    "gpt54nano": ("gpt54nano", "GPT-5.4-nano"),
    "gemini":    ("gemini", "Gemini-3.1-Pro", "Gemini-3-Pro"),
    "grok":      ("grok", "Grok-4"),
    "llama":     ("llama", "Llama-3.3-70B", "Llama-3-70B"),
    "deepseek":  ("deepseek", "DeepSeek-V4-Pro", "DeepSeek-chat"),
}


def find_sample_for_model(samples, model_label):
    """Return the first non-error sample whose focal-model metadata matches.

    Different tasks store the focal model under different keys. We check
    top-level `model`, scenario.metadata.{model, focal_model, manipulator_model}.
    """
    targets = set(MODEL_ALIASES.get(model_label, (model_label,)))
    targets_lower = {t.lower() for t in targets}

    def matches(val):
        return val is not None and (val in targets or str(val).lower() in targets_lower)

    for s in samples:
        if s.error:
            continue
        md = s.metadata or {}
        sc = md.get("scenario") or {}
        smd = sc.get("metadata") or {}
        for v in (md.get("model"),
                  smd.get("model"),
                  smd.get("focal_model"),
                  smd.get("manipulator_model"),
                  smd.get("interested_model_label")):
            if matches(v):
                return s
    return None


def render_sample(s, label) -> str:
    md = s.metadata or {}
    sc = md.get("scenario") or {}
    smd = sc.get("metadata") or {}
    out = [f"## {label}", ""]
    out.append(f"- **sample id:** `{s.id}`")
    out.append(f"- **frame / incentive / difficulty:** "
               f"`{md.get('frame') or smd.get('frame')}` / "
               f"`{md.get('incentive') or smd.get('incentive')}` / "
               f"`{md.get('difficulty') or smd.get('difficulty')}`")
    if md.get("model"):
        out.append(f"- **model (single-agent):** `{md['model']}`")
    mm = smd.get("model_mapping")
    if mm:
        out.append(f"- **model_mapping:**")
        for agent, model in mm.items():
            out.append(f"  - `{agent}` → `{model}`")
    if smd.get("manipulator"):
        out.append(f"- **manipulator:** `{smd['manipulator']}` (`{smd.get('manipulator_model')}`)")

    # Agent system prompts (multi-agent tasks)
    agents = sc.get("agents") or []
    if agents:
        out.append("")
        out.append("### Agent system prompts")
        for a in agents:
            out.append(f"\n#### `{a['name']}` (model_role=`{a.get('model_role')}`, position=`{a.get('position')}`)")
            sp = a.get("system_prompt") or ""
            out.append(fence("text", sp))

    # Scores
    scores = s.scores or {}
    if scores:
        out.append("")
        out.append("### Scores")
        for sn, sv in scores.items():
            v = sv.value
            if isinstance(v, dict):
                out.append(f"- **{sn}:** ")
                for k, val in v.items():
                    if isinstance(val, float):
                        out.append(f"  - `{k}`: {val:.4f}")
                    else:
                        out.append(f"  - `{k}`: {val}")
            else:
                out.append(f"- **{sn}:** `{v}`")

    # Trace
    out.append("")
    out.append("### Conversation trace (per model call)")
    out.append("")
    attachments = s.attachments or {}
    events = s.events or []
    n = 0
    for e in events:
        if type(e).__name__ == "ModelEvent":
            n += 1
            out.append(f"---\n")
            out.append(f"#### Call {n}")
            out.append(render_event(e, attachments))
    if n == 0:
        # fallback: render messages
        out.append("_(no ModelEvents — falling back to flat message list)_")
        for i, m in enumerate(s.messages or []):
            out.append(f"\n**msg{i} [{m.role}]**")
            content = stringify_content(getattr(m, "content", None), attachments)
            out.append(fence("text", content))

    return "\n".join(out)


def render_task(task_dir: str, env_name: str, large_pick: str, small_pick: str | None):
    large_log = ROOT / "paper" / task_dir / "eval_log.eval"
    small_log = ROOT / "paper" / task_dir / "eval_log_small_model_sweep.eval"
    out_path = OUT_DIR / f"{task_dir}_traces.md"

    parts = [f"# {task_dir} — sample traces", ""]
    parts.append(f"Environment: **{env_name}**.  One sample per model.")
    parts.append("")

    # Large
    if large_log.exists():
        print(f"  loading {large_log.name} ...", flush=True)
        log = read_eval_log(str(large_log))
        s = find_sample_for_model(log.samples, large_pick)
        if s is None:
            parts.append(f"_(no sample found in large log for model `{large_pick}`)_")
        else:
            parts.append(render_sample(s, f"Large model: `{large_pick}`  (from `{large_log.name}`)"))
        parts.append("")

    # Small
    if small_pick and small_log.exists():
        print(f"  loading {small_log.name} ...", flush=True)
        log = read_eval_log(str(small_log))
        s = find_sample_for_model(log.samples, small_pick)
        if s is None:
            parts.append(f"_(no sample found in small log for model `{small_pick}`)_")
        else:
            parts.append(render_sample(s, f"Small model: `{small_pick}`  (from `{small_log.name}`)"))
        parts.append("")
    elif small_pick is None:
        parts.append(f"_(no small-model sweep log for {task_dir})_")

    out_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"  wrote {out_path.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", type=int, default=None,
                    help="Render only task N (1-6). Default: all.")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for i, (task_dir, env, large, small) in enumerate(TASKS, 1):
        if args.task is not None and args.task != i:
            continue
        print(f"[{task_dir}]")
        render_task(task_dir, env, large, small)


if __name__ == "__main__":
    main()
