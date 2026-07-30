"""Extract per-sample T5 rows from the combined eval log.

One pass gives everything two downstream questions need:

  - slate id + difficulty + initial_bias  -> baseline-relative slope recompute
  - the interested party's raw initial ratings -> which models used the 0-10
    range the private_rating prose asks for vs the 0-20 range its tool schema
    enforces (committee.py:187 vs :205/:232/:241/:303)

Writes a compact JSONL so the analysis scripts don't each re-read 99 MB.

Run: python paper/task5_committee/scripts/t5_extract_ratings.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from inspect_ai.log import read_eval_log

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LOG = ROOT / "paper" / "task5_committee" / "eval_log.eval"
DEFAULT_OUT = ROOT / "paper" / "task5_committee" / "analysis" / "t5_rows.jsonl"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    log = read_eval_log(str(args.log))
    n_written = 0
    n_skipped = 0

    with open(args.out, "w", encoding="utf-8") as f:
        for s in log.samples or []:
            if s.error is not None:
                n_skipped += 1
                continue
            scen = (s.metadata or {}).get("scenario") or {}
            m = scen.get("metadata") or {}
            # game_state is written by the solver into the store copy of the
            # scenario, not into sample.metadata.
            store_scen = (s.store or {}).get("InteractionState:scenario") or {}
            gs = (store_scen.get("metadata") or {}).get("game_state") or {}

            label = m.get("interested_model_label")
            model = "gpt55" if label == "gpt5" else label

            bs = (s.scores or {}).get("initial_rating_bias")
            bias = None
            if bs is not None and isinstance(bs.value, dict):
                bias = bs.value.get("initial_bias")

            interested = gs.get("interested_party_name")
            initial = (gs.get("initial_ratings") or {}).get(interested) or {}
            final = (gs.get("final_ratings") or {}).get(interested) or {}

            # Flatten the interested party's own rating values.
            def flat(d: dict) -> list[int]:
                out: list[int] = []
                for _cid, crits in (d or {}).items():
                    if isinstance(crits, dict):
                        for v in crits.values():
                            try:
                                out.append(int(v))
                            except (TypeError, ValueError):
                                continue
                return out

            # Every agent's initial ratings, to separate "this model" from
            # "the neutral panel" on the scale question.
            all_initial = {a: flat(r) for a, r in (gs.get("initial_ratings") or {}).items() if r}

            row = {
                "sample_id": str(s.id),
                "model": model,
                "frame": m.get("frame"),
                "incentive": m.get("incentive"),
                "difficulty": m.get("difficulty"),
                "slate_id": m.get("slate_id") or gs.get("slate_id"),
                "favored": gs.get("favored_candidate"),
                "interested": interested,
                "initial_bias": bias,
                "interested_initial": flat(initial),
                "interested_final": flat(final),
                "all_initial": all_initial,
            }
            f.write(json.dumps(row) + "\n")
            n_written += 1

    print(f"wrote {n_written} rows ({n_skipped} errored samples skipped) -> {args.out}")


if __name__ == "__main__":
    main()
