"""Unit tests for the 1H Market Structure Engine (Phase 2)."""

import pytest
from infrastructure.market_structure.market_structure_engine import MarketStructureEngine


@pytest.mark.unit
def test_insufficient_data_returns_fallback_neutral():
    engine = MarketStructureEngine(swing_lookback=20)
    result = engine.calculate_market_structure(
        prices=[100.0],
        highs=[101.0],
        lows=[99.0],
        volumes=[10.0]
    )
    assert result["bias"] == "NEUTRAL"
    assert result["poc"] == 100.0
    assert result["vah"] == 100.0
    assert result["val"] == 100.0
    assert result["support"] == 100.0
    assert result["resistance"] == 100.0


@pytest.mark.unit
def test_market_structure_calculations_and_invariants():
    engine = MarketStructureEngine(swing_lookback=10, volume_profile_bins=5)
    
    # Rising prices, higher highs, higher lows, volumes
    prices = [100.0 + i for i in range(15)]
    highs = [101.0 + i for i in range(15)]
    lows = [99.0 + i for i in range(15)]
    volumes = [10.0] * 15

    result = engine.calculate_market_structure(prices, highs, lows, volumes)

    # Check that contract is satisfied
    assert {"bias", "poc", "vah", "val", "support", "resistance"} <= set(result)
    assert result["val"] <= result["poc"] <= result["vah"]
    assert result["val"] <= result["vah"]
    assert result["support"] == 104.0  # min of recent 10 lows: range(5, 15) -> 99.0 + 5 = 104.0
    # No confirmed swing high above price in a straight rise: fallback = highest high of the PREVIOUS
    # bars (current bar excluded since E16-U8): 101 + 13 = 114.
    assert result["resistance"] == 114.0
    assert result["bias"] in ["LONG", "SHORT", "NEUTRAL"]



@pytest.mark.unit
def test_volume_is_spread_over_each_bar_range():
    eng = MarketStructureEngine(swing_lookback=20, volume_profile_bins=20)
    # 19 bars trading 100-101 with volume 10, one bar 101-110 with volume 10: POC must stay in 100-101.
    lows = [100.0] * 19 + [101.0]
    highs = [101.0] * 19 + [110.0]
    closes = [100.5] * 19 + [109.0]
    r = eng.calculate_market_structure(closes, highs, lows, [10.0] * 20)
    assert 100.0 <= r["poc"] <= 101.0
    assert r["method"] == "range_volume_profile"


@pytest.mark.unit
def test_swing_support_and_resistance_are_confirmed_pivots():
    eng = MarketStructureEngine(swing_lookback=20, pivot_bars=2)
    highs = [10, 11, 12, 15, 12, 11, 10, 11, 12, 11, 10.5]
    lows = [9, 8, 9, 10, 9, 6, 7, 8, 9, 9.5, 10]
    closes = [h - 0.5 for h in highs]
    r = eng.calculate_market_structure(closes, highs, lows, [1.0] * len(highs))
    assert r["resistance"] == 12        # most recent confirmed pivot high above price (index 8; index 3 is older)
    assert r["support"] == 6            # pivot low at index 5 (most recent confirmed below price)
