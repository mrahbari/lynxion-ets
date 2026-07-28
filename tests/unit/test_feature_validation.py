"""Unit tests for the Quantitative Feature Validation Framework (Milestone 4)."""

import pytest
import os
from decimal import Decimal

from domain.value_objects import Symbol, Side, ExchangeTimestamp
from domain.entities import FeatureSnapshot, FeatureEventRecord, RegimeStats
from infrastructure.research.feature_validator import QuantitativeFeatureValidator


@pytest.fixture
def btc_symbol():
    return Symbol("BTC-USDT")


@pytest.fixture
def sample_ticks(btc_symbol):
    from domain.entities import TradeTick
    from domain.value_objects import Price, Quantity
    # Base timestamp = 1700000000000
    # Create trades for 1m (+60k), 5m (+300k), 15m (+900k), 1h (+3.6M)
    return [
        TradeTick(symbol=btc_symbol, trade_id=1, price=Price(Decimal("100.0"), btc_symbol),
                  quantity=Quantity(Decimal("1.0"), "BTC"), timestamp=ExchangeTimestamp(1700000000000), side=Side.BUY),
        # 1m tick: price = 101.0 (return = +1%)
        TradeTick(symbol=btc_symbol, trade_id=2, price=Price(Decimal("101.0"), btc_symbol),
                  quantity=Quantity(Decimal("1.0"), "BTC"), timestamp=ExchangeTimestamp(1700000060000), side=Side.BUY),
        # 5m tick: price = 105.0 (return = +5%)
        TradeTick(symbol=btc_symbol, trade_id=3, price=Price(Decimal("105.0"), btc_symbol),
                  quantity=Quantity(Decimal("1.0"), "BTC"), timestamp=ExchangeTimestamp(1700000300000), side=Side.BUY),
        # 15m tick: price = 98.0 (return = -2%)
        TradeTick(symbol=btc_symbol, trade_id=4, price=Price(Decimal("98.0"), btc_symbol),
                  quantity=Quantity(Decimal("1.0"), "BTC"), timestamp=ExchangeTimestamp(1700000900000), side=Side.BUY),
        # 1h tick: price = 110.0 (return = +10%)
        TradeTick(symbol=btc_symbol, trade_id=5, price=Price(Decimal("110.0"), btc_symbol),
                  quantity=Quantity(Decimal("1.0"), "BTC"), timestamp=ExchangeTimestamp(1700003600000), side=Side.BUY),
    ]


@pytest.mark.unit
def test_forward_return_analyzer_exact_horizons(btc_symbol, sample_ticks):
    """Verify that forward returns are calculated correctly at specific horizons."""
    validator = QuantitativeFeatureValidator()
    
    # Analyze from first tick: timestamp 1700000000000, price 100.0
    # Future ticks are the ones after 1700000000000
    future_ticks = sample_ticks[1:]
    
    returns = validator.calculate_forward_returns(
        feature_ts=ExchangeTimestamp(1700000000000),
        current_price=Decimal("100.0"),
        ticks=future_ticks
    )

    assert returns["1m"] == Decimal("0.01")     # (101 - 100)/100
    assert returns["5m"] == Decimal("0.05")     # (105 - 100)/100
    assert returns["15m"] == Decimal("-0.02")   # (98 - 100)/100
    assert returns["1h"] == Decimal("0.10")     # (110 - 100)/100


@pytest.mark.unit
def test_forward_return_analyzer_missing_data(btc_symbol):
    """Verify missing future ticks fallback gracefully to zero return or last known tick."""
    validator = QuantitativeFeatureValidator()
    
    # Empty future ticks
    returns = validator.calculate_forward_returns(
        feature_ts=ExchangeTimestamp(1700000000000),
        current_price=Decimal("100.0"),
        ticks=[]
    )
    assert returns["1m"] == Decimal("0")
    assert returns["1h"] == Decimal("0")


