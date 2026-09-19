import math
from decimal import Decimal

from domain.entities import Order
from domain.value_objects import Money, Symbol
from infrastructure.brokers.multi_broker_service import MultiBrokerExecutionService
from shared.utils import sanitize_sltp_levels


class _Logger:
    def info(self, *_args, **_kwargs):
        pass


def test_nonfinite_sltp_falls_back_to_finite_long_defaults():
    stop, target = sanitize_sltp_levels(100.0, "BUY", float("nan"), float("inf"))

    assert math.isfinite(stop) and stop < 100.0
    assert math.isfinite(target) and target > 100.0


def test_nonfinite_entry_fails_closed():
    assert sanitize_sltp_levels(float("nan"), "SELL", 101.0, 99.0) == (0.0, 0.0)
    assert sanitize_sltp_levels(float("inf"), "BUY", 99.0, 101.0) == (0.0, 0.0)


def test_multi_broker_enhancement_never_preserves_nan_protection(monkeypatch):
    monkeypatch.setattr(
        "infrastructure.services.symbol_validator.symbol_validator.is_symbol_approved",
        lambda _symbol: True,
    )
    service = object.__new__(MultiBrokerExecutionService)
    service.logger = _Logger()
    order = Order(
        symbol=Symbol("BTCUSDT"),
        side="BUY",
        quantity=Decimal("0.001"),
        price=Money(Decimal("60000"), "USDT"),
        stop_loss_price=Money(Decimal("NaN"), "USDT"),
        take_profit_price=Money(Decimal("Infinity"), "USDT"),
    )

    enhanced = service._enhance_order_with_risk_parameters(order)

    stop = float(enhanced.stop_loss_price.amount)
    target = float(enhanced.take_profit_price.amount)
    assert math.isfinite(stop) and stop < 60000.0
    assert math.isfinite(target) and target > 60000.0
