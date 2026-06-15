"""Characterization: data-integrity validation behind a port (E3.T10, F5).

Pins that migrating the integrity checker/report from ``utils/`` into
``infrastructure/data/integrity/`` behind ``DataIntegrityPort`` changes NO output:

* the integrity report on a corrupted-data fixture (missing candles, an empty
  frame, and an absent symbol) reproduces its exact fields + pass/fail status,
* the migrated class, the ``utils`` re-export shim, and the container-resolved
  adapter all produce identical reports, and
* the adapter conforms to ``DataIntegrityPort`` and is resolvable from the
  composition root.
"""

import pytest

pytest.importorskip("pandas")

import pandas as pd
from datetime import datetime

from bootstrap.settings.loaders import load_settings
from bootstrap.container import Container


START = datetime(2023, 1, 1)
END = datetime(2023, 1, 10)  # '1d' -> expected_count = 9 days + 1 = 10
SYMBOLS = ["GOODUSDT", "EMPTYUSDT", "ABSENTUSDT"]


def _corrupted_fixture():
    """5 of 10 expected daily candles present (50% missing) + an empty frame."""
    ts = [int(datetime(2023, 1, d).timestamp()) for d in range(1, 6)]
    present = pd.DataFrame({
        "timestamp": ts,
        "open": [1.0, 2.0, 3.0, 4.0, 5.0],
        "high": [1.0, 2.0, 3.0, 4.0, 5.0],
        "low": [1.0, 2.0, 3.0, 4.0, 5.0],
        "close": [1.0, 2.0, 3.0, 4.0, 5.0],
        "volume": [10, 20, 30, 40, 50],
    })
    empty = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    # ABSENTUSDT intentionally omitted from the dict.
    return {"GOODUSDT": present, "EMPTYUSDT": empty}


def _report(checker):
    rep = checker.generate_integrity_report(_corrupted_fixture(), SYMBOLS, START, END, "1d")
    rep.pop("validation_timestamp", None)  # run-dependent
    return rep


@pytest.mark.unit
def test_corrupted_fixture_report_fields_pinned():
    from infrastructure.data.integrity.data_integrity_checker import DataIntegrityChecker

    rep = _report(DataIntegrityChecker())

    assert rep["timeframe"] == "1d"
    assert rep["date_range"] == {"start": START.isoformat(), "end": END.isoformat()}

    good = rep["symbols"]["GOODUSDT"]
    assert good["status"] == "FAIL"            # 50% missing > 5% threshold
    assert good["missing_ratio"] == 0.5
    assert good["message"] == "Missing ratio: 50.00% (FAIL)"
    assert good["total_rows"] == 5

    assert rep["symbols"]["EMPTYUSDT"]["status"] == "EMPTY"
    assert rep["symbols"]["EMPTYUSDT"]["missing_ratio"] == 1.0
    assert rep["symbols"]["ABSENTUSDT"]["status"] == "MISSING"
    assert rep["symbols"]["ABSENTUSDT"]["missing_ratio"] == 1.0


@pytest.mark.unit
def test_migrated_shim_and_container_reports_identical():
    from infrastructure.data.integrity.data_integrity_checker import DataIntegrityChecker as Migrated
    from utils.data_integrity_checker import DataIntegrityChecker as Shim

    container = Container(load_settings())
    resolved = container.resolve("data_integrity_checker")

    rep_migrated = _report(Migrated())
    rep_shim = _report(Shim())
    rep_container = _report(resolved)

    assert rep_shim == rep_migrated          # shim re-exports the migrated class
    assert rep_container == rep_migrated      # container resolves the same behavior
    assert Shim is Migrated                   # shim is a pure re-export, not a copy


@pytest.mark.unit
def test_missing_candle_ratio_and_validation_pinned():
    from infrastructure.data.integrity.data_integrity_checker import DataIntegrityChecker

    checker = DataIntegrityChecker()
    df = _corrupted_fixture()["GOODUSDT"]

    assert checker.calculate_missing_candle_ratio(df, START, END, "1d") == 0.5
    # 50% missing fails the default 5% threshold; a 60% threshold passes it.
    assert checker.validate_symbol_data(df, "GOODUSDT", START, END, "1d") is False
    assert checker.validate_symbol_data(df, "GOODUSDT", START, END, "1d", max_missing_ratio=0.6) is True


@pytest.mark.unit
def test_port_conformance_and_resolvability():
    from domain.ports.data_ports import DataIntegrityPort

    container = Container(load_settings())
    checker = container.resolve("data_integrity_checker")
    report = container.resolve("data_integrity_report")

    for method in (m for m in dir(DataIntegrityPort) if not m.startswith("_")):
        assert callable(getattr(checker, method, None)), f"checker missing {method}"

    # Both integrity components resolvable + cached.
    assert container.resolve("data_integrity_checker") is checker
    assert container.resolve("data_integrity_report") is report
