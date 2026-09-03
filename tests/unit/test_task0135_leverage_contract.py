"""Contract and hydration regressions for TASK-0135."""

from decimal import Decimal
from types import SimpleNamespace
import logging


def _adapter_with_positions(rows):
    from infrastructure.brokers.adapters.bingx_adapter import BingXBrokerAdapter

    adapter = object.__new__(BingXBrokerAdapter)
    adapter.connected = True
    adapter.logger = SimpleNamespace(warning=lambda *args, **kwargs: None)
    adapter._broker = SimpleNamespace(get_open_positions=lambda: rows)
    return adapter


def _position_row(symbol="BTC-USDT", leverage="5", isolated=True):
    return {
        "symbol": symbol,
        "positionAmt": "0.01",
        "avgPrice": "100",
        "markPrice": "101",
        "unrealisedPnl": "0.01",
        "positionSide": "LONG",
        "leverage": leverage,
        "isolated": isolated,
        "time": "1788450000000",
    }


def test_hydration_retains_authoritative_leverage_and_margin_mode():
    position = _adapter_with_positions([_position_row()]).get_all_positions()[0]

    assert position.leverage == Decimal("5")
    assert position.isolated is True


def test_malformed_leverage_stays_untrusted_without_breaking_reconciliation():
    rows = [
        _position_row("BTC-USDT", leverage="NaN", isolated="true"),
        _position_row("ETH-USDT", leverage="5", isolated=True),
    ]

    positions = _adapter_with_positions(rows).get_all_positions()

    assert len(positions) == 2
    assert positions[0].leverage is None
    assert positions[0].isolated is None
    assert positions[1].leverage == Decimal("5")
    assert positions[1].isolated is True


def test_non_derivatives_contracts_remain_backward_compatible():
    from domain.entities import ExecutionIntent, Order, OrderSide, Position, PositionSide
    from domain.value_objects import Money, Percentage, Symbol
    from datetime import datetime

    intent = ExecutionIntent(
        symbol=Symbol("BTCUSDT"),
        strategy_name="compat",
        side=OrderSide.BUY,
        intent_confidence=Percentage(Decimal("0.5")),
        risk_parameters={},
        timestamp=datetime.now(),
    )
    order = Order(symbol=Symbol("BTCUSDT"), side=OrderSide.BUY, quantity=Decimal("1"))
    position = Position(
        symbol=Symbol("BTCUSDT"),
        side=PositionSide.LONG,
        quantity=Decimal("1"),
        entry_price=Money(Decimal("100"), "USDT"),
        timestamp=datetime.now(),
    )

    assert intent.requested_leverage is None
    assert order.requested_leverage is None
    assert position.leverage is None and position.isolated is None


def _entry_order(leverage="5"):
    from domain.entities import Order, OrderSide, PositionSide
    from domain.value_objects import Money, Symbol

    return Order(
        symbol=Symbol("NEWUSDT"),
        side=OrderSide.BUY,
        position_side=PositionSide.LONG,
        quantity=Decimal("0.1"),
        price=Money(Decimal("100"), "USDT"),
        stop_loss_price=Money(Decimal("98"), "USDT"),
        requested_leverage=Decimal(leverage),
    )


def _admission_broker(monkeypatch, *, exchange="5", margin="ISOLATED", positions=None,
                      configured=5, ceiling=5, fail_endpoint=None, leverage_data=None,
                      readback_time=None):
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    broker = object.__new__(_BingXBroker)
    broker.logger = logging.getLogger("task0135")
    calls = []

    def request(method, endpoint, **kwargs):
        calls.append((method, endpoint, kwargs.get("params")))
        if endpoint == fail_endpoint:
            return {"code": 1, "data": None}
        if endpoint.endswith("/user/positions"):
            return {"code": 0, "data": positions or []}
        if endpoint.endswith("/marginType") and method == "GET":
            return {"code": 0, "data": {"marginType": margin}, "timestamp": readback_time}
        if endpoint.endswith("/leverage") and method == "GET":
            return {
                "code": 0,
                "data": leverage_data if leverage_data is not None else {
                    "longLeverage": exchange, "shortLeverage": exchange,
                },
                "timestamp": readback_time,
            }
        return {"code": 0, "data": {}}

    monkeypatch.setattr(broker, "_make_request", request)
    monkeypatch.setattr(
        "infrastructure.risk.risk_enforcement.build_vst_risk_enforcement",
        lambda: SimpleNamespace(enforce=lambda order: (True, "approved")),
    )
    monkeypatch.setattr(
        "bootstrap.settings.loaders.load_settings",
        lambda: SimpleNamespace(
            safety=SimpleNamespace(max_open_positions=5),
            risk=SimpleNamespace(max_leverage=configured, max_leverage_limit=ceiling),
        ),
    )
    return broker, calls


