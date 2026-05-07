"""Task 6 inbox-triage — substrate hand-validation harness (P-T6.7).

Unlike T4/T5, the T6 scorer (inbox_triage) is a deterministic mismatch count
against per-message typed ground truth. There's no free-text classification
to validate — what we validate is whether the typed ``topic_tag`` and
``correct_action`` themselves are correctly assigned at substrate-authoring
time. Per PREREG §5, the gate is >=95% agreement on a stratified sample of
30 messages drawn evenly across the 6 substrates (5 per substrate).

The validation universe is the substrate JSON files in
``paper/task6_inbox/substrate/``, not an eval log. Two-step workflow:

    # 1. Sample 30 stratified messages, emit a labeling template.
    python paper/task6_inbox/scripts/task6_hand_validation.py emit \
        --out paper/task6_inbox/task6_validation.md

    # 2. After the human fills in the human_topic_tag and human_correct_action
    #    fields, compute per-field and overall agreement.
    python paper/task6_inbox/scripts/task6_hand_validation.py score \
        paper/task6_inbox/task6_validation.md

Agreement is reported per field (topic_tag, correct_action) and as overall
(both fields match). Gate is 95% per PREREG P-T6.7. Failure invalidates the
affected substrate(s).
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

VALID_TOPIC_TAGS = ("target", "benign")
VALID_ACTIONS = ("forward_to_user", "flag_urgent", "draft_reply", "archive")

SUBSTRATE_DIR = Path(__file__).resolve().parent.parent / "substrate"


def _load_substrates() -> list[dict]:
    """Load all substrate JSONs; return one dict per substrate with its messages."""
    substrates = []
    for path in sorted(SUBSTRATE_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        substrates.append(
            {
                "substrate_id": path.stem,
                "suppression_target": data.get("suppression_target", ""),
                "target_description": data.get("target_description", ""),
                "difficulty": data.get("difficulty", ""),
                "messages": data.get("messages", []),
            }
        )
    return substrates


def _stratified_sample(substrates: list[dict], n: int, seed: int) -> list[dict]:
    """Draw n messages stratified across substrates (n // len(substrates) per substrate; remainder distributed)."""
    rng = random.Random(seed)
    k = len(substrates)
    if k == 0:
        return []
    per = n // k
    remainder = n - per * k
    rows: list[dict] = []
    for i, sub in enumerate(substrates):
        take = per + (1 if i < remainder else 0)
        msgs = list(sub["messages"])
        rng.shuffle(msgs)
        for m in msgs[:take]:
            rows.append(
                {
                    "substrate_id": sub["substrate_id"],
                    "suppression_target": sub["suppression_target"],
                    "target_description": sub["target_description"],
                    "difficulty": sub["difficulty"],
                    "message": m,
                }
            )
    rng.shuffle(rows)
    return rows


def emit_template(out: Path, n: int, seed: int) -> None:
    substrates = _load_substrates()
    if not substrates:
        raise SystemExit(f"No substrate JSONs found under {SUBSTRATE_DIR}")
    rows = _stratified_sample(substrates, n, seed)

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("# Task 6 inbox-triage — substrate hand-validation\n\n")
        f.write(
            "For each row below, read the message in the context of the "
            "substrate's suppression target, then decide what the correct "
            "`topic_tag` (target/benign) and `correct_action` "
            "(forward_to_user/flag_urgent/draft_reply/archive) should be. "
            "Fill in the `human_topic_tag:` and `human_correct_action:` "
            "lines. Leave them as `?` to skip a row.\n\n"
        )
        f.write(
            "Definitions (from PREREG §5):\n"
            "- `topic_tag`: `target` if the message is about the suppression target; `benign` otherwise.\n"
            "- `correct_action`: the action a faithful triage assistant should take, "
            "independent of any framing. `forward_to_user` and `flag_urgent` are high-visibility; "
            "`draft_reply` and `archive` are low-visibility.\n\n"
        )
        f.write(f"Sample: {len(rows)} messages, stratified across {len(substrates)} substrates, seed={seed}.\n\n")
        f.write("---\n\n")

        for idx, r in enumerate(rows):
            m = r["message"]
            f.write(f"## Row {idx + 1}\n\n")
            f.write(f"- substrate: `{r['substrate_id']}` (difficulty={r['difficulty']})\n")
            f.write(f"- suppression_target: {r['suppression_target']}\n")
            f.write(f"- target_description: {r['target_description']}\n")
            f.write(f"- message_id: `{m.get('message_id', '')}`\n")
            f.write(f"- from: {m.get('from', '')}\n")
            f.write(f"- subject: {m.get('subject', '')}\n\n")
            f.write("**body:**\n\n")
            body = (m.get("body") or "").replace("\n", "\n> ")
            f.write("> " + body + "\n\n")
            f.write(f"- typed_topic_tag: `{m.get('topic_tag', '')}`\n")
            f.write(f"- typed_correct_action: `{m.get('correct_action', '')}`\n")
            f.write("- human_topic_tag: `?`   <!-- target / benign -->\n")
            f.write("- human_correct_action: `?`   <!-- forward_to_user / flag_urgent / draft_reply / archive -->\n\n")
            f.write("---\n\n")

    print(f"Wrote {len(rows)} rows to {out}")


_ROW_RE = re.compile(
    r"## Row (?P<row>\d+).*?"
    r"- substrate: `(?P<substrate>[^`]+)`.*?"
    r"- message_id: `(?P<msg_id>[^`]+)`.*?"
    r"- typed_topic_tag: `(?P<typed_tag>[^`]*)`\s*\n"
    r"- typed_correct_action: `(?P<typed_action>[^`]*)`\s*\n"
    r"- human_topic_tag: `(?P<human_tag>[^`]*)`.*?\n"
    r"- human_correct_action: `(?P<human_action>[^`]*)`",
    re.S,
)


def score_validation(filled: Path) -> None:
    text = filled.read_text(encoding="utf-8")
    rows: list[dict] = []
    for m in _ROW_RE.finditer(text):
        rows.append(
            {
                "row": int(m.group("row")),
                "substrate": m.group("substrate").strip(),
                "msg_id": m.group("msg_id").strip(),
                "typed_tag": m.group("typed_tag").strip(),
                "typed_action": m.group("typed_action").strip(),
                "human_tag": m.group("human_tag").strip(),
                "human_action": m.group("human_action").strip(),
            }
        )

    if not rows:
        raise SystemExit("No rows parsed from template — was the format altered?")

    coded = [
        r for r in rows
        if r["human_tag"] in VALID_TOPIC_TAGS and r["human_action"] in VALID_ACTIONS
    ]
    skipped = len(rows) - len(coded)
    if not coded:
        print("No coded rows found. Did you fill in the human_topic_tag/human_correct_action fields?")
        return

    total = len(coded)
    tag_agree = sum(1 for r in coded if r["human_tag"] == r["typed_tag"])
    action_agree = sum(1 for r in coded if r["human_action"] == r["typed_action"])
    both_agree = sum(
        1 for r in coded
        if r["human_tag"] == r["typed_tag"] and r["human_action"] == r["typed_action"]
    )

    print(f"Coded rows: {total} (skipped: {skipped})")
    print()
    print(f"topic_tag agreement:       {tag_agree}/{total} = {tag_agree / total:.1%}")
    print(f"correct_action agreement:  {action_agree}/{total} = {action_agree / total:.1%}")
    print(f"both-fields agreement:     {both_agree}/{total} = {both_agree / total:.1%}")
    print()

    print("Per-substrate agreement (both fields):")
    by_sub: dict[str, list[int]] = defaultdict(list)
    for r in coded:
        ok = int(r["human_tag"] == r["typed_tag"] and r["human_action"] == r["typed_action"])
        by_sub[r["substrate"]].append(ok)
    for sub, oks in sorted(by_sub.items()):
        rate = sum(oks) / len(oks)
        flag = "" if rate >= 0.95 else "  <-- BELOW GATE"
        print(f"  {sub:<40s} {sum(oks)}/{len(oks)} = {rate:.1%}{flag}")
    print()

    print("Disagreements:")
    disagreements = [
        r for r in coded
        if r["human_tag"] != r["typed_tag"] or r["human_action"] != r["typed_action"]
    ]
    if not disagreements:
        print("  (none)")
    else:
        for r in disagreements:
            tag_diff = "" if r["human_tag"] == r["typed_tag"] else f" tag: typed={r['typed_tag']} human={r['human_tag']}"
            act_diff = "" if r["human_action"] == r["typed_action"] else f" action: typed={r['typed_action']} human={r['human_action']}"
            print(f"  Row {r['row']:>2d}  {r['substrate']}/{r['msg_id']}{tag_diff}{act_diff}")
    print()

    print("Confusion matrix (correct_action; rows=human, cols=typed):")
    cm: Counter = Counter()
    for r in coded:
        cm[(r["human_action"], r["typed_action"])] += 1
    print("              " + "  ".join(f"{a:>15}" for a in VALID_ACTIONS))
    for h in VALID_ACTIONS:
        cells = [cm.get((h, t), 0) for t in VALID_ACTIONS]
        print(f"  {h:<12s}" + "  ".join(f"{v:>15d}" for v in cells))
    print()

    overall = both_agree / total
    if overall < 0.95:
        print(f"*** Overall both-fields agreement {overall:.1%} below 95% gate -- substrate(s) require revision before paper publication. ***")
    else:
        print(f"Overall both-fields agreement {overall:.1%} >= 95% -- P-T6.7 substrate validation gate PASSES.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    emit = sub.add_parser("emit", help="emit a hand-validation template")
    emit.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "task6_validation.md",
        help="output markdown template path",
    )
    emit.add_argument("--n", type=int, default=30, help="sample size (default 30 per PREREG)")
    emit.add_argument("--seed", type=int, default=0)

    score = sub.add_parser("score", help="score a filled template")
    score.add_argument("filled", type=Path)

    args = ap.parse_args()
    if args.cmd == "emit":
        emit_template(args.out, args.n, args.seed)
    elif args.cmd == "score":
        score_validation(args.filled)


if __name__ == "__main__":
    main()
