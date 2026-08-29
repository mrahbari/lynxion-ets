"""Unit tests for SymbolCooldownGate and RiskEnforcement cooldown integration."""

import os
import tempfile
import time
from datetime import datetime
import pytest

from infrastructure.risk.symbol_cooldown_gate import SymbolCooldownGate
from infrastructure.risk.advanced_risk_management import AdvancedRiskManagementService


@pytest.mark.unit
def test_symbol_cooldown_gate_sl_exit():
    """Verify that Stop Loss exit activates 60-minute cooldown on all symbol format variants."""
    gate = SymbolCooldownGate()
    gate._sl_cooldowns.clear()

    # Record SL exit for BICOUSDT
    gate.record_stop_loss_exit("BICOUSDT")

    # Verify BICO-USDT, BICOUSDT, BICO/USDT are all blocked
    allowed1, reason1 = gate.is_symbol_allowed("BICOUSDT", cooldown_minutes=60)
    assert not allowed1
    assert "Cooldown ACTIVE" in reason1

    allowed2, reason2 = gate.is_symbol_allowed("BICO-USDT", cooldown_minutes=60)
    assert not allowed2

    allowed3, reason3 = gate.is_symbol_allowed("BICO/USDT", cooldown_minutes=60)
    assert not allowed3

    # Verify unrelated symbol is allowed
    allowed_other, _ = gate.is_symbol_allowed("BTCUSDT", cooldown_minutes=60)
    assert allowed_other


@pytest.mark.unit
def test_symbol_cooldown_gate_tp_spacing():
    """Verify that Take Profit exit registers a 15-minute spacing window and clears after 15m."""
    gate = SymbolCooldownGate()
    gate._sl_cooldowns.clear()

    # Record SL exit (60m)
    gate.record_stop_loss_exit("BICOUSDT")
    allowed_sl, _ = gate.is_symbol_allowed("BICOUSDT", cooldown_minutes=60)
    assert not allowed_sl

    # Take Profit exit sets 15m spacing window
    gate.record_take_profit_exit("BICOUSDT")
    # Immediate check should have 15m cooldown active
    allowed_tp_immediate, reason = gate.is_symbol_allowed("BICOUSDT", cooldown_minutes=60)
    assert not allowed_tp_immediate
    assert "Cooldown ACTIVE" in reason

    # After 16 minutes, symbol should be allowed
    gate._sl_cooldowns["BICOUSDT"] = time.time() - 3601.0
    allowed_after, reason_after = gate.is_symbol_allowed("BICOUSDT", cooldown_minutes=60)
    assert allowed_after
    assert reason_after == "ALLOWED"


@pytest.mark.unit
def test_symbol_health_gate_24h_circuit_breaker():
    """Verify that 2 rapid losses within 2 hours engage the 24-hour circuit breaker."""
    gate = SymbolCooldownGate()
    gate._sl_cooldowns.clear()
    gate._symbol_loss_history.clear()

    # First loss -> standard 60m cooldown
    gate.record_stop_loss_exit("SOLUSDT")
    rem_ts_1 = gate._sl_cooldowns.get("SOLUSDT", 0) - time.time()
    assert rem_ts_1 <= 3605.0  # Approx 60 minutes

    # Second loss 10 minutes later -> triggers 24-hour circuit breaker
    gate.record_stop_loss_exit("SOLUSDT")
    rem_ts_2 = gate._sl_cooldowns.get("SOLUSDT", 0) - time.time()
    assert rem_ts_2 > 22 * 3600.0  # > 22 hours remaining (24h lockout)

    allowed, reason = gate.is_symbol_allowed("SOLUSDT", cooldown_minutes=60)
    assert not allowed
    assert "60m Stop Loss Cooldown ACTIVE" in reason


