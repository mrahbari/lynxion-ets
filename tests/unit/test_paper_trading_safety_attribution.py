"""Unit tests verifying Paper Trading Safety & Attribution features (Task 12)."""

import pytest
import time
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from domain.value_objects import Symbol, Money, Percentage
from domain.enums.order_side import OrderSide
from domain.entities import ExecutionIntent, MarketObservation
from infrastructure.tracking.trade_tracker import TradeTracker
from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
from infrastructure.messaging.event_system import SignalProcessor
from application.containers.container import container


@pytest.fixture(autouse=True)
def setup_mock_container():
    # Register a mock risk engine in the global container to avoid DI resolution errors
    mock_risk_engine = MagicMock()
    mock_risk_mgr = MagicMock()
    mock_risk_mgr.positions = {}
    mock_risk_mgr.starting_equity = 10000.0
    mock_risk_mgr.total_pnl = 0.0
    mock_risk_mgr.calculate_drawdown_factor.return_value = 1.0
    mock_risk_mgr.calculate_correlation_penalty.return_value = 1.0
    mock_risk_mgr.max_risk_per_trade = 0.02
    mock_risk_engine._risk_manager = mock_risk_mgr
    mock_risk_engine.calculate_dynamic_size.return_value = 1.0
    
    # Store original service if exists
    original_service = container._services.get("risk_engine")
    container.register("risk_engine", mock_risk_engine, singleton=True)
    yield mock_risk_engine
    if original_service is not None:
        container._services["risk_engine"] = original_service
    elif "risk_engine" in container._services:
        del container._services["risk_engine"]


@pytest.mark.unit
def test_setup_level_pnl_attribution():
    tracker = TradeTracker(forensic_logging_enabled=False)
    now = datetime.utcnow()

    # 1. Register and close BREAKOUT wins
    tracker.register_trade("t1", "BTCUSDT", "BUY", 100.0, 1.0, 95.0, 110.0, now, "BREAKOUT")
    tracker.close_trade("t1", 105.0, "TP", now + timedelta(minutes=10))

    # 2. Register and close BREAKOUT loss
    tracker.register_trade("t2", "BTCUSDT", "BUY", 100.0, 1.0, 95.0, 110.0, now, "BREAKOUT")
    tracker.close_trade("t2", 95.0, "SL", now + timedelta(minutes=5))

    # 3. Register and close REVERSION win
    tracker.register_trade("t3", "BTCUSDT", "BUY", 100.0, 1.0, 95.0, 110.0, now, "REVERSION")
    tracker.close_trade("t3", 110.0, "TP", now + timedelta(minutes=15))

    # Get attribution
    attr = tracker.get_setup_pnl_attribution()

    # Assert Breakout stats
    assert "BREAKOUT" in attr
    bo = attr["BREAKOUT"]
    assert bo["total_trades"] == 2
    assert bo["win_rate"] == 0.5
    assert bo["realized_pnl"] == 0.0  # +5.0 and -5.0
    assert bo["average_holding_time"] == 450.0  # (10 + 5) / 2 = 7.5 mins = 450s
    assert bo["max_drawdown_contribution"] == -5.0

    # Assert Reversion stats
    assert "REVERSION" in attr
    rev = attr["REVERSION"]
    assert rev["total_trades"] == 1
    assert rev["win_rate"] == 1.0
    assert rev["realized_pnl"] == 10.0
    assert rev["max_drawdown_contribution"] == 0.0


