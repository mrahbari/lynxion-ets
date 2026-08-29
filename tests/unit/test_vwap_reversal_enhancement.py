"""Unit tests verifying VWAPReversal (NGMR_REVERSION) enhancements."""
import pytest
from decimal import Decimal
from domain.value_objects import Symbol
from infrastructure.strategies.setup_engine import SetupEngine


def test_vwap_reversal_buy_vetoed_in_bear_trend():
    """Verify that dip-buying is vetoed when market breaks down below VAL in a strong bear trend."""
    engine = SetupEngine()
    sym = Symbol("ETH-USDT")

    # Downward trending prices (15% drop over 25 bars)
    prices = [120.0 - i * 1.5 for i in range(25)]
    highs = [p + 0.5 for p in prices]
    lows = [p - 0.5 for p in prices]
    val = 85.0  # current_price is 84.0 < 85.0 * 0.995 (breakdown below VAL)
    vah = 110.0
    poc = 95.0

    setups = engine.scan_for_setups(
        symbol=sym,
        prices=prices,
        highs=highs,
        lows=lows,
        val=val,
        vah=vah,
        poc=poc
    )

    reversion_buys = [s for s in setups if s.setup_type == "NGMR_REVERSION" and s.direction == "BUY"]
    assert len(reversion_buys) == 0


def test_vwap_reversal_sell_vetoed_in_bull_trend():
    """Verify that shorting is vetoed when market breaks out above VAH in a strong bull trend."""
    engine = SetupEngine()
    sym = Symbol("BTC-USDT")

    # Upward trending prices (25% rally over 25 bars)
    prices = [100.0 + i * 2.0 for i in range(25)]
    highs = [p + 1.0 for p in prices]
    lows = [p - 1.0 for p in prices]
    val = 110.0
    vah = 145.0  # current_price is 148.0 > 145.0 * 1.005 (breakout above VAH)
    poc = 125.0

    setups = engine.scan_for_setups(
        symbol=sym,
        prices=prices,
        highs=highs,
        lows=lows,
        val=val,
        vah=vah,
        poc=poc
    )

    reversion_sells = [s for s in setups if s.setup_type == "NGMR_REVERSION" and s.direction == "SELL"]
    assert len(reversion_sells) == 0


def test_vwap_reversal_buy_in_ranging_market_expands_rr_to_at_least_1_5():
    """Verify that in a ranging market, VWAPReversal produces a valid setup with R:R >= 1.5."""
    engine = SetupEngine()
    sym = Symbol("SOL-USDT")

    prices = [98.0, 99.0, 100.0, 101.0, 100.0, 99.0, 98.0, 97.5, 97.0, 96.5,
              96.0, 97.0, 98.0, 99.0, 100.0, 99.5, 99.0, 98.0, 97.0, 96.5,
              96.0, 95.8, 95.5, 95.3, 95.2]

    highs = [p + 0.8 for p in prices]
    lows = [p - 0.8 for p in prices]
    lows[-1] = 94.4
    highs[-1] = 95.8

    val = 95.2
    vah = 101.0
    poc = 98.0

    data_buffer = [{"open": 95.0, "high": 95.8, "low": 94.4, "close": 95.2, "volume": 1000.0}]

    setups = engine.scan_for_setups(
        symbol=sym,
        prices=prices,
        highs=highs,
        lows=lows,
        val=val,
        vah=vah,
        poc=poc,
        data_buffer=data_buffer
    )

    reversion_buys = [s for s in setups if s.setup_type == "NGMR_REVERSION" and s.direction == "BUY"]
    assert len(reversion_buys) == 1
    setup = reversion_buys[0]
    entry = float(setup.trigger_price)
    sl = float(setup.stop_loss_level)
    tp = float(setup.take_profit_level)

    rr = (tp - entry) / (entry - sl)
    assert round(rr, 2) >= 1.50