@pytest.mark.unit
def test_active_position_manager_breakeven_and_trailing():
    """Verify ActivePositionManager triggers Breakeven at +5% ROE and Trailing Stop at +10% ROE."""
    from infrastructure.risk.active_position_manager import ActivePositionManager
    from unittest.mock import MagicMock

    mgr = ActivePositionManager(
        be_trigger_roe=5.0,
        trail_trigger_roe=10.0,
        trail_distance_pct=0.005,
        fee_buffer_pct=0.001,
        leverage_multiplier=10.0
    )
    mgr._positions_state.clear()
    mgr._sync_sl_to_exchange = MagicMock(return_value=True)

    mock_pos_long = MagicMock()
    mock_pos_long.symbol = "ETHUSDT"
    mock_pos_long.side.value = "BUY"
    mock_pos_long.quantity = 1.0
    mock_pos_long.entry_price = 2000.0
    mock_pos_long.current_price = 2000.0

    mock_broker = MagicMock()
    mock_broker.get_all_positions.return_value = [mock_pos_long]

    # Initial state (0% ROE) -> No action
    actions = mgr.evaluate_open_positions(mock_broker, current_prices={"ETHUSDT": 2000.0})
    assert len(actions) == 0

    # Price moves to 2012.0 (+0.6% price move -> +6.0% ROE) -> Triggers Breakeven (+0.1% buffer = $2002.0)
    actions = mgr.evaluate_open_positions(mock_broker, current_prices={"ETHUSDT": 2012.0})
    assert len(actions) == 1
    assert actions[0]["type"] == "BREAKEVEN_ACTIVATED"
    assert actions[0]["new_sl_price"] == pytest.approx(2002.0, abs=1e-2)

    # Price moves to 2030.0 (+1.5% price move -> +15.0% ROE) -> Triggers Trailing Stop Ratchet (0.5% below 2030 = $2019.85)
    actions = mgr.evaluate_open_positions(mock_broker, current_prices={"ETHUSDT": 2030.0})
    assert len(actions) == 1
    assert actions[0]["type"] == "TRAILING_STOP_RATCHET"
    assert actions[0]["new_sl_price"] == pytest.approx(2019.85, abs=1e-2)

    # Price drops to 2015.0 (below trailing stop $2019.85) -> Triggers Trailing Exit Executed
    actions = mgr.evaluate_open_positions(mock_broker, current_prices={"ETHUSDT": 2015.0})
    assert any(a["type"] == "TRAILING_EXIT_EXECUTED" for a in actions)


@pytest.mark.unit
def test_active_position_manager_does_not_record_breakeven_when_exchange_sync_fails():
    """A failed broker update must remain eligible for retry on the next management loop."""
    from infrastructure.risk.active_position_manager import ActivePositionManager
    from unittest.mock import MagicMock

    mgr = ActivePositionManager(be_trigger_roe=5.0, trail_trigger_roe=10.0)
    mgr._positions_state.clear()
    mgr._sync_sl_to_exchange = MagicMock(return_value=False)

    position = MagicMock()
    position.symbol = "ZECUSDT"
    position.side.value = "BUY"
    position.quantity = 1.0
    position.entry_price = 100.0
    position.current_price = 100.0
    broker = MagicMock()
    broker.get_all_positions.return_value = [position]
    broker.get_pending_orders.return_value = [{"type": "STOP_MARKET"}]

    actions = mgr.evaluate_open_positions(broker, current_prices={"ZECUSDT": 100.6})

    assert actions == []
    state = mgr._positions_state["ZECUSDT"]
    assert state["breakeven_active"] is False
    assert state["trailing_sl_price"] == 0.0


@pytest.mark.unit
def test_active_position_manager_confirms_pending_stop_before_reporting_success():
    """The broker must expose the requested position-closing stop after placement."""
    from infrastructure.risk.active_position_manager import ActivePositionManager

    class ConfirmingBroker:
        def __init__(self):
            self.pending = []

        def _place_conditional_order(self, **kwargs):
            self.pending = [{
                "type": kwargs["order_type"],
                "side": kwargs["side"],
                "positionSide": kwargs["position_side"],
                "stopPrice": kwargs["stop_price"],
            }]
            return {"success": True, "order_id": "replacement-stop"}

        def get_pending_orders(self, symbol):
            return self.pending

    mgr = ActivePositionManager()
    assert mgr._sync_sl_to_exchange(ConfirmingBroker(), "AVAXUSDT", False, 2.0, 7.41) is True


