"""A BingX account-read failure cannot masquerade as zero positions."""

import pytest

from infrastructure.brokers.adapters.bingx_adapter import _BingXBroker


def _broker_returning(response):
    broker = _BingXBroker.__new__(_BingXBroker)
    broker._make_request = lambda *args, **kwargs: response
    return broker


def test_valid_flat_account_is_an_empty_list():
    assert _broker_returning({"code": 0, "data": []}).get_open_positions() == []


def test_exchange_error_is_not_an_empty_position_snapshot():
    with pytest.raises(RuntimeError, match="code=100001"):
        _broker_returning({"code": 100001, "data": []}).get_open_positions()


def test_missing_position_list_is_not_an_empty_position_snapshot():
    with pytest.raises(RuntimeError, match="no position list"):
        _broker_returning({"code": 0}).get_open_positions()


def test_transport_error_propagates():
    broker = _BingXBroker.__new__(_BingXBroker)

    def failed_request(*args, **kwargs):
        raise TimeoutError("public transport timeout")

    broker._make_request = failed_request
    with pytest.raises(TimeoutError, match="transport timeout"):
        broker.get_open_positions()
