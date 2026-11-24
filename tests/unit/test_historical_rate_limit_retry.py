"""Platform review 2026-11-24: venue throttling must not starve strategies of data for 5 minutes."""
import pytest

import application.symbol_management.centralized_symbol_manager as csm
from domain.value_objects import Symbol
from infrastructure.data.configurable_historical_data_provider import ConfigurableHistoricalDataProvider as P
from infrastructure.data import configurable_historical_data_provider as mod


@pytest.fixture
def provider(monkeypatch):
    p = P.__new__(P)
    p.logger = type("L", (), {k: staticmethod(lambda *a, **kw: None) for k in ("debug", "info", "warning", "error")})()
    p.preferred_data_source, p.fallback_sources = "bingx", []
    p.usage_stats, p.unsupported_exchange_symbols, p.unsupported_exchange_ttl = {}, {}, 86400
    p.failed_symbols_cache, p.failed_symbols_cache_duration = {}, 300
    p._has_acceptable_coverage = lambda *a, **k: True
    p._get_cached_data_fallback = lambda *a, **k: []
    monkeypatch.setattr(csm, "is_symbol_approved", lambda s: True)
    monkeypatch.setattr(P, "RATE_LIMIT_RETRY_S", 0.0)
    return p


def test_one_retry_after_rate_limit(provider):
    calls = []

    def fetch(*a):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("BingX API error: 请稍后重试")
        return [{"close": 1.0}]
    provider._fetch_from_source = fetch
    assert provider.get_historical_data(Symbol("OKBUSDT"), "10d", "1h", market_type=mod.MarketType.PERPETUAL)
    assert len(calls) == 2


def test_rate_limited_failure_is_held_briefly_and_per_timeframe(provider, monkeypatch):
    def fetch(*a):
        raise RuntimeError("BingX API error: 请稍后重试")
    provider._fetch_from_source = fetch
    mt = mod.MarketType.PERPETUAL
    assert provider.get_historical_data(Symbol("OKBUSDT"), "12h", "5m", market_type=mt) == []
    key = (mt.value, "OKBUSDT", "5m")
    assert key in provider.failed_symbols_cache and key in provider._transient_failures
    provider._fetch_from_source = lambda *a: [{"close": 1.0}]
    assert provider.get_historical_data(Symbol("OKBUSDT"), "10d", "1h", market_type=mt)   # other TF not blocked
    provider.failed_symbols_cache[key] -= 31
    assert provider.get_historical_data(Symbol("OKBUSDT"), "12h", "5m", market_type=mt)   # 30 s hold, not 300 s
