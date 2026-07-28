"""Unit tests for the 1m Execution Optimizer (Phase 5)."""

import pytest
from domain.value_objects import Symbol
from infrastructure.execution.execution_optimizer import ExecutionOptimizer


@pytest.mark.unit
def test_execution_optimizer_rules():
    optimizer = ExecutionOptimizer(max_spread_pct=0.001)  # 0.1% max spread
    symbol = Symbol("BTC-USDT")

    # Valid spread, buy order -> limit price should be best bid, POST_ONLY TIF
    order = optimizer.optimize_order(
        symbol=symbol,
        direction="BUY",
        current_price=50000.0,
        best_bid=49990.0,
        best_ask=50010.0,  # spread 20.0 (0.04% of price)
        quantity=1.0
    )

    assert order is not None
    assert order["order_side"] == "BUY"
    assert order["order_type"] == "LIMIT"
    assert float(order["price"]) == 49990.0
    assert order["time_in_force"] == "POST_ONLY"

    # Valid spread, sell order -> limit price should be best ask
    order_sell = optimizer.optimize_order(
        symbol=symbol,
        direction="SELL",
        current_price=50000.0,
        best_bid=49990.0,
        best_ask=50010.0,
        quantity=1.0
    )
    assert float(order_sell["price"]) == 50010.0

    # Invalid spread (spread too wide) -> should return None
    bad_order = optimizer.optimize_order(
        symbol=symbol,
        direction="BUY",
        current_price=50000.0,
        best_bid=49900.0,
        best_ask=50100.0,  # spread 200.0 (0.4% of price)
        quantity=1.0
    )
    assert bad_order is None
