#!/usr/bin/env python3
"""
Comprehensive Portfolio Backtest Runner - Execute advanced multi-strategy, multi-symbol backtesting
with portfolio-level risk management and strategy selection.
"""
import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
import numpy as np

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.portfolio.comprehensive_portfolio_backtester import ComprehensivePortfolioBacktester, load_sample_strategies
from shared.logger import EnhancedLogger


def load_symbols_from_env() -> List[str]:
    """Load symbols from environment variable."""
    symbols_str = os.getenv("WFO_COINS", "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,ADAUSDT")
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def run_comprehensive_portfolio_backtest(symbols: List[str],
                                       strategy_functions: Dict[str, callable],
                                       strategy_params: Dict[str, Dict] = None,
                                       start_date: datetime = None,
                                       end_date: datetime = None,
                                       initial_capital: float = 100000.0,
                                       fee_rate: float = 0.001,
                                       slippage_factor: float = 0.0005,
                                       min_success_rate: float = 0.7) -> Dict[str, Any]:
    """Run the comprehensive portfolio backtest process."""
    logger = EnhancedLogger("ComprehensivePortfolioBacktestRunner")

    print(f"🔄 Starting comprehensive portfolio backtest...")
    print(f"   Symbols: {symbols}")
    print(f"   Strategies: {list(strategy_functions.keys())}")
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Initial Capital: ${initial_capital:,.2f}")
    print(f"   Fee Rate: {fee_rate:.3%}")
    print(f"   Slippage Factor: {slippage_factor:.3%}")
    print(f"   Min Success Rate: {min_success_rate:.1%}")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = datetime.now()

    # Initialize comprehensive portfolio backtester
    backtester = ComprehensivePortfolioBacktester(
        initial_capital=initial_capital,
        fee_rate=fee_rate,
        slippage_factor=slippage_factor
    )

    try:
        # Run comprehensive backtest
        results = backtester.run_comprehensive_backtest(
            symbols=symbols,
            strategy_functions=strategy_functions,
            strategy_params=strategy_params,
            start_date=start_date,
            end_date=end_date,
            min_success_rate=min_success_rate
        )

        if 'error' not in results:
            print(f"   ✅ Comprehensive backtest completed successfully")

            # Print summary
            summary = results['summary']
            print(f"\n📊 PORTFOLIO BACKTEST SUMMARY")
            print(f"   Total Strategies: {summary['total_strategies']}")
            print(f"   Accepted Strategies: {summary['accepted_strategies_count']}")
            print(f"   Rejected Strategies: {summary['rejected_strategies_count']}")
            print(f"   Total Symbols: {summary['total_symbols']}")
            print(f"   Data Available: {summary['data_symbols_count']}")

            # Print strategy rankings
            print(f"\n🏆 STRATEGY RANKINGS (by Return)")
            for i, ranking in enumerate(results['strategy_rankings'][:10], 1):  # Top 10
                status = "✅" if ranking['acceptance_status'] == 'accepted' else "❌"
                print(f"   {i}. {ranking['strategy']:<20} "
                      f"Return: {ranking['avg_return']:.2%}, "
                      f"Sharpe: {ranking['avg_sharpe']:.2f}, "
                      f"Status: {status}")

            # Print accepted strategies with weights
            print(f"\n💰 ACCEPTED STRATEGIES WITH CAPITAL ALLOCATION")
            for strategy_name in results['accepted_strategies']:
                weight = results['capital_weights'].get(strategy_name, 0)
                metrics = results['admission_metrics'][strategy_name]
                print(f"   • {strategy_name:<20} "
                      f"Weight: {weight:.2%}, "
                      f"Return: {metrics['avg_return']:.2%}, "
                      f"Sharpe: {metrics['avg_sharpe']:.2f}")

        else:
            print(f"   ❌ Comprehensive backtest failed: {results['error']}")

    except Exception as e:
        print(f"   ❌ Error during comprehensive portfolio backtest: {e}")
        import traceback
        traceback.print_exc()
        results = {"error": str(e)}

    # Add end time and duration
    end_time = datetime.now()
    results['end_time'] = end_time.isoformat()
    results['duration_seconds'] = (end_time - start_time).total_seconds()

    # Print final summary
    print(f"\n⏱️  PROCESSING TIME: {results['duration_seconds']:.2f}s")

    return results


def main():
    """Main entry point for the comprehensive portfolio backtest runner."""
    parser = argparse.ArgumentParser(
        description='Run comprehensive portfolio backtesting for multiple strategies and symbols',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --start 360d --end today --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT ADAUSDT
  %(prog)s --start 2023-01-01 --end 2023-12-31 --capital 50000 --min-success-rate 0.6
        """
    )

    parser.add_argument('--start', type=str, required=True,
                       help='Start date in YYYY-MM-DD format or relative (e.g., "30d", "90d")')

    parser.add_argument('--end', type=str, default='today',
                       help='End date in YYYY-MM-DD format or "today" (default: today)')

    parser.add_argument('--symbols', nargs='+', type=str,
                       help='Specific symbols to backtest (default: from WFO_COINS env var)')

    parser.add_argument('--capital', type=float, default=100000.0,
                       help='Initial capital for backtest (default: 100000.0)')

    parser.add_argument('--fee', type=float, default=0.001,
                       help='Fee rate per trade (default: 0.001 = 0.1%%)')

    parser.add_argument('--slippage', type=float, default=0.0005,
                       help='Slippage factor (default: 0.0005 = 0.05%%)')

    parser.add_argument('--min-success-rate', type=float, default=0.7,
                       help='Minimum success rate for strategy acceptance (default: 0.7 = 70%%)')

    parser.add_argument('--output', type=str,
                       help='Output file to save results (JSON format)')

    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')

    args = parser.parse_args()

    # Parse dates
    def parse_date(date_str: str) -> datetime:
        if date_str == 'today':
            return datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        elif date_str.endswith('d'):
            days = int(date_str[:-1])
            return datetime.now() - timedelta(days=days)
        else:
            return datetime.strptime(date_str, '%Y-%m-%d')

    start_date = parse_date(args.start)
    end_date = parse_date(args.end)

    # Get symbols
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = load_symbols_from_env()

    print(f"🚀 Comprehensive Portfolio Backtest Runner Started")
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Symbols: {symbols}")
    print(f"   Initial Capital: ${args.capital:,.2f}")
    print(f"   Min Success Rate: {args.min_success_rate:.1%}")

    # Load strategy functions
    strategy_functions = load_sample_strategies()
    print(f"   Loaded {len(strategy_functions)} strategies")

    try:
        # Run comprehensive portfolio backtest
        results = run_comprehensive_portfolio_backtest(
            symbols=symbols,
            strategy_functions=strategy_functions,
            start_date=start_date,
            end_date=end_date,
            initial_capital=args.capital,
            fee_rate=args.fee,
            slippage_factor=args.slippage,
            min_success_rate=args.min_success_rate
        )

        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")

        # Check for backtest failures
        if 'error' in results:
            print(f"\n❌ Portfolio backtest process failed")
            return 1
        else:
            print(f"\n🎉 Portfolio backtest completed successfully!")
            return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Portfolio backtest process failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())