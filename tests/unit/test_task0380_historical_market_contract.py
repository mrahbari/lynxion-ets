import pytest

from infrastructure.data.historical_market_contract import (
    HistoricalMarketRequest,
    MarketType,
    verified_candle_endpoint,
)


def test_spot_and_perpetual_cache_identities_are_isolated():
    spot = HistoricalMarketRequest("Binance", MarketType.SPOT, "btcusdt", "1m")
    perpetual = HistoricalMarketRequest("Binance", MarketType.PERPETUAL, "btcusdt", "1m")

    assert spot.cache_identity == ("binance", "spot", "BTCUSDT", "1m")
    assert perpetual.cache_identity == ("binance", "perpetual", "BTCUSDT", "1m")
    assert spot.cache_identity != perpetual.cache_identity


def test_binance_endpoint_mapping_never_crosses_market_type():
    spot = HistoricalMarketRequest("binance", MarketType.SPOT, "BTCUSDT", "1m")
    perpetual = HistoricalMarketRequest("binance", MarketType.PERPETUAL, "BTCUSDT", "1m")

    assert verified_candle_endpoint(spot) == "https://api.binance.com/api/v3/klines"
    assert verified_candle_endpoint(perpetual) == "https://fapi.binance.com/fapi/v1/klines"


def test_implicit_or_unverified_market_mapping_fails_closed():
    with pytest.raises(TypeError, match="explicit MarketType"):
        HistoricalMarketRequest("binance", "perpetual", "BTCUSDT", "1m")

    bingx = HistoricalMarketRequest("bingx", MarketType.PERPETUAL, "BTCUSDT", "1m")
    with pytest.raises(ValueError, match="unsupported historical market mapping"):
        verified_candle_endpoint(bingx)
