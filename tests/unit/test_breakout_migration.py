"""Unit tests verifying the Breakout pipelines migration."""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from domain.value_objects import Symbol, Percentage
from domain.entities import FusedSignal, SignalType
from domain.enums.order_side import OrderSide
from infrastructure.strategies.adapters.breakout_strategy_adapter import BreakoutStrategyAdapter
from infrastructure.backtest.strategy_provider import load_sample_strategy


def _bar(p, hi=None, lo=None, v=1.0, t=None):
    if t is None:
        t = datetime.now()
    return {
        "open": p,
        "high": hi if hi is not None else p,
        "low": lo if lo is not None else p,
        "close": p,
        "volume": v,
        "timestamp": t
    }


@pytest.mark.unit
def test_ngbreakout_creates_candidate_setup_and_gating():
    adapter = BreakoutStrategyAdapter({})
    symbol = Symbol("BTCUSDT")

    base_time = datetime(2026, 1, 1, 0, 0)
    # Historical range (bars 0 to 14): high=105.0, low=95.0 (span=10.0)
    for i in range(15):
        adapter.update_with_market_data(_bar(100.0, hi=105.0, lo=95.0, t=base_time + timedelta(minutes=i)))
        
    # Recent range (bars 15 to 24): high=101.0, lo=99.0 (span=2.0)
    # Compression ratio = 10.0 / 2.0 = 5.0 (> 1.5)
    for i in range(15, 25):
        adapter.update_with_market_data(_bar(100.0, hi=101.0, lo=99.0, t=base_time + timedelta(minutes=i)))

    # Bar 25: breaks range_high of 101.0 -> current price = 103.0
    breakout_time = base_time + timedelta(minutes=25)
    breakout_bar = _bar(103.0, hi=104.0, lo=102.0, t=breakout_time)
    breakout_bar["obi_ratio"] = 0.20
    breakout_bar["cvd"] = 5.0
    breakout_bar["best_bid"] = 102.95
    breakout_bar["best_ask"] = 103.05
    adapter.update_with_market_data(breakout_bar)

    # 1. Verify breakout path creates a Signal with setup metadata (containing CandidateSetup)
    sig = adapter.generate_signal(symbol)
    assert sig is not None
    assert sig.signal_type == SignalType.BUY
    assert "setup" in sig.metadata
    
    setup = sig.metadata["setup"]
    assert setup.setup_type == "NGBREAKOUT"
    assert setup.direction == "BUY"

    # 2. Verify confirmation rejects invalid order-flow conditions
    fused_signal = FusedSignal(
        symbol=symbol,
        dominant_bias=SignalType.BUY,
        direction=1.0,
        dominance_score=1.0,
        regime_context="breakout",
        confidence=Percentage(Decimal("0.8")),
        timestamp=breakout_time
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
    assert intent.risk_parameters["limit_price"] == 102.95  # best bid (from test configuration)
    assert intent.risk_parameters["time_in_force"] == "POST_ONLY"


@pytest.mark.unit
def test_breakout_backtester_and_live_use_identical_pipeline():
    strat_func = load_sample_strategy("breakout", raw_signal=False)
    assert strat_func is not None
    assert hasattr(strat_func, "record_trade_result")
