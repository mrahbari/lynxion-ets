"""Broker activation boundaries for the multi-broker service."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
def test_phemex_is_not_initialized_when_disabled(monkeypatch):
    """Configured credentials must not bypass the enabled_brokers flag."""
    from infrastructure.brokers.multi_broker_service import MultiBrokerExecutionService

    settings = SimpleNamespace(
        broker=SimpleNamespace(
            binance_api_key="",
            binance_secret_key="",
            bingx_api_key="",
            bingx_secret_key="",
            bingx_passphrase="",
            mexc_api_key="",
            mexc_secret_key="",
            phemex_api_key="configured-key",
            phemex_secret_key="configured-secret",
            phemex_testnet=True,
            enabled_brokers=["bingx"],
        )
    )
    service = object.__new__(MultiBrokerExecutionService)
    service._settings = settings
    service.logger = MagicMock()
    service.brokers = {}
    phemex_adapter = MagicMock()
    monkeypatch.setattr(
        "infrastructure.brokers.multi_broker_service.PhemexBrokerAdapter",
        phemex_adapter,
    )

    service._initialize_brokers()

    phemex_adapter.assert_not_called()
    assert "phemex" not in service.brokers
