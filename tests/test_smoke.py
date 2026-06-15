"""Smoke test establishing a known-green baseline for the test harness.

Verifies pytest discovery, marker registration, and the root-path
``conftest.py`` are wired correctly. Replaced/expanded by real unit tests
as the refactor proceeds.
"""

import pytest


@pytest.mark.unit
def test_smoke_baseline_is_green():
    assert True
