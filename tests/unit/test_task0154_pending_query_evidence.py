from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker
from infrastructure.risk.active_position_manager import ActivePositionManager


def _broker(response=None, error=None):
    broker = _BingXBroker({"api_key": "test", "secret_key": "test", "testnet": True})

    def request(*args, **kwargs):
        if error is not None:
            raise error
        return response

    broker._make_request = request
    return broker


def test_success_empty_is_distinct_from_failures_and_preserves_legacy_list():
    broker = _broker({"code": 0, "data": {"orders": []}})
    assert broker.get_pending_orders_evidence("BTC-USDT") == {
        "status": "OK", "orders": [], "error": None,
    }
    assert broker.get_pending_orders("BTC-USDT") == []


def test_nonzero_exchange_response_is_explicit_but_legacy_stays_empty():
    broker = _broker({"code": 100001, "msg": "secret-capable exchange text"})
    assert broker.get_pending_orders_evidence("BTC-USDT") == {
        "status": "API_ERROR", "orders": [], "error": "exchange_code:100001",
    }
    assert broker.get_pending_orders("BTC-USDT") == []


def test_exception_records_only_type_and_never_exception_text():
    broker = _broker(error=RuntimeError("sensitive request detail"))
    assert broker.get_pending_orders_evidence("BTC-USDT") == {
        "status": "EXCEPTION", "orders": [], "error": "RuntimeError",
    }


def test_malformed_success_payload_is_not_success_empty():
    assert _broker({"code": 0, "data": {}}).get_pending_orders_evidence("BTC-USDT") == {
        "status": "MALFORMED", "orders": [], "error": "orders_not_list",
    }
    assert _broker(None).get_pending_orders_evidence("BTC-USDT") == {
        "status": "MALFORMED", "orders": [], "error": "response_not_object",
    }


def test_stop_response_preserves_exchange_order_identity(monkeypatch):
    class Broker:
        def _place_conditional_order(self, **kwargs):
            return {"success": True, "order_id": 12345}

        def get_pending_orders(self, symbol):
            return [{
                "type": "STOP_MARKET", "side": "SELL", "positionSide": "LONG",
                "stopPrice": "101", "orderId": 12345,
            }]

    events = []
    manager = ActivePositionManager(exit_observer=events.append, observer_run_id="run-1")
    monkeypatch.setattr("infrastructure.risk.active_position_manager.time.sleep", lambda _: None)
    context = {
        "evaluation_id": "eval-1", "position_key": "BTCUSDT:LONG:100",
        "symbol": "BTCUSDT", "is_long": True, "quantity": 1.0,
        "entry_price": 100.0, "current_price": 102.0, "exchange_leverage": 10.0,
        "roe_pct": 20.0, "peak_price": 102.0, "peak_roe_pct": 20.0,
        "state_before": {},
    }
    assert manager._sync_sl_to_exchange(
        Broker(), "BTCUSDT", True, 1.0, 101.0, observation_context=context,
    ) is True
    response = next(event for event in events if event["event_type"] == "STOP_REPLACE_RESPONDED")
    assert response["exchange_order_id"] == "12345"
