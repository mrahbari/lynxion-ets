"""Unit tests verifying the OI Footprint pipeline migration."""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from domain.value_objects import Symbol, Percentage
from domain.entities import FusedSignal, SignalType
from domain.enums.order_side import OrderSide
from infrastructure.strategies.adapters.oi_footprint_strategy_adapter import OIFootprintStrategyAdapter
from infrastructure.backtest.strategy_provider import load_sample_strategy


def _bar(p, hi=None, lo=None, v=1.0, oi=0.0, t=None):
    if t is None:
        t = datetime.now()
    return {
        "open": p,
        "high": hi if hi is not None else p,
        "low": lo if lo is not None else p,
        "close": p,
        "volume": v,
        "open_interest": oi,
        "timestamp": t
    }


@pytest.mark.unit
def test_ngoi_creates_candidate_setup_under_real_oi():
    adapter = OIFootprintStrategyAdapter({})
    symbol = Symbol("BTCUSDT")

    # Feed bars to establish baseline
    base_time = datetime(2026, 1, 1, 0, 0)
    for i in range(24):
        adapter.update_with_market_data(_bar(100.0, oi=10000.0, t=base_time + timedelta(minutes=i)))

    # Bar 25: Rising price, falling Open Interest -> BUY (Short Squeeze)
    trigger_time = base_time + timedelta(minutes=24)
    trigger_bar = _bar(105.0, oi=9500.0, t=trigger_time)  # price up by 5%, OI down by 5%
    trigger_bar["obi_ratio"] = 0.20
    trigger_bar["cvd"] = 5.0
    trigger_bar["best_bid"] = 104.95
    trigger_bar["best_ask"] = 105.05
    adapter.update_with_market_data(trigger_bar)

    # 1. Verify OI path creates a Signal with setup metadata (containing CandidateSetup)
    sig = adapter.generate_signal(symbol)
    assert sig is not None
    assert sig.signal_type == SignalType.BUY
    assert "setup" in sig.metadata
    
    setup = sig.metadata["setup"]
    assert setup.setup_type == "NGOI_SETUP"
    assert setup.direction == "BUY"

    # 2. Verify confirmation rejects invalid order-flow conditions
    fused_signal = FusedSignal(
        symbol=symbol,
        dominant_bias=SignalType.BUY,
        direction=1.0,
        dominance_score=1.0,
        regime_context="breakout",
        confidence=Percentage(Decimal("0.8")),
        timestamp=trigger_time
    )

    # Case A: OBI/CVD does not confirm -> should return None
    adapter.data_buffer[-1]["obi_ratio"] = -0.05
    intent_none = adapter.evaluate_fused_signal(fused_signal)
    assert intent_none is None

    # Case B: OBI/CVD confirms -> should return valid ExecutionIntent
    adapter.data_buffer[-1]["obi_ratio"] = 0.25
    intent = adapter.evaluate_fused_signal(fused_signal)
    assert intent is not None
    assert intent.side == OrderSide.BUY

    # 3. Verify optimizer produces maker execution parameters
    assert intent.risk_parameters["limit_price"] == 104.95
    assert intent.risk_parameters["time_in_force"] == "POST_ONLY"


@pytest.mark.unit
def test_ngoi_creates_candidate_setup_under_proxy_fallback():
    adapter = OIFootprintStrategyAdapter({})
    symbol = Symbol("BTCUSDT")

    # Feed bars with alternating prices to maintain normal RSI (~50)
    base_time = datetime(2026, 1, 1, 0, 0)
    for i in range(24):
        p = 98.0 if i % 2 == 1 else 100.0
        adapter.update_with_market_data(_bar(p, v=1.0, t=base_time + timedelta(minutes=i)))

    # Bar 25: Volume spike, price up, rsi ok -> BUY (Volume Proxy setup)
    trigger_time = base_time + timedelta(minutes=24)
    trigger_bar = _bar(105.0, v=5.0, t=trigger_time)  # volume spike = 5.0 (avg is 1.0)
    trigger_bar["obi_ratio"] = 0.20
    trigger_bar["cvd"] = 5.0
    trigger_bar["best_bid"] = 104.95
    trigger_bar["best_ask"] = 105.05
    adapter.update_with_market_data(trigger_bar)

    sig = adapter.generate_signal(symbol)
    assert sig is not None
    assert sig.signal_type == SignalType.BUY
    assert "setup" in sig.metadata
    
    setup = sig.metadata["setup"]
    assert setup.setup_type == "NGOI_SETUP"
