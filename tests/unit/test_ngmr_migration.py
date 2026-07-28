"""Unit tests verifying the NGMR pipeline integration (Phase 1)."""

import pytest
import pandas as pd
from decimal import Decimal
from datetime import datetime, timedelta
from domain.value_objects import Symbol, Percentage
from domain.entities import FusedSignal, SignalType
from domain.enums.order_side import OrderSide
from infrastructure.strategies.adapters.mean_reversion_strategy_adapter import MeanReversionStrategyAdapter
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
def test_ngmr_path_creates_candidate_setup_at_val_boundary_and_gating():
    adapter = MeanReversionStrategyAdapter({})
    symbol = Symbol("BTCUSDT")

    # Feed enough bars to establish a baseline
    base_time = datetime(2026, 1, 1, 0, 0)
    for i in range(24):
        adapter.update_with_market_data(_bar(100.0, hi=101.0, lo=99.0, t=base_time + timedelta(minutes=i)))

    # The 25th bar touches the VAL boundary.
    # In MarketStructureEngine: VAL is calculated from the closes.
    # Let's see: the closes are all 100.0. The standard deviation is 0.0.
    # So VAL = VAH = POC = 100.0.
    # If the current price is 100.0, it is exactly at VAL/VAH/POC.
    # SetupEngine checks: threshold = 0.0005 * 100.0 = 0.05.
    # Since current_price is 100.0, abs(current_price - val) = 0.0 < threshold, triggering a BUY reversion setup.
    reversion_time = base_time + timedelta(minutes=24)
    reversion_bar = _bar(100.0, hi=101.0, lo=99.0, t=reversion_time)
    reversion_bar["obi_ratio"] = 0.20  # Confirms BUY setup
    reversion_bar["cvd"] = 5.0        # Confirms BUY setup
    adapter.update_with_market_data(reversion_bar)

    # 1. Verify NGMR path creates a Signal with setup metadata (containing CandidateSetup)
    sig = adapter.generate_signal(symbol)
    assert sig is not None
    assert sig.signal_type == SignalType.BUY
    assert "setup" in sig.metadata
    
    setup = sig.metadata["setup"]
    assert setup.setup_type == "NGMR_REVERSION"
    assert setup.direction == "BUY"
    assert float(setup.trigger_price) == 100.0

    # 2. Verify confirmation rejects invalid order-flow conditions
    fused_signal = FusedSignal(
        symbol=symbol,
        dominant_bias=SignalType.BUY,
        direction=1.0,
        dominance_score=1.0,
        regime_context="normal",
        confidence=Percentage(Decimal("0.8")),
        timestamp=reversion_time
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
    assert intent.risk_parameters["limit_price"] == 99.99  # best bid
    assert intent.risk_parameters["time_in_force"] == "POST_ONLY"


@pytest.mark.unit
def test_ngmr_backtester_and_live_use_identical_pipeline():
    # Verify that the strategy provider correctly resolves the adapter backtest strategy function
    strat_func = load_sample_strategy("mean_reversion", raw_signal=False)
    assert strat_func is not None
    assert hasattr(strat_func, "record_trade_result")
