"""Characterization: shadow deployment single cycle (E2.T5.0, updated for E2.T5.1).

Pins the CURRENT behavior of the shadow trading cycle with a deterministic CSV
loader stub and a fixed strategy set:

* one cycle loads data for each symbol exactly once (via the injected loader),
* generates signals through the configured strategies,
* virtual execution produces ZERO trades because ``calculate_position_size``
  currently returns 0.0 (risk module owns sizing — pinned as-is), and
* the equity curve grows by exactly one point per cycle.

E2.T5.1 extracted the orchestration out of ``runner_shadow_deployment`` into
``ShadowDeploymentUseCase``; the behavioral assertions below are byte-identical
to the pre-extraction pins — only the construction site moved (ports are now
injected rather than monkeypatched onto the runner module). No network, no real
strategies, no infinite loop.
"""

import pandas as pd
import pytest
from bootstrap.settings.loaders import load_settings

from application.use_cases.run_shadow_deployment import ShadowDeploymentUseCase


class _StubCSVLoader:
    """Deterministic, offline CSV loader returning a fixed OHLCV frame."""

    def __init__(self):
        self.load_calls = []

    def load(self, symbol):
        self.load_calls.append(symbol)
        idx = pd.to_datetime(["2023-01-01 00:00:00", "2023-01-01 00:01:00"])
        return pd.DataFrame(
            {
                "open": [100.0, 101.0],
                "high": [102.0, 103.0],
                "low": [99.0, 100.0],
                "close": [101.0, 102.0],
                "volume": [1000, 1100],
                "rsi": [55.0, 60.0],
            },
            index=idx,
        )


def _neutral_strategy(data_point, context):
    return 0


def _make_use_case(loader, **overrides):
    kwargs = dict(
        settings=load_settings(),
        symbols=["BTCUSDT"],
        strategies=["fixed_neutral"],
        initial_capital=100000.0,
        risk_per_trade=0.02,
        strategy_provider=lambda: {"fixed_neutral": _neutral_strategy},
        csv_loader_factory=lambda: loader,
        kpi_reporter=lambda current_metrics, baseline_metrics: {"kpi": "stub"},
    )
    kwargs.update(overrides)
    return ShadowDeploymentUseCase(**kwargs)


@pytest.mark.e2e
def test_shadow_single_cycle_is_deterministic():
    loader = _StubCSVLoader()
    system = _make_use_case(loader)

    # Baseline: one initial equity point, no trades.
    assert len(system.equity_curve) == 1
    assert system.trade_log == []

    system.run_shadow_cycle()

    # Loader was driven exactly once for the single symbol.
    assert loader.load_calls == ["BTCUSDT"]
    # Pinned current behavior: position sizing returns 0.0 -> no trades executed.
    assert system.trade_log == []
    assert system.shadow_metrics["total_trades"] == 0
    # Equity curve grew by exactly one point.
    assert len(system.equity_curve) == 2
    assert system.equity_curve[-1]["equity"] == system.initial_capital


@pytest.mark.e2e
def test_shadow_report_structure():
    loader = _StubCSVLoader()
    system = _make_use_case(loader)
    system.run_shadow_cycle()

    report = system.get_shadow_report()

    assert set(report.keys()) >= {
        "timestamp", "summary", "metrics", "kpi_report", "symbols", "strategies", "config",
    }
    assert report["summary"]["initial_capital"] == 100000.0
    assert report["summary"]["total_trades"] == 0
    assert report["symbols"] == ["BTCUSDT"]
    assert report["strategies"] == ["fixed_neutral"]
    assert report["kpi_report"] == {"kpi": "stub"}