def test_exact_configured_and_exchange_leverage_agreement_permits_boundary(monkeypatch):
    broker, calls = _admission_broker(monkeypatch)

    allowed, reason = broker._assert_entry_admission(_entry_order())

    assert allowed is True
    assert "authoritative leverage" in reason
    assert [call[:2] for call in calls[-4:]] == [
        ("POST", "/openApi/swap/v2/trade/marginType"),
        ("POST", "/openApi/swap/v2/trade/leverage"),
        ("GET", "/openApi/swap/v2/trade/marginType"),
        ("GET", "/openApi/swap/v2/trade/leverage"),
    ]


def test_exchange_leverage_mismatch_rejects(monkeypatch):
    broker, _ = _admission_broker(monkeypatch, exchange="10")
    allowed, reason = broker._assert_entry_admission(_entry_order())
    assert allowed is False and "mismatch" in reason


def test_missing_leverage_readback_rejects(monkeypatch):
    broker, _ = _admission_broker(monkeypatch, leverage_data={})
    allowed, reason = broker._assert_entry_admission(_entry_order())
    assert allowed is False and "malformed" in reason


def test_stale_leverage_readback_rejects(monkeypatch):
    broker, _ = _admission_broker(monkeypatch, readback_time=1)
    allowed, reason = broker._assert_entry_admission(_entry_order())
    assert allowed is False and "stale" in reason


def test_cross_margin_readback_rejects(monkeypatch):
    broker, _ = _admission_broker(monkeypatch, margin="CROSSED")
    allowed, reason = broker._assert_entry_admission(_entry_order())
    assert allowed is False and "cross-margin" in reason


def test_conflicting_configured_ceilings_reject(monkeypatch):
    broker, calls = _admission_broker(monkeypatch, configured=5, ceiling=10)
    allowed, reason = broker._assert_entry_admission(_entry_order())
    assert allowed is False and "conflicting leverage ceilings" in reason
    assert calls == []


def test_existing_excessive_leverage_blocks_new_symbol(monkeypatch):
    existing = _position_row("BTC-USDT", leverage="10")
    broker, calls = _admission_broker(monkeypatch, positions=[existing])
    allowed, reason = broker._assert_entry_admission(_entry_order())
    assert allowed is False and "existing position leverage" in reason
    assert not any(method == "POST" for method, _, _ in calls)


def test_broker_write_error_rejects(monkeypatch):
    endpoint = "/openApi/swap/v2/trade/leverage"
    broker, _ = _admission_broker(monkeypatch, fail_endpoint=endpoint)
    allowed, reason = broker._assert_entry_admission(_entry_order())
    assert allowed is False and "broker rejected" in reason


def test_rejection_never_reaches_order_execution(monkeypatch):
    broker, _ = _admission_broker(monkeypatch, exchange="10")
    reached = []
    monkeypatch.setattr(
        broker,
        "_execute_order_after_admission",
        lambda order: reached.append(order) or {"success": True},
    )

    result = broker.execute_order(_entry_order())

    assert result["success"] is False
    assert reached == []


def _managed_position(leverage):
    from domain.entities import Position, PositionSide
    from domain.value_objects import Money, Symbol
    from datetime import datetime

    return Position(
        symbol=Symbol("BTCUSDT"),
        side=PositionSide.LONG,
        quantity=Decimal("1"),
        entry_price=Money(Decimal("100"), "USDT"),
        mark_price=102.0,
        timestamp=datetime.now(),
        leverage=leverage,
        isolated=True,
    )


def test_active_manager_uses_each_positions_authoritative_leverage(monkeypatch):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    manager = ActivePositionManager(be_trigger_roe=9.0, trail_trigger_roe=20.0)
    synced = []
    monkeypatch.setattr(
        manager,
        "_sync_sl_to_exchange",
        lambda broker, symbol, is_long, quantity, stop: synced.append(stop) or True,
    )
    broker = SimpleNamespace(get_all_positions=lambda: [_managed_position(Decimal("5"))])

    actions = manager.evaluate_open_positions(broker)

    assert synced
    assert actions[0]["type"] == "BREAKEVEN_ACTIVATED"
    assert actions[0]["roe_pct"] == 10.0


def test_active_manager_never_substitutes_leverage_when_hydration_is_unknown(monkeypatch):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    manager = ActivePositionManager(leverage_multiplier=10.0)
    synced = []
    monkeypatch.setattr(
        manager,
        "_sync_sl_to_exchange",
        lambda *args: synced.append(args) or True,
    )
    broker = SimpleNamespace(get_all_positions=lambda: [_managed_position(None)])

    actions = manager.evaluate_open_positions(broker)

    assert actions == []
    assert synced == []
    assert manager._positions_state == {}