@pytest.mark.unit
def test_active_position_manager_retries_when_accepted_stop_is_not_visible():
    """An accepted response alone must not mark a stop as synced."""
    from infrastructure.risk.active_position_manager import ActivePositionManager

    class InvisibleStopBroker:
        def _place_conditional_order(self, **kwargs):
            return {"success": True, "order_id": "unverified-stop"}

        def get_pending_orders(self, symbol):
            return []

    mgr = ActivePositionManager()
    assert mgr._sync_sl_to_exchange(InvisibleStopBroker(), "ZECUSDT", True, 1.0, 800.0) is False


@pytest.mark.unit
def test_auto_detection_marks_running_before_starting_protection_threads():
    """A background protection loop must not observe a false running flag at startup."""
    from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator
    from unittest.mock import MagicMock

    orchestrator = object.__new__(AutoDetectionOrchestrator)
    orchestrator.logger = MagicMock()
    orchestrator.is_running = False
    observed = []
    orchestrator._start_background_services = lambda: observed.append(orchestrator.is_running)

    orchestrator.initialize_system()

    assert observed == [True]
    assert orchestrator.is_running is True


@pytest.mark.unit
def test_active_position_loop_continues_to_bingx_after_another_broker_fails(monkeypatch):
    """A failed non-primary broker must not prevent VST stop management."""
    from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator
    from infrastructure.risk import active_position_manager as manager_module
    from unittest.mock import MagicMock

    class FailingBroker:
        name = "binance"

        @staticmethod
        def get_all_positions():
            raise RuntimeError("unavailable")

    class BingxBroker:
        name = "bingx"

        @staticmethod
        def get_all_positions():
            return [{"symbol": "ZEC-USDT", "markPrice": 815.58}]

    bad_broker = FailingBroker()
    bingx_broker = BingxBroker()

    manager = MagicMock()
    manager.normalize_symbol.side_effect = lambda symbol: str(symbol).replace("-", "")
    manager.evaluate_open_positions.return_value = []
    monkeypatch.setattr(manager_module, "active_position_manager", manager)

    orchestrator = object.__new__(AutoDetectionOrchestrator)
    orchestrator.logger = MagicMock()
    orchestrator.execution_service = MagicMock()
    orchestrator.execution_service.broker.brokers = {"binance": bad_broker, "bingx": bingx_broker}
    orchestrator.market_data_repo = None
    orchestrator.is_running = True
    monkeypatch.setattr("infrastructure.orchestrators.auto_detection_orchestrator.time.sleep",
                        lambda _: setattr(orchestrator, "is_running", False))

    orchestrator._active_position_management_loop()

    manager.evaluate_open_positions.assert_called_once_with(
        bingx_broker, current_prices={"ZECUSDT": 815.58}
    )


@pytest.mark.unit
def test_active_position_loop_prioritizes_the_configured_primary_broker(monkeypatch):
    """BingX VST protection runs before ancillary exchange adapters."""
    from infrastructure.orchestrators.auto_detection_orchestrator import AutoDetectionOrchestrator
    from unittest.mock import MagicMock

    binance_broker = object()
    bingx_broker = object()

    class BrokerRoot:
        primary_broker = "bingx"
        brokers = {"binance": binance_broker, "bingx": bingx_broker}

    orchestrator = object.__new__(AutoDetectionOrchestrator)
    orchestrator.logger = MagicMock()
    orchestrator.execution_service = type("ExecutionService", (), {"broker": BrokerRoot()})()
    orchestrator.is_running = True
    visited = []

    def manage(broker, manager):
        visited.append(broker)

    orchestrator._manage_active_positions_for_broker = manage
    monkeypatch.setattr("infrastructure.orchestrators.auto_detection_orchestrator.time.sleep",
                        lambda _: setattr(orchestrator, "is_running", False))

    orchestrator._active_position_management_loop()

    assert visited == [bingx_broker, binance_broker]
