"""Append T6 (inbox triage) rows to paper/cross_task/results.csv.

Reads only T6 eval logs (frontier-6 canonical + per-model sweeps + pilot)
and appends them to the existing CSV. Used when the full T1-T6 regeneration
would OOM the box. Caller is responsible for first dropping any existing
T6 rows from the CSV (otherwise we duplicate).

Picks up the same glob set as eval_logs_to_csv.py's DEFAULT_T6_SWEEP_GLOBS,
plus paper/task6_inbox/eval_log.eval. Variant inference and per-row schema
match eval_logs_to_csv.py exactly.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parent))

from eval_logs_to_csv import (  # noqa: E402
    DEFAULT_T6_SWEEP_GLOBS,
    _order_column_names,
    _rows_from_log,
)

DEFAULT_OUTPUT = REPO_ROOT / "paper/cross_task/data/results.csv"


def collect_t6_log_paths() -> list[Path]:
    paths: list[Path] = []
    canonical = REPO_ROOT / "paper/task6_inbox/eval_log.eval"
    if canonical.exists():
        paths.append(canonical)
    for pattern in DEFAULT_T6_SWEEP_GLOBS:
        for p in (REPO_ROOT).glob(pattern):
            if p.suffix == ".eval":
                paths.append(p)
    return sorted({p.resolve() for p in paths})


def main() -> None:
    out_path = DEFAULT_OUTPUT
    if not out_path.exists():
        raise SystemExit(f"{out_path} does not exist; run eval_logs_to_csv.py first")

    log_paths = collect_t6_log_paths()
    if not log_paths:
        raise SystemExit("no T6 eval logs found")
    print(f"[append_t6] {len(log_paths)} T6 logs:", file=sys.stderr)
    for p in log_paths:
        print(f"  {p.relative_to(REPO_ROOT)}", file=sys.stderr)

    new_rows: list[dict] = []
    for p in log_paths:
        rows = _rows_from_log(p)
        new_rows.extend(rows)
    print(f"[append_t6] collected {len(new_rows)} T6 rows", file=sys.stderr)

    if not new_rows:
        raise SystemExit("no rows extracted")

    # Read existing CSV header to determine column order; new T6-specific columns
    # (inbox_triage__*, suppression_target, etc.) get appended at the end.
    with out_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        existing_cols = next(reader)
    existing_set = set(existing_cols)
    new_keys = set()
    for r in new_rows:
        new_keys.update(r.keys())
    extra_cols = sorted(k for k in new_keys if k not in existing_set)
    final_cols = existing_cols + extra_cols
    final_cols = _order_column_names(final_cols)

    if extra_cols:
        print(f"[append_t6] adding {len(extra_cols)} new columns: {extra_cols[:5]}{'...' if len(extra_cols) > 5 else ''}", file=sys.stderr)
        # Need to rewrite full CSV with the new column set; reading existing rows back.
        # Safe because we already dropped T6 rows and the rest fits in memory.
        import pandas as pd
        existing_df = pd.read_csv(out_path, low_memory=False)
        new_df = pd.DataFrame(new_rows)
        merged = pd.concat([existing_df, new_df], ignore_index=True)
        # Reorder columns
        for c in final_cols:
            if c not in merged.columns:
                merged[c] = None
        merged = merged[final_cols]
        merged.to_csv(out_path, index=False)
        print(f"[append_t6] rewrote {out_path} with {len(merged)} rows × {len(final_cols)} cols", file=sys.stderr)
    else:
        # Pure append path - faster, no rewrite
        with out_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=existing_cols, extrasaction="ignore")
            for r in new_rows:
                writer.writerow(r)
        print(f"[append_t6] appended {len(new_rows)} rows in place", file=sys.stderr)


if __name__ == "__main__":
    main()
