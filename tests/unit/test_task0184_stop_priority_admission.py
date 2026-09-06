import pytest

from infrastructure.brokers.adapters.bingx_adapter import (
    RateLimitAdmissionTimeout,
    _BingXBroker,
)


def _broker():
    broker = _BingXBroker({"api_key": "test", "secret_key": "test", "testnet": True})
    broker._format_price = lambda symbol, value: str(value)
    broker._format_quantity = lambda symbol, value: str(value)
    return broker


def test_rate_limit_timeout_is_explicit(monkeypatch):
    broker = _broker()
    monkeypatch.setattr(
        "infrastructure.brokers.adapters.bingx_adapter.global_rate_limiter.wait_for_tokens",
        lambda *args, **kwargs: False,
    )
    with pytest.raises(RateLimitAdmissionTimeout):
        broker._rate_limit(priority=True, timeout=0)


def test_stop_order_uses_bounded_priority_admission():
    broker = _broker()
    calls = []

    def request(*args, **kwargs):
        calls.append((args, kwargs))
        return {"code": 0, "data": {"order": {"orderId": "stop-1"}},
                "_client_rate_limit_wait_ms": 12.5}

    broker._make_request = request
    result = broker._place_conditional_order(
        "BTC-USDT", "SELL", "1", "99", "STOP_MARKET", "LONG"
    )

    assert calls[0][1]["request_priority"] is True
    assert calls[0][1]["rate_limit_timeout"] == 15.0
    assert result["rate_limit_wait_ms"] == 12.5


def test_stop_admission_timeout_never_reaches_http():
    broker = _broker()
    broker._make_request = lambda *args, **kwargs: (_ for _ in ()).throw(
        RateLimitAdmissionTimeout(15000.0)
    )

    result = broker._place_conditional_order(
        "BTC-USDT", "SELL", "1", "99", "STOP_MARKET", "LONG"
    )
    assert result == {
        "success": False,
        "error": "rate limit admission timeout",
        "rate_limit_wait_ms": 15000.0,
    }
