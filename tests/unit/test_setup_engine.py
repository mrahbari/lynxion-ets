"""Unit tests for the 15m Setup Engine (Phase 3)."""

import pytest
from domain.value_objects import Symbol
from infrastructure.strategies.setup_engine import SetupEngine


@pytest.mark.unit
def test_setup_engine_scans_and_triggers_setups():
    engine = SetupEngine()
    symbol = Symbol("BTC-USDT")

    # Construct realistic series for a bullish sweep (low of last bar penetrates 20-bar low, closes green above midpoint)
    prices = [10.0] * 19 + [10.0, 10.2]
    highs = [11.0] * 19 + [11.0, 11.2]
    lows = [9.0] * 19 + [9.0, 8.5]    # previous 20 lows: min is 9.0
    
    setups = engine.scan_for_setups(
        symbol=symbol,
        prices=prices,
        highs=highs,
        lows=lows,
        val=8.0,
        vah=12.0,
        poc=10.0
    )

    assert len(setups) > 0
    sweep_setup = [s for s in setups if s.setup_type == "NGLS_SWEEP"][0]
    assert sweep_setup.direction == "BUY"
    assert float(sweep_setup.trigger_price) == 10.2
    assert 0.0 < float(sweep_setup.stop_loss_level) < float(sweep_setup.trigger_price)


@pytest.mark.unit
def test_setup_engine_triggers_ngmr_reversions():
    engine = SetupEngine()
    symbol = Symbol("BTC-USDT")

    # Prices ending exactly at VAL (5.0)
    prices = [10.0] * 10
    prices[-1] = 5.0
    highs = [11.0] * 10
    lows = [9.0] * 10

    setups = engine.scan_for_setups(
        symbol=symbol,
        prices=prices,
        highs=highs,
        lows=lows,
        val=5.0,
        vah=15.0,
        poc=10.0
    )

    assert len(setups) > 0
    reversion_setup = [s for s in setups if s.setup_type == "NGMR_REVERSION"][0]
    assert reversion_setup.direction == "BUY"
    assert float(reversion_setup.trigger_price) == 5.0
    assert float(reversion_setup.take_profit_level) == 10.0

