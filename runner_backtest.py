#!/usr/bin/env python3
"""
Backtest Runner - thin entry point (E2.T4b - Composition Root Hardening).

All orchestration and strategy loading now live in the application/infrastructure
layers:

* ``application.use_cases.run_backtest.RunBacktestUseCase`` - orchestration
* ``infrastructure.backtest.strategy_provider`` - strategy loading/wrapping

This module only owns: the canonical CLI ``main()`` shim and a backward-compatible
``run_backtest_process`` helper that delegates to the container-wired use case. It
imports no infrastructure and constructs no adapters directly.
"""
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bootstrap.settings.loaders import load_settings


def load_symbols_from_env() -> List[str]:
    """Load symbols from configuration."""
    symbols_str = load_settings().wfo.wfo_coins if load_settings().wfo and load_settings().wfo.wfo_coins else "BTCUSDT,ETHUSDT"
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def run_backtest_process(symbols: List[str],
                         strategy_name: str,
                         start_date: datetime,
                         end_date: datetime,
                         initial_capital: float = 10000.0,
                         fee_rate: float = 0.001,
                         slippage_factor: float = 0.0005,
                         strategy_params: Dict[str, Any] = None,
                         file_repository=None) -> Dict[str, Any]:
    """Backward-compatible API: run a single-strategy backtest.

    Delegates to ``RunBacktestUseCase`` wired from the composition root. When a
    ``file_repository`` port is supplied it is used directly; the remaining ports
    (backtester factory, strategy provider, CSV loader) are resolved from the
    container. No infrastructure is instantiated here.
    """
    from application.use_cases.run_backtest import BacktestRequest, RunBacktestUseCase
    from bootstrap.lifecycle import lifespan

    with lifespan() as container:
        use_case = RunBacktestUseCase(
            file_repository=file_repository if file_repository is not None else container.resolve("file_repository"),
            backtester_factory=container.resolve("backtester_factory"),
            strategy_provider=container.resolve("backtest_strategy_provider"),
            csv_history_loader=container.resolve("csv_history_loader"),
        )
        return use_case.execute(BacktestRequest(
            symbols=symbols,
            strategy_names=[strategy_name],
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            fee_rate=fee_rate,
            slippage_factor=slippage_factor,
            strategy_params=strategy_params or {},
        ))


def main():
    """Backward-compatible entry point.

    Argument parsing, composition-root wiring, and process I/O live in
    :mod:`interface.cli.backtest`. This shim delegates so existing invocations of
    ``runner_backtest.py`` keep working unchanged while the canonical path runs
    through the container-wired ``RunBacktestUseCase``.
    """
    from interface.cli.backtest import main as cli_main
    return cli_main()


if __name__ == "__main__":
    exit(main())
