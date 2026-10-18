"""Offline regression for ambiguous BingX order POST responses."""

import logging
from types import SimpleNamespace

import pytest
import requests


@pytest.mark.parametrize("order_type", ["MARKET", "STOP_MARKET", "TAKE_PROFIT_MARKET"])
def test_order_post_timeout_is_not_blindly_retried(order_type):
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    attempts = []

    def lost_response(*_args, **_kwargs):
        attempts.append(1)
        raise requests.exceptions.Timeout("response lost")

    broker = object.__new__(_BingXBroker)
    broker.base_url = "https://example.invalid"
    broker.api_key = "isolated-test-key"
    broker.secret_key = "isolated-test-secret"
    broker.default_timeout = 1
    broker.logger = logging.getLogger("test_bingx_order_post_retry")
    broker.session = SimpleNamespace(post=lost_response)
    broker._rate_limit = lambda **_kwargs: 0.0

    with pytest.raises(requests.exceptions.Timeout):
        broker._make_request(
            "POST", "/openApi/swap/v2/trade/order",
            data={"symbol": "BTC-USDT", "type": order_type}, signed=True,
        )
    assert len(attempts) == 1


def test_non_order_post_retains_transient_retry():
    from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker

    attempts = []

    def transient(*_args, **_kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise requests.exceptions.Timeout("response lost")
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"code": 0})

    broker = object.__new__(_BingXBroker)
    broker.base_url = "https://example.invalid"
    broker.api_key = "isolated-test-key"
    broker.secret_key = "isolated-test-secret"
    broker.default_timeout = 1
    broker.logger = logging.getLogger("test_bingx_non_order_post_retry")
    broker.session = SimpleNamespace(post=transient)
    broker._rate_limit = lambda **_kwargs: 0.0

    result = broker._make_request(
        "POST", "/openApi/swap/v2/trade/leverage",
        data={"symbol": "BTC-USDT"}, signed=True,
    )
    assert result["code"] == 0
    assert len(attempts) == 2
