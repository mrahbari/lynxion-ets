#!/usr/bin/env python3
"""
Comprehensive Hedge Fund System Runner - Execute the complete portfolio validation pipeline
including multi-symbol backtesting, strategy selection, capital allocation, risk management,
and Monte Carlo validation.
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
from utils.data_integrity_checker import DataIntegrityChecker


def load_symbols_from_env() -> List[str]:
    """Load symbols from environment variable."""
    symbols_str = os.getenv("WFO_COINS", "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,ADAUSDT")
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def generate_mock_data(symbol: str, days: int = 180) -> pd.DataFrame:
    """Generate mock price data for testing when real data is not available."""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')

    # Generate mock OHLCV data
    np.random.seed(hash(symbol) % 2**32)  # Different seed for each symbol
    returns = np.random.normal(0.0005, 0.02, days)  # Daily returns ~0.05% mean, 2% std
    closes = 40000 * np.exp(np.cumsum(returns))  # Starting at ~$40,000

    opens = closes * np.exp(np.random.normal(0, 0.001, days))
    highs = np.maximum(opens, closes) * (1 + np.abs(np.random.normal(0, 0.01, days)))
    lows = np.minimum(opens, closes) * (1 - np.abs(np.random.normal(0, 0.01, days)))

    volumes = np.random.lognormal(15, 1, days)  # Mock volume data

    df = pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)

    return df


def run_comprehensive_hedge_fund_validation(symbols: List[str],
                                         strategy_functions: Dict[str, callable],
                                         strategy_params: Dict[str, Dict] = None,
                                         start_date: datetime = None,
                                         end_date: datetime = None,
                                         initial_capital: float = 100000.0,
                                         fee_rate: float = 0.001,
                                         slippage_factor: float = 0.0005,
                                         min_success_rate: float = 0.7) -> Dict[str, Any]:
    """Run the complete hedge fund validation pipeline."""
    logger = EnhancedLogger("ComprehensiveHedgeFundValidation")

    print(f"🚀 Starting comprehensive hedge fund validation pipeline...")
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

    # Load data for all symbols
    data_loader = CSVHistoryLoaderAdapter()
    data_dict = {}

    # Check if mock data is allowed in validation
    use_mock_data = os.getenv('USE_MOCK_DATA_FOR_VALIDATION', 'false').lower() == 'true'

    for symbol in symbols:
        try:
            df = data_loader.load(symbol=symbol)

            if df.empty:
                if use_mock_data:
                    logger.warning(f"No real data found for {symbol}, generating mock data")
                    # Generate mock data for testing
                    df = generate_mock_data(symbol, days=(end_date - start_date).days)
                else:
                    logger.error(f"No real data found for {symbol}, and mock data is forbidden in production validation.")
                    raise RuntimeError(f"Real data not found for {symbol}, and mock data is forbidden in production validation.")
            else:
                # Convert timestamp column to datetime if it exists
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    # Filter data by date range using the timestamp column
                    df = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]
                    # Set timestamp as index for compatibility with the rest of the system
                    df = df.set_index('timestamp')
                else:
                    # If no timestamp column, try to use index as datetime
                    df.index = pd.to_datetime(df.index)
                    df = df[(df.index >= start_date) & (df.index <= end_date)]

            if len(df) < 10:
                if use_mock_data:
                    logger.warning(f"Insufficient data for {symbol} (only {len(df)} rows), generating mock data")
                    df = generate_mock_data(symbol, days=(end_date - start_date).days)
                else:
                    logger.error(f"Insufficient data for {symbol} (only {len(df)} rows), and mock data is forbidden in production validation.")
                    raise RuntimeError(f"Insufficient real data for {symbol}, and mock data is forbidden in production validation.")

            data_dict[symbol] = df
            logger.info(f"Using data for {symbol} ({len(df)} rows)")

        except Exception as e:
            if use_mock_data:
                logger.warning(f"Error loading data for {symbol}: {e}, generating mock data")
                # Generate mock data as fallback
                df = generate_mock_data(symbol, days=(end_date - start_date).days)
                data_dict[symbol] = df
                logger.info(f"Generated mock data for {symbol} ({len(df)} rows)")
            else:
                logger.error(f"Error loading data for {symbol}: {e}, and mock data is forbidden in production validation.")
                raise RuntimeError(f"Error loading data for {symbol}: {e}, and mock data is forbidden in production validation.")

    if not data_dict:
        logger.error("No data loaded for any symbols")
        return {"error": "No data available for validation"}

    print(f"   ✅ Loaded/Generated data for {len(data_dict)} symbols")

    # IMPLEMENT HARD DATA INTEGRITY VALIDATION GATE: Block backtesting if data quality is poor
    print(f"\n🔒 DATA INTEGRITY CHECK: Validating data quality before backtesting...")
    integrity_checker = DataIntegrityChecker()

    # Validate data quality for all symbols
    validation_results = integrity_checker.validate_multiple_symbols(
        data_dict,
        symbols,
        start_date,
        end_date,
        timeframe="1d",  # Assuming daily data based on the context
        max_missing_ratio=0.05  # Maximum 5% missing data allowed
    )

    # Check if any symbol failed validation
    failed_symbols = [symbol for symbol, is_valid in validation_results.items() if not is_valid]
    if failed_symbols:
        logger.error(f"Data integrity validation failed for symbols: {failed_symbols}")
        print(f"   ❌ Data integrity validation failed for {len(failed_symbols)} symbols: {failed_symbols}")
        print(f"   🚫 BLOCKING backtest execution due to poor data quality")
        raise RuntimeError(f"Data integrity validation failed for symbols: {failed_symbols}. Backtest blocked due to poor data quality.")

    print(f"   ✅ All {len(symbols)} symbols passed data integrity validation")
    print(f"   📊 Data quality check completed - Ready for backtesting")

    # Phase 1: Run comprehensive portfolio backtest
    print(f"\n🔍 PHASE 1: Running comprehensive portfolio backtest...")
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
        return portfolio_backtest_results

    print(f"   ✅ Portfolio backtest completed")
    print(f"      Total Strategies: {portfolio_backtest_results['summary']['total_strategies']}")
    print(f"      Accepted Strategies: {portfolio_backtest_results['summary']['accepted_strategies_count']}")
    print(f"      Data Symbols: {portfolio_backtest_results['summary']['data_symbols_count']}")

    # Phase 2: Create capital allocator
    print(f"\n💰 PHASE 2: Creating capital allocator...")
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
        
        # Print top allocations
        sorted_allocations = sorted(allocations.items(), key=lambda x: x[1], reverse=True)
        print(f"      Top 5 Allocations:")
        for i, (strategy, alloc) in enumerate(sorted_allocations[:5]):
            print(f"        {i+1}. {strategy}: ${alloc:,.2f} ({alloc/initial_capital:.2%})")
    else:
        print(f"   ⚠️  Failed to create capital allocator")
        allocations = {}

    # Phase 3: Run Monte Carlo risk simulation
    print(f"\n🎲 PHASE 3: Running Monte Carlo risk simulation...")
    monte_carlo_results = run_monte_carlo_analysis_from_backtest_results(portfolio_backtest_results)
    
    if 'error' not in monte_carlo_results:
        print(f"   ✅ Monte Carlo simulation completed")
        # Check the structure of the results
        risk_metrics = {}
        if 'combined_analysis' in monte_carlo_results:
            if 'monte_carlo_results' in monte_carlo_results['combined_analysis']:
                risk_metrics = monte_carlo_results['combined_analysis']['monte_carlo_results'].get('risk_metrics', {})
            elif 'risk_metrics' in monte_carlo_results['combined_analysis']:
                risk_metrics = monte_carlo_results['combined_analysis']['risk_metrics']
        elif 'risk_metrics' in monte_carlo_results:
            risk_metrics = monte_carlo_results['risk_metrics']

        print(f"      Probability of Ruin: {risk_metrics.get('probability_of_ruin', 0):.2%}")
        print(f"      Worst Case Drawdown: {risk_metrics.get('worst_case_drawdown', 0):.2%}")
        print(f"      Value at Risk: {risk_metrics.get('value_at_risk', 0):.2%}")
    else:
        print(f"   ⚠️  Monte Carlo simulation failed: {monte_carlo_results['error']}")
        monte_carlo_results = {}

    # Phase 4: Create strategy kill-switch engine
    print(f"\n⚡ PHASE 4: Creating strategy kill-switch engine...")
    kill_switch_engine = create_kill_switch_from_backtest_results(portfolio_backtest_results)
    
    if kill_switch_engine:
        print(f"   ✅ Created kill-switch engine with {len(kill_switch_engine.strategy_states)} strategies")
        
        # Get health report
        health_report = kill_switch_engine.get_strategy_health_report()
        active_strategies = kill_switch_engine.get_active_strategies()
        disabled_strategies = kill_switch_engine.get_disabled_strategies()
        
        print(f"      Active Strategies: {len(active_strategies)}")
        print(f"      Disabled Strategies: {len(disabled_strategies)}")
        
        # Print recommendations
        recommendations = kill_switch_engine.get_kill_switch_recommendations()
        if recommendations:
            print(f"      Recommendations: {len(recommendations)}")
            for rec in recommendations[:3]:  # Show first 3
                print(f"        - {rec['strategy']}: {rec['action']} ({rec['reason'][:50]}...)")
    else:
        print(f"   ⚠️  Failed to create kill-switch engine")
        kill_switch_engine = None

    # Phase 5: Run portfolio walk-forward validation
    print(f"\n📊 PHASE 5: Running portfolio walk-forward validation...")
    walk_forward_results = run_portfolio_walk_forward_validation_from_backtest_results(
        portfolio_backtest_results,
        data_dict,
        strategy_functions,
        strategy_params
    )
    
    if 'error' not in walk_forward_results:
        print(f"   ✅ Walk-forward validation completed")
        wf_metrics = walk_forward_results.get('validation_metrics', {})
        success_rate = walk_forward_results.get('success_rate', 0)
        print(f"      Success Rate: {success_rate:.2%}")
        print(f"      Avg Return: {wf_metrics.get('avg_total_return', 0):.2%}")
        print(f"      Avg Sharpe: {wf_metrics.get('avg_sharpe_ratio', 0):.3f}")
    else:
        print(f"   ⚠️  Walk-forward validation failed: {walk_forward_results['error']}")
        walk_forward_results = {}

    # Compile final results
    final_results = {
        'pipeline_start_time': start_time.isoformat(),
        'pipeline_end_time': datetime.now().isoformat(),
        'duration_seconds': (datetime.now() - start_time).total_seconds(),
        'portfolio_backtest_results': portfolio_backtest_results,
        'capital_allocation_results': {
            'allocations': allocations,
            'allocator_summary': capital_allocator.get_allocation_summary() if capital_allocator else {}
        } if capital_allocator else {},
        'monte_carlo_results': monte_carlo_results,
        'kill_switch_results': {
            'health_report': health_report if kill_switch_engine else {},
            'active_strategies': active_strategies if kill_switch_engine else [],
            'disabled_strategies': disabled_strategies if kill_switch_engine else [],
            'recommendations': recommendations if kill_switch_engine else []
        } if kill_switch_engine else {},
        'walk_forward_results': walk_forward_results,
        'validation_summary': {
            'total_strategies': portfolio_backtest_results['summary']['total_strategies'],
            'accepted_strategies': portfolio_backtest_results['summary']['accepted_strategies_count'],
            'data_symbols': portfolio_backtest_results['summary']['data_symbols_count'],
            'monte_carlo_success': 'error' not in monte_carlo_results,
            'walk_forward_success': 'error' not in walk_forward_results,
            'capital_allocator_created': capital_allocator is not None,
            'kill_switch_created': kill_switch_engine is not None
        }
    }

    # Print final summary
    print(f"\n🏆 COMPREHENSIVE VALIDATION SUMMARY")
    print(f"   Pipeline Duration: {final_results['duration_seconds']:.2f}s")
    print(f"   Total Strategies: {final_results['validation_summary']['total_strategies']}")
    print(f"   Accepted Strategies: {final_results['validation_summary']['accepted_strategies']}")
    print(f"   Data Symbols: {final_results['validation_summary']['data_symbols']}")
    print(f"   Monte Carlo Success: {'✅' if final_results['validation_summary']['monte_carlo_success'] else '❌'}")
    print(f"   Walk-Forward Success: {'✅' if final_results['validation_summary']['walk_forward_success'] else '❌'}")
    print(f"   Capital Allocator: {'✅' if final_results['validation_summary']['capital_allocator_created'] else '❌'}")
    print(f"   Kill Switch: {'✅' if final_results['validation_summary']['kill_switch_created'] else '❌'}")

    # Print top performing strategies
    if 'strategy_rankings' in portfolio_backtest_results:
        top_strategies = portfolio_backtest_results['strategy_rankings'][:5]
        print(f"\n🥇 TOP 5 PERFORMING STRATEGIES:")
        for i, strategy in enumerate(top_strategies, 1):
            status = "✅" if strategy['acceptance_status'] == 'accepted' else "❌"
            print(f"   {i}. {strategy['strategy']:<20} "
                  f"Return: {strategy['avg_return']:.2%}, "
                  f"Sharpe: {strategy['avg_sharpe']:.3f}, "
                  f"Status: {status}")

    return final_results


def main():
    """Main entry point for the comprehensive hedge fund validation runner."""
    parser = argparse.ArgumentParser(
        description='Run comprehensive hedge fund validation pipeline',
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

    print(f"🚀 Comprehensive Hedge Fund Validation Pipeline Started")
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Symbols: {symbols}")
    print(f"   Initial Capital: ${args.capital:,.2f}")
    print(f"   Min Success Rate: {args.min_success_rate:.1%}")

    # Load strategy functions
    strategy_functions = load_sample_strategies()
    print(f"   Loaded {len(strategy_functions)} strategies")

    try:
        # Run comprehensive validation pipeline
        results = run_comprehensive_hedge_fund_validation(
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

        # Check for pipeline failures
        if 'error' in results:
            print(f"\n❌ Validation pipeline failed")
            return 1
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