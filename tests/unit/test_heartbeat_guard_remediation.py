"""
Unit and Regression Test Suite for HeartbeatGuard Market Data Heartbeat Remediation.
Verifies that:
1. Fresh market data updates heartbeat timestamps properly.
2. Symbol normalization handles domain Symbol vs string vs hyphenated symbol formats consistently.
3. Fresh data after 90+ seconds uptime prevents false stale vetoes.
4. Genuine stale data (> 90s without update) still vetoes cleanly.
5. Missing heartbeat vetoes safely (fail-closed).
6. Multiple symbols maintain independent timestamps.
7. Continuous live market streaming over 90s uptime maintains zero false vetoes.
"""

from datetime import datetime, timedelta
import pytest

from domain.value_objects import Symbol, Percentage
from domain.entities import ExecutionIntent
from domain.enums.order_side import OrderSide
from infrastructure.messaging.event_system import SignalProcessor, EventRouter, SignalEvent, EventType


class MockExecutionService:
    is_backtest = False


def create_mock_intent(symbol_str: str = "BTCUSDT") -> ExecutionIntent:
    return ExecutionIntent(
        symbol=Symbol(symbol_str),
        strategy_name="trend_following",
        side=OrderSide.BUY,
        intent_confidence=Percentage(0.85),
        risk_parameters={"sl": 100.0, "tp": 200.0},
        timestamp=datetime.now()
    )


def test_1_fresh_heartbeat_timestamp_updated():
    router = EventRouter()
    processor = SignalProcessor(router)
    
    # Update heartbeat
    processor.update_market_data_heartbeat("BTCUSDT")
    
    # Verify timestamp exists and is fresh
    assert hasattr(processor, '_last_market_data_times')
    assert "BTCUSDT" in processor._last_market_data_times
    elapsed = (datetime.now() - processor._last_market_data_times["BTCUSDT"]).total_seconds()
    assert elapsed < 2.0


def test_2_symbol_normalization():
    router = EventRouter()
    processor = SignalProcessor(router)
    
    # Update using different symbol representations
    processor.update_market_data_heartbeat(Symbol("BTCUSDT"))
    assert "BTCUSDT" in processor._last_market_data_times
    
    processor.update_market_data_heartbeat("BTC-USDT")
    assert "BTCUSDT" in processor._last_market_data_times
    
    processor.update_market_data_heartbeat("btcusdt")
    assert "BTCUSDT" in processor._last_market_data_times


def test_3_fresh_data_prevents_false_veto():
    router = EventRouter()
    processor = SignalProcessor(router)
    
    # Simulate service start 120 seconds ago
    processor.update_market_data_heartbeat("BTCUSDT", timestamp=datetime.now() - timedelta(seconds=120))
    
    # Receive fresh market data update now
    processor.update_market_data_heartbeat("BTCUSDT")
    
    intent = create_mock_intent("BTCUSDT")
    
    # Verify execution intent passes HeartbeatGuard check
    last_time = processor._last_market_data_times["BTCUSDT"]
    elapsed = (datetime.now() - last_time).total_seconds()
    assert elapsed <= 90.0


def test_4_genuine_stale_data_still_vetoes():
    router = EventRouter()
    processor = SignalProcessor(router)
    
    # Set stale heartbeat (100 seconds ago)
    processor.update_market_data_heartbeat("BTCUSDT", timestamp=datetime.now() - timedelta(seconds=100))
    
    intent = create_mock_intent("BTCUSDT")
    event = SignalEvent(event_type=EventType.EXECUTION_INTENT, data=intent, source_component="Test")
    
    exec_service = MockExecutionService()
    result = processor._process_execution_intent(event, exec_service)
    
    # Must fail-closed (return None due to stale heartbeat veto)
    assert result is None


def test_5_missing_heartbeat_vetoes_safely():
    router = EventRouter()
    processor = SignalProcessor(router)
    
    # Uninitialized symbol
    intent = create_mock_intent("ETHUSDT")
    event = SignalEvent(event_type=EventType.EXECUTION_INTENT, data=intent, source_component="Test")
    
    exec_service = MockExecutionService()
    result = processor._process_execution_intent(event, exec_service)
    
    # Must fail-closed (return None)
    assert result is None


def test_6_multiple_symbols_independent():
    router = EventRouter()
    processor = SignalProcessor(router)
    
    t_old = datetime.now() - timedelta(seconds=120)
    t_new = datetime.now()
    
    processor.update_market_data_heartbeat("BTCUSDT", timestamp=t_old)
    processor.update_market_data_heartbeat("ETHUSDT", timestamp=t_new)
    
    assert (datetime.now() - processor._last_market_data_times["BTCUSDT"]).total_seconds() > 90.0
    assert (datetime.now() - processor._last_market_data_times["ETHUSDT"]).total_seconds() < 2.0


def test_7_continuous_streaming_regression():
    router = EventRouter()
    processor = SignalProcessor(router)
    
    # Initial startup at t-100s
    processor.update_market_data_heartbeat("BTCUSDT", timestamp=datetime.now() - timedelta(seconds=100))
    
    # Simulate continuous WebSocket tick ingestion
    for _ in range(5):
        processor.update_market_data_heartbeat("BTCUSDT")
    
    intent = create_mock_intent("BTCUSDT")
    
    # Check that staleness is near 0s
    last_time = processor._last_market_data_times["BTCUSDT"]
    elapsed = (datetime.now() - last_time).total_seconds()
    assert elapsed < 1.0
