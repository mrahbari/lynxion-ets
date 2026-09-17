import pytest

from infrastructure.data.configurable_historical_data_provider import (
    ConfigurableHistoricalDataProvider,
)
from infrastructure.data.historical_market_contract import MarketType


def provider_with_sources(*sources):
    provider = ConfigurableHistoricalDataProvider.__new__(ConfigurableHistoricalDataProvider)
    provider.brokers = {source: object() for source in sources}
    provider.logger = type("Logger", (), {"warning": lambda *args: None})()
    return provider


def test_binance_perpetual_route_uses_only_fapi_endpoint():
    provider = provider_with_sources("binance")
    calls = []
    provider._fetch_binance_historical = lambda symbol, period, timeframe, endpoint: calls.append(
        (symbol, period, timeframe, endpoint)
    ) or []

    provider._fetch_from_source(
        "binance", "BTCUSDT", "1d", "1m", MarketType.PERPETUAL
    )

    assert calls == [
        ("BTCUSDT", "1d", "1m", "https://fapi.binance.com/fapi/v1/klines")
    ]


def test_unverified_perpetual_source_does_not_fall_back_to_binance_spot():
    provider = provider_with_sources("bingx")

    with pytest.raises(ValueError, match="unsupported historical market mapping"):
        provider._fetch_from_source(
            "bingx", "BTCUSDT", "1d", "1m", MarketType.PERPETUAL
        )


def test_market_type_is_required_at_provider_boundary():
    with pytest.raises(TypeError, match="market_type"):
        ConfigurableHistoricalDataProvider.get_historical_data(
            provider_with_sources("binance"), "BTCUSDT", "1d", "1m"
        )