@pytest.mark.unit
def test_validation_lookahead_prevention(btc_symbol, sample_ticks):
    """Verify that prices before the event timestamp are ignored to prevent lookahead bias."""
    validator = QuantitativeFeatureValidator()
    
    # Event occurs at 1700000060000 (1m mark) where current price was 101.0
    # If the engine correctly prevents lookahead bias, it won't use the tick at 1700000000000 (price 100.0)
    # The ticks passed to calculate_forward_returns should only be those at or after the target windows
    # which we ensure in build_event_dataset.
    snapshots = [
        FeatureSnapshot(
            symbol=btc_symbol,
            timestamp=ExchangeTimestamp(1700000060000),
            obi_ratio=Decimal("0.5"),
            obi_multi_level=Decimal("0.4"),
            obi_velocity=Decimal("0.1"),
            buy_volume=Decimal("10"),
            sell_volume=Decimal("5"),
            delta=Decimal("5"),
            cumulative_delta=Decimal("100"),
            is_sweep=False,
            sweep_level_price=None,
            sweep_volume_consumed=Decimal("0"),
            sweep_rejection_ratio=Decimal("0"),
            is_absorption=False,
            absorption_volume=Decimal("0"),
            absorption_price_range=Decimal("0"),
            volatility=Decimal("2.0"),
            spread=Decimal("0.5"),
            depth_total=Decimal("500"),
            regime_context="RANGING"
        )
    ]

    records = validator.build_event_dataset(snapshots, sample_ticks)
    assert len(records) == 1
    rec = records[0]
    
    # 5m horizon from 1700000060000 target is 1700000360000.
    # Closest tick at or after 1700000360000 is 1h tick (110.0) or 15m tick (98.0) depending on time boundaries.
    # From 1700000060000:
    # 5m target: 1700000360000 -> closest tick at or after is 15m tick (1700000900000) at 98.0.
    # Return 5m = (98.0 - 101.0)/101.0
    expected_ret = (Decimal("98.0") - Decimal("101.0")) / Decimal("101.0")
    assert rec.forward_return_5m == expected_ret


@pytest.mark.unit
def test_validation_stats_calculation(btc_symbol):
    """Verify stats engine calculations: hit rate, average, volatility, IC, correlations."""
    validator = QuantitativeFeatureValidator()
    
    # Create 3 records:
    # 1. Expected BUY (obi = 0.5), actual return +2% -> Hit
    # 2. Expected SELL (obi = -0.5), actual return -1% -> Hit
    # 3. Expected BUY (obi = 0.4), actual return -3% -> Miss
    records = [
        FeatureEventRecord(
            timestamp=ExchangeTimestamp(100), symbol=btc_symbol, market_regime="RANGING",
            obi=Decimal("0.5"), obi_velocity=Decimal("0"), cvd=Decimal("10"), is_sweep=False, is_absorption=False,
            spread=Decimal("1"), depth_total=Decimal("100"),
            forward_return_1m=Decimal("0"), forward_return_5m=Decimal("0.02"),
            forward_return_15m=Decimal("0"), forward_return_1h=Decimal("0")
        ),
        FeatureEventRecord(
            timestamp=ExchangeTimestamp(200), symbol=btc_symbol, market_regime="RANGING",
            obi=Decimal("-0.5"), obi_velocity=Decimal("0"), cvd=Decimal("-10"), is_sweep=False, is_absorption=False,
            spread=Decimal("1"), depth_total=Decimal("100"),
            forward_return_1m=Decimal("0"), forward_return_5m=Decimal("-0.01"),
            forward_return_15m=Decimal("0"), forward_return_1h=Decimal("0")
        ),
        FeatureEventRecord(
            timestamp=ExchangeTimestamp(300), symbol=btc_symbol, market_regime="RANGING",
            obi=Decimal("0.4"), obi_velocity=Decimal("0"), cvd=Decimal("8"), is_sweep=False, is_absorption=False,
            spread=Decimal("1"), depth_total=Decimal("100"),
            forward_return_1m=Decimal("0"), forward_return_5m=Decimal("-0.03"),
            forward_return_15m=Decimal("0"), forward_return_1h=Decimal("0")
        )
    ]

    stats = validator.analyze_regime("RANGING", records)
    
    assert stats.sample_count == 3
    # Hit rate: 2 correct predictions out of 3 = 66.67%
    assert stats.hit_rate == Decimal("2") / Decimal("3")
    
    # Average Return: (0.02 - 0.01 - 0.03)/3 = -0.02/3 = -0.006666...
    assert stats.avg_return == Decimal("-0.02") / Decimal("3")
    
    # Volatility should be standard deviation of [0.02, -0.01, -0.03]
    # Mean = -0.006666...
    # Variance = ((0.02 - Mean)^2 + (-0.01 - Mean)^2 + (-0.03 - Mean)^2) / 2 = 0.0006333333333333333
    # Volatility = sqrt(Variance) = 0.0251661147842
    assert stats.volatility == pytest.approx(Decimal("0.025166"), abs=Decimal("0.0001"))

    # Check correlations dict exists and populated
    assert "obi_to_return" in stats.feature_correlations
    assert "cvd_to_return" in stats.feature_correlations


