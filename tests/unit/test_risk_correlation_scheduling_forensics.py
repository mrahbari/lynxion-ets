"""Offline characterization of the current correlation scheduling contract."""

import threading

import pytest

from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager


class DeferredThread:
    created = []

    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon
        self.started = False
        self.created.append(self)

    def start(self):
        self.started = True


@pytest.fixture
def risk_manager(monkeypatch):
    DeferredThread.created.clear()
    monkeypatch.setattr(threading, "Thread", DeferredThread)
    manager = EnterpriseRiskManager()
    return manager


def test_worker_is_started_but_first_update_is_deferred(risk_manager):
    assert risk_manager.correlation_update_interval_sec == 10.0
    assert len(DeferredThread.created) == 1
    assert DeferredThread.created[0].started
    assert DeferredThread.created[0].daemon
    assert risk_manager.correlation_matrix == {}


def test_update_uses_current_price_prefix_and_empty_updates_are_idempotent(risk_manager):
    btc = [100, 101, 102, 103, 104]
    eth = [200, 202, 204, 206, 208]
    for b, e in zip(btc, eth):
        risk_manager.record_price("BTCUSDT", b)
        risk_manager.record_price("ETHUSDT", e)
    assert risk_manager.correlation_matrix == {}
    risk_manager.recalculate_correlations()
    first = {symbol: dict(row) for symbol, row in risk_manager.correlation_matrix.items()}
    assert first["BTCUSDT"]["ETHUSDT"] == pytest.approx(1.0)
    risk_manager.recalculate_correlations()
    assert risk_manager.correlation_matrix == first


def test_order_size_depends_on_whether_worker_precedes_sizing(risk_manager):
    for b, e in zip([100, 101, 102, 103, 104], [200, 202, 204, 206, 208]):
        risk_manager.record_price("BTCUSDT", b)
        risk_manager.record_price("ETHUSDT", e)

    before_penalty = risk_manager.calculate_correlation_penalty("BTCUSDT", ["ETHUSDT"])
    before_size = risk_manager.calculate_position_size(
        entry_price=100, stop_loss=90, portfolio_equity=10000,
        correlation_penalty=before_penalty,
    )
    risk_manager.recalculate_correlations()
    after_penalty = risk_manager.calculate_correlation_penalty("BTCUSDT", ["ETHUSDT"])
    after_size = risk_manager.calculate_position_size(
        entry_price=100, stop_loss=90, portfolio_equity=10000,
        correlation_penalty=after_penalty,
    )
    assert before_penalty == 1.0
    assert after_penalty == pytest.approx(1.2)
    assert before_size == pytest.approx(10.0)
    assert after_size == pytest.approx(10.0 / 1.2)
