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
    assert set(result) == {"bias", "poc", "vah", "val", "support", "resistance"}
    assert result["val"] <= result["poc"] <= result["vah"]
    assert result["val"] <= result["vah"]
    assert result["support"] == 104.0  # min of recent 10 lows: range(5, 15) -> 99.0 + 5 = 104.0
    assert result["resistance"] == 115.0  # max of recent 10 highs: range(5, 15) -> 101.0 + 14 = 115.0
    assert result["bias"] in ["LONG", "SHORT", "NEUTRAL"]
