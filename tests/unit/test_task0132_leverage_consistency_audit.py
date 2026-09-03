"""Read-only characterization of the verified TASK-0132 leverage boundary."""
from dataclasses import fields
from decimal import Decimal
from types import SimpleNamespace
import logging


def _order():
    from domain.entities import Order, OrderSide
    from domain.value_objects import Money, Symbol
    return Order(symbol=Symbol("NEWUSDT"),side=OrderSide.BUY,quantity=Decimal("0.1"),
                 price=Money(Decimal("100"),"USDT"),stop_loss_price=Money(Decimal("98"),"USDT"))


def test_order_and_position_contracts_carry_authoritative_leverage_fields():
    from domain.entities import ExecutionIntent, Order, Position
    assert "requested_leverage" in {f.name for f in fields(ExecutionIntent)}
    assert "requested_leverage" in {f.name for f in fields(Order)}
    assert {"leverage", "isolated"} <= {f.name for f in fields(Position)}


def test_bingx_admission_rejects_missing_requested_leverage(monkeypatch):
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker
    broker=object.__new__(_BingXBroker);broker.logger=logging.getLogger("task0132")
    monkeypatch.setattr(
        broker,"_make_request",lambda *a,**k:{"code":0,"data":[{
            "symbol":"BTC-USDT","positionAmt":"0.01","avgPrice":"100","markPrice":"100","leverage":"10"
        }]})
    monkeypatch.setattr(
        "infrastructure.risk.risk_enforcement.build_vst_risk_enforcement",
        lambda:SimpleNamespace(enforce=lambda order:(True,"approved")))
    monkeypatch.setattr(
        "bootstrap.settings.loaders.load_settings",
        lambda:SimpleNamespace(
            safety=SimpleNamespace(max_open_positions=5),
            risk=SimpleNamespace(max_leverage=5.0, max_leverage_limit=5.0),
        ))
    allowed,reason=broker._assert_entry_admission(_order())
    assert allowed is False and "leverage" in reason


def test_active_position_manager_has_no_production_leverage_default():
    from infrastructure.risk.active_position_manager import ActivePositionManager
    assert ActivePositionManager().leverage_multiplier is None
