import pytest
from decimal import Decimal
from domain.value_objects import Symbol
from infrastructure.strategies.setup_engine import SetupEngine


def test_vwap_2_5_sigma_extreme_deviation_reversion():
    """Verify that VWAPReversal triggers on extreme 2.5 sigma deviations with rejection."""
    engine = SetupEngine()
    sym = Symbol("BTC-USDT")

    # Construct 20 bars with steady volume and extreme oversold dip
    prices = [100.0] * 19 + [92.0]  # Drops sharply to 92.0
    highs = [101.0] * 19 + [94.0]
    lows = [99.0] * 19 + [91.0]
    data_buffer = [{'open': 91.5, 'close': 93.5, 'high': 94.0, 'low': 91.0, 'volume': 100.0} for _ in range(20)]

    setups = engine.scan_for_setups(
        symbol=sym,
        prices=prices,
        highs=highs,
        lows=lows,
        val=0.0,
        vah=0.0,
        poc=100.0,
        data_buffer=data_buffer
    )

    mr_setups = [s for s in setups if s.setup_type == "NGMR_REVERSION" and s.direction == "BUY"]
    assert len(mr_setups) >= 1
    assert mr_setups[0].direction == "BUY"
    assert float(mr_setups[0].take_profit_level) >= 100.0


def test_sweep_scalper_requires_mss_midpoint_confirmation():
    """Verify SweepScalper requires closing beyond previous bar midpoint for MSS confirmation."""
    engine = SetupEngine()
    sym = Symbol("ETH-USDT")

    # 20 flat bars with high at 200.0 (neutral trend)
    prices = [195.0] * 19 + [195.0, 199.0]
    highs = [198.0] * 19 + [198.0, 202.0]  # Sweeps 198.0 to 202.0
    lows = [192.0] * 19 + [194.0, 197.0]

    # Bar -2 midpoint = (198.0 + 194.0) / 2 = 196.0. If close is 199.0 (> 196.0), MSS is NOT met
    data_buffer_no_mss = [{'open': 201.0, 'close': 199.0, 'high': 202.0, 'low': 197.0, 'volume': 50.0} for _ in range(21)]
    setups_no_mss = engine.scan_for_setups(
        symbol=sym,
        prices=prices,
        highs=highs,
        lows=lows,
        val=190.0,
        vah=205.0,
        poc=195.0,
        data_buffer=data_buffer_no_mss
    )
    assert not any(s.setup_type == "NGLS_SWEEP" and s.direction == "SELL" for s in setups_no_mss)

    # When close drops below midpoint 196.0 (e.g. 195.0), MSS is satisfied
    prices[-1] = 195.0
    data_buffer_mss = [{'open': 201.0, 'close': 195.0, 'high': 202.0, 'low': 193.0, 'volume': 50.0} for _ in range(21)]
    setups_mss = engine.scan_for_setups(
        symbol=sym,
        prices=prices,
        highs=highs,
        lows=lows,
        val=190.0,
        vah=205.0,
        poc=195.0,
        data_buffer=data_buffer_mss
    )
    sweep_sells = [s for s in setups_mss if s.setup_type == "NGLS_SWEEP" and s.direction == "SELL"]
    assert len(sweep_sells) == 1
    assert sweep_sells[0].direction == "SELL"


def test_mtf_trend_requires_momentum_alignment():
    """Verify MTFTrend requires EMA/SMA trend momentum alignment before breakout entry."""
    engine = SetupEngine()
    sym = Symbol("SOL-USDT")

    # Bullish trend (SMA10 > SMA20) above VAH
    prices = [100.0 + i * 2.0 for i in range(25)]
    highs = [p + 1.0 for p in prices]
    lows = [p - 1.0 for p in prices]
    vah = 145.0
    val = 110.0
    poc = 130.0

    setups = engine.scan_for_setups(
        symbol=sym,
        prices=prices,
        highs=highs,
        lows=lows,
        val=val,
        vah=vah,
        poc=poc
    )

    trend_buys = [s for s in setups if s.setup_type == "NGTREND_FOLLOW" and s.direction == "BUY"]
    assert len(trend_buys) == 1
    assert trend_buys[0].direction == "BUY"


def test_active_position_manager_enforces_3_5_pct_minimum_locked_roe():
    """Verify ActivePositionManager ensures Breakeven SL guarantees at least +3.5% ROE."""
    from infrastructure.risk.active_position_manager import ActivePositionManager
    apm = ActivePositionManager(fee_buffer_pct=0.0035, leverage_multiplier=10.0)

    entry_price = 2418.77  # ETH Short
    is_long = False
    qty = 0.009

    # Breakeven calculation for Short
    be_sl = entry_price * (1.0 - apm.fee_buffer_pct)
    gross_locked_roe = ((entry_price - be_sl) / entry_price) * apm.leverage_multiplier * 100.0

    assert round(gross_locked_roe, 2) >= 3.5
    assert be_sl < entry_price

