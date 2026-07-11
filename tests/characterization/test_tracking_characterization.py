"""Characterization: consolidated tracking system (E3.T5).

Pins that the single ``ConsolidatedTrackingAdapter`` produces tracked-metric
values and persistence output IDENTICAL to the three legacy trackers it
consolidates (``TradeTracker``, ``ResultsTracker``, ``ShadowKPIMonitor``), so the
E3.T5 consolidation cannot change tracking behavior or persistence format.

A fixture run is driven through both the legacy tracker and the adapter; their
outputs are compared directly. All storage is redirected to ``tmp_path`` so no
real DB/JSON files are touched.
"""

import pytest

pytest.importorskip("numpy")
pytest.importorskip("pandas")

from datetime import datetime

from infrastructure.tracking.tracking_adapter import ConsolidatedTrackingAdapter


# --- Trade tracking: PnL/ROI summary must match the legacy TradeTracker -------

def _trade_fixture():
    return dict(
        trade_id="T1", symbol="BTCUSDT", side="BUY", price=100.0, quantity=2.0,
        sl=95.0, tp=110.0, timestamp=datetime(2023, 1, 1, 0, 0, 0),
    )


@pytest.mark.unit
def test_trade_close_summary_matches_legacy():
    from infrastructure.tracking.trade_tracker import TradeTracker

    exit_ts = datetime(2023, 1, 1, 1, 0, 0)

    legacy = TradeTracker()
    legacy.register_trade(**_trade_fixture())
    legacy_summary = legacy.close_trade("T1", exit_price=105.0, exit_reason="tp",
                                        exit_timestamp=exit_ts)

    adapter = ConsolidatedTrackingAdapter(trade_tracker=TradeTracker())
    adapter.register_trade(**_trade_fixture())
    adapter_summary = adapter.close_trade("T1", exit_price=105.0, exit_reason="tp",
                                          exit_timestamp=exit_ts)

    assert adapter_summary == legacy_summary
    # Pin the exact tracked values for the fixture (BUY: (105-100)*2 == 10 PnL).
    assert adapter_summary == {
        "trade_id": "T1",
        "pnl": 10.0,
        "roi_pct": 0.05,
        "exit_reason": "tp",
        "holding_seconds": 3600,
    }


# --- Results tracking: persisted rows + best-parameters must match ------------

def _backtest_fixture(symbol="BTCUSDT"):
    return dict(
        strategy_name="strat", symbol=symbol, parameters={"a": 1},
        total_return=0.42, sharpe_ratio=1.5, max_drawdown=0.1, win_rate=0.6,
        total_trades=20, profit_factor=1.8,
    )


@pytest.mark.unit
def test_results_persistence_format_matches_legacy(tmp_path):
    from infrastructure.results_tracking.results_tracker import ResultsTracker

    def _row(tracker):
        tracker.save_backtest_result(**_backtest_fixture())
        rows = tracker.get_backtest_results(strategy_name="strat", symbol="BTCUSDT")
        assert len(rows) == 1
        row = rows[0]
        # Drop the autoincrement id / timestamp (run-dependent); pin the rest.
        row.pop("id", None)
        row.pop("timestamp", None)
        return row

    legacy = ResultsTracker(storage_dir=str(tmp_path / "legacy_store"),
                            db_path=str(tmp_path / "legacy.db"))
    adapter = ConsolidatedTrackingAdapter(
        results_tracker=ResultsTracker(storage_dir=str(tmp_path / "adapter_store"),
                                       db_path=str(tmp_path / "adapter.db"))
    )

    legacy_row = _row(legacy)
    adapter_row = _row(adapter)

    assert adapter_row == legacy_row
    assert adapter_row["total_return"] == 0.42
    assert adapter_row["sharpe_ratio"] == 1.5
    assert adapter_row["parameters"] == {"a": 1}


@pytest.mark.unit
def test_results_best_parameters_matches_legacy(tmp_path):
    from infrastructure.results_tracking.results_tracker import ResultsTracker

    adapter = ConsolidatedTrackingAdapter(
        results_tracker=ResultsTracker(storage_dir=str(tmp_path / "store"),
                                       db_path=str(tmp_path / "best.db"))
    )
    adapter.save_backtest_result(**_backtest_fixture())
    adapter.save_backtest_result(**{**_backtest_fixture(), "sharpe_ratio": 2.5})

    best = adapter.get_best_parameters("strat", "BTCUSDT", metric="sharpe_ratio")
    assert best is not None
    assert best["metric_value"] == 2.5


# --- Shadow KPI tracking: computed KPIs must match the legacy monitor ---------

CURRENT = {"total_signals": 110, "win_rate": 0.55, "avg_trade_pnl": 12.0,
           "total_trades": 90, "regime_classification_accuracy": 0.95}
BASELINE = {"total_signals": 100, "win_rate": 0.50, "avg_trade_pnl": 10.0,
            "total_trades": 100, "regime_classification_accuracy": 1.0}


@pytest.mark.unit
def test_shadow_kpis_match_legacy(tmp_path):
    from infrastructure.monitoring.shadow_kpi_monitor import ShadowKPIMonitor

    legacy = ShadowKPIMonitor(base_path=str(tmp_path / "legacy_shadow"))
    adapter = ConsolidatedTrackingAdapter(
        shadow_kpi_monitor=ShadowKPIMonitor(base_path=str(tmp_path / "adapter_shadow"))
    )

    legacy_kpis = legacy.calculate_kpis(CURRENT, BASELINE)
    adapter_kpis = adapter.calculate_kpis(CURRENT, BASELINE)

    # Compare metric values/thresholds/alerts (timestamp is run-dependent).
    assert adapter_kpis["metrics"] == legacy_kpis["metrics"]
    assert adapter_kpis["overall_kpi_score"] == legacy_kpis["overall_kpi_score"]
    # Pin a couple of exact tracked values.
    assert adapter_kpis["metrics"]["signal_deviation_vs_backtest"]["value"] == pytest.approx(0.10)
    assert adapter_kpis["metrics"]["win_rate_deviation"]["value"] == pytest.approx(0.10)

    # Alerts derived from the KPIs must also match.
    alerts_adapter = adapter.check_alerts(adapter_kpis)
    alerts_legacy = legacy.check_alerts(legacy_kpis)
    for a in alerts_adapter:
        a.pop("timestamp", None)
    for a in alerts_legacy:
        a.pop("timestamp", None)
    assert alerts_adapter == alerts_legacy



# --- Container wiring: one tracking adapter resolvable behind the port --------

@pytest.mark.unit
def test_container_resolves_single_tracking_adapter():
    from bootstrap.settings.loaders import load_settings
    from bootstrap.container import Container

    container = Container(load_settings())
    tracking = container.resolve("tracking")
    assert isinstance(tracking, ConsolidatedTrackingAdapter)
    # Cached: same instance on re-resolve.
    assert container.resolve("tracking") is tracking
