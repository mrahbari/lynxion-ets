"""Helpers for golden / characterization tests.

A golden file pins the canonical output of a pipeline. Tests recompute the
output and diff it against the committed golden file; any drift fails the test.

Set the environment variable ``GOLDEN_UPDATE=1`` to (re)write golden files
instead of asserting against them. This is only used intentionally when the
canonical behavior is meant to change.
"""

import json
import os
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "golden"


def _normalize(obj: Any) -> Any:
    """Make values JSON-stable (handle inf/nan and round floats)."""
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    if isinstance(obj, float):
        if obj != obj:  # NaN
            return "nan"
        if obj == float("inf"):
            return "inf"
        if obj == float("-inf"):
            return "-inf"
        return round(obj, 6)
    return obj


def assert_golden(filename: str, actual: Any) -> None:
    """Compare ``actual`` against the committed golden ``filename``.

    When ``GOLDEN_UPDATE=1`` the golden file is written instead of compared.
    """
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    path = FIXTURES_DIR / filename
    normalized = _normalize(actual)

    if os.environ.get("GOLDEN_UPDATE") == "1":
        path.write_text(json.dumps(normalized, indent=2, sort_keys=True), encoding="utf-8")
        return

    assert path.exists(), (
        f"Golden file {path} is missing. Run with GOLDEN_UPDATE=1 to create it."
    )
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert normalized == expected, (
        f"Output drift detected vs golden {filename}.\n"
        f"Expected: {json.dumps(expected, sort_keys=True)}\n"
        f"Actual:   {json.dumps(normalized, sort_keys=True)}"
    )
