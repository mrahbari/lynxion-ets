"""E14: real OBI/CVD confirmation — snapshot math, shadow (never blocks) and enforce (fail-closed) modes."""
import time
from types import SimpleNamespace

import pytest

from infrastructure.execution import orderflow_snapshot as ofs
from infrastructure.strategies.decision_pipeline import DecisionPipeline


@pytest.fixture(autouse=True)
def _clean():
    ofs.clear()
    yield
    ofs.clear()


def _args(direction="BUY"):
    return SimpleNamespace(direction=direction), SimpleNamespace(symbol="BTC-USDT")


def test_book_imbalance_and_trade_delta():
    assert ofs.book_imbalance([("1", "3")], [("2", "1")]) == pytest.approx(0.5)
    assert ofs.book_imbalance([], []) is None
    now = 1_000_000_000
    trades = [{"time": now - 10_000, "isBuyerMaker": False, "quoteQty": "100"},   # aggressive buy
              {"time": now - 20_000, "isBuyerMaker": True, "quoteQty": "30"},     # aggressive sell
              {"time": now - 400_000, "isBuyerMaker": True, "quoteQty": "999"}]   # outside 5 min
    assert ofs.trade_delta(trades, now_ms=now) == pytest.approx(70)
    assert ofs.trade_delta([], now_ms=now) is None


def test_snapshot_staleness_and_symbol_normalisation():
    ofs.record("BTC-USDT", 0.2, 50.0, ts=time.time() - 500)
    assert ofs.get("BTCUSDT", max_age_s=180) is None
    ofs.record("BTCUSDT", 0.2, 50.0)
    assert ofs.get("BTC-USDT")["obi"] == pytest.approx(0.2)


def test_shadow_never_blocks(monkeypatch):
    monkeypatch.setenv("ORDERFLOW_CONFIRMATION_MODE", "shadow")
    p = DecisionPipeline()
    setup, sig = _args("BUY")
    assert p._orderflow_gate(setup, sig, "s") is True          # no data
    ofs.record("BTCUSDT", -0.5, -100.0)                          # contradicts BUY
    assert p._orderflow_gate(setup, sig, "s") is True


def test_enforce_is_fail_closed(monkeypatch):
    monkeypatch.setenv("ORDERFLOW_CONFIRMATION_MODE", "enforce")
    p = DecisionPipeline()
    setup, sig = _args("BUY")
    assert p._orderflow_gate(setup, sig, "s") is False         # missing data -> no entry
    ofs.record("BTCUSDT", -0.5, -100.0)
    assert p._orderflow_gate(setup, sig, "s") is False         # flow against the trade
    ofs.record("BTCUSDT", 0.3, 100.0)
    assert p._orderflow_gate(setup, sig, "s") is True
    sell, _ = _args("SELL")
    assert p._orderflow_gate(sell, sig, "s") is False


def test_off_skips(monkeypatch):
    monkeypatch.setenv("ORDERFLOW_CONFIRMATION_MODE", "off")
    setup, sig = _args("BUY")
    assert DecisionPipeline()._orderflow_gate(setup, sig, "s") is True