@pytest.mark.unit
def test_regime_segmentation_isolation(btc_symbol):
    """Verify that perform_validation partitions records and computes stats independently per regime."""
    validator = QuantitativeFeatureValidator()
    
    records = [
        # HIGH_VOLATILITY record
        FeatureEventRecord(
            timestamp=ExchangeTimestamp(100), symbol=btc_symbol, market_regime="HIGH_VOLATILITY",
            obi=Decimal("0.5"), obi_velocity=Decimal("0"), cvd=Decimal("10"), is_sweep=False, is_absorption=False,
            spread=Decimal("1"), depth_total=Decimal("100"),
            forward_return_1m=Decimal("0"), forward_return_5m=Decimal("0.05"),
            forward_return_15m=Decimal("0"), forward_return_1h=Decimal("0")
        ),
        # LOW_VOLATILITY trending record
        FeatureEventRecord(
            timestamp=ExchangeTimestamp(200), symbol=btc_symbol, market_regime="TRENDING",
            obi=Decimal("-0.5"), obi_velocity=Decimal("0"), cvd=Decimal("-10"), is_sweep=False, is_absorption=False,
            spread=Decimal("1"), depth_total=Decimal("100"),
            forward_return_1m=Decimal("0"), forward_return_5m=Decimal("-0.02"),
            forward_return_15m=Decimal("0"), forward_return_1h=Decimal("0")
        )
    ]

    results = validator.perform_validation(records)
    
    assert "ALL" in results
    assert "HIGH_VOLATILITY" in results
    assert "LOW_VOLATILITY" in results
    assert "TRENDING" in results
    assert "RANGING" in results

    # Check isolation counts
    assert results["HIGH_VOLATILITY"].sample_count == 1
    assert results["LOW_VOLATILITY"].sample_count == 1
    assert results["TRENDING"].sample_count == 1
    assert results["RANGING"].sample_count == 0


@pytest.mark.unit
def test_validation_report_generation(btc_symbol, tmp_path):
    """Verify report generation compiles the Markdown stats report correctly."""
    validator = QuantitativeFeatureValidator()
    
    records = [
        FeatureEventRecord(
            timestamp=ExchangeTimestamp(100), symbol=btc_symbol, market_regime="RANGING",
            obi=Decimal("0.5"), obi_velocity=Decimal("0"), cvd=Decimal("10"), is_sweep=False, is_absorption=False,
            spread=Decimal("1"), depth_total=Decimal("100"),
            forward_return_1m=Decimal("0"), forward_return_5m=Decimal("0.02"),
            forward_return_15m=Decimal("0"), forward_return_1h=Decimal("0")
        )
    ]

    results = validator.perform_validation(records)
    report_file = os.path.join(tmp_path, "feature_validation_report.md")
    
    validator.generate_report(results, report_file)
    
    assert os.path.exists(report_file)
    with open(report_file, "r") as f:
        content = f.read()
    
    assert "# Quantitative Feature Validation Report" in content
    assert "RANGING" in content
