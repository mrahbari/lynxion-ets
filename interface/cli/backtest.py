#!/usr/bin/env python3
"""Backtest CLI shell (E2.T2).

The new entry point for the backtest feature (F7). It owns argument parsing
and process I/O, builds the composition root, resolves the data-access port,
and delegates orchestration to :class:`RunBacktestUseCase`. CLI arguments,
console output, and exit codes are preserved verbatim from the legacy
``runner_backtest`` so the golden backtest test stays byte-identical.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional

# Ensure project root is importable when invoked as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from domain.enums.strategy_type import StrategyType
from application.use_cases.run_backtest import BacktestRequest, RunBacktestUseCase
from bootstrap.lifecycle import lifespan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Run backtesting for trading strategies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --strategy rsi_strategy --start 2023-01-01 --end 2023-12-31
  %(prog)s --strategy ma_crossover_strategy --start 90d --end today --symbols BTCUSDT
  %(prog)s --strategy crypto_breakout --start 2023-01-01 --end 2023-06-30 --capital 50000
  %(prog)s --all-strategies --start 180d --end today --symbols BTCUSDT
        """
    )

    strategy_group = parser.add_mutually_exclusive_group(required=False)
    strategy_group.add_argument('--strategy', type=str,
                                default='rsi_strategy',
                                help='Single strategy name to backtest (default: rsi_strategy)')

    strategy_group.add_argument('--all-strategies', action='store_true',
                                help='Run all available strategies for comparison')

    strategy_group.add_argument('--strategies', nargs='+', type=str,
                                help='List of specific strategies to run (space-separated)')

    parser.add_argument('--start', type=str, required=True,
                        help='Start date in YYYY-MM-DD format or relative (e.g., "30d", "90d")')

    parser.add_argument('--end', type=str, default='today',
                        help='End date in YYYY-MM-DD format or "today" (default: today)')

    parser.add_argument('--symbols', nargs='+', type=str,
                        help='Specific symbols to backtest (default: from WFO_COINS env var)')

    parser.add_argument('--capital', type=float, default=10000.0,
                        help='Initial capital for backtest (default: 10000.0)')

    parser.add_argument('--fee', type=float, default=0.001,
                        help='Fee rate per trade (default: 0.001 = 0.1%%)')

    parser.add_argument('--slippage', type=float, default=0.0005,
                        help='Slippage factor (default: 0.0005 = 0.05%%)')

    parser.add_argument('--output', type=str,
                        help='Output file to save results (JSON format)')

    parser.add_argument('--validate', action='store_true',
                        help='Validate results after backtesting')

    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')

    return parser


def _parse_date(date_str: str) -> datetime:
    if date_str == 'today':
        return datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    elif date_str.endswith('d'):
        days = int(date_str[:-1])
        return datetime.now() - timedelta(days=days)
    else:
        return datetime.strptime(date_str, '%Y-%m-%d')


def main(argv: Optional[List[str]] = None) -> int:
    """Backtest entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    start_date = _parse_date(args.start)
    end_date = _parse_date(args.end)

    # Get symbols
    if args.symbols:
        symbols = args.symbols
    else:
        from runner_backtest import load_symbols_from_env
        symbols = load_symbols_from_env()

    # Determine which strategies to run
    if args.all_strategies:
        all_available_strategies = [strategy.value for strategy in StrategyType]
        all_available_strategies.append('crypto_breakout')
        strategy_names = all_available_strategies
        print(f"🚀 Multi-Strategy Backtest Runner Started")
        print(f"   Strategies: {strategy_names}")
    elif args.strategies:
        strategy_names = args.strategies
        print(f"🚀 Multi-Strategy Backtest Runner Started")
        print(f"   Strategies: {strategy_names}")
    else:
        strategy_names = [args.strategy]
        print(f"🚀 Backtest Runner Started")
        print(f"   Strategy: {args.strategy}")

    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Symbols: {symbols}")
    print(f"   Initial Capital: ${args.capital:,.2f}")

    try:
        request = BacktestRequest(
            symbols=symbols,
            strategy_names=strategy_names,
            start_date=start_date,
            end_date=end_date,
            initial_capital=args.capital,
            fee_rate=args.fee,
            slippage_factor=args.slippage,
        )

        # Build the composition root and run through the use case, resolving the
        # data-access port from the container (E2.T2). Teardown is automatic.
        with lifespan() as container:
            use_case = RunBacktestUseCase(
                file_repository=container.resolve("file_repository"),
                backtester_factory=container.resolve("backtester_factory"),
                strategy_provider=container.resolve("backtest_strategy_provider"),
                csv_history_loader=container.resolve("csv_history_loader"),
            )
            results = use_case.execute(request)

            # Validate results if requested
            if args.validate:
                validation_results = use_case.validate_results(results)
                results['validation'] = validation_results

        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")

        # Check for backtest failures
        if results and 'summary' in results and 'failed_backtests' in results['summary']:
            failed_count = results['summary']['failed_backtests']
            if failed_count > 0:
                print(f"\n⚠️  Process completed with {failed_count} failed backtests")
                return min(failed_count, 1)  # Return 1 if any failed, but cap at 1
            else:
                print(f"\n🎉 All backtests completed successfully!")
                return 0
        else:
            print(f"\n⚠️  Process completed but results are incomplete or unavailable")
            return 1

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Backtest process failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
