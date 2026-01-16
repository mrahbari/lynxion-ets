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
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

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


async def download_1d_data_for_symbols(symbols: List[str], days_back: int = 180):
    """Download 1-day timeframe data for specified symbols."""
    from application.data_sync.sync_manager import SyncManager
    from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
    from infrastructure.data_sync.data_downloader_adapter import DataDownloaderAdapter

    print(f"   Downloading 1-day data for {len(symbols)} symbols...")

    # Create components for data download
    file_repo = FileRepositoryAdapter()
    data_downloader = DataDownloaderAdapter()
    sync_manager = SyncManager(file_repo, data_downloader)

    # Use context manager for proper resource cleanup
    async with data_downloader:
        start_time = datetime.now()

        # Calculate date range
        end_time = datetime.now()
        start_time_data = end_time - timedelta(days=days_back)

        for symbol in symbols:
            # Convert format if needed (e.g., BTCUSDT -> BTC-USDT)
            formatted_symbol = format_symbol_for_storage(symbol)

            try:
                print(f"     Downloading 1-day data for {symbol} (formatted as {formatted_symbol})...")

                # Download 1-day timeframe data specifically
                result = await sync_manager.sync_symbol_data(
                    symbol=formatted_symbol,  # Use formatted symbol for download
                    timeframes=['1d'],
                    start_time=int(start_time_data.timestamp()),
                    end_time=int(end_time.timestamp())
                )

                if result and result.get('rows_written', 0) > 0:
                    print(f"       ✅ {result.get('rows_written', 0)} candles downloaded for {symbol}")
                else:
                    print(f"       ⚠️  No data downloaded for {symbol}")

            except Exception as e:
                print(f"     ❌ Error downloading 1-day data for {symbol}: {e}")

        print(f"   1-day data download completed for {len(symbols)} symbols.")


def format_symbol_for_storage(symbol: str) -> str:
    """Format symbol for storage (e.g., BTCUSDT to BTC-USDT)."""
    # If the symbol appears to be in format like BTCUSDT, convert to BTC-USDT
    if not '-' in symbol and len(symbol) >= 6:  # Basic check for format like BTCUSDT
        # Look for common base currencies
        for base in ['USDT', 'USD', 'BTC', 'ETH']:
            if symbol.endswith(base):
                base_part = symbol[-len(base):]
                quote_part = symbol[:-len(base)]
                return f"{quote_part}-{base_part}"

    return symbol  # Return as is if already in correct format


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

    # Download 1-day timeframe data first for better optimization
    print(f"\n📥 Downloading 1-day timeframe data for optimization...")
    asyncio.run(download_1d_data_for_symbols(symbols, days_back=180))  # 6 months for better optimization

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
            # Load data for the symbol - specifically 1-day timeframe for retune
            from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
            import pandas as pd
            data_repo = FileRepositoryAdapter()

            # Get normalized symbol and construct file path
            normalized_symbol = data_repo._normalize_symbol_for_file(symbol)
            file_path = data_repo.get_processed_file_path(normalized_symbol, "1d")

            print(f"   🔍 Loading 1-day data from: {file_path}")

            if os.path.exists(file_path):
                # Load the CSV file directly
                df = pd.read_csv(file_path)

                # Convert timestamp to datetime and set as index
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
                    df = df.set_index('timestamp').sort_index()

                if df.empty:
                    print(f"   ⚠️  No 1-day data found for {normalized_symbol}, skipping...")
                    continue
            else:
                print(f"   ⚠️  1-day data file does not exist: {file_path}")
                continue

            # Use only the last N days of data
            if days_back > 0:
                cutoff_date = datetime.now() - timedelta(days=days_back)
                # Convert cutoff_date to timezone-aware to match the DataFrame index
                cutoff_date_utc = pd.Timestamp(cutoff_date, tz='UTC')
                df = df[df.index >= cutoff_date_utc]

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
