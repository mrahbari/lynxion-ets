"""E2.T5.3 pilot: production + auto-detect migration.

Pins the production migration WITHOUT touching real brokers / network / infinite
loops (stub orchestrators are injected). Also verifies the headline safety win:
``run_trading_system`` is now import-safe and is a pure router.

1. The container registers the orchestrator factories as offline-safe callables.
2. The shared production wiring goes through the broker_registry singleton (so
   there is no duplicate execution service / broker session).
3. RunLiveTradingUseCase drives initialize_system() -> run_production_trading()
   via the injected factory, preserving the sample fetcher + risk config.
4. RunAutoDetectionUseCase resolves symbols, drives run_auto_detection(), and
   swallows KeyboardInterrupt, via the injected factory.
5. run_trading_system imports cleanly (no heavy infra) and routes production to
   the production CLI / non-production modes to the modes CLI.
"""

import inspect
from pathlib import Path

import pytest

pytest.importorskip("pandas")

from bootstrap.lifecycle import create_container
import bootstrap.container as container_mod
from application.use_cases.run_live_trading import RunLiveTradingUseCase
from application.use_cases.run_auto_detection import RunAutoDetectionUseCase


@pytest.mark.e2e
def test_container_registers_orchestrator_factories(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        keys = container.registered_keys()
        for key in ("production_orchestrator_factory", "auto_detection_orchestrator_factory"):
            assert key in keys
            # Resolving returns a lazy callable; no infrastructure is built offline.
            assert callable(container.resolve(key))
    finally:
        container.shutdown()


@pytest.mark.e2e
def test_production_wiring_uses_broker_registry_singleton():
    # The shared wiring (used by BOTH production and auto-detect factories) must
    # go through the broker_registry singleton -> one execution service per run.
    src = inspect.getsource(container_mod.Container._build_production_data_and_services)
    assert "broker_registry" in src
    assert "get_execution_service" in src
    # Both factories funnel through the single shared wiring helper.
    prod = inspect.getsource(container_mod.Container._build_production_orchestrator_factory)
    auto = inspect.getsource(container_mod.Container._build_auto_detection_orchestrator_factory)
    assert "_build_production_data_and_services" in prod
    assert "_build_production_data_and_services" in auto


@pytest.mark.e2e
def test_live_trading_use_case_drives_lifecycle(capsys):
    events = []

    class _StubOrchestrator:
        def initialize_system(self):
            events.append("init")

        def run_production_trading(self, data_fetcher, strategy_name, risk_config):
            events.append(("run", strategy_name, risk_config))
            # Exercise the injected sample fetcher (no infinite loop in the stub).
            events.append(("data", data_fetcher()))

    factory_calls = {"count": 0}

    def _factory():
        factory_calls["count"] += 1
        return _StubOrchestrator()

    use_case = RunLiveTradingUseCase(orchestrator_factory=_factory)
    rc = use_case.run(strategy_name="crypto_breakout", symbol="ETH/USDT")

    out = capsys.readouterr().out
    assert rc == 0
    assert factory_calls["count"] == 1
    assert events[0] == "init"
    assert events[1][0] == "run"
    assert events[1][1] == "crypto_breakout"
    assert events[1][2] == {"max_risk": 0.02, "atr_multiplier": 1.5, "use_dynamic_position": True}
    data = events[2][1]
    assert list(data.keys()) == ["ETH/USDT"]  # symbol routed into the fetcher
    assert "Running production orchestrator with sample data" in out


@pytest.mark.e2e
def test_live_trading_default_symbol_key():
    captured = {}

    class _StubOrchestrator:
        def initialize_system(self):
            pass

        def run_production_trading(self, data_fetcher, strategy_name, risk_config):
            captured["data"] = data_fetcher()

    RunLiveTradingUseCase(orchestrator_factory=lambda: _StubOrchestrator()).run()
    assert list(captured["data"].keys()) == ["BTCUSD"]  # default when no symbol


@pytest.mark.e2e
def test_auto_detection_use_case_resolves_symbols_and_handles_interrupt(capsys):
    captured = {}

    class _StubOrchestrator:
        def run_auto_detection(self):
            captured["ran"] = True

    def _factory(symbols, risk_config, comprehensive_logging):
        captured["symbols"] = symbols
        captured["risk_config"] = risk_config
        captured["comprehensive_logging"] = comprehensive_logging
        return _StubOrchestrator()

    use_case = RunAutoDetectionUseCase(orchestrator_factory=_factory)
    rc = use_case.run(symbols_arg="BTC/USDT,ETH/USDT", symbol_arg=None, comprehensive_logging=True)

    out = capsys.readouterr().out
    assert rc == 0
    assert captured["ran"] is True
    assert captured["symbols"] == ["BTC/USDT", "ETH/USDT"]
    assert captured["comprehensive_logging"] is True
    assert "Starting auto-detection mode" in out


@pytest.mark.e2e
def test_auto_detection_use_case_swallows_keyboard_interrupt(capsys):
    class _StubOrchestrator:
        def run_auto_detection(self):
            raise KeyboardInterrupt()

    use_case = RunAutoDetectionUseCase(orchestrator_factory=lambda *a: _StubOrchestrator())
    rc = use_case.run(symbols_arg=None, symbol_arg=None, comprehensive_logging=False)

    out = capsys.readouterr().out
    assert rc == 0
    assert "Auto-detection mode stopped by user" in out


@pytest.mark.e2e
def test_runner_is_import_safe_and_routes(monkeypatch):
    # E2.T5.3: the runner no longer pulls heavy infra at import, so this is safe.
    import run_trading_system as runner

    import interface.cli.trading_system_modes as modes_cli
    import interface.cli.trading_system_production as production_cli

    routed = {}

    def _record(key):
        def _main(argv=None):
            routed[key] = argv
            return 0
        return _main

    monkeypatch.setattr(modes_cli, "main", _record("modes"))
    monkeypatch.setattr(production_cli, "main", _record("production"))

    parser = runner.create_parser()

    assert runner._dispatch(parser.parse_args(["--mode", "backtest"])) == 0
    assert "modes" in routed

    assert runner._dispatch(parser.parse_args(["--mode", "production"])) == 0
    assert "production" in routed


@pytest.mark.e2e
def test_runner_has_no_infrastructure_imports_at_top():
    src = (Path(__file__).resolve().parents[2] / "run_trading_system.py").read_text(encoding="utf-8")
    # No orchestration class / wiring function remains in the runner.
    assert "class ProductionTradingOrchestrator" not in src
    assert "def run_production_orchestrator" not in src
