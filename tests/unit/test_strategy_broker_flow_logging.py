import logging

import pytest

from shared.logger import EnhancedLogger


@pytest.mark.unit
def test_strategy_to_broker_flow_is_available_and_emits_execution_context():
    enhanced = EnhancedLogger("StrategyBrokerFlowRegression")
    records = []
    handler = logging.Handler()
    handler.emit = records.append
    enhanced.logger.addHandler(handler)
    try:
        enhanced.log_strategy_to_broker_flow(
            symbol="BTCUSDT",
            strategy_name="TrendFollow",
            trade_executed=False,
            signal_type="BUY",
            confidence=0.75,
            reason="execution intent generated",
        )
    finally:
        enhanced.logger.removeHandler(handler)

    assert len(records) == 1
    message = records[0].getMessage()
    assert "STRATEGY TO BROKER: TrendFollow" in message
    assert "Symbol: BTCUSDT" in message
    assert "Status: PENDING_OR_REJECTED" in message
    assert "Confidence: 75.00%" in message
