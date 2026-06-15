#!/usr/bin/env python3
"""
OptimizeStrategyUseCase - application-layer orchestration for automated
hyperparameter retuning of trading strategies.

Orchestration moved here from runner_retune.py (E2.T4). Infrastructure
collaborators (file repository, sync manager, data downloader, parameter space,
hyperopt optimizer) are supplied by the composition root; this use case never
instantiates infrastructure classes directly.
"""
import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from shared.logger import EnhancedLogger


@dataclass
class OptimizeStrategyRequest:
    symbols: List[str]
    strategy_name: str = "crypto_breakout"
    max_evals: int = 50
    days_back: int = 90


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


class OptimizeStrategyUseCase:
    """Run the retune/optimization pipeline using container-injected ports."""

    def __init__(self,
                 settings,
                 file_repository: Optional[Any] = None,
                 sync_manager: Optional[Any] = None,
                 data_downloader: Optional[Any] = None,
                 hyperopt_param_space_factory: Optional[Callable[[], Any]] = None,
                 hyperopt_optimizer_factory: Optional[Callable[[Any, str], Any]] = None) -> None:
        # Settings injected by the composition root (E1.T5); read off self._settings
        # instead of importing bootstrap.settings.loaders.
        self._settings = settings
        self._file_repository = file_repository
        self._sync_manager = sync_manager
        self._data_downloader = data_downloader
        self._hyperopt_param_space_factory = hyperopt_param_space_factory
        self._hyperopt_optimizer_factory = hyperopt_optimizer_factory

    def execute(self, request: OptimizeStrategyRequest) -> Dict[str, Any]:
        return self._run_retune_process(
            symbols=request.symbols,
            strategy_name=request.strategy_name,
            max_evals=request.max_evals,
            days_back=request.days_back,
        )

    async def _download_1d_data_for_symbols(self, symbols: List[str], days_back: int = 180):
        """Download 1-day timeframe data for specified symbols."""
        print(f"   Downloading 1-day data for {len(symbols)} symbols...")

        # Data-sync ports are injected by the composition root.
        data_downloader = self._data_downloader
        sync_manager = self._sync_manager

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

    def _run_retune_process(self,
                            symbols: List[str],
                            strategy_name: str = "crypto_breakout",
                            max_evals: int = 50,
                            days_back: int = 90) -> Dict[str, Any]:
        """Run the retune process for specified symbols and strategy."""
        logger = EnhancedLogger(f"RetuneRunner_{strategy_name}")

        print(f"🔄 Starting retune process for strategy: {strategy_name}")
        print(f"   Symbols: {symbols}")
        print(f"   Max evaluations per symbol: {max_evals}")
        print(f"   Data window: {days_back} days")
        print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Download 1-day timeframe data first for better optimization
        print(f"\n📥 Downloading 1-day timeframe data for optimization...")
        asyncio.run(self._download_1d_data_for_symbols(symbols, days_back=180))  # 6 months for better optimization

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
                'initial_capital': self._settings.backtest.initial_capital if self._settings.backtest and hasattr(self._settings.backtest, 'initial_capital') else 100000.0,
                'fee_rate': self._settings.execution.fee_rate if self._settings.execution and hasattr(self._settings.execution, 'fee_rate') else 0.001,
                'slippage_factor': self._settings.execution.slippage_factor if self._settings.execution and hasattr(self._settings.execution, 'slippage_factor') else 0.0005
            }
        }

        from shared.configurable_hyperopt import HyperoptConfig
        hyperopt_config_obj = HyperoptConfig(strategy_name=strategy_name)
        optimizer = self._hyperopt_optimizer_factory(hyperopt_config_obj, strategy_name)
        param_space_handler = self._hyperopt_param_space_factory()

        for symbol in symbols:
            print(f"\n🔍 Optimizing {strategy_name} for {symbol}...")

            try:
                # Load data for the symbol - specifically 1-day timeframe for retune
                import pandas as pd
                data_repo = self._file_repository

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

    def validate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
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
