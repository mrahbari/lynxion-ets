"""Structured exchange-visibility evidence for TASK-0139."""


def test_pending_stop_verification_preserves_matching_exchange_evidence():
    from infrastructure.risk.active_position_manager import ActivePositionManager

    class Broker:
        def __init__(self):
            self.pending_calls = 0

        def get_pending_orders(self, symbol):
            self.pending_calls += 1
            return [
                {
                    "orderId": "wrong-side",
                    "type": "STOP_MARKET",
                    "side": "BUY",
                    "positionSide": "SHORT",
                    "stopPrice": "101.0",
                },
                {
                    "orderId": "visible-stop-7",
                    "type": "STOP_MARKET",
                    "side": "SELL",
                    "positionSide": "LONG",
                    "stopPrice": "101.0",
                },
            ]

    broker = Broker()
    evidence = ActivePositionManager._verify_pending_stop(
        broker, "BTC-USDT", "SELL", "LONG", 101.0
    )

    assert broker.pending_calls == 1
    assert evidence["order_id"] == "visible-stop-7"
    assert evidence["visible_stop_price"] == 101.0
    assert evidence["observed_at_utc"].endswith("+00:00")


def test_pending_stop_verification_exhaustion_preserves_existing_poll_count(monkeypatch):
    from infrastructure.risk.active_position_manager import ActivePositionManager

    class Broker:
        def __init__(self):
            self.pending_calls = 0

        def get_pending_orders(self, symbol):
            self.pending_calls += 1
            return []

    broker = Broker()
    sleeps = []
    monkeypatch.setattr(
        "infrastructure.risk.active_position_manager.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    evidence = ActivePositionManager._verify_pending_stop(
        broker, "BTC-USDT", "SELL", "LONG", 101.0
    )

    assert evidence is None
    assert broker.pending_calls == 3
    assert sleeps == [0.2, 0.2, 0.2]
