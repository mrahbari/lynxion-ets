"""E2.T4 pilot: validation/optimization runners wired through the composition root.

These runners (walk-forward, retune/hyperopt, comprehensive portfolio backtest,
comprehensive validation, extended-horizon validation) drive heavy and/or
network-bound infrastructure, so the guarantees verified here are:

1. The container wires the new validation/optimization ports/factories correctly
   and resolves them offline (``resolve_all``).
2. The migrated use cases obtain *all* infrastructure via injection and never
   instantiate infra classes directly when a factory/port is supplied -- proven
   by driving the moved orchestration against deterministic offline stubs.

Byte-identical external behavior of the full pipelines is preserved by the
verbatim orchestration move; the backtest and data-sync goldens remain the
suite-wide regression guard.
"""

import pytest
from bootstrap.settings.loaders import load_settings

pytest.importorskip("pandas")

try:
    from bootstrap.lifecycle import create_container, lifespan
    from application.use_cases.run_walkforward import (
        RunWalkforwardUseCase, WalkforwardRequest,
    )
    from application.use_cases.optimize_strategy import (
        OptimizeStrategyUseCase, OptimizeStrategyRequest,
    )
    from application.use_cases.validate_portfolio import ValidatePortfolioUseCase
except Exception as exc:  # pragma: no cover - environment guard
    pytest.skip(f"validation pilot dependencies unavailable: {exc}", allow_module_level=True)


_NEW_KEYS = (
    "csv_history_loader",
    "data_integrity_checker",
    "hyperopt_param_space_factory",
    "portfolio_backtester_factory",
    "wfo_orchestrator_factory",
    "hyperopt_optimizer_factory",
)


@pytest.mark.e2e
def test_container_resolves_validation_optimization_ports(tmp_path):
    with lifespan(base_data_dir=str(tmp_path)) as container:
        resolved = container.resolve_all()
        for key in _NEW_KEYS:
            assert key in resolved and resolved[key] is not None

        # Config-free ports are concrete adapters.
        assert type(container.resolve("csv_history_loader")).__name__ == "CSVHistoryLoaderAdapter"
        assert type(container.resolve("data_integrity_checker")).__name__ == "DataIntegrityChecker"

        # Request-parameterized infra is exposed as callables.
        for key in ("hyperopt_param_space_factory", "portfolio_backtester_factory",
                    "wfo_orchestrator_factory", "hyperopt_optimizer_factory"):
            assert callable(container.resolve(key))


@pytest.mark.e2e
def test_portfolio_backtester_factory_builds_with_request_params(tmp_path):
    with lifespan(base_data_dir=str(tmp_path)) as container:
        factory = container.resolve("portfolio_backtester_factory")
        backtester = factory(50000.0, 0.002, 0.001)
        assert type(backtester).__name__ == "ComprehensivePortfolioBacktester"
        assert backtester.initial_capital == 50000.0


@pytest.mark.e2e
def test_walkforward_use_case_drives_injected_orchestrator():
    """RunWalkforwardUseCase orchestration runs against an injected stub factory
    without ever importing/instantiating the real WFO orchestrator."""
    calls = {}

    class _FakeOrchestrator:
        def __init__(self, config):
            calls["config"] = config

        def run_complete_wfo_pipeline(self, symbols, strategy_name):
            calls["symbols"] = symbols
            calls["strategy_name"] = strategy_name
            return {
                "comprehensive_report": {"summary_metrics": {}},
                "data_validation": {"all_symbols_valid": True},
                "cross_validation_results": {},
                "multi_asset_optimization": {},
                "walk_forward_results": {"total_periods": 3},
            }

    def factory(config):
        return _FakeOrchestrator(config)

    use_case = RunWalkforwardUseCase(settings=load_settings(), wfo_orchestrator_factory=factory)
    results = use_case.execute(WalkforwardRequest(symbols=["BTCUSDT"], strategy_name="crypto_breakout",
                                                  train_size=60, test_size=20, step_size=20,
                                                  max_evals=5, cv_splits=3))

    assert results["status"] == "completed"
    assert calls["symbols"] == ["BTCUSDT"]
    assert calls["strategy_name"] == "crypto_breakout"
    # Request params flow through into the orchestrator config.
    assert calls["config"]["train_size"] == 60
    assert calls["config"]["cv_n_splits"] == 3


@pytest.mark.e2e
def test_validate_portfolio_use_case_uses_injected_factory():
    """ValidatePortfolioUseCase._build_backtester forwards request params to the
    injected factory and never falls back to direct instantiation."""
    recorded = {}

    sentinel = object()

    def factory(initial_capital, fee_rate, slippage_factor):
        recorded["args"] = (initial_capital, fee_rate, slippage_factor)
        return sentinel

    use_case = ValidatePortfolioUseCase(settings=load_settings(), portfolio_backtester_factory=factory)
    built = use_case._build_backtester(100000.0, 0.001, 0.0005)
    assert built is sentinel
    assert recorded["args"] == (100000.0, 0.001, 0.0005)


@pytest.mark.e2e
def test_optimize_strategy_use_case_drives_injected_ports():
    """OptimizeStrategyUseCase runs its retune loop fully offline against injected
    data-sync ports, parameter-space and optimizer factories. With no local data
    files every symbol is skipped, so the optimizer's optimize step is never
    reached -- proving all collaborators come from injection."""

    state = {"download_calls": 0, "optimize_calls": 0,
             "param_space_built": 0, "optimizer_built": 0}

    class _StubDownloader:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _StubSyncManager:
        async def sync_symbol_data(self, symbol, timeframes, start_time, end_time):
            state["download_calls"] += 1
            return {"rows_written": 0}

    class _StubFileRepo:
        def _normalize_symbol_for_file(self, symbol):
            return symbol.replace("USDT", "-USDT")

        def get_processed_file_path(self, normalized_symbol, timeframe):
            return f"/__nonexistent__/{normalized_symbol}_{timeframe}.csv"

    class _StubParamSpace:
        def get_space(self, strategy_name):
            return {}

    class _StubOptimizer:
        def optimize_with_config(self, **kwargs):
            state["optimize_calls"] += 1
            return {"best_params": {}, "best_value": 0.0}

    def _param_space_factory():
        state["param_space_built"] += 1
        return _StubParamSpace()

    def _optimizer_factory(hyperopt_config, strategy_name):
        state["optimizer_built"] += 1
        return _StubOptimizer()

    use_case = OptimizeStrategyUseCase(
        settings=load_settings(),
        file_repository=_StubFileRepo(),
        sync_manager=_StubSyncManager(),
        data_downloader=_StubDownloader(),
        hyperopt_param_space_factory=_param_space_factory,
        hyperopt_optimizer_factory=_optimizer_factory,
    )

    results = use_case.execute(OptimizeStrategyRequest(symbols=["BTCUSDT"], strategy_name="crypto_breakout",
                                                       max_evals=5, days_back=30))

    # Download port + factories were all driven through injection.
    assert state["download_calls"] == 1
    assert state["param_space_built"] == 1
    assert state["optimizer_built"] == 1
    # No local data file -> symbol skipped before the optimize step.
    assert state["optimize_calls"] == 0
    assert results["total_processed"] == 1
    assert results["successful_optimizations"] == 0
    assert results["failed_optimizations"] == 0
    assert results["results"] == {}
