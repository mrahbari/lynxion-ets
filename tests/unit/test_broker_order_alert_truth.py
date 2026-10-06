"""Order alerts must distinguish broker acceptance from a verified fill."""

from types import SimpleNamespace

from infrastructure.brokers.multi_broker_service import MultiBrokerExecutionService


def test_bingx_vst_alert_names_route_and_unverified_fill(monkeypatch):
    sent = []

    class FakeTelegram:
        def __init__(self, **kwargs):
            pass

        def send_notification(self, message, subject, level, parse_mode):
            sent.append((message, subject, level, parse_mode))
            return True

    monkeypatch.setattr(
        "infrastructure.services.risk_alerts.TelegramNotificationService", FakeTelegram
    )
    service = MultiBrokerExecutionService.__new__(MultiBrokerExecutionService)
    service._settings = SimpleNamespace(monitoring=SimpleNamespace(
        telegram_notifications_enabled=True, telegram_bot_token="test", telegram_chat_id="test"
    ))
    service.logger = SimpleNamespace(info=lambda *args: None, warning=lambda *args: None)
    order = SimpleNamespace(
        symbol=SimpleNamespace(value="DOGEUSDT"),
        side=SimpleNamespace(name="BUY"),
        quantity="240",
        price=SimpleNamespace(amount="0.08741"),
        strategy_name="VWAPReversal",
    )

    service._send_order_placed_notification(order, "OID-1", "BINGX", "testnet")

    assert len(sent) == 1
    message, subject, level, parse_mode = sent[0]
    assert "Order accepted by broker — fill not verified" in message
    assert "VST / TESTNET" in message
    assert "BINGX" in message
    assert "OID-1" in message
    assert "Order value (est.):</b> <code>20.98 USDT" in message
    assert "fill not verified" in message
    assert "accepted on BINGX VST / TESTNET" in subject
    assert (level, parse_mode) == ("info", "HTML")


def test_requested_notional_is_not_fabricated_without_reference_price():
    from shared.utils import format_requested_order_notional

    order = SimpleNamespace(quantity="240", price=None)
    assert format_requested_order_notional(order) == "N/A"


def test_single_broker_alert_shows_estimated_notional(monkeypatch):
    from infrastructure.services.broker_execution_service import BrokerExecutionService

    sent = []

    class FakeTelegram:
        def __init__(self, **kwargs):
            pass

        def send_notification(self, message, subject, level, parse_mode):
            sent.append(message)
            return True

    monkeypatch.setattr(
        "infrastructure.services.risk_alerts.TelegramNotificationService", FakeTelegram
    )
    service = BrokerExecutionService.__new__(BrokerExecutionService)
    service._settings = SimpleNamespace(monitoring=SimpleNamespace(
        telegram_notifications_enabled=True, telegram_bot_token="test", telegram_chat_id="test"
    ))
    service.logger = SimpleNamespace(info=lambda *args: None, warning=lambda *args: None)
    order = SimpleNamespace(
        symbol=SimpleNamespace(value="DOGEUSDT"),
        side=SimpleNamespace(name="BUY"),
        quantity="240",
        price=SimpleNamespace(amount="0.08741"),
        strategy_name="VWAPReversal",
    )

    service._send_order_placed_notification(order, "OID-2")

    assert len(sent) == 1
    assert "Order value (est.):</b> <code>20.98 USDT" in sent[0]
