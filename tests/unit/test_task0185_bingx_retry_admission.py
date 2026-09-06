import requests

from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker


class Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {"code": 0, "data": {}}


def test_every_physical_http_retry_reacquires_rate_capacity(monkeypatch):
    broker = _BingXBroker({"api_key": "test", "secret_key": "test", "testnet": True})
    admission_calls = []
    http_calls = []

    def admit(**kwargs):
        admission_calls.append(kwargs)
        return 7.5

    def post(*args, **kwargs):
        http_calls.append((args, kwargs))
        if len(http_calls) == 1:
            raise requests.exceptions.Timeout("transient")
        return Response()

    monkeypatch.setattr(broker, "_rate_limit", admit)
    monkeypatch.setattr(broker.session, "post", post)
    monkeypatch.setattr("shared.retry.time.sleep", lambda _: None)

    result = broker._make_request(
        "POST", "/test", params={"symbol": "BTC-USDT"}, signed=True,
        request_priority=True, rate_limit_timeout=15.0,
    )

    assert len(http_calls) == 2
    assert admission_calls == [
        {"priority": True, "timeout": 15.0},
        {"priority": True, "timeout": 15.0},
    ]
    assert result["_client_rate_limit_wait_ms"] == 15.0
