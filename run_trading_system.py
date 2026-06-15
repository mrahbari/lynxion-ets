"""Trading system entry point / CLI router.

Orchestration has been migrated into the application + interface layers
(E2.T5.1/.2/.3):

* non-production modes (config-test / backtest / optimize / retune / monitor)
  -> ``interface.cli.trading_system_modes``
* production + auto-detect
  -> ``interface.cli.trading_system_production``
* the production orchestrator class
  -> ``infrastructure.orchestrators.production_trading_orchestrator``

This module now only parses arguments and routes to the owning CLI. It
constructs no infrastructure, imports no heavy/optional deps at module top, and
holds no orchestration logic — which also makes it safe to import in-process.
(Final entry-point de-duplication is E2.T5.4.)
"""

import sys
import argparse
import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def create_parser():
    """Create argument parser for the trading system."""
    parser = argparse.ArgumentParser(
        description="Hedge Fund Trading System - Production-Ready Algorithmic Trading Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run optimization for a specific strategy/symbol
  python run_trading_system.py --mode optimize --strategy crypto_breakout --symbol BTC/USDT

  # Run backtest with optimized parameters
  python run_trading_system.py --mode backtest --strategy crypto_breakout --symbol BTC/USDT --use-optimized-params

  # Run auto-retune on multiple symbols
  python run_trading_system.py --mode retune --strategy crypto_breakout --symbols BTC/USDT,ETH/USDT,SOL/USDT

  # Monitor system performance
  python run_trading_system.py --mode monitor

  # Run in production mode (with all features enabled)
  python run_trading_system.py --mode production

  # Run in auto-detection mode (watcher detects opportunities and triggers strategies automatically)
  python run_trading_system.py --mode production --auto-detect --symbols BTC/USDT,ETH/USDT

  # Test configuration
  python run_trading_system.py --mode config-test
        """
    )

    parser.add_argument(
        "--mode",
        choices=["optimize", "backtest", "retune", "monitor", "production", "config-test"],
        default="optimize",
        help="Operation mode to run (default: optimize)"
    )

    parser.add_argument(
        "--strategy",
        default="crypto_breakout",
        help="Trading strategy to use (default: crypto_breakout)"
    )

    parser.add_argument(
        "--symbol",
        help="Trading pair symbol (e.g., BTC/USDT)"
    )

    parser.add_argument(
        "--symbols",
        help="Comma-separated list of symbols (e.g., BTC/USDT,ETH/USDT)"
    )

    parser.add_argument(
        "--timeframe",
        default="1h",
        help="Timeframe for data (default: 1h)"
    )

    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )

    parser.add_argument(
        "--max-evals",
        type=int,
        default=100,
        help="Maximum number of hyperopt evaluations (default: 100)"
    )

    parser.add_argument(
        "--use-optimized-params",
        action="store_true",
        help="Use previously optimized parameters instead of defaults"
    )

    parser.add_argument(
        "--days-back",
        type=int,
        default=30,
        help="Number of days of historical data to use (default: 30)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory for log files (default: logs)"
    )

    parser.add_argument(
        "--auto-detect",
        action="store_true",
        help="Run in auto-detection mode (watcher detects opportunities and triggers strategies automatically)"
    )

    parser.add_argument(
        "--comprehensive-logs",
        action="store_true",
        help="Enable comprehensive logging with detailed background activity tracking"
    )

    return parser


def _dispatch(args):
    """Route a parsed args namespace to the owning CLI and return its exit code."""
    # Non-production modes (E2.T5.2)
    if args.mode in ("config-test", "backtest", "optimize", "retune", "monitor"):
        from interface.cli.trading_system_modes import main as modes_main
        return modes_main(sys.argv[1:])

    # Production + auto-detect (E2.T5.3)
    if args.mode == "production":
        from interface.cli.trading_system_production import main as production_main
        return production_main(sys.argv[1:])

    print(f"❌ Unknown mode: {args.mode}")
    create_parser().print_help()
    return 1


def main():
    """Single entry point: parse arguments and route to the owning CLI.

    Importable and callable by other scripts; also the ``__main__`` path below.
    """
    parser = create_parser()
    args = parser.parse_args()

    # Handle --help by just showing the help text
    if '--help' in sys.argv or '-h' in sys.argv:
        parser.print_help()
        sys.exit(0)

    print(f"🚀 Starting Trading System in {args.mode} mode...")
    sys.exit(_dispatch(args))


if __name__ == "__main__":
    main()
