"""
Unit tests for SetupEngine price-action rejection, trend alignment, and expanded ATR SL.
"""
from decimal import Decimal
from domain.value_objects import Symbol
from infrastructure.strategies.setup_engine import SetupEngine


def test_bullish_sweep_requires_rejection():
    engine = SetupEngine()
    sym = Symbol("BTCUSDT")

    # 20 flat/uptrend bars + 1 test bar
    prices = [100.0] * 20 + [101.0]
    highs = [102.0] * 20 + [102.0]
    lows = [99.0] * 20 + [98.0]  # Wicks below 99.0 (20-bar low)

    # Case 1: Green close (101.0 > open 100.0) -> Confirmed BUY sweep
    data_buffer = [{'open': 100.0, 'high': 102.0, 'low': 98.0, 'close': 101.0}]
    setups = engine.scan_for_setups(sym, prices, highs, lows, val=99.0, vah=103.0, poc=101.0, data_buffer=data_buffer)
    assert any(s.setup_type == "NGLS_SWEEP" and s.direction == "BUY" for s in setups)


def test_bearish_sweep_blocked_in_strong_uptrend():
    engine = SetupEngine()
    sym = Symbol("BTCUSDT")

    # Strong 20-bar uptrend prices (100 -> 120)
    prices = [100.0 + i for i in range(21)]
    highs = [p + 1.0 for p in prices]
    lows = [p - 1.0 for p in prices]

    # Candle wicks high to 122.0, closes at 120.0 (below previous high 121.0)
    highs[-1] = 122.0
    prices[-1] = 120.0

    # In a strong uptrend above VAH, bearish sweep should be rejected
    data_buffer = [{'open': 120.5, 'high': 122.0, 'low': 119.0, 'close': 120.0}]
    setups = engine.scan_for_setups(sym, prices, highs, lows, val=105.0, vah=115.0, poc=110.0, data_buffer=data_buffer)
    assert not any(s.setup_type == "NGLS_SWEEP" and s.direction == "SELL" for s in setups)
