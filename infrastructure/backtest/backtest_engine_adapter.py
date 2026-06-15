"""
Canonical backtest engine adapter (E3.T1 -- Option A: Retire & Redefine).

``RealisticBacktesterAdapter`` is the single canonical implementation of
:class:`domain.ports.backtest_ports.BacktestEnginePort`. It is a thin,
pure-delegation wrapper around the live, golden-tested
:class:`infrastructure.backtest.realistic_backtester.RealisticBacktester` (the
sole trusted backtest truth source, pinned by tests/e2e/test_backtest_golden.py).

It introduces NO logic and NO transformation: ``run_backtest`` forwards its
arguments verbatim so backtest behavior is preserved exactly.
"""
from typing import Any, Dict, Optional

from domain.ports.backtest_ports import BacktestEnginePort


class RealisticBacktesterAdapter(BacktestEnginePort):
    """Pure-delegation BacktestEnginePort over the canonical RealisticBacktester."""

    def __init__(self, backtester):
        self._bt = backtester

    def run_backtest(self,
                     data: Any,
                     strategy_function,
                     strategy_params: Optional[Dict[str, Any]] = None,
                     initial_capital: Optional[float] = None,
                     strategy_name: Optional[str] = None) -> Dict[str, Any]:
        return self._bt.run_backtest(
            data,
            strategy_function,
            strategy_params=strategy_params,
            initial_capital=initial_capital,
            strategy_name=strategy_name,
        )
