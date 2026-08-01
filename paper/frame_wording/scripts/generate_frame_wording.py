"""Generate the T5/T6 frame-wording scenarios.

Varies ONLY the frame-axis wording. Everything else -- incentive text, difficulty
substrate/slate, scoring, agent layout -- comes from the published generators
unchanged: this script imports them and swaps the frame-text constant, then calls
their own scenario builders. Nothing in src/ or in the frozen generators is
modified.

Frame texts come from paper/frame_wording/frame_paraphrases.json, whose v1
entries are diff-checked byte-identical to the frozen FRAME_PROMPTS.

Fixed cells (paper/frame_wording/cell_selection.json, picked by the Appendix F
rule -- the (incentive, difficulty) cell whose |frame slope| is closest to the
per-task mean):
    committee  incentive=none, difficulty=medium
    inbox      incentive=high, difficulty=medium

Run: python paper/frame_wording/scripts/generate_frame_wording.py
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "paper/frame_wording/scenarios"
PARA = json.load(open(REPO / "paper/frame_wording/frame_paraphrases.json", encoding="utf-8"))

FRAMES = ("prohibitive", "pro_social", "minimal", "selfish", "permissive")
VERSIONS = (1, 2, 3)

# 5 frozen-roster models (Grok 4 deprecated) + Grok 4.3 substitute.
# Grok 4.3 runs its own v1 arm, so its v1->v2/v3 contrast is internally valid.
ROSTER = [
    ("claude", "model_claude"),
    ("gpt55", "model_gpt55"),
    ("gemini", "model_gemini"),
    ("grok43", "model_grok43"),
    ("llama", "model_llama"),
    ("deepseek", "model_deepseek"),
]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def gen_inbox() -> list[dict]:
    mod = load(REPO / "paper/task6_inbox/scripts/generate_task6_inbox.py", "gen_t6")
    orig = copy.deepcopy(mod.FRAME_PROMPTS["inbox"])
    # Substrates are JSON files on disk, not a module constant. The frozen design
    # runs 4 rows per (model, frame, incentive, difficulty) = 2 medium substrates
    # x 2 reps, so the sweep matches that.
    med = sorted(
        (json.loads(p.read_text(encoding="utf-8")) for p in mod.SUBSTRATE_DIR.glob("*.json")),
        key=lambda s: s["suppression_target"],
    )
    med = [s for s in med if s.get("difficulty") == "medium"]
    if len(med) != 2:
        raise SystemExit(f"expected 2 medium inbox substrates, found {len(med)} -- stopping")
    REPS_PER_SUBSTRATE = 2
    out = []
    try:
        for v in VERSIONS:
            for f in FRAMES:
                mod.FRAME_PROMPTS["inbox"][f] = PARA["inbox"][f][str(v)]
            for sub in med:
                for rep in range(REPS_PER_SUBSTRATE):
                    for label, role in ROSTER:
                        for f in FRAMES:
                            sc = mod.build_scenario(
                                substrate=sub,
                                frame=f,
                                incentive="high",
                                difficulty="medium",
                                model_label=label,
                                model_role=role,
                                rep=rep,
                            )
                            sc["id"] = f"fw_{sc['id']}_v{v}"
                            sc["metadata"]["frame_version"] = v
                            sc["metadata"]["frame_text"] = PARA["inbox"][f][str(v)]
                            out.append(sc)
    finally:
        mod.FRAME_PROMPTS["inbox"] = orig
    return out


def gen_committee() -> list[dict]:
    mod = load(REPO / "paper/task5_committee/scripts/generate_task5_committee.py", "gen_t5")
    orig = copy.deepcopy(mod.FRAMES)
    orig_models = list(mod.UNDER_TEST_MODELS)
    mod.UNDER_TEST_MODELS = [{"label": lbl, "role": role} for lbl, role in ROSTER]
    out = []
    try:
        for v in VERSIONS:
            for f in FRAMES:
                # dict-valued: vary 'interested' only, hold 'neutral' byte-identical
                entry = dict(orig[f])
                entry["interested"] = PARA["committee"][f][str(v)]
                mod.FRAMES[f] = entry
            scen = mod._generate(
                interested_labels=[lbl for lbl, _ in ROSTER],
                frames=list(FRAMES),
                incentives=["none"],
                difficulties=["medium"],
                seeds_per_cell=1,
            )
            for sc in scen:
                sc["id"] = f"fw_{sc['id']}_v{v}"
                md = sc.setdefault("metadata", {})
                md["frame_version"] = v
                md["frame_text"] = (
                    PARA["committee"][md.get("frame", "?")][str(v)]
                    if md.get("frame") in PARA["committee"]
                    else None
                )
            out += scen
    finally:
        mod.FRAMES.clear()
        mod.FRAMES.update(orig)
        mod.UNDER_TEST_MODELS = orig_models
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for env, fn in (("inbox", gen_inbox), ("committee", gen_committee)):
        rows = fn()
        p = OUT / f"frame_wording_{env}.jsonl"
        with open(p, "w", encoding="utf-8") as w:
            for r in rows:
                w.write(json.dumps(r, ensure_ascii=False) + "\n")
        per_v = {v: sum(1 for r in rows if r["metadata"]["frame_version"] == v) for v in VERSIONS}
        print(f"  {p.name:<34} {len(rows):5d} scenarios   per version {per_v}")
        ids = {r["id"] for r in rows}
        if len(ids) != len(rows):
            raise SystemExit(f"{env}: duplicate scenario ids")


if __name__ == "__main__":
    main()
