"""E4.T5 — unit tests for infrastructure/data/integrity/data_integrity_checker.py.

Deterministic data-quality validation (E3.T10 canonical). The missing-candle
ratio is a pure function of row count vs the expected count for a timeframe, so
small in-memory DataFrames give exact, deterministic results. No I/O.
"""

from datetime import datetime

import pandas as pd
import pytest

from infrastructure.data.integrity.data_integrity_checker import DataIntegrityChecker

START = datetime(2026, 1, 1)
END = datetime(2026, 1, 10)          # 9 days span -> expected daily count = 10
_BASE_TS = 1_767_225_600            # arbitrary unix seconds


def _daily_df(rows):
    """DataFrame with `rows` daily candles (timestamp column in unix seconds)."""
    return pd.DataFrame({"timestamp": [_BASE_TS + i * 86_400 for i in range(rows)]})


@pytest.fixture
def checker():
    return DataIntegrityChecker()


@pytest.mark.unit
def test_empty_dataframe_is_fully_missing(checker):
    assert checker.calculate_missing_candle_ratio(pd.DataFrame(), START, END, "1d") == 1.0


@pytest.mark.unit
def test_complete_daily_data_has_zero_missing(checker):
    assert checker.calculate_missing_candle_ratio(_daily_df(10), START, END, "1d") == 0.0


@pytest.mark.unit
def test_half_the_candles_missing(checker):
    assert checker.calculate_missing_candle_ratio(_daily_df(5), START, END, "1d") == pytest.approx(0.5)


@pytest.mark.unit
def test_surplus_rows_clamp_ratio_to_zero(checker):
    # more rows than expected -> ratio clamped at 0.0, never negative
    assert checker.calculate_missing_candle_ratio(_daily_df(20), START, END, "1d") == 0.0


@pytest.mark.unit
def test_validate_symbol_data_threshold(checker):
    assert checker.validate_symbol_data(_daily_df(10), "BTCUSDT", START, END, "1d") is True
    # 50% missing exceeds the default 5% threshold -> fail
    assert checker.validate_symbol_data(_daily_df(5), "BTCUSDT", START, END, "1d") is False
    # ...but passes when the threshold is relaxed above the missing ratio
    assert checker.validate_symbol_data(_daily_df(5), "BTCUSDT", START, END, "1d", max_missing_ratio=0.6) is True


@pytest.mark.unit
def test_validate_symbol_data_empty_is_false(checker):
    assert checker.validate_symbol_data(pd.DataFrame(), "BTCUSDT", START, END, "1d") is False


@pytest.mark.unit
def test_validate_multiple_symbols_marks_missing_symbol_false(checker):
    data = {"BTCUSDT": _daily_df(10)}     # ETHUSDT intentionally absent
    results = checker.validate_multiple_symbols(data, ["BTCUSDT", "ETHUSDT"], START, END, "1d")
    assert results == {"BTCUSDT": True, "ETHUSDT": False}
