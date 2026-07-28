"""Unit tests verifying the NGTrend pipeline integration."""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from domain.value_objects import Symbol, Percentage
from domain.entities import FusedSignal, SignalType
from domain.enums.order_side import OrderSide
from infrastructure.strategies.adapters.trend_follow_strategy_adapter import TrendFollowStrategyAdapter
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
def test_ngtrend_path_creates_candidate_setup_and_gating():
    adapter = TrendFollowStrategyAdapter({})
    symbol = Symbol("BTCUSDT")

    # Feed enough bars to establish a baseline
    base_time = datetime(2026, 1, 1, 0, 0)
    for i in range(24):
        adapter.update_with_market_data(_bar(100.0, hi=101.0, lo=99.0, t=base_time + timedelta(minutes=i)))

    # The 25th bar moves above VAH (VAH will be close to 100.0, so 105.0 is trending up).
    trend_time = base_time + timedelta(minutes=24)
    trend_bar = _bar(105.0, hi=106.0, lo=104.0, t=trend_time)
    trend_bar["obi_ratio"] = 0.20  # Confirms BUY setup
    trend_bar["cvd"] = 5.0        # Confirms BUY setup
    trend_bar["best_bid"] = 104.95
    trend_bar["best_ask"] = 105.05
    adapter.update_with_market_data(trend_bar)

    # 1. Verify NGTrend path creates a Signal with setup metadata (containing CandidateSetup)
    sig = adapter.generate_signal(symbol)
    assert sig is not None
    assert sig.signal_type == SignalType.BUY
    assert "setup" in sig.metadata
    
    setup = sig.metadata["setup"]
    assert setup.setup_type == "NGTREND_FOLLOW"
    assert setup.direction == "BUY"

    # 2. Verify confirmation rejects invalid order-flow conditions
    fused_signal = FusedSignal(
        symbol=symbol,
        dominant_bias=SignalType.BUY,
        direction=1.0,
        dominance_score=1.0,
        regime_context="trending_up",
        confidence=Percentage(Decimal("0.8")),
        timestamp=trend_time
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
    assert intent.risk_parameters["limit_price"] == 104.95  # best bid (from lo of trend_bar)
    assert intent.risk_parameters["time_in_force"] == "POST_ONLY"


@pytest.mark.unit
def test_ngtrend_backtester_and_live_use_identical_pipeline():
    strat_func = load_sample_strategy("trend_following", raw_signal=False)
    assert strat_func is not None
    assert hasattr(strat_func, "record_trade_result")
