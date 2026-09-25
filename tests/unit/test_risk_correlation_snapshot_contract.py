"""One immutable correlation publication is pinned per dynamic sizing call."""

import threading
from types import SimpleNamespace

import pytest

from application.risk_management.enterprise_risk_manager import EnterpriseRiskManager
from infrastructure.risk.risk_engine_adapter import ConsolidatedRiskEngineAdapter


class DeferredThread:
    def __init__(self, target, daemon):
        self.target = target
        self.daemon = daemon

    def start(self):
        pass


@pytest.fixture
def manager(monkeypatch):
    monkeypatch.setattr(threading, "Thread", DeferredThread)
    return EnterpriseRiskManager()


def _inputs():
    intent = SimpleNamespace(
        symbol=SimpleNamespace(value="BTCUSDT"),
        risk_parameters={"limit_price": 100.0, "stop_loss": 90.0},
        fused_signal=None,
        intent_confidence=SimpleNamespace(value=1.0),
    )
    portfolio = SimpleNamespace(
        total_value=SimpleNamespace(amount=10000.0),
        positions=[SimpleNamespace(symbol=SimpleNamespace(value="ETHUSDT"))],
    )
    return intent, portfolio


def _record_correlated_prices(manager):
    for btc, eth in zip([100, 101, 102, 103, 104], [200, 202, 204, 206, 208]):
        manager.record_price("BTCUSDT", btc)
        manager.record_price("ETHUSDT", eth)


def test_publication_is_deeply_immutable_and_versioned(manager):
    old = manager.get_correlation_snapshot()
    assert old.version == 0
    _record_correlated_prices(manager)
    manager.recalculate_correlations()
    new = manager.get_correlation_snapshot()
    assert new.version == 1
    assert old.matrix == {}
    assert new.matrix["BTCUSDT"]["ETHUSDT"] == pytest.approx(1.0)
    with pytest.raises(TypeError):
        new.matrix["BTCUSDT"] = {}
    with pytest.raises(TypeError):
        new.matrix["BTCUSDT"]["ETHUSDT"] = 0.0


def test_inflight_refresh_does_not_change_pinned_sizing(manager, monkeypatch):
    _record_correlated_prices(manager)
    intent, portfolio = _inputs()
    adapter = ConsolidatedRiskEngineAdapter(manager)
    original = manager.calculate_drawdown_factor

    def publish_between_pin_and_penalty():
        manager.recalculate_correlations()
        return original()

    monkeypatch.setattr(manager, "calculate_drawdown_factor", publish_between_pin_and_penalty)
    first_size = adapter.calculate_dynamic_size(intent, portfolio)
    assert first_size == pytest.approx(10.0)
    assert manager.get_correlation_snapshot().version == 1

    monkeypatch.setattr(manager, "calculate_drawdown_factor", original)
    second_size = adapter.calculate_dynamic_size(intent, portfolio)
    assert second_size == pytest.approx(10.0 / 1.2)
    assert adapter.calculate_dynamic_size(intent, portfolio) == pytest.approx(second_size)


def test_scopes_do_not_share_snapshots(manager, monkeypatch):
    second = EnterpriseRiskManager()
    _record_correlated_prices(manager)
    manager.recalculate_correlations()
    assert manager.get_correlation_snapshot().version == 1
    assert second.get_correlation_snapshot().version == 0
    assert second.correlation_matrix == {}
