# src/manipulation_bench/viz/__init__.py
"""Simulation visualization — static HTML report generation."""

from __future__ import annotations

import json
import webbrowser
from pathlib import Path

from manipulation_bench.viz.extract import extract_simulation_data

_TEMPLATE_PATH = Path(__file__).parent / "template.html"


def generate_report(
    eval_path: str | Path,
    output: str | Path | None = None,
    open_browser: bool = True,
) -> Path:
    """Generate an HTML visualization report from an eval log.

    Args:
        eval_path: Path to a .eval file.
        output: Output HTML path or directory. Defaults to <eval_path>.html.
        open_browser: Whether to open the report in the default browser.

    Returns:
        Path to the generated HTML file.
    """
    eval_path = Path(eval_path)
    data = extract_simulation_data(eval_path)

    if output is None:
        output_path = eval_path.with_suffix(".html")
    else:
        output_path = Path(output)
        if output_path.is_dir():
            output_path = output_path / eval_path.with_suffix(".html").name
        if output_path.suffix != ".html":
            output_path = output_path.with_suffix(".html")

    template = _TEMPLATE_PATH.read_text()
    data_json = json.dumps(data)
    html = template.replace('"__DATA_PLACEHOLDER__"', data_json)

    output_path.write_text(html)

    if open_browser:
        webbrowser.open(f"file://{output_path.resolve()}")

    return output_path
