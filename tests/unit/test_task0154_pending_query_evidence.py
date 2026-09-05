from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker


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
