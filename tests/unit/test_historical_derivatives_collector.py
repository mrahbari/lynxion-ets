"""Unit tests for HistoricalDerivativesCollector."""

import pytest
import tempfile
import shutil
from decimal import Decimal
from datetime import datetime, timezone
import httpx

from domain.value_objects import Symbol, ExchangeTimestamp, Quantity, Money
from domain.entities.market_data import FundingRate, OpenInterest
from infrastructure.data.collector.historical_derivatives_collector import HistoricalDerivativesCollector


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


@pytest.mark.asyncio
async def test_fetch_funding_rates_success(temp_dir):
    mock_response = [
        {
            "symbol": "BTCUSDT",
            "fundingRate": "0.00010000",
            "fundingTime": 1700000000000,
            "nextFundingTime": 1700028800000,
        },
        {
            "symbol": "BTCUSDT",
            "fundingRate": "-0.00020000",
            "fundingTime": 1700028800000,
            "nextFundingTime": 1700057600000,
        },
        # Duplicate record test
        {
            "symbol": "BTCUSDT",
            "fundingRate": "0.00010000",
            "fundingTime": 1700000000000,
            "nextFundingTime": 1700028800000,
        },
    ]

    def mock_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_response)

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_transport))
    collector = HistoricalDerivativesCollector(
        http_client=async_client,
        storage_dir=temp_dir
    )

    symbol = Symbol("BTCUSDT")
    rates = await collector.fetch_funding_rates(symbol)

    assert len(rates) == 2  # Duplicate filtered out
    assert rates[0].timestamp.millis == 1700000000000
    assert rates[0].rate == Decimal("0.00010000")
    assert rates[1].timestamp.millis == 1700028800000
    assert rates[1].rate == Decimal("-0.00020000")

    # Test storage save and load
    save_path = collector.save_funding_rates(symbol, rates)
    assert save_path != ""

    loaded = collector.load_funding_rates(symbol, 2023, 11)
    assert len(loaded) == 2
    assert loaded[0].rate == Decimal("0.00010000")

    await collector.close()


@pytest.mark.asyncio
async def test_fetch_open_interest_success(temp_dir):
    mock_response = [
        {
            "symbol": "ETHUSDT",
            "sumOpenInterest": "125000.50",
            "sumOpenInterestValue": "250000000.00",
            "timestamp": 1700000000000,
        },
        {
            "symbol": "ETHUSDT",
            "sumOpenInterest": "126000.00",
            "sumOpenInterestValue": "252000000.00",
            "timestamp": 1700003600000,
        },
    ]

    def mock_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_response)

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_transport))
    collector = HistoricalDerivativesCollector(
        http_client=async_client,
        storage_dir=temp_dir
    )

    symbol = Symbol("ETHUSDT")
    oi_list = await collector.fetch_open_interest_history(symbol)

    assert len(oi_list) == 2
    assert oi_list[0].value.value == Decimal("125000.50")
    assert oi_list[0].value_quote.amount == Decimal("250000000.00")
    assert oi_list[0].value_quote.currency == "USDT"

    # Test storage save and load
    save_path = collector.save_open_interest(symbol, oi_list)
    assert save_path != ""

    loaded = collector.load_open_interest(symbol, 2023, 11)
    assert len(loaded) == 2
    assert loaded[0].value_quote.amount == Decimal("250000000.00")

    await collector.close()


@pytest.mark.asyncio
async def test_fetch_retry_on_rate_limit(temp_dir):
    calls = 0

    def mock_transport(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0.01"})
        return httpx.Response(200, json=[])

    async_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_transport))
    collector = HistoricalDerivativesCollector(
        http_client=async_client,
        storage_dir=temp_dir,
        backoff_factor=0.01
    )

    symbol = Symbol("BTCUSDT")
    rates = await collector.fetch_funding_rates(symbol)

    assert calls == 2
    assert rates == []

    await collector.close()
