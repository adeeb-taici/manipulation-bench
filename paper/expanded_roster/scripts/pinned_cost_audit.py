"""Audit where the pinned-support cost actually goes, from the committed T2 log.

cost_model.py established that pinned support agents cost a fixed ~$262 per
added model-config and dominate every roster decision. This script asks the next
question -- WHICH pinned call is that money -- by reading per-model-call events
out of paper/task2_debate/eval_log.eval rather than trusting the label.

It finds two things the aggregate hides:

1. cost_model.py's line labelled "claude-opus-4.7 (truthful debater)" is not the
   truthful debater. Debate turns are ~4.7k input tokens per scenario across 4
   calls. Nearly all Opus spend is the SCORER stack, which is pinned to the same
   model (task2_debate/prereg.md sec.3 pins judge and truthful debater to the
   same slug, which is why the aggregate cannot separate them). The total is
   right to within 3%; the attribution is not.

2. ~75% of Opus input tokens sit in prompts sent VERBATIM 7 times -- two
   repeat-groups of 7, one per agent. That is juror_voting(n_jurors=7)
   (scorers/voting.py), which re-sends the full transcript per vote. The votes
   are genuine independent draws at temperature 0.7 and issued sequentially, so
   this is the scorer working as designed, not a bug.

Repeated prompts are detected by message CONTENT, not by hashing the raw event
input: Inspect stamps a unique id on every message instance, so two byte-identical
prompts have different serialisations and a naive key finds zero duplicates.

Run: python paper/expanded_roster/scripts/pinned_cost_audit.py
"""

from __future__ import annotations

import collections
import json
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LOG = REPO / "paper/task2_debate/eval_log.eval"

JUDGE_IN, JUDGE_OUT = 5.00, 25.00  # claude-opus-4.7 $/M, OpenRouter catalogue
N_T2 = 690  # T2 scenarios per model-config, full factorial
STRIDE_TARGET = 400  # stratified sample size across the whole log


def content_key(inp) -> str:
    """Identity of a prompt by content alone, ignoring per-message uuids."""
    parts = []
    for m in inp or []:
        if isinstance(m, dict):
            c = m.get("content")
            parts.append((c if isinstance(c, str) else json.dumps(c))[:300])
    return "|".join(parts)


def main() -> None:
    if not LOG.exists():
        raise SystemExit(f"missing {LOG} -- run `git lfs pull` first")
    z = zipfile.ZipFile(LOG)
    names = sorted(n for n in z.namelist() if n.startswith("samples/"))
    sel = names[:: max(1, len(names) // STRIDE_TARGET)]

    n = 0
    o_in = o_out = 0
    r_in = r_out = 0
    group_shapes: collections.Counter = collections.Counter()
    for nm in sel:
        s = json.loads(z.read(nm))
        ev = [
            e
            for e in (s.get("events") or [])
            if e.get("event") == "model" and "opus" in str(e.get("model", ""))
        ]
        if not ev:
            continue
        n += 1
        seen = collections.Counter(content_key(e.get("input")) for e in ev)
        group_shapes[tuple(sorted((v for v in seen.values()), reverse=True))] += 1
        for e in ev:
            u = (e.get("output") or {}).get("usage") or {}
            i, o = u.get("input_tokens", 0), u.get("output_tokens", 0)
            o_in += i
            o_out += o
            if seen[content_key(e.get("input"))] > 1:
                r_in += i
                r_out += o

    def dollars(tin: float, tout: float) -> float:
        return tin * JUDGE_IN / 1e6 + tout * JUDGE_OUT / 1e6

    per_all = dollars(o_in / n, o_out / n)
    per_rep = dollars(r_in / n, r_out / n)

    print("=" * 88)
    print(f"PINNED-COST AUDIT -- T2 debate, {n} stratified samples of {len(names)}")
    print("=" * 88)
    print(f"  Opus per scenario           in {o_in / n:>9,.0f}   out {o_out / n:>7,.0f}")
    print(
        f"  of which 7x-repeated prompts in {r_in / n:>9,.0f}   out {r_out / n:>7,.0f}"
        f"   ({100 * r_in / o_in:.1f}% of input)"
    )
    print()
    print(f"  {'':<34}{'$/scenario':>12}{'$/config (x690)':>18}")
    print(f"  {'Opus total':<34}{per_all:>12.4f}{per_all * N_T2:>18.2f}")
    print(f"  {'  juror_voting (unreported)':<34}{per_rep:>12.4f}{per_rep * N_T2:>18.2f}")
    print(
        f"  {'  everything else':<34}{per_all - per_rep:>12.4f}{(per_all - per_rep) * N_T2:>18.2f}"
    )
    print()
    print("  repeat-group shapes (calls sharing one prompt), most common first:")
    for shape, c in group_shapes.most_common(3):
        print(f"    {c:>4} samples  {shape}")
    print()
    print("  cross-check: cost_model.py assumes Opus $217.68/config from 52,732 in / 2,073 out")
    print(
        f"               this audit measures ${per_all * N_T2:.2f}/config -- agreement within "
        f"{abs(per_all * N_T2 - 217.68) / 217.68 * 100:.0f}%"
    )


if __name__ == "__main__":
    main()
