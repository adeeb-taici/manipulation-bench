"""Append T6 inbox rows to paper/cross_task/results.csv.

Memory-light alternative to a full eval_logs_to_csv rerun: reads only the T6
canonical log + the OpenAI/Anthropic sweep T6 logs, produces rows in the same
schema as the existing results.csv, then concatenates.

Reuses _row_from_sample() from load.py for schema consistency.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

from inspect_ai.log import read_eval_log_samples

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).parent))

from load import _row_from_sample, _flatten_metadata  # noqa: E402

EXISTING_CSV = REPO_ROOT / "paper/cross_task/data/results.csv"
DEST_CSV = REPO_ROOT / "paper/cross_task/data/results.csv"
CSV_MIRROR = REPO_ROOT / "paper/cross_task/data/corpus.csv"

T6_LOGS: list[Path] = [
    REPO_ROOT / "paper/task6_inbox/eval_log.eval",
    *sorted(REPO_ROOT.glob("logs/openai_sweep/*_t6/*.eval")),
    *sorted(REPO_ROOT.glob("logs/openai_sweep/*_t6_pilot/*.eval")),
    *sorted(REPO_ROOT.glob("logs/anthropic_sweep/*_t6/*.eval")),
    *sorted(REPO_ROOT.glob("logs/anthropic_sweep/*_t6_pilot/*.eval")),
]


def _variant_for(path: Path) -> str:
    if "openai_sweep" in path.parts or "anthropic_sweep" in path.parts:
        return "small_model_sweep"
    if path.name == "eval_log.eval":
        return "canonical"
    return "other"


def _flatten_scores(scores: dict[str, Any] | None) -> dict[str, Any]:
    if not scores:
        return {}
    out: dict[str, Any] = {}
    for scorer_name, score in scores.items():
        value = getattr(score, "value", None)
        if value is None:
            continue
        if isinstance(value, dict):
            for k, v in value.items():
                out[f"{scorer_name}__{k}"] = v
        else:
            out[scorer_name] = value
    return out


EXTRA_SETUP_KEYS = ("scenario_id", "manipulator", "num_agents", "topology", "topic")


def _extra_setup_fields(sample: Any, md: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"epoch": getattr(sample, "epoch", None)}
    for k in EXTRA_SETUP_KEYS:
        out[k] = md.get(k)
    mm = md.get("model_mapping")
    out["model_mapping"] = json.dumps(mm) if mm is not None else None
    return out


def _t6_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in T6_LOGS:
        if not path.exists():
            continue
        variant = _variant_for(path)
        log_rows = 0
        for sample in read_eval_log_samples(str(path), all_samples_required=False):
            base = _row_from_sample(sample, "inbox")
            if base is None:
                continue
            md = _flatten_metadata(sample)
            row: dict[str, Any] = {
                "task": "inbox",
                "variant": variant,
                "log_path": str(path.relative_to(REPO_ROOT)),
                "sample_id": base["sample_id"],
                "model": base["model"],
                "frame": base["frame"],
                "incentive": base["incentive"],
                "difficulty": base["difficulty"],
                "cluster_id": base["cluster_id"],
                "manipulation_metric": base["metric"],
                "manipulation_occurred": base["manipulation_occurred"],
            }
            row.update(_extra_setup_fields(sample, md))
            row.update(_flatten_scores(sample.scores))
            rows.append(row)
            log_rows += 1
        print(f"[append_t6] {path.relative_to(REPO_ROOT)}: {log_rows} rows", file=sys.stderr)
    return rows


def main() -> None:
    new_rows = _t6_rows()
    if not new_rows:
        print("[append_t6] no T6 rows extracted", file=sys.stderr)
        sys.exit(1)
    print(f"[append_t6] extracted {len(new_rows)} T6 rows", file=sys.stderr)

    with EXISTING_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        existing_header = next(reader)
        existing_n = sum(1 for _ in reader)

    new_keys = set()
    for r in new_rows:
        new_keys.update(r.keys())
    novel = [k for k in sorted(new_keys) if k not in existing_header]
    if novel:
        print(f"[append_t6] new columns added by T6: {novel}", file=sys.stderr)

    final_header = list(existing_header) + novel
    field_set = set(final_header)

    tmp_out = DEST_CSV.with_suffix(".tmp.csv")
    n_existing_written = 0
    n_t6_written = 0
    with EXISTING_CSV.open("r", encoding="utf-8", newline="") as src, \
         tmp_out.open("w", encoding="utf-8", newline="") as dst:
        reader = csv.reader(src)
        next(reader)
        writer = csv.writer(dst)
        writer.writerow(final_header)
        for row in reader:
            row_padded = row + [""] * (len(final_header) - len(row))
            writer.writerow(row_padded)
            n_existing_written += 1

        dict_writer = csv.DictWriter(dst, fieldnames=final_header, extrasaction="ignore")
        for r in new_rows:
            dict_writer.writerow({k: ("" if v is None else v) for k, v in r.items() if k in field_set})
            n_t6_written += 1

    tmp_out.replace(DEST_CSV)
    print(f"[append_t6] wrote {n_existing_written} existing + {n_t6_written} T6 = {n_existing_written + n_t6_written} rows -> {DEST_CSV.relative_to(REPO_ROOT)}", file=sys.stderr)

    if CSV_MIRROR.exists() or CSV_MIRROR.parent.exists():
        import shutil
        CSV_MIRROR.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DEST_CSV, CSV_MIRROR)
        print(f"[append_t6] mirrored -> {CSV_MIRROR.relative_to(REPO_ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()
