#!/usr/bin/env python3
"""Non-production trading-system CLI shell (E2.T5.2).

Owns argument parsing and process I/O for the live runner's NON-production modes
(``config-test``, ``backtest``, ``optimize``, ``retune``, ``monitor``), builds
the composition root, resolves the required ports, and delegates orchestration
to :class:`TradingModesUseCase`. CLI arguments, console output, and exit codes
are preserved verbatim from ``run_trading_system``.

Production + auto-detect modes are intentionally NOT handled here (E2.T5.3); the
parser still accepts them for argv fidelity, but they are routed by
``run_trading_system`` itself.

Flow: Runner -> CLI -> UseCase -> Port -> Infrastructure.
"""

import argparse
import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from application.use_cases.run_trading_modes import TradingModesUseCase
from bootstrap.lifecycle import lifespan

_NON_PRODUCTION_MODES = ("config-test", "backtest", "optimize", "retune", "monitor")


def create_parser() -> argparse.ArgumentParser:
    """Argument parser for the trading system (mirrors run_trading_system)."""
    parser = argparse.ArgumentParser(
        description="Hedge Fund Trading System - Production-Ready Algorithmic Trading Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["optimize", "backtest", "retune", "monitor", "production", "config-test"],
        default="optimize",
        help="Operation mode to run (default: optimize)"
    )
    parser.add_argument("--strategy", default="crypto_breakout",
                        help="Trading strategy to use (default: crypto_breakout)")
    parser.add_argument("--symbol", help="Trading pair symbol (e.g., BTC/USDT)")
    parser.add_argument("--symbols", help="Comma-separated list of symbols (e.g., BTC/USDT,ETH/USDT)")
    parser.add_argument("--timeframe", default="1h", help="Timeframe for data (default: 1h)")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--max-evals", type=int, default=100,
                        help="Maximum number of hyperopt evaluations (default: 100)")
    parser.add_argument("--use-optimized-params", action="store_true",
                        help="Use previously optimized parameters instead of defaults")
    parser.add_argument("--days-back", type=int, default=30,
                        help="Number of days of historical data to use (default: 30)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--log-dir", default="logs", help="Directory for log files (default: logs)")
    parser.add_argument("--auto-detect", action="store_true",
                        help="Run in auto-detection mode")
    parser.add_argument("--comprehensive-logs", action="store_true",
                        help="Enable comprehensive logging with detailed background activity tracking")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.mode not in _NON_PRODUCTION_MODES:
        # Production / auto-detect are handled by run_trading_system (E2.T5.3).
        print(f"❌ Mode '{args.mode}' is not a non-production mode handled by this CLI")
        return 1

    with lifespan() as container:
        use_case = TradingModesUseCase(
            backtest_use_case_factory=container.resolve("legacy_backtest_use_case_factory"),
            hyperopt_config_factory=container.resolve("hyperopt_config_factory"),
            hyperopt_optimizer_factory=container.resolve("hyperopt_optimizer_factory"),
            auto_retune_optimizer_factory=container.resolve("auto_retune_optimizer_factory"),
        )

        if args.mode == "config-test":
            return use_case.run_config_test()
        if args.mode == "backtest":
            return use_case.run_backtest(args.strategy, args.symbol, args.days_back)
        if args.mode == "optimize":
            return use_case.run_optimize(args.strategy, args.symbol, args.max_evals)
        if args.mode == "retune":
            return use_case.run_retune(args.strategy, args.symbol, args.symbols)
        if args.mode == "monitor":
            return use_case.run_monitor()

    return 0


if __name__ == "__main__":
    sys.exit(main())
