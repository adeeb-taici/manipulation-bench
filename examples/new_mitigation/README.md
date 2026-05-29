# Adding a new mitigation (defense)

A **mitigation** is a plug-in that tries to *reduce* measured manipulation —
e.g. forewarn the targets, or run a critic LLM that flags the manipulator's
messages before they are delivered. Mitigations are resolved at runtime
(`-T mitigations=...`), so the same scenario JSONL runs baseline vs. defended
without regeneration.

This directory is a copy-pasteable starting point. The example
([`my_mitigation.py`](my_mitigation.py)) hardens every *protected* agent by
appending one line to its system prompt — it overrides a single hook.

## The interface

Subclass [`Mitigation`](../../src/manipulation_bench/mitigations/base.py) and
override only the hook(s) you need; the rest are no-ops:

| Hook | When | Use for |
|------|------|---------|
| `transform_agent` | once, before the loop | rewrite a role (e.g. add a skeptical-framing suffix) |
| `transform_messages` | per turn, before `generate` | rewrite the model input (async) |
| `transform_response` | per turn, after `generate` | flag / redact / rewrite the output before delivery (async) |

Targeting (manipulator vs. protected) is read from `AgentRole.adversary` via
`mitigations._targeting.is_adversary` — generators set that flag.

## Run it (no API key)

```bash
inspect eval src/manipulation_bench/task.py \
  -T scenarios=debate_2agent.jsonl \
  -T mitigations=examples.new_mitigation.my_mitigation.my_defense \
  --model mockllm/model --limit 1
```

## Five-step checklist

1. **Subclass `Mitigation`** in your own module. Override one hook; set
   `name` (it is stamped into `Turn.metadata['mitigations_applied']`).
2. **Add a no-arg factory** (`def my_defense(): return MyDefense()`) — the
   resolver calls it with no arguments.
3. **Wire `--model-role`** only if your defense calls another model (the
   built-in `critic_monitor` uses the `mitigation_critic` role).
4. **Smoke-test with `mockllm/model`** using the command above.
5. **Ship a real defense** by dropping it in
   `src/manipulation_bench/mitigations/` and re-exporting it from that
   package's `__init__.py`, so it resolves by bare name
   (`-T mitigations=my_defense`).

See the two reference defenses for the shapes:
[`prompt_suffix.py`](../../src/manipulation_bench/mitigations/prompt_suffix.py)
(~25 LOC, `transform_agent`) and
[`critic_monitor.py`](../../src/manipulation_bench/mitigations/critic_monitor.py)
(~80 LOC, `transform_response` with an LLM critic).
