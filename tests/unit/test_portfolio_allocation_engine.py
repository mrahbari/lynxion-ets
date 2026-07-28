"""
Unit tests for PortfolioAllocationEngine (Task 0037).

Covers:
- Equal Weight allocation
- Fractional Kelly (Quarter-Kelly) allocation
- Single, multiple, and empty asset inputs
- Invalid probabilities and payoff ratios
- NaN and Infinity inputs
- Missing asset stats and fallback behavior
- Deterministic repeated execution
- Numerical stability and weight sum validation
"""
import math
import pytest
from typing import Dict

from infrastructure.risk.portfolio_allocation_engine import (
    PortfolioAllocationEngine,
    AllocationResult,
    AllocationMode,
    AssetPerformanceStats,
)


@pytest.fixture
def allocation_engine():
    return PortfolioAllocationEngine()


@pytest.fixture
def sample_asset_stats() -> Dict[str, AssetPerformanceStats]:
    return {
        "SOLUSDT": AssetPerformanceStats(symbol="SOLUSDT", win_rate=0.543, win_loss_ratio=2.05),
        "ETHUSDT": AssetPerformanceStats(symbol="ETHUSDT", win_rate=0.600, win_loss_ratio=1.07),
        "XRPUSDT": AssetPerformanceStats(symbol="XRPUSDT", win_rate=0.357, win_loss_ratio=2.14),
        "BNBUSDT": AssetPerformanceStats(symbol="BNBUSDT", win_rate=0.488, win_loss_ratio=0.99),
        "BTCUSDT": AssetPerformanceStats(symbol="BTCUSDT", win_rate=0.455, win_loss_ratio=1.09),
    }


def test_equal_weight_allocation(allocation_engine):
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]
    res = allocation_engine.compute_weights(symbols, mode=AllocationMode.EQUAL_WEIGHT)

    assert isinstance(res, AllocationResult)
    assert res.mode == AllocationMode.EQUAL_WEIGHT
    assert not res.is_fallback
    assert len(res.weights) == 5
    assert sum(res.weights.values()) == pytest.approx(1.0, abs=1e-4)
    assert res.is_valid()
    for s in symbols:
        assert res.weights[s] == pytest.approx(0.20, abs=1e-4)


def test_single_asset_portfolio(allocation_engine):
    res = allocation_engine.compute_weights(["BTCUSDT"], mode=AllocationMode.EQUAL_WEIGHT)

    assert res.is_valid()
    assert res.weights == {"BTCUSDT": 1.0}
    assert not res.is_fallback


def test_empty_asset_portfolio(allocation_engine):
    res = allocation_engine.compute_weights([], mode=AllocationMode.EQUAL_WEIGHT)

    assert res.is_fallback
    assert res.weights == {}
    assert res.reason == "Empty symbol list provided."


def test_fractional_kelly_valid_stats(allocation_engine, sample_asset_stats):
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]
    res = allocation_engine.compute_weights(
        symbols,
        asset_stats=sample_asset_stats,
        mode=AllocationMode.FRACTIONAL_KELLY,
        kelly_fraction=0.25,
    )

    assert isinstance(res, AllocationResult)
    assert res.mode == AllocationMode.FRACTIONAL_KELLY
    assert not res.is_fallback
    assert res.is_valid()
    assert sum(res.weights.values()) == pytest.approx(1.0, abs=1e-4)

    # SOLUSDT has highest edge (p=0.543, b=2.05), should receive highest allocation
    assert res.weights["SOLUSDT"] > res.weights["BTCUSDT"]
    assert res.weights["SOLUSDT"] > res.weights["BNBUSDT"]


