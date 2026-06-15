"""Layering contract test (E6.T2) — local mirror of the CI ``lint-imports`` gate.

This test runs the *same* import-linter contracts that CI runs, read from the
single source of truth in ``pyproject.toml`` (``[tool.importlinter]``, added in
E6.T1). It gives fast local feedback so an architecture-violating import is
caught before it reaches CI.

It is an *enforcement* test, not a refactoring one: it asserts the contracts
defined in ``pyproject.toml`` hold as-is, including the documented
``ignore_imports`` allowlist of pre-existing debt owned by deferred tasks
(E1 settings shim, E5-B risk wiring, E8 shared cleanup). It does not change,
relax, or "fix" any of those edges — it only locks in the current architecture
and fails on any *new* violation.

Rules enforced (see ``docs/reports/phase2-target-architecture.md`` §4):

* R1 — interface must not import infrastructure directly.
* R2 — application -> domain only.
* R3 — infrastructure -> domain only.
* R4 — nothing imports bootstrap except interface.
* R5 — domain is pure (imports nothing above it).
* R6 — shared -> nothing (everyone may use it; it uses no layer).
"""

from __future__ import annotations

from pathlib import Path

import pytest

# import-linter backs this test. It is installed in CI; skip with a clear
# pointer if a local dev hasn't installed it (CI still enforces the gate).
importlinter_config = pytest.importorskip(
    "importlinter.configuration",
    reason="import-linter not installed — run `pip install import-linter` to enable the local layering gate",
)
from importlinter.application.use_cases import (  # noqa: E402
    create_report,
    read_user_options,
    _register_contract_types,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"

# Contract names exactly as declared in pyproject.toml [tool.importlinter].
_LAYERS_CONTRACT = "Layered architecture (R2, R3, R4, R5, R6)"
_R1_CONTRACT = "Interface must not import infrastructure directly (R1)"

# Initialise import-linter's reader/builder registry (the CLI does this too).
importlinter_config.configure()


def _broken_contracts() -> list[str]:
    """Return the names of any import-linter contracts that are currently broken.

    Caching is disabled so freshly-written probe modules are picked up within
    the same test session.
    """
    user_options = read_user_options(config_filename=str(_PYPROJECT))
    _register_contract_types(user_options)
    report = create_report(user_options, cache_dir=None)
    return [
        contract.name
        for contract, check in report.get_contracts_and_checks()
        if not check.kept
    ]


@pytest.mark.contract
def test_layering_contracts_hold_on_current_tree():
    """All R1-R6 contracts in pyproject.toml hold on the current codebase."""
    broken = _broken_contracts()
    assert not broken, (
        "Layering contract(s) violated: "
        + ", ".join(broken)
        + ". Run `lint-imports` for the offending imports. "
        "Fix the import or, if it is sanctioned pre-existing debt, add a "
        "documented entry to `ignore_imports` in pyproject.toml."
    )


@pytest.mark.contract
def test_layering_test_detects_injected_violation(tmp_path):
    """A prohibited dependency (domain -> infrastructure) is reliably detected.

    Proves the gate actually bites: introduce an R5/layers violation by adding a
    domain module that imports infrastructure, confirm the layered contract is
    reported broken (and names the rule), then remove the probe and confirm the
    tree is clean again.
    """
    probe = _REPO_ROOT / "domain" / "_layering_probe.py"
    assert not probe.exists(), f"stale probe file present: {probe}"
    probe.write_text("import infrastructure  # E6.T2 injected-violation probe\n", encoding="utf-8")
    try:
        broken = _broken_contracts()
    finally:
        probe.unlink(missing_ok=True)

    assert _LAYERS_CONTRACT in broken, (
        "Injected domain->infrastructure import was NOT caught by the "
        f"'{_LAYERS_CONTRACT}' contract; broken contracts were: {broken or 'none'}"
    )

    # Cleanup restored a conformant tree.
    assert not _broken_contracts(), "tree not clean after removing the injected probe"
