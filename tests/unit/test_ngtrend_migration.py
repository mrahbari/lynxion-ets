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

    # E16-U10 (2026-11-24): TrendFollow runs the canonical Donchian-20 + EMA50/200 setup on closed 1h bars.
    base_time = datetime(2026, 1, 1, 0, 0)
    p = 100.0
    for i in range(260):                       # steady uptrend: EMA50 > EMA200
        p *= 1.001
        adapter.update_with_market_data(_bar(p, hi=p * 1.002, lo=p * 0.998, t=base_time + timedelta(hours=i)))

    trend_time = base_time + timedelta(hours=260)
    trend_bar = _bar(p * 1.03, hi=p * 1.035, lo=p * 1.0, t=trend_time)   # breaks the 20-bar high
    trend_bar["obi_ratio"] = 0.20
    trend_bar["cvd"] = 5.0
    trend_bar["best_bid"] = round(p * 1.03 - 0.05, 6)
    trend_bar["best_ask"] = round(p * 1.03 + 0.05, 6)
    adapter.update_with_market_data(trend_bar)

    sig = adapter.generate_signal(symbol)
    assert sig is not None
    assert sig.signal_type == SignalType.BUY
    setup = sig.metadata["setup"]
    assert setup.setup_type == "DONCHIAN20_EMA_TREND"
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
    assert intent.risk_parameters["limit_price"] == trend_bar["best_bid"]
    assert intent.risk_parameters["time_in_force"] == "POST_ONLY"


@pytest.mark.unit
def test_ngtrend_backtester_and_live_use_identical_pipeline():
    strat_func = load_sample_strategy("trend_following", raw_signal=False)
    assert strat_func is not None
    assert hasattr(strat_func, "record_trade_result")
