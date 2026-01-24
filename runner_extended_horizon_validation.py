#!/usr/bin/env python3
"""
Extended Horizon Validation Runner - Execute long-term backtesting across multiple horizons
(180, 360, 720 days) to test alpha durability and regime stability.
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
from infrastructure.portfolio.capital_allocator import create_capital_allocator_from_backtest_results
from infrastructure.risk.monte_carlo_simulator import run_monte_carlo_analysis_from_backtest_results
from infrastructure.risk.strategy_kill_switch import create_kill_switch_from_backtest_results
from infrastructure.backtest.portfolio_walk_forward_validator import run_portfolio_walk_forward_validation_from_backtest_results
from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
from shared.logger import EnhancedLogger


def load_symbols_from_env() -> List[str]:
    """Load symbols from environment variable."""
    symbols_str = os.getenv("WFO_COINS", "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,ADAUSDT")
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def run_extended_horizon_validation(horizons: List[int],
                                 symbols: List[str],
                                 strategy_functions: Dict[str, callable],
                                 strategy_params: Dict[str, Dict] = None,
                                 initial_capital: float = 100000.0,
                                 fee_rate: float = 0.001,
                                 slippage_factor: float = 0.0005,
                                 min_success_rate: float = 0.7) -> Dict[str, Any]:
    """Run extended horizon validation across multiple time periods."""
    logger = EnhancedLogger("ExtendedHorizonValidation")

    print(f"🚀 Starting extended horizon validation...")
    print(f"   Horizons: {horizons} days")
    print(f"   Symbols: {symbols}")
    print(f"   Strategies: {list(strategy_functions.keys())}")
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

    # Results storage for each horizon
    horizon_results = {}

    for horizon in horizons:
        print(f"\n🔍 HORIZON {horizon} DAYS:")
        print(f"   Calculating date range...")

        # Calculate date range for this horizon
        end_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        start_date = end_date - timedelta(days=horizon)

        print(f"   Date Range: {start_date.date()} to {end_date.date()}")

        # Check if mock data is allowed in validation
        use_mock_data = os.getenv('USE_MOCK_DATA_FOR_VALIDATION', 'false').lower() == 'true'

        # Load data for all symbols
        data_loader = CSVHistoryLoaderAdapter()
        data_dict = {}

        for symbol in symbols:
            try:
                df = data_loader.load(symbol=symbol)

                if df.empty:
                    if use_mock_data:
                        logger.warning(f"No real data found for {symbol}, generating mock data")
                        # Generate mock data for testing
                        df = backtester.generate_mock_data(symbol, start_date, end_date)
                    else:
                        logger.error(f"No real data found for {symbol}, and mock data is forbidden in production validation.")
                        raise RuntimeError(f"Real data not found for {symbol}, and mock data is forbidden in production validation.")
                else:
                    # Check if timestamp column exists (returned by CSV loader)
                    if 'timestamp' in df.columns:
                        # Convert timestamp column to datetime if it exists
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)

                        # Convert start_date and end_date to timezone-aware if they aren't already
                        from datetime import timezone
                        if start_date.tzinfo is None:
                            start_date = start_date.replace(tzinfo=timezone.utc)
                        if end_date.tzinfo is None:
                            end_date = end_date.replace(tzinfo=timezone.utc)


                        # Filter data by date range using the timestamp column
                        df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
                        # Set timestamp as index for compatibility with the rest of the system
                        df = df.set_index('timestamp')
                    else:
                        # If no timestamp column, try to use index as datetime
                        df.index = pd.to_datetime(df.index)

                        # Convert start_date and end_date to timezone-aware if they aren't already
                        from datetime import timezone
                        if start_date.tzinfo is None:
                            start_date = start_date.replace(tzinfo=timezone.utc)
                        if end_date.tzinfo is None:
                            end_date = end_date.replace(tzinfo=timezone.utc)


                        # Filter data by date range
                        df = df[(df.index >= start_date) & (df.index <= end_date)]

                if len(df) < 10:
                    if use_mock_data:
                        logger.warning(f"Insufficient data for {symbol} (only {len(df)} rows), generating mock data")
                        df = backtester.generate_mock_data(symbol, start_date, end_date)
                    else:
                        logger.error(f"Insufficient data for {symbol} (only {len(df)} rows), and mock data is forbidden in production validation.")
                        raise RuntimeError(f"Insufficient real data for {symbol}, and mock data is forbidden in production validation.")

                data_dict[symbol] = df
                logger.info(f"Using data for {symbol} ({len(df)} rows) for {horizon}-day horizon")

            except Exception as e:
                if use_mock_data:
                    logger.warning(f"Error loading data for {symbol}: {e}, generating mock data")
                    # Generate mock data as fallback
                    df = backtester.generate_mock_data(symbol, start_date, end_date)
                    data_dict[symbol] = df
                    logger.info(f"Generated mock data for {symbol} ({len(df)} rows) for {horizon}-day horizon")
                else:
                    logger.error(f"Error loading data for {symbol}: {e}, and mock data is forbidden in production validation.")
                    raise RuntimeError(f"Error loading data for {symbol}: {e}, and mock data is forbidden in production validation.")

        if not data_dict:
            logger.error(f"No data loaded for any symbols in {horizon}-day horizon")
            horizon_results[horizon] = {"error": f"No data available for {horizon}-day horizon validation"}
            continue

        print(f"   ✅ Loaded/Generated data for {len(data_dict)} symbols")

        # Run comprehensive portfolio backtest for this horizon
        print(f"   Running comprehensive portfolio backtest...")
        portfolio_backtest_results = backtester.run_comprehensive_backtest(
            symbols=list(data_dict.keys()),
            strategy_functions=strategy_functions,
            strategy_params=strategy_params,
            start_date=start_date,
            end_date=end_date,
            min_success_rate=min_success_rate
        )

        if 'error' in portfolio_backtest_results:
            print(f"   ❌ Portfolio backtest failed: {portfolio_backtest_results['error']}")
            horizon_results[horizon] = portfolio_backtest_results
            continue

        print(f"   ✅ Portfolio backtest completed")
        print(f"      Total Strategies: {portfolio_backtest_results['summary']['total_strategies']}")
        print(f"      Accepted Strategies: {portfolio_backtest_results['summary']['accepted_strategies_count']}")
        print(f"      Data Symbols: {portfolio_backtest_results['summary']['data_symbols_count']}")

        # Create capital allocator
        print(f"   Creating capital allocator...")
        capital_allocator = create_capital_allocator_from_backtest_results(
            portfolio_backtest_results,
            total_capital=initial_capital
        )

        if capital_allocator:
            allocations = capital_allocator.calculate_allocations(
                strategy_names=portfolio_backtest_results['accepted_strategies'],
                correlation_matrix=pd.DataFrame(portfolio_backtest_results['correlation_matrix']) if portfolio_backtest_results['correlation_matrix'] else None
            )
            print(f"   ✅ Created capital allocator with {len(allocations)} strategy allocations")
        else:
            print(f"   ⚠️  Failed to create capital allocator")
            allocations = {}

        # Run Monte Carlo risk simulation
        print(f"   Running Monte Carlo risk simulation...")
        monte_carlo_results = run_monte_carlo_analysis_from_backtest_results(portfolio_backtest_results)

        if 'error' not in monte_carlo_results:
            print(f"   ✅ Monte Carlo simulation completed")
        else:
            print(f"   ⚠️  Monte Carlo simulation failed: {monte_carlo_results['error']}")
            monte_carlo_results = {}

        # Create strategy kill-switch engine
        print(f"   Creating strategy kill-switch engine...")
        kill_switch_engine = create_kill_switch_from_backtest_results(portfolio_backtest_results)

        if kill_switch_engine:
            print(f"   ✅ Created kill-switch engine with {len(kill_switch_engine.strategy_states)} strategies")
        else:
            print(f"   ⚠️  Failed to create kill-switch engine")
            kill_switch_engine = None

        # Run portfolio walk-forward validation
        print(f"   Running portfolio walk-forward validation...")
        walk_forward_results = run_portfolio_walk_forward_validation_from_backtest_results(
            portfolio_backtest_results,
            data_dict,
            strategy_functions,
            strategy_params
        )

        if 'error' not in walk_forward_results:
            print(f"   ✅ Walk-forward validation completed")
        else:
            print(f"   ⚠️  Walk-forward validation failed: {walk_forward_results['error']}")
            walk_forward_results = {}

        # Store results for this horizon
        horizon_results[horizon] = {
            'portfolio_backtest_results': portfolio_backtest_results,
            'capital_allocation_results': {
                'allocations': allocations,
                'allocator_summary': capital_allocator.get_allocation_summary() if capital_allocator else {}
            } if capital_allocator else {},
            'monte_carlo_results': monte_carlo_results,
            'kill_switch_results': {
                'health_report': kill_switch_engine.get_strategy_health_report() if kill_switch_engine else {},
                'active_strategies': kill_switch_engine.get_active_strategies() if kill_switch_engine else [],
                'disabled_strategies': kill_switch_engine.get_disabled_strategies() if kill_switch_engine else [],
                'recommendations': kill_switch_engine.get_kill_switch_recommendations() if kill_switch_engine else []
            } if kill_switch_engine else {},
            'walk_forward_results': walk_forward_results,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': horizon
            }
        }

        # Print top performing strategies for this horizon
        if 'strategy_rankings' in portfolio_backtest_results:
            top_strategies = portfolio_backtest_results['strategy_rankings'][:5]
            print(f"   🥇 TOP 5 PERFORMING STRATEGIES FOR {horizon}D HORIZON:")
            for i, strategy in enumerate(top_strategies, 1):
                status = "✅" if strategy['acceptance_status'] == 'accepted' else "❌"
                print(f"      {i}. {strategy['strategy']:<20} "
                      f"Return: {strategy['avg_return']:.2%}, "
                      f"Sharpe: {strategy['avg_sharpe']:.3f}, "
                      f"Status: {status}")

    # Compile final results
    final_results = {
        'pipeline_start_time': start_time.isoformat(),
        'pipeline_end_time': datetime.now().isoformat(),
        'duration_seconds': (datetime.now() - start_time).total_seconds(),
        'horizon_results': horizon_results,
        'horizons_tested': horizons,
        'symbols': symbols,
        'strategy_functions': list(strategy_functions.keys()),
        'summary': {
            'total_horizons': len(horizons),
            'successful_horizons': len([h for h, r in horizon_results.items() if 'error' not in r]),
            'failed_horizons': len([h for h, r in horizon_results.items() if 'error' in r])
        }
    }

    # Print final summary
    print(f"\n🏆 EXTENDED HORIZON VALIDATION SUMMARY")
    print(f"   Pipeline Duration: {final_results['duration_seconds']:.2f}s")
    print(f"   Total Horizons: {final_results['summary']['total_horizons']}")
    print(f"   Successful Horizons: {final_results['summary']['successful_horizons']}")
    print(f"   Failed Horizons: {final_results['summary']['failed_horizons']}")

    # Print performance decay analysis
    print(f"\n📉 PERFORMANCE DECAY ANALYSIS")
    for horizon in sorted(horizons):
        if horizon in horizon_results and 'error' not in horizon_results[horizon]:
            results = horizon_results[horizon]['portfolio_backtest_results']
            avg_return = np.mean([s['avg_return'] for s in results['strategy_rankings'] if s['acceptance_status'] == 'accepted']) if results['strategy_rankings'] else 0
            avg_sharpe = np.mean([s['avg_sharpe'] for s in results['strategy_rankings'] if s['acceptance_status'] == 'accepted']) if results['strategy_rankings'] else 0
            accepted_count = results['summary']['accepted_strategies_count']
            
            print(f"   {horizon}D: Return={avg_return:.2%}, Sharpe={avg_sharpe:.3f}, Accepted={accepted_count}")

    return final_results


def main():
    """Main entry point for the extended horizon validation runner."""
    parser = argparse.ArgumentParser(
        description='Run extended horizon validation across multiple time periods',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --horizons 180 360 720 --symbols BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT ADAUSDT
  %(prog)s --horizons 180 360 --capital 50000 --min-success-rate 0.6
        """
    )

    parser.add_argument('--horizons', nargs='+', type=int, required=True,
                       help='Horizon lengths in days (e.g., 180 360 720)')

    parser.add_argument('--symbols', nargs='+', type=str,
                       help='Specific symbols to validate (default: from WFO_COINS env var)')

    parser.add_argument('--capital', type=float, default=100000.0,
                       help='Initial capital for validation (default: 100000.0)')

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

    # Get symbols
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = load_symbols_from_env()

    print(f"🚀 Extended Horizon Validation Pipeline Started")
    print(f"   Horizons: {args.horizons} days")
    print(f"   Symbols: {symbols}")
    print(f"   Initial Capital: ${args.capital:,.2f}")
    print(f"   Min Success Rate: {args.min_success_rate:.1%}")

    # Load strategy functions
    strategy_functions = load_sample_strategies()
    print(f"   Loaded {len(strategy_functions)} strategies")

    try:
        # Run extended horizon validation pipeline
        results = run_extended_horizon_validation(
            horizons=args.horizons,
            symbols=symbols,
            strategy_functions=strategy_functions,
            strategy_params=None,  # Will use default parameters
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

        # Check for pipeline failures
        if any('error' in r for r in results['horizon_results'].values()):
            print(f"\n⚠️  Validation pipeline completed with some failures")
            return 0  # Return 0 to indicate partial success
        else:
            print(f"\n🎉 Validation pipeline completed successfully!")
            return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Validation pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())