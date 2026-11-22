"""P0: a strategy's candle buffer must belong to the symbol being evaluated.

Live intents used to be priced from one never-refreshed buffer (the first symbol ever
loaded), so e.g. ETH entries carried OKB's entry/SL/TP levels.
"""
from types import SimpleNamespace

from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class _Probe(BaseStrategyAdapter):
    def generate_signal(self, symbol):
        return None

    def evaluate_fused_signal(self, fused_signal):
        return None


def _bars(px):
    return [{"close": px, "high": px, "low": px, "volume": 1.0}]


def _adapter():
    a = _Probe("Probe")
    calls = []
    a.bind_history_loader(lambda sym, cfg: (calls.append(sym.value), _bars(100.0 if sym.value == "AUSDT" else 5.0))[1])
    return a, calls


def test_buffer_reloads_for_a_different_symbol():
    a, calls = _adapter()
    a.ensure_data_buffer(SimpleNamespace(value="AUSDT"))
    assert a.data_buffer[-1]["close"] == 100.0
    a.ensure_data_buffer(SimpleNamespace(value="BUSDT"))
    assert a.data_buffer[-1]["close"] == 5.0
    assert calls == ["AUSDT", "BUSDT"]


def test_buffer_is_reused_for_same_symbol_until_stale(monkeypatch):
    a, calls = _adapter()
    a.ensure_data_buffer(SimpleNamespace(value="AUSDT"))
    a.ensure_data_buffer(SimpleNamespace(value="AUSDT"))
    assert calls == ["AUSDT"]
    monkeypatch.setenv("STRATEGY_BUFFER_REFRESH_SECONDS", "0")
    a.ensure_data_buffer(SimpleNamespace(value="AUSDT"))
    assert calls == ["AUSDT", "AUSDT"]


def test_failed_reload_leaves_empty_buffer_not_foreign_bars():
    a = _Probe("Probe")
    a.bind_history_loader(lambda sym, cfg: _bars(100.0) if sym.value == "AUSDT" else [])
    a.ensure_data_buffer(SimpleNamespace(value="AUSDT"))
    a.ensure_data_buffer(SimpleNamespace(value="BUSDT"))
    assert a.data_buffer == []


def test_feed_owned_buffer_is_untouched():
    a, calls = _adapter()
    a.update_with_market_data(_bars(42.0))
    a.ensure_data_buffer(SimpleNamespace(value="BUSDT"))
    assert a.data_buffer[-1]["close"] == 42.0 and calls == []
