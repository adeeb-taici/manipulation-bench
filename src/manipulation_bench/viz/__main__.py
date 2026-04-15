# src/manipulation_bench/viz/__main__.py
"""CLI entry point: python -m manipulation_bench.viz <eval_file> [options]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from manipulation_bench.viz import generate_report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate HTML visualization reports from manipulation-bench eval logs.",
    )
    parser.add_argument(
        "eval_files",
        nargs="+",
        type=Path,
        help="Path(s) to .eval log files",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output path (file for single input, directory for multiple)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't open the report in a browser",
    )

    args = parser.parse_args()

    for eval_file in args.eval_files:
        if not eval_file.exists():
            print(f"Error: {eval_file} not found", file=sys.stderr)
            continue

        output = args.output
        if output and len(args.eval_files) > 1 and not output.is_dir():
            output.mkdir(parents=True, exist_ok=True)

        try:
            result = generate_report(
                eval_file,
                output=output,
                open_browser=not args.no_open,
            )
            print(f"Generated: {result}")
        except (KeyError, ValueError) as e:
            print(f"Skipping {eval_file}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
