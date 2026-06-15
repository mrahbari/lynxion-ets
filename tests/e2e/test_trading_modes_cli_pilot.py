"""E2.T5.2 pilot: non-production trading modes via the composition root.

These are the behavioral pins that were impossible in E2.T5.0 (the live runner
could not be imported offline). After extraction, the non-production modes live
in import-safe modules (``TradingModesUseCase`` / ``interface.cli.trading_system_modes``)
whose heavy deps are lazy/injected, so they CAN be exercised offline:

1. The container registers the new mode ports as offline-safe callables.
2. ``config-test`` runs end-to-end through the real CLI (deterministic).
3. ``backtest`` / ``optimize`` / ``retune`` drive injected factories (stubbed —
   no hyperopt, no infra) and preserve the legacy output/symbol formatting.
4. ``monitor`` is capped at N cycles via a patched ``time.sleep``.
5. ``run_trading_system`` delegates non-production modes and keeps production
   logic intact (pinned statically — the live router is import-unsafe).
"""

from pathlib import Path

import pytest

pytest.importorskip("pandas")

from bootstrap.lifecycle import create_container
from application.use_cases.run_trading_modes import TradingModesUseCase
import interface.cli.trading_system_modes as modes_cli

_RUNNER_SRC = (Path(__file__).resolve().parents[2] / "run_trading_system.py").read_text(encoding="utf-8")


@pytest.mark.e2e
def test_container_registers_mode_ports(tmp_path):
    container = create_container(base_data_dir=str(tmp_path))
    try:
        keys = container.registered_keys()
        # Resolve ONLY the mode ports individually: each returns a lazy callable
        # (no infrastructure constructed offline), so this stays fast and never
        # spawns the heavy data/sync adapters that a full resolve_all() would.
        for key in ("legacy_backtest_use_case_factory", "hyperopt_config_factory",
                    "auto_retune_optimizer_factory", "hyperopt_optimizer_factory"):
            assert key in keys
            assert callable(container.resolve(key))
    finally:
        container.shutdown()


@pytest.mark.e2e
def test_config_test_mode_runs_via_cli(capsys):
    rc = modes_cli.main(["--mode", "config-test"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Testing configuration" in out
    assert "Configuration test completed successfully" in out


@pytest.mark.e2e
def test_backtest_mode_uses_injected_pipeline(capsys):
    captured = {}

    class _StubBacktestUseCase:
        def execute(self, symbol, start_date, end_date, initial_capital, strategy_name):
            captured["symbol"] = symbol
            captured["initial_capital"] = initial_capital
            captured["strategy_name"] = strategy_name
            return {"total_return": 0.1, "win_rate": 0.5, "total_trades": 3}

    factory_calls = {"count": 0}

    def _factory(strategy_name):
        factory_calls["count"] += 1
        captured["factory_strategy"] = strategy_name
        return _StubBacktestUseCase()

    use_case = TradingModesUseCase(backtest_use_case_factory=_factory)
    rc = use_case.run_backtest("crypto_breakout", "BTC/USDT", 30)

    out = capsys.readouterr().out
    assert rc == 0
    assert factory_calls["count"] == 1
    assert captured["factory_strategy"] == "crypto_breakout"
    assert "BTCUSDT" in str(captured["symbol"])  # BTC/USDT -> BTCUSDT
    assert captured["initial_capital"] == 10000
    assert "Backtest completed" in out
    assert "Total Return = 10.00%" in out
    assert "Win Rate = 50.00%" in out
    assert "Total Trades = 3" in out


@pytest.mark.e2e
def test_optimize_mode_uses_injected_optimizer(capsys):
    captured = {}

    class _StubOptimizer:
        def optimize_with_config(self, strategy_name, data, symbol, custom_config):
            captured["strategy_name"] = strategy_name
            captured["symbol"] = symbol
            captured["custom_config"] = custom_config
            return {"best_params": {"x": 1}, "best_value": 1.23}

    use_case = TradingModesUseCase(
        hyperopt_config_factory=lambda strategy_name: {"cfg": strategy_name},
        hyperopt_optimizer_factory=lambda cfg, strategy_name: _StubOptimizer(),
    )
    rc = use_case.run_optimize("crypto_breakout", "BTCUSDT", 5)

    out = capsys.readouterr().out
    assert rc == 0
    assert captured["strategy_name"] == "crypto_breakout"
    assert captured["symbol"] == "BTCUSDT"
    assert captured["custom_config"] == {"max_evals": 5}
    assert "Optimization completed" in out
    assert "Best parameters: {'x': 1}" in out


@pytest.mark.e2e
def test_retune_mode_uses_injected_factory(capsys):
    calls = []

    class _StubAutoRetune:
        def run_auto_retune(self, strategy_name, symbols, risk_config):
            calls.append((strategy_name, tuple(symbols)))
            return {"ok": True}

    use_case = TradingModesUseCase(
        auto_retune_optimizer_factory=lambda strategy_name, threshold: _StubAutoRetune(),
    )
    rc = use_case.run_retune("crypto_breakout", None, "BTC/USDT,ETH/USDT")

    out = capsys.readouterr().out
    assert rc == 0
    assert calls == [("crypto_breakout", ("BTC/USDT",)), ("crypto_breakout", ("ETH/USDT",))]
    assert "All auto-retune processes completed" in out


@pytest.mark.e2e
def test_monitor_mode_is_capped(monkeypatch, capsys):
    import time

    cycles = {"count": 0}
    max_cycles = 3

    def _fake_sleep(_seconds):
        cycles["count"] += 1
        if cycles["count"] >= max_cycles:
            raise KeyboardInterrupt()

    monkeypatch.setattr(time, "sleep", _fake_sleep)

    use_case = TradingModesUseCase()
    rc = use_case.run_monitor()  # must terminate (cap), not loop forever

    out = capsys.readouterr().out
    assert rc == 0
    assert "Starting monitoring mode" in out
    assert "Monitoring stopped by user" in out
    assert out.count("Monitoring system: Portfolio value") == max_cycles


@pytest.mark.e2e
def test_runner_delegates_non_production_and_production():
    # The router delegates the 5 non-production modes to the modes CLI (E2.T5.2)...
    assert "from interface.cli.trading_system_modes import main as modes_main" in _RUNNER_SRC
    assert "modes_main(sys.argv[1:])" in _RUNNER_SRC
    # ...and production to the production CLI (E2.T5.3).
    assert "from interface.cli.trading_system_production import main as production_main" in _RUNNER_SRC
    assert "production_main(sys.argv[1:])" in _RUNNER_SRC
