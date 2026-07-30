"""Unit tests for the 15m Setup Engine (Phase 3)."""

import pytest
from domain.value_objects import Symbol
from infrastructure.strategies.setup_engine import SetupEngine


@pytest.mark.unit
def test_setup_engine_scans_and_triggers_setups():
    engine = SetupEngine()
    symbol = Symbol("BTC-USDT")

    # Construct series for a bullish sweep (low of last bar penetrates minimum of previous 20 lows)
    # Minimum of range(1, 21) is 1. We'll set last low to 0.5 (penetrates), but last close to 2.0 (pullback)
    prices = [float(i + 2) for i in range(21)]  # ends at 22.0
    highs = [float(i + 3) for i in range(21)]
    lows = [float(i + 1) for i in range(21)]    # previous 20 lows: min is 1.0
    
    # Modify last bar to trigger bullish sweep
    lows[-1] = 0.5
    prices[-1] = 2.0
    
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
    sweep_setup = [s for s in setups if s.setup_type == "NGLS_SWEEP"][0]
    assert sweep_setup.direction == "BUY"
    assert float(sweep_setup.trigger_price) == 2.0
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

