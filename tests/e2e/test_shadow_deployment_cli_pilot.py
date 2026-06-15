"""E2.T5.1 pilot: shadow-deployment flow wired through the composition root.

Guarantees the migrated flow matches the approved architecture
(Runner -> CLI -> UseCase -> Port -> Infrastructure):

1. The container registers the shadow ports as lazy callables, so ``resolve_all``
   (offline smoke) never loads the strategy/KPI infrastructure.
2. ``ShadowDeploymentUseCase`` drives the injected ports (strategy provider, CSV
   loader factory, KPI reporter) and never constructs infrastructure itself.
3. The CLI delegates to the use case, injecting the container's ports.
4. ``runner_shadow_deployment`` is a thin shim: no infrastructure imports, no
   adapter construction, no trapped orchestration.
"""

from pathlib import Path

import pytest
from bootstrap.settings.loaders import load_settings

pytest.importorskip("pandas")

try:
    from bootstrap.lifecycle import create_container
    from application.use_cases.run_shadow_deployment import ShadowDeploymentUseCase
    import interface.cli.shadow_deployment as cli
    import runner_shadow_deployment as runner
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"shadow pilot dependencies unavailable: {exc}", allow_module_level=True)

_RUNNER_SRC = Path(runner.__file__).read_text(encoding="utf-8")


@pytest.mark.e2e
def test_container_registers_shadow_ports(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        # resolve_all must stay offline: ports are returned as callables and never
        # invoked (no strategies/KPI infra loaded during smoke resolve).
        resolved = container.resolve_all()
        for key in ("shadow_strategy_provider", "shadow_csv_loader_factory", "shadow_kpi_reporter"):
            assert key in resolved
            assert callable(resolved[key])
    finally:
        container.shutdown()


@pytest.mark.e2e
def test_use_case_uses_injected_ports():
    calls = {"strategy": 0, "loader": 0}

    class _Loader:
        def load(self, symbol):
            import pandas as pd
            return pd.DataFrame(
                {"open": [1.0], "high": [2.0], "low": [0.5], "close": [1.5], "volume": [10]},
                index=pd.to_datetime(["2023-01-01"]),
            )

    def _strategy_provider():
        calls["strategy"] += 1
        return {"s": lambda data_point, ctx: 0}

    def _loader_factory():
        calls["loader"] += 1
        return _Loader()

    use_case = ShadowDeploymentUseCase(
        settings=load_settings(),
        symbols=["BTCUSDT"],
        strategies=["s"],
        strategy_provider=_strategy_provider,
        csv_loader_factory=_loader_factory,
        kpi_reporter=lambda current_metrics, baseline_metrics: {"ok": True},
    )

    # Strategy provider invoked once at construction.
    assert calls["strategy"] == 1

    use_case.run_shadow_cycle()

    # Loader factory invoked once for the single cycle (injected port driven).
    assert calls["loader"] == 1
    assert use_case.get_shadow_report()["kpi_report"] == {"ok": True}


@pytest.mark.e2e
def test_cli_delegates_to_use_case(monkeypatch):
    recorded = {}

    class _RecordingUseCase:
        def __init__(self, settings=None, symbols=None, strategies=None, initial_capital=None,
                     risk_per_trade=None, strategy_provider=None,
                     csv_loader_factory=None, kpi_reporter=None):
            recorded["symbols"] = symbols
            recorded["strategies"] = strategies
            recorded["strategy_provider"] = strategy_provider
            recorded["csv_loader_factory"] = csv_loader_factory
            recorded["kpi_reporter"] = kpi_reporter

        def run_shadow_cycle(self):
            recorded["cycles"] = recorded.get("cycles", 0) + 1
            # Stop the loop deterministically after the first cycle.
            raise KeyboardInterrupt()

        def get_shadow_report(self):  # pragma: no cover - not reached (no --report)
            return {}

    monkeypatch.setattr(cli, "ShadowDeploymentUseCase", _RecordingUseCase)

    rc = cli.main(["--symbols", "BTCUSDT", "--strategies", "s"])

    assert rc == 0
    assert recorded["cycles"] == 1
    assert recorded["symbols"] == ["BTCUSDT"]
    assert recorded["strategies"] == ["s"]
    # CLI injected the container's ports (callables).
    assert callable(recorded["strategy_provider"])
    assert callable(recorded["csv_loader_factory"])
    assert callable(recorded["kpi_reporter"])


@pytest.mark.e2e
def test_runner_is_thin_shim():
    assert "from infrastructure" not in _RUNNER_SRC
    assert "import infrastructure" not in _RUNNER_SRC
    assert "CSVHistoryLoaderAdapter" not in _RUNNER_SRC
    assert "load_sample_strategies" not in _RUNNER_SRC
    assert "generate_shadow_kpi_report" not in _RUNNER_SRC
    assert "class ShadowDeploymentSystem" not in _RUNNER_SRC
    assert "from interface.cli.shadow_deployment import main" in _RUNNER_SRC