@pytest.mark.unit
def test_market_data_heartbeat_safety_guard(setup_mock_container):
    # Setup SignalProcessor with mock router and services
    router = MagicMock()
    processor = SignalProcessor(router)
    processor.logger = MagicMock()

    # Stub execution service
    exec_service = MagicMock()
    exec_service.is_backtest = False
    exec_service.get_current_price.return_value = 50000.0

    # Simulate observation to register last market data time
    obs = MarketObservation(
        symbol=Symbol("BTCUSDT"),
        observation_type="price_tick",
        observation_value=50000.0,
        confidence=Percentage(Decimal("1.0")),
        timestamp=datetime.now()
    )
    event_obs = MagicMock()
    event_obs.data = obs
    processor._process_observation(event_obs, MagicMock())

    # Verify heartbeat exists
    assert "BTCUSDT" in processor._last_market_data_times

    # 1. Normal case: Heartbeat is fresh (under 15s)
    intent = ExecutionIntent(
        symbol=Symbol("BTCUSDT"),
        strategy_name="TrendFollowing",
        side=OrderSide.BUY,
        intent_confidence=Percentage(Decimal("0.8")),
        risk_parameters={"limit_price": 50000.0, "stop_loss": 49000.0},
        timestamp=datetime.now()
    )
    event_intent = MagicMock()
    event_intent.data = intent

    # Check if order creation proceeds (execute_order called)
    processor._process_execution_intent(event_intent, exec_service)
    assert exec_service.execute_order.called

    # 2. Veto case: Stale heartbeat (20 seconds ago)
    exec_service.execute_order.reset_mock()
    processor._last_market_data_times["BTCUSDT"] = datetime.now() - timedelta(seconds=20)

    processor._process_execution_intent(event_intent, exec_service)
    # Submission must be vetoed / rejected, so execute_order should not be called
    assert not exec_service.execute_order.called


@pytest.mark.unit
def test_order_book_liquidity_depth_guard(setup_mock_container):
    router = MagicMock()
    processor = SignalProcessor(router)
    processor.logger = MagicMock()

    # Stub execution service with broker exposing fetch_order_book
    exec_service = MagicMock()
    exec_service.is_backtest = False
    exec_service.get_current_price.return_value = 100.0
    
    broker = MagicMock()
    # Mock broker to return low liquidity in top 3 levels: total 0.5 units
    broker.fetch_order_book.return_value = {
        "bids": [[99.0, 0.2], [98.0, 0.2], [97.0, 0.1]],
        "asks": [[101.0, 0.2], [102.0, 0.2], [103.0, 0.1]]
    }
    exec_service.broker = broker

    # Make heartbeat fresh
    processor._last_market_data_times = {"BTCUSDT": datetime.now()}

    # Set custom size mock to return 2.0 (so that size starts at 2.0)
    setup_mock_container.calculate_dynamic_size.return_value = 2.0

    # Submit intent with size 2.0
    intent = ExecutionIntent(
        symbol=Symbol("BTCUSDT"),
        strategy_name="Breakout",
        side=OrderSide.BUY,
        intent_confidence=Percentage(Decimal("0.8")),
        risk_parameters={"limit_price": 100.0, "stop_loss": 95.0, "position_quantity": 2.0},
        timestamp=datetime.now()
    )
    event_intent = MagicMock()
    event_intent.data = intent

    processor._process_execution_intent(event_intent, exec_service)
    
    # Assert quantity is scaled down to 0.5
    assert exec_service.execute_order.called
    submitted_order = exec_service.execute_order.call_args[0][0]
    assert float(submitted_order.quantity) == pytest.approx(0.5)


@pytest.mark.unit
def test_rolling_correlation_calculation():
    # Setup risk manager with short update interval
    risk_mgr = EnterpriseRiskManager(max_correlation=0.7)
    
    # Stop background thread to calculate manually
    risk_mgr.correlation_update_interval_sec = 999999.0 

    # Populate price history for BTC and ETH
    for p in [100, 102, 101, 103, 104, 106, 105]:
        risk_mgr.record_price("BTCUSDT", float(p))
    for p in [200, 204, 202, 206, 208, 212, 210]:
        risk_mgr.record_price("ETHUSDT", float(p))

    # Assert history populated
    assert len(risk_mgr.price_history_for_correlation["BTCUSDT"]) == 7
    assert len(risk_mgr.price_history_for_correlation["ETHUSDT"]) == 7

    # Calculate correlation
    risk_mgr.recalculate_correlations()

    # Get correlation between BTC and ETH
    corr = risk_mgr.correlation_matrix["BTCUSDT"]["ETHUSDT"]
    # Positive correlation should be close to 1.0 (since they moved together)
    assert corr > 0.8
    assert corr <= 1.0
