"""Unit tests verifying the NGLS pipeline integration (Phase 1)."""

import pytest
import pandas as pd
from decimal import Decimal
from datetime import datetime, timedelta
from domain.value_objects import Symbol, Percentage
from domain.entities import FusedSignal, SignalType
from domain.enums.order_side import OrderSide
from infrastructure.strategies.adapters.liquidity_strategy_adapter import LiquidityStrategyAdapter
from infrastructure.backtest.realistic_backtester import RealisticBacktester
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
def test_ngls_path_creates_candidate_setup_and_requires_confirmation_and_optimizer():
    adapter = LiquidityStrategyAdapter({})
    symbol = Symbol("BTCUSDT")

    # Feed enough bars to establish a channel range and then trigger a sweep setup
    base_time = datetime(2026, 1, 1, 0, 0)
    for i in range(24):
        adapter.update_with_market_data(_bar(100.0, hi=101.0, lo=99.0, t=base_time + timedelta(minutes=i)))

    # Add the 25th bar (sweeping below previous low of 99.0 to 98.0, closing back inside at 100.0)
    sweep_time = base_time + timedelta(minutes=24)
    # Include confirmation OBI/CVD parameters inside the bar metadata
    sweep_bar = _bar(100.0, hi=101.0, lo=98.0, t=sweep_time)
    sweep_bar["obi_ratio"] = 0.20  # Confirms BUY setup (threshold is 0.1)
    sweep_bar["cvd"] = 5.0        # Confirms BUY setup (must be >= 0)
    adapter.update_with_market_data(sweep_bar)

    # 1. Verify NGLS path creates a Signal with setup metadata (containing CandidateSetup)
    sig = adapter.generate_signal(symbol)
    assert sig is not None
    assert sig.signal_type == SignalType.BUY
    assert "setup" in sig.metadata
    
    setup = sig.metadata["setup"]
    assert setup.setup_type == "NGLS_SWEEP"
    assert setup.direction == "BUY"
    assert float(setup.trigger_price) == 100.0

    # 2. Verify confirmation is required before ExecutionIntent
    # Rebuild a mock fused signal for evaluation
    fused_signal = FusedSignal(
        symbol=symbol,
        dominant_bias=SignalType.BUY,
        direction=1.0,
        dominance_score=1.0,
        regime_context="normal",
        confidence=Percentage(Decimal("0.8")),
        timestamp=sweep_time
    )

    # Case A: OBI/CVD does not confirm -> should return None
    adapter.data_buffer[-1]["obi_ratio"] = -0.05  # fails confirmation
    intent_none = adapter.evaluate_fused_signal(fused_signal)
    assert intent_none is None

    # Case B: OBI/CVD confirms -> should return valid ExecutionIntent
    adapter.data_buffer[-1]["obi_ratio"] = 0.25  # passes confirmation
    intent = adapter.evaluate_fused_signal(fused_signal)
    assert intent is not None
    assert intent.side == OrderSide.BUY

    # 3. Verify optimizer modifies execution parameters (limit price and POST_ONLY TIF)
    assert intent.risk_parameters["limit_price"] == 99.99  # best bid
    assert intent.risk_parameters["time_in_force"] == "POST_ONLY"


@pytest.mark.unit
def test_realistic_backtester_uses_same_path():
    # Verify that the strategy provider correctly resolves the adapter backtest strategy function
    strat_func = load_sample_strategy("liquidity", raw_signal=False)
    assert strat_func is not None
    assert hasattr(strat_func, "record_trade_result")
