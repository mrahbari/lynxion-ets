from types import SimpleNamespace

from infrastructure.data.configurable_historical_data_provider import (
    ConfigurableHistoricalDataProvider,
)
from domain.value_objects import Symbol
from infrastructure.data.historical_market_contract import MarketType


NOW = 1_800_000_000


def rows(count, *, end=NOW - 60, step=60):
    start = end - (count - 1) * step
    return [{'timestamp': start + i * step} for i in range(count)]


def test_provider_initializes_market_scoped_failure_cache(monkeypatch):
    monkeypatch.setattr(ConfigurableHistoricalDataProvider, '_initialize_brokers', lambda self: None)
    settings = SimpleNamespace(
        data=SimpleNamespace(
            preferred_historical_data_source='binance',
            historical_data_fallback_sources=['binance'],
        )
    )

    provider = ConfigurableHistoricalDataProvider(settings, fallback_sources=['binance'])

    assert provider.failed_symbols_cache == {}
    assert provider.failed_symbols_cache_duration > 0


def test_api_page_cannot_masquerade_as_thirty_day_minute_history():
    assert not ConfigurableHistoricalDataProvider._has_acceptable_coverage(
        rows(1000), '30d', '1m', NOW
    )


def test_nearly_complete_fresh_window_passes():
    assert ConfigurableHistoricalDataProvider._has_acceptable_coverage(
        rows(1438), '1d', '1m', NOW
    )


def test_stale_or_duplicate_inflated_window_fails_closed():
    stale = rows(1440, end=NOW - 172800)
    duplicate = [{'timestamp': NOW - 60}] * 1440
    assert not ConfigurableHistoricalDataProvider._has_acceptable_coverage(stale, '1d', '1m', NOW)
    assert not ConfigurableHistoricalDataProvider._has_acceptable_coverage(duplicate, '1d', '1m', NOW)


def test_malformed_period_timeframe_or_timestamp_fails_closed():
    assert not ConfigurableHistoricalDataProvider._has_acceptable_coverage(rows(10), 'bad', '1m', NOW)
    assert not ConfigurableHistoricalDataProvider._has_acceptable_coverage(rows(10), '1d', 'bad', NOW)
    assert not ConfigurableHistoricalDataProvider._has_acceptable_coverage(
        [{'timestamp': 'not-a-time'}], '1d', '1m', NOW
    )


def test_incomplete_primary_is_not_cached_and_complete_fallback_is_used(monkeypatch):
    provider = ConfigurableHistoricalDataProvider.__new__(ConfigurableHistoricalDataProvider)
    provider.preferred_data_source = 'primary'
    provider.fallback_sources = ['fallback']
    provider.failed_symbols_cache = {}
    provider.failed_symbols_cache_duration = 60
    provider.unsupported_exchange_symbols = {}
    provider.unsupported_exchange_ttl = 60
    provider.usage_stats = {
        'primary': {'requests': 0, 'errors': 0},
        'fallback': {'requests': 0, 'errors': 0},
    }
    provider.logger = type('Logger', (), {
        'info': lambda *args: None,
        'debug': lambda *args: None,
        'warning': lambda *args: None,
        'error': lambda *args: None,
    })()
    cached = []
    provider._fetch_from_source = lambda source, *_: (
        rows(1000) if source == 'primary' else rows(1438)
    )
    provider._cache_data_locally = lambda symbol, data: cached.append((symbol, data))
    provider._get_cached_data_fallback = lambda *_: []
    monkeypatch.setattr(
        'application.symbol_management.centralized_symbol_manager.is_symbol_approved',
        lambda _symbol: True,
    )
    monkeypatch.setattr('time.time', lambda: NOW)

    result = provider.get_historical_data(
        Symbol('BTCUSDT'), '1d', '1m', market_type=MarketType.PERPETUAL
    )

    assert len(result) == 1438
    assert cached == []


def test_failed_request_is_cached_by_market_and_symbol(monkeypatch):
    provider = ConfigurableHistoricalDataProvider.__new__(ConfigurableHistoricalDataProvider)
    provider.preferred_data_source = 'binance'
    provider.fallback_sources = []
    provider.failed_symbols_cache = {}
    provider.failed_symbols_cache_duration = 60
    provider.unsupported_exchange_symbols = {}
    provider.unsupported_exchange_ttl = 60
    provider.usage_stats = {'binance': {'requests': 0, 'errors': 0}}
    provider.logger = type('Logger', (), {
        'info': lambda *args: None,
        'debug': lambda *args: None,
        'warning': lambda *args: None,
        'error': lambda *args: None,
    })()
    provider._fetch_from_source = lambda *_: []
    provider._get_cached_data_fallback = lambda *_: []
    monkeypatch.setattr(
        'application.symbol_management.centralized_symbol_manager.is_symbol_approved',
        lambda _symbol: True,
    )
    monkeypatch.setattr('time.time', lambda: NOW)

    result = provider.get_historical_data(
        Symbol('BTCUSDT'), '30m', '1m', market_type=MarketType.PERPETUAL
    )

    assert result == []
    assert provider.failed_symbols_cache == {('perpetual', 'BTCUSDT'): NOW}
