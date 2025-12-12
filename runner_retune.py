#!/usr/bin/env python3
"""
Retune Runner - Automated hyperparameter retuning for trading strategies.

This script automates the process of retuning trading strategies by:
1. Loading historical data
2. Running hyperparameter optimization
3. Validating results
4. Updating parameters for production use
"""
import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.configurable_hyperopt import ConfigurableHyperoptOptimizer
from infrastructure.optimization.hyperopt_space import HyperoptParameterSpace
from application.data_sync.watcher_retune import WatcherRetuneUseCase
from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
from infrastructure.backtest.realistic_backtester import RealisticBacktester
from shared.logger import EnhancedLogger


def load_symbols_from_env() -> List[str]:
    """Load symbols from environment variable."""
    symbols_str = os.getenv("WFO_COINS", "BTCUSDT,ETHUSDT")
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def run_retune_process(
        symbols: List[str],
        strategy_name: str = "crypto_breakout",
        max_evals: int = 50,
        days_back: int = 90
) -> Dict[str, Any]:
    """Run the retune process for specified symbols and strategy."""
    logger = EnhancedLogger(f"RetuneRunner_{strategy_name}")

    print(f"🔄 Starting retune process for strategy: {strategy_name}")
    print(f"   Symbols: {symbols}")
    print(f"   Max evaluations per symbol: {max_evals}")
    print(f"   Data window: {days_back} days")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = datetime.now()
    results = {
        'strategy': strategy_name,
        'symbols_processed': [],
        'successful_optimizations': 0,
        'failed_optimizations': 0,
        'results': {}
    }

    # Initialize hyperopt components
    config = {
        'strategy_name': strategy_name,
        'risk_config': {
            'initial_capital': float(os.getenv('INITIAL_CAPITAL', '100000')),
            'fee_rate': float(os.getenv('FEE_RATE', '0.001')),
            'slippage_factor': float(os.getenv('SLIPPAGE_FACTOR', '0.0005'))
        }
    }

    from shared.configurable_hyperopt import HyperoptConfig
    hyperopt_config_obj = HyperoptConfig(strategy_name=strategy_name)
    optimizer = ConfigurableHyperoptOptimizer(hyperopt_config=hyperopt_config_obj, strategy_name=strategy_name)
    param_space_handler = HyperoptParameterSpace()

    for symbol in symbols:
        print(f"\n🔍 Optimizing {strategy_name} for {symbol}...")

        try:
            # Load data for the symbol
            data_loader = None  # Would need proper data loading implementation
            # For now, we'll create sample data or use existing loaders
            from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
            data_loader = CSVHistoryLoaderAdapter()

            try:
                df = data_loader.load(symbol=symbol)
                if df.empty:
                    print(f"   ⚠️  No data found for {symbol}, skipping...")
                    continue
            except Exception as e:
                print(f"   ❌ Error loading data for {symbol}: {e}")
                continue

            # Use only the last N days of data
            if days_back > 0:
                cutoff_date = datetime.now() - timedelta(days=days_back)
                df = df[df.index >= cutoff_date]

            if len(df) < 20:  # Need minimum data for optimization
                print(f"   ⚠️  Insufficient data for {symbol} (only {len(df)} rows), skipping...")
                continue

            # Get parameter space for this strategy
            param_space = param_space_handler.get_space(strategy_name)

            # Run optimization
            optimization_result = optimizer.optimize_with_config(
                strategy_name=strategy_name,
                data=df,
                symbol=symbol,
                custom_config={
                    "max_evals": max_evals,
                    "parameter_space": param_space
                }
            )

            if 'best_params' in optimization_result:
                results['results'][symbol] = {
                    'status': 'success',
                    'best_params': optimization_result['best_params'],
                    'best_value': optimization_result.get('best_value', -float('inf')),
                    'trials_completed': optimization_result.get('trials_completed', 0),
                    'timestamp': datetime.now().isoformat()
                }
                results['successful_optimizations'] += 1
                print(f"   ✅ {symbol} optimization completed")
                print(f"      Best value: {optimization_result.get('best_value', 'N/A')}")
            else:
                results['results'][symbol] = {
                    'status': 'failed',
                    'error': 'No best params found',
                    'timestamp': datetime.now().isoformat()
                }
                results['failed_optimizations'] += 1
                print(f"   ❌ {symbol} optimization failed")

        except Exception as e:
            print(f"   ❌ Error during optimization for {symbol}: {e}")
            results['results'][symbol] = {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            results['failed_optimizations'] += 1

    results['symbols_processed'] = symbols
    results['total_processed'] = len(symbols)
    results['end_time'] = datetime.now().isoformat()
    results['duration_seconds'] = (datetime.now() - start_time).total_seconds()

    # Print summary
    print(f"\n📊 RETUNE PROCESS SUMMARY")
    print(f"   Strategy: {strategy_name}")
    print(f"   Symbols processed: {results['total_processed']}")
    print(f"   Successful: {results['successful_optimizations']}")
    print(f"   Failed: {results['failed_optimizations']}")
    print(f"   Duration: {results['duration_seconds']:.2f}s")

    return results


def validate_retune_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the results of the retune process."""
    print(f"\n✅ Validating retune results...")

    validation_results = {
        'valid': 0,
        'invalid': 0,
        'total': results['total_processed'],
        'validation_details': {}
    }

    for symbol, result in results['results'].items():
        if result['status'] == 'success':
            # Basic validation checks
            is_valid = True
            issues = []

            if 'best_params' not in result or not result['best_params']:
                is_valid = False
                issues.append("No best_params found")

            if result.get('best_value', -float('inf')) == -float('inf'):
                is_valid = False
                issues.append("No best_value found")

            validation_results['validation_details'][symbol] = {
                'valid': is_valid,
                'issues': issues
            }

            if is_valid:
                validation_results['valid'] += 1
            else:
                validation_results['invalid'] += 1
        else:
            validation_results['validation_details'][symbol] = {
                'valid': False,
                'issues': [result.get('error', 'Unknown error')]
            }
            validation_results['invalid'] += 1

    print(f"   Valid results: {validation_results['valid']}")
    print(f"   Invalid results: {validation_results['invalid']}")

    return validation_results


def main():
    """Main entry point for the retune runner."""
    parser = argparse.ArgumentParser(
        description='Automated hyperparameter retuning for trading strategies',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                         # Retune all strategies for all symbols
  %(prog)s --strategy crypto_breakout    # Retune specific strategy for all symbols
  %(prog)s --symbols BTCUSDT ETHUSDT     # Retune all strategies for specific symbols
  %(prog)s --strategy crypto_breakout --symbols BTCUSDT --evals 100 --days 60
        """
    )

    parser.add_argument('--strategy', type=str,
                        default='crypto_breakout',
                        help='Strategy name to retune (default: crypto_breakout)')

    parser.add_argument('--symbols', nargs='+', type=str,
                        help='Specific symbols to retune (default: from WFO_COINS env var)')

    parser.add_argument('--evals', type=int, default=50,
                        help='Maximum number of hyperopt evaluations per symbol (default: 50)')

    parser.add_argument('--days', type=int, default=90,
                        help='Number of days of historical data to use (default: 90)')

    parser.add_argument('--output', type=str,
                        help='Output file to save results (JSON format)')

    parser.add_argument('--validate', action='store_true',
                        help='Validate results after retuning')

    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')

    args = parser.parse_args()

    # Get symbols
    if args.symbols:
        symbols = args.symbols
    else:
        symbols = load_symbols_from_env()

    print(f"🚀 Retune Runner Started")
    print(f"   Strategy: {args.strategy}")
    print(f"   Symbols: {symbols}")
    print(f"   Max evals: {args.evals}")
    print(f"   Days back: {args.days}")

    try:
        # Run retune process
        results = run_retune_process(
            symbols=symbols,
            strategy_name=args.strategy,
            max_evals=args.evals,
            days_back=args.days
        )

        # Validate results if requested
        if args.validate:
            validation_results = validate_retune_results(results)
            results['validation'] = validation_results

        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")

        # Exit with appropriate code
        failed_count = results['failed_optimizations']
        if failed_count > 0:
            print(f"\n⚠️  Process completed with {failed_count} failed optimizations")
            return min(failed_count, 1)  # Return 1 if any failed, but cap at 1
        else:
            print(f"\n🎉 All optimizations completed successfully!")
            return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Retune process failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
