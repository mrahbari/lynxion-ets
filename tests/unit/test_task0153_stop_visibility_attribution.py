"""Disconnected source-semantics evidence for TASK-0153."""

from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker
from infrastructure.risk.active_position_manager import ActivePositionManager


def _broker():
    broker = _BingXBroker({"api_key": "test", "secret_key": "test", "testnet": True})
    broker._format_price = lambda symbol, value: str(value)
    broker._format_quantity = lambda symbol, value: str(value)
    return broker


def test_code_zero_without_order_identity_is_reported_as_success():
    broker = _broker()
    broker._make_request = lambda *args, **kwargs: {"code": 0, "data": {}}
    result = broker._place_conditional_order(
        "BTC-USDT", "SELL", "1", "99", "STOP_MARKET", "LONG"
    )
    assert result["success"] is True
    assert result["order_id"] is None


def test_pending_query_conflates_exchange_error_exception_and_empty_book():
    broker = _broker()
    broker._make_request = lambda *args, **kwargs: {"code": 100001, "msg": "query failed"}
    api_error = broker.get_pending_orders("BTC-USDT")

    def fail(*args, **kwargs):
        raise RuntimeError("transport failed")

    broker._make_request = fail
    transport_error = broker.get_pending_orders("BTC-USDT")
    broker._make_request = lambda *args, **kwargs: {"code": 0, "data": {"orders": []}}
    genuinely_empty = broker.get_pending_orders("BTC-USDT")
    assert api_error == transport_error == genuinely_empty == []


def test_visibility_match_does_not_require_placement_order_id(monkeypatch):
    class Broker:
        def get_pending_orders(self, symbol):
            return [{
                "type": "STOP_MARKET", "side": "SELL", "positionSide": "LONG",
                "stopPrice": "99", "orderId": None,
            }]

    monkeypatch.setattr("infrastructure.risk.active_position_manager.time.sleep", lambda _: None)
    evidence = ActivePositionManager._verify_pending_stop(
        Broker(), "BTC-USDT", "SELL", "LONG", 99.0
    )
    assert evidence == {
        "order_id": None,
        "visible_stop_price": 99.0,
        "observed_at_utc": evidence["observed_at_utc"],
    }
