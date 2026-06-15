#!/usr/bin/env python3
"""Production / auto-detect trading-system CLI shell (E2.T5.3).

Owns argument parsing and process I/O for the live runner's ``production`` mode
(both the orchestrator path and the ``--auto-detect`` path), builds the
composition root, resolves the orchestrator factories, and delegates the
lifecycle to the application use cases. CLI arguments, console output, and exit
codes are preserved verbatim from ``run_trading_system``.

The broker/data/execution wiring lives entirely in the composition root and goes
through the broker_registry singleton, so there is no duplicate execution service
and no duplicate broker session.

Flow: Runner -> CLI -> UseCase -> Port -> Infrastructure.
"""

import argparse
import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from application.use_cases.run_live_trading import RunLiveTradingUseCase
from application.use_cases.run_auto_detection import RunAutoDetectionUseCase
from bootstrap.lifecycle import lifespan


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

    if args.mode != "production":
        print(f"❌ Mode '{args.mode}' is not handled by the production CLI")
        return 1

    with lifespan() as container:
        # R2: startup preflight — refuse to start a LIVE (real-funds) session on an
        # inconsistent/unsafe configuration. PAPER/TESTNET only warn.
        try:
            from bootstrap.settings.loaders import load_settings
            from shared.preflight import run_preflight
            pf = run_preflight(load_settings())
            print(f"🔎 Preflight: mode={pf['mode']} ok={pf['ok']} flags={pf['flags']}", flush=True)
            for w in pf["warnings"]:
                print(f"   ⚠️ {w}", flush=True)
            for b in pf["blocking"]:
                print(f"   ⛔ {b}", flush=True)
            if pf["mode"] == "LIVE" and not pf["ok"]:
                print("❌ Preflight FAILED for LIVE mode — refusing to start. Fix the blocking issues above.")
                return 2
        except Exception as e:
            print(f"⚠️ Preflight check skipped due to error: {e}")

        if args.auto_detect:
            use_case = RunAutoDetectionUseCase(
                orchestrator_factory=container.resolve("auto_detection_orchestrator_factory"),
            )
            return use_case.run(
                symbols_arg=args.symbols,
                symbol_arg=args.symbol,
                comprehensive_logging=args.comprehensive_logs,
            )

        use_case = RunLiveTradingUseCase(
            orchestrator_factory=container.resolve("production_orchestrator_factory"),
        )
        return use_case.run(strategy_name=args.strategy, symbol=args.symbol)


if __name__ == "__main__":
    sys.exit(main())