def test_fractional_kelly_invalid_probabilities(allocation_engine):
    invalid_stats = {
        "SOLUSDT": AssetPerformanceStats(symbol="SOLUSDT", win_rate=-0.5, win_loss_ratio=2.0),
        "ETHUSDT": AssetPerformanceStats(symbol="ETHUSDT", win_rate=1.5, win_loss_ratio=1.5),
    }
    symbols = ["SOLUSDT", "ETHUSDT"]
    res = allocation_engine.compute_weights(
        symbols,
        asset_stats=invalid_stats,
        mode=AllocationMode.FRACTIONAL_KELLY,
    )

    assert res.is_valid()
    assert sum(res.weights.values()) == pytest.approx(1.0, abs=1e-4)
    # Invalid stats fall back to floor weights and normalize equally
    assert res.weights["SOLUSDT"] == pytest.approx(0.50, abs=1e-4)
    assert res.weights["ETHUSDT"] == pytest.approx(0.50, abs=1e-4)


def test_fractional_kelly_invalid_payoff_ratios(allocation_engine):
    invalid_stats = {
        "SOLUSDT": AssetPerformanceStats(symbol="SOLUSDT", win_rate=0.5, win_loss_ratio=-1.0),
        "ETHUSDT": AssetPerformanceStats(symbol="ETHUSDT", win_rate=0.5, win_loss_ratio=0.0),
    }
    symbols = ["SOLUSDT", "ETHUSDT"]
    res = allocation_engine.compute_weights(
        symbols,
        asset_stats=invalid_stats,
        mode=AllocationMode.FRACTIONAL_KELLY,
    )

    assert res.is_valid()
    assert sum(res.weights.values()) == pytest.approx(1.0, abs=1e-4)


def test_nan_and_inf_handling(allocation_engine):
    nan_stats = {
        "SOLUSDT": AssetPerformanceStats(symbol="SOLUSDT", win_rate=float("nan"), win_loss_ratio=2.0),
        "ETHUSDT": AssetPerformanceStats(symbol="ETHUSDT", win_rate=0.5, win_loss_ratio=float("inf")),
    }
    symbols = ["SOLUSDT", "ETHUSDT"]

    # Should execute without throwing uncaught exceptions
    res = allocation_engine.compute_weights(
        symbols,
        asset_stats=nan_stats,
        mode=AllocationMode.FRACTIONAL_KELLY,
    )

    assert res.is_valid()
    assert sum(res.weights.values()) == pytest.approx(1.0, abs=1e-4)


def test_missing_asset_stats_fallback(allocation_engine):
    symbols = ["BTCUSDT", "ETHUSDT"]
    res = allocation_engine.compute_weights(
        symbols,
        asset_stats=None,
        mode=AllocationMode.FRACTIONAL_KELLY,
    )

    assert res.is_fallback
    assert res.mode == AllocationMode.FRACTIONAL_KELLY
    assert res.weights["BTCUSDT"] == pytest.approx(0.50, abs=1e-4)
    assert res.weights["ETHUSDT"] == pytest.approx(0.50, abs=1e-4)


def test_deterministic_repeated_execution(allocation_engine, sample_asset_stats):
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]
    first_res = allocation_engine.compute_weights(
        symbols,
        asset_stats=sample_asset_stats,
        mode=AllocationMode.FRACTIONAL_KELLY,
    )

    for _ in range(100):
        subsequent_res = allocation_engine.compute_weights(
            symbols,
            asset_stats=sample_asset_stats,
            mode=AllocationMode.FRACTIONAL_KELLY,
        )
        assert subsequent_res.weights == first_res.weights


def test_duplicate_symbols_deduplication(allocation_engine):
    symbols = ["BTCUSDT", "BTCUSDT", "ETHUSDT", "ETHUSDT"]
    res = allocation_engine.compute_weights(symbols, mode=AllocationMode.EQUAL_WEIGHT)

    assert len(res.weights) == 2
    assert res.weights["BTCUSDT"] == pytest.approx(0.50, abs=1e-4)
    assert res.weights["ETHUSDT"] == pytest.approx(0.50, abs=1e-4)
