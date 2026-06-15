"""E4.T4 — unit tests for infrastructure/tracking/tracking_adapter.py.

ConsolidatedTrackingAdapter unifies three trackers behind three ports. It is a
pure delegator, so it is exercised with three recording fakes (injected via the
constructor) — no SQLite/JSON/forensic I/O. Pins that every port method forwards
its arguments unchanged and returns the underlying value unchanged (the E3.T5
"persistence format / tracked values preserved byte-for-byte" guarantee at the seam).
"""

from datetime import datetime

import pytest

from infrastructure.tracking.tracking_adapter import ConsolidatedTrackingAdapter


class _Recorder:
    """Records (method, args, kwargs) and returns a per-method canned value."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return f"ret::{name}"
        return _method


@pytest.fixture
def adapter_and_fakes():
    trades, results, shadow = _Recorder(), _Recorder(), _Recorder()
    adapter = ConsolidatedTrackingAdapter(
        trade_tracker=trades, results_tracker=results, shadow_kpi_monitor=shadow
    )
    return adapter, trades, results, shadow


@pytest.mark.unit
def test_trade_tracking_delegation(adapter_and_fakes):
    adapter, trades, _, _ = adapter_and_fakes
    ts = datetime(2026, 1, 1)
    assert adapter.register_trade("t1", "BTCUSDT", "BUY", 100.0, 1.0, 90.0, 110.0, ts) == "ret::register_trade"
    assert adapter.close_trade("t1", 105.0, "tp") == "ret::close_trade"
    assert trades.calls[0] == ("register_trade", ("t1", "BTCUSDT", "BUY", 100.0, 1.0, 90.0, 110.0, ts), {})
    assert trades.calls[1] == ("close_trade", ("t1", 105.0, "tp", None), {})


@pytest.mark.unit
def test_results_tracking_delegation(adapter_and_fakes):
    adapter, _, results, _ = adapter_and_fakes
    assert adapter.save_hyperopt_result("s", "BTCUSDT", {"p": 1}, 1.5, 100) == "ret::save_hyperopt_result"
    assert adapter.save_backtest_result("s", "BTCUSDT", {"p": 1}, 0.2, 1.1, 0.1, 0.6, 50, 1.3) == "ret::save_backtest_result"
    assert adapter.get_hyperopt_results("s") == "ret::get_hyperopt_results"
    assert adapter.get_backtest_results("s") == "ret::get_backtest_results"
    assert adapter.get_best_parameters("s", "BTCUSDT") == "ret::get_best_parameters"
    forwarded = {c[0] for c in results.calls}
    assert forwarded == {
        "save_hyperopt_result", "save_backtest_result",
        "get_hyperopt_results", "get_backtest_results", "get_best_parameters",
    }
    # positional pass-through preserved on a representative call
    assert results.calls[0] == ("save_hyperopt_result", ("s", "BTCUSDT", {"p": 1}, 1.5, 100, None, None, None), {})


@pytest.mark.unit
def test_shadow_kpi_delegation(adapter_and_fakes):
    adapter, _, _, shadow = adapter_and_fakes
    assert adapter.calculate_kpis({"a": 1}, {"a": 0}) == "ret::calculate_kpis"
    assert adapter.check_alerts({"k": 1}) == "ret::check_alerts"
    assert adapter.log_kpis({"k": 1}) == "ret::log_kpis"
    assert adapter.log_alerts([{"x": 1}]) == "ret::log_alerts"
    assert adapter.generate_dashboard_report() == "ret::generate_dashboard_report"
    assert {c[0] for c in shadow.calls} == {
        "calculate_kpis", "check_alerts", "log_kpis", "log_alerts", "generate_dashboard_report",
    }


@pytest.mark.unit
def test_trackers_are_independent(adapter_and_fakes):
    adapter, trades, results, shadow = adapter_and_fakes
    adapter.close_trade("t1", 1.0, "sl")
    # a trade-port call must not touch the results/shadow collaborators
    assert results.calls == [] and shadow.calls == []
