"""Run-backtest use case (E2.T4b - Composition Root Hardening).

Application-layer entry point for the backtest feature (F7). All orchestration
lives here; every infrastructure dependency is received through a port resolved
from the composition root (``bootstrap.container``):

* ``file_repository``            - data-access port (raw OHLCV files)
* ``csv_history_loader``         - fallback data-access port
* ``backtester_factory``         - builds the realistic backtester per request
* ``strategy_provider``          - yields execution-intent-wrapped strategies

This module imports only stdlib / third-party libraries and the ``shared``
logger; it never imports ``infrastructure``, ``runner_*`` or ``interface``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np

from shared.logger import EnhancedLogger


@dataclass
class BacktestRequest:
    """Inputs for a backtest run, mirroring the CLI surface (F7)."""

    symbols: List[str]
    strategy_names: List[str]
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0
    fee_rate: float = 0.001
    slippage_factor: float = 0.0005
    strategy_params: Dict[str, Any] = field(default_factory=dict)


def calculate_indicators_with_shifting(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate technical indicators with proper shifting to prevent lookahead bias."""
    df = df.copy()

    # RSI with shifting
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = (100 - (100 / (1 + rs))).shift(1)  # Shift to prevent lookahead

    # Moving averages with shifting
    df['sma_5'] = df['close'].rolling(window=5).mean().shift(1)
    df['sma_10'] = df['close'].rolling(window=10).mean().shift(1)
    df['sma_20'] = df['close'].rolling(window=20).mean().shift(1)
    df['sma_50'] = df['close'].rolling(window=50).mean().shift(1)

    # Bollinger Bands with shifting
    df['bb_middle'] = df['close'].rolling(window=20).mean().shift(1)
    bb_std = df['close'].rolling(window=20).std().shift(1)
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)

    # ATR (Average True Range) with shifting
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift(1))  # Use previous close
    low_close = abs(df['low'] - df['close'].shift(1))  # Use previous close
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean().shift(1)

    # Rate of Change (ROC) with shifting
    df['roc_10'] = ((df['close'] - df['close'].shift(11)) / df['close'].shift(11)).shift(1)

    # ADX (Average Directional Index) - for trend strength
    up_move = df['high'] - df['high'].shift(1)
    down_move = df['low'].shift(1) - df['low']
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    plus_di_raw = 100 * (pd.Series(plus_dm).rolling(window=14).mean() / df['atr'])
    minus_di_raw = 100 * (pd.Series(minus_dm).rolling(window=14).mean() / df['atr'])

    # Handle division by zero
    plus_di = plus_di_raw.shift(1)
    minus_di = minus_di_raw.shift(1)

    # Calculate DX with division by zero handling
    di_sum = plus_di + minus_di
    di_diff = abs(plus_di - minus_di)
    dx = np.where(di_sum != 0, 100 * di_diff / di_sum, 0)
    df['adx'] = pd.Series(dx).rolling(window=14).mean().shift(1)

    # Volume indicators with shifting
    df['sma_volume_20'] = df['volume'].rolling(window=20).mean().shift(1)
    df['sma_atr_20'] = df['atr'].rolling(window=20).mean().shift(1)

    # High/Low indicators with shifting
    df['high_5'] = df['high'].rolling(window=5).max().shift(1)
    df['high_20'] = df['high'].rolling(window=20).max().shift(1)
    df['low_5'] = df['low'].rolling(window=5).min().shift(1)
    df['low_20'] = df['low'].rolling(window=20).min().shift(1)

    # VWAP (Volume Weighted Average Price) - simplified version
    # For simplicity, we'll approximate VWAP using typical price weighted by volume
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    df['vwap'] = (typical_price * df['volume']).rolling(window=20).sum().shift(1) / df['volume'].rolling(
        window=20).sum().shift(1)

    # Bid-Ask Spread approximation (using high-low as proxy)
    df['bid_ask_spread'] = (df['high'] - df['low']) / df['close']

    # Multi-timeframe indicators (simulated)
    # For demonstration purposes, we'll create slower moving averages as "longer timeframe" indicators
    df['sma_20_short'] = df['close'].rolling(window=20).mean().shift(1)  # Shorter timeframe
    df['sma_50_short'] = df['close'].rolling(window=50).mean().shift(1)  # Shorter timeframe
    df['sma_20_long'] = df['close'].rolling(window=20).mean().shift(1)  # Longer timeframe (simulated)
    df['sma_50_long'] = df['close'].rolling(window=50).mean().shift(1)  # Longer timeframe (simulated)

    # Volatility regime indicators
    df['volatility_regime'] = df['atr'].rolling(window=20).mean().shift(1)
    df['volatility_percentile'] = df['atr'].rolling(window=100).rank(pct=True).shift(1)

    # Trend strength indicator
    df['trend_strength'] = abs(df['sma_20'] - df['sma_50']) / df['atr']

    return df


def classify_market_regime(df: pd.DataFrame) -> Dict[str, Any]:
    """Classify the current market regime based on indicators."""
    if df.empty:
        return {'regime': 'unknown', 'confidence': 0.0}

    # Calculate regime indicators
    latest_row = df.iloc[-1]

    # Trend strength (based on ADX)
    adx = latest_row.get('adx', 20)
    trend_strength = 'strong' if adx > 30 else 'weak' if adx < 20 else 'moderate'

    # Volatility regime
    atr = latest_row.get('atr', 0)
    volatility_regime = latest_row.get('volatility_regime', 0)
    volatility_level = 'high' if volatility_regime > df['volatility_regime'].quantile(0.7) else \
        'low' if volatility_regime < df['volatility_regime'].quantile(0.3) else 'normal'

    # Determine market regime
    if trend_strength == 'strong' and volatility_level == 'high':
        regime = 'TREND_HIGH_VOL'
    elif trend_strength == 'strong' and volatility_level != 'high':
        regime = 'TREND'
    elif trend_strength == 'weak' and volatility_level == 'high':
        regime = 'CHOPPY_HIGH_VOL'
    elif trend_strength == 'weak':
        regime = 'RANGE'
    else:
        regime = 'NORMAL'

    return {
        'regime': regime,
        'trend_strength': trend_strength,
        'volatility_level': volatility_level,
        'adx': adx,
        'atr': atr,
        'confidence': 0.8  # High confidence in classification
    }


def audit_signal_density(df: pd.DataFrame, strategy_function) -> Dict[str, int]:
    """Audit signal generation and filtering for the strategy."""
    if df.empty:
        return {'signals_generated': 0, 'signals_filtered': 0, 'entries_taken': 0, 'entry_ratio': 0.0}

    signals_generated = 0
    signals_filtered = 0
    entries_taken = 0

    for idx, row in df.iterrows():
        # Generate signal
        signal = strategy_function(row, {})
        signals_generated += 1

        # Count if signal is non-zero (indicating entry taken)
        if signal != 0:
            entries_taken += 1
        else:
            signals_filtered += 1

    entry_ratio = entries_taken / signals_generated if signals_generated > 0 else 0.0

    return {
        'signals_generated': signals_generated,
        'signals_filtered': signals_filtered,
        'entries_taken': entries_taken,
        'entry_ratio': entry_ratio
    }


def validate_backtest_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the results of the backtest process."""
    print(f"\n✅ Validating backtest results...")

    validation_results = {
        'valid': 0,
        'invalid': 0,
        'total': results['summary']['successful_backtests'] + results['summary']['failed_backtests'],
        'validation_details': {}
    }

    for symbol, result in results['backtest_results'].items():
        if 'error' not in result and result:  # Successful backtest
            # Basic validation checks
            is_valid = True
            issues = []

            # Check for reasonable values
            total_return = result.get('total_return', 0)
            if abs(total_return) > 10:  # 1000% return seems unreasonable
                is_valid = False
                issues.append(f"Unreasonable return: {total_return:.2%}")

            sharpe_ratio = result.get('sharpe_ratio', 0)
            if abs(sharpe_ratio) > 5:  # Sharpe > 5 is typically unrealistic
                is_valid = False
                issues.append(f"Unreasonable Sharpe ratio: {sharpe_ratio:.2f}")

            max_drawdown = result.get('max_drawdown', 0)
            if max_drawdown > 0:  # Drawdown should be negative
                is_valid = False
                issues.append(f"Positive drawdown value: {max_drawdown:.2%}")

            win_rate = result.get('win_rate', 0)
            if win_rate < 0 or win_rate > 1:  # Win rate should be 0-1
                is_valid = False
                issues.append(f"Invalid win rate: {win_rate:.2%}")

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


def _run_backtest_process(symbols: List[str],
                         strategy_name: str,
                         start_date: datetime,
                         end_date: datetime,
                         initial_capital: float = 10000.0,
                         fee_rate: float = 0.001,
                         slippage_factor: float = 0.0005,
                         strategy_params: Dict[str, Any] = None,
                         file_repository=None,
                         backtester_factory=None,
                         strategy_provider=None,
                         csv_history_loader=None) -> Dict[str, Any]:
    """Run the backtest process for specified symbols and strategy.

    All collaborators (``file_repository``, ``backtester_factory``,
    ``strategy_provider``, ``csv_history_loader``) are injected ports supplied by
    the composition root; this function constructs no infrastructure directly.
    """
    logger = EnhancedLogger(f"BacktestRunner_{strategy_name}")

    if strategy_params is None:
        strategy_params = {}

    print(f"📈 Starting backtest process for strategy: {strategy_name}")
    print(f"   Symbols: {symbols}")
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Initial Capital: ${initial_capital:,.2f}")
    print(f"   Fee Rate: {fee_rate:.3%}")
    print(f"   Slippage Factor: {slippage_factor:.3%}")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = datetime.now()

    # Initialize backtester
    backtester = backtester_factory(
        initial_capital=initial_capital,
        fee_rate=fee_rate,
        slippage_factor=slippage_factor
    )

    # Load the execution-intent-wrapped strategy function via the injected port.
    strategy_function = strategy_provider.get_strategy(strategy_name)

    results = {
        'strategy_name': strategy_name,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'initial_capital': initial_capital,
        'fee_rate': fee_rate,
        'slippage_factor': slippage_factor,
        'strategy_params': strategy_params,
        'backtest_results': {},
        'summary': {
            'total_symbols': len(symbols),
            'successful_backtests': 0,
            'failed_backtests': 0,
            'aggregate_metrics': {}
        },
        'signal_audit': {},  # Track signal generation and filtering
        'regime_classification': {}  # Track market regime classification
    }

    # Track aggregate metrics across all symbols
    all_returns = []
    all_sharpes = []
    all_drawdowns = []
    all_win_rates = []
    all_total_trades = []

    for symbol in symbols:
        print(f"\n🔍 Backtesting {strategy_name} on {symbol}...")

        try:
            # Load data for the symbol (injected port, or default adapter).
            file_repo = file_repository
            raw_data_path = file_repo.get_raw_file_path(symbol)

            if os.path.exists(raw_data_path):
                df = pd.read_csv(raw_data_path)

                # Ensure the first column is treated as datetime index
                # Check if the first column is named 'timestamp' or similar
                if 'timestamp' in df.columns:
                    # Convert timestamp column to datetime if it's not already
                    if df['timestamp'].dtype == 'object':
                        # Try to convert string timestamps to datetime
                        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                    elif df['timestamp'].dtype in ['int64', 'float64']:
                        # Assume it's Unix timestamp and convert to datetime
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')

                    # Set timestamp as index
                    df = df.set_index('timestamp')
                else:
                    # If no timestamp column, try to parse the first column as datetime
                    first_col = df.columns[0]
                    df[first_col] = pd.to_datetime(df[first_col], errors='coerce')
                    df = df.set_index(first_col)

                # Ensure index is datetime type - keep timezone as is
                df.index = pd.to_datetime(df.index)

                # Convert both the index and the date range to the same timezone-naive format for comparison
                # This ensures consistent comparison regardless of timezone differences
                df_index_naive = df.index.tz_localize(None) if df.index.tz is not None else df.index
                start_date_naive = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
                end_date_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date

                # Create a mask for date filtering
                date_mask = (df_index_naive >= start_date_naive) & (df_index_naive <= end_date_naive)

                # Apply the mask to filter the dataframe
                df = df[date_mask]

                # Reset the index to maintain the original timezone if it existed
                if df.index.tz is not None:
                    df.index = df.index.tz_convert(df.index.tz)

                # Debug: Print date range info
                if len(df) > 0:
                    print(f"   Date range filter applied: {start_date_naive.date()} to {end_date_naive.date()}, "
                          f"data range: {df.index[0].date()} to {df.index[-1].date()}, "
                          f"rows: {len(df)}")

                if len(df) < 10:  # Need minimum data for backtest
                    print(f"   ⚠️  Insufficient data for {symbol} (only {len(df)} rows), skipping...")
                    continue
            else:
                # Use the injected CSV history loader port.
                data_loader = csv_history_loader

                try:
                    # Timeframe-suitability evaluation hook: when BACKTEST_TIMEFRAME is
                    # set, load resampled higher-TF data (data/history/raw/<tf>/). Default
                    # (unset) preserves the canonical 1m load behavior exactly.
                    _tf = os.environ.get("BACKTEST_TIMEFRAME")
                    df = data_loader.load(symbol=symbol, timeframe=_tf) if _tf else data_loader.load(symbol=symbol)
                    if df.empty:
                        print(f"   ⚠️  No data found for {symbol}, skipping...")
                        continue

                    # Ensure index is datetime type - keep timezone as is for CSV loader too
                    df.index = pd.to_datetime(df.index)

                    # Convert both the index and the date range to the same timezone-naive format for comparison
                    # This ensures consistent comparison regardless of timezone differences
                    df_index_naive = df.index.tz_localize(None) if df.index.tz is not None else df.index
                    start_date_naive = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
                    end_date_naive = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date

                    # Create a mask for date filtering
                    date_mask = (df_index_naive >= start_date_naive) & (df_index_naive <= end_date_naive)

                    # Apply the mask to filter the dataframe
                    df = df[date_mask]

                    # Debug: Print date range info
                    if len(df) > 0:
                        print(f"   Date range filter applied: {start_date_naive.date()} to {end_date_naive.date()}, "
                              f"data range: {df.index[0].date()} to {df.index[-1].date()}, "
                              f"rows: {len(df)}")

                    if len(df) < 10:
                        print(f"   ⚠️  Insufficient data for {symbol} (only {len(df)} rows), skipping...")
                        continue

                except Exception as e:
                    print(f"   ❌ Error loading data for {symbol}: {e}")
                    continue

            # Calculate indicators with proper shifting
            df_with_indicators = calculate_indicators_with_shifting(df)

            # Fill NaN values with reasonable defaults instead of dropping all rows
            # This preserves more data for backtesting. (ffill/bfill are the
            # supported equivalents of the removed fillna(method=...) kwarg.)
            df_with_indicators = df_with_indicators.ffill().bfill()

            # If still have NaN values, fill with defaults
            df_with_indicators = df_with_indicators.fillna(0)

            if len(df_with_indicators) < 10:
                print(f"   ⚠️  Insufficient data after indicator calculation for {symbol}, skipping...")
                continue

            # Classify market regime based on indicators
            regime_info = classify_market_regime(df_with_indicators)
            results['regime_classification'][symbol] = regime_info

            # E-P5.2: thread the per-symbol identity through so the strategy
            # adapter's discipline AND the backtester's outcome feedback key off
            # the symbol actually being tested (symbol-agnostic — every approved
            # symbol must be testable; no hardcoded default).
            symbol_params = {**(strategy_params or {}), 'symbol': symbol}

            # Run backtest
            backtest_result = backtester.run_backtest(
                data=df_with_indicators,
                strategy_function=strategy_function,
                strategy_params=symbol_params,
                strategy_name=strategy_name
            )

            # Perform signal density audit
            signal_audit = audit_signal_density(df_with_indicators, strategy_function)
            results['signal_audit'][symbol] = signal_audit

            if 'error' not in backtest_result:
                results['backtest_results'][symbol] = backtest_result
                results['summary']['successful_backtests'] += 1

                # Collect metrics for aggregate calculation
                all_returns.append(backtest_result.get('total_return', 0))
                all_sharpes.append(backtest_result.get('sharpe_ratio', 0))
                all_drawdowns.append(backtest_result.get('max_drawdown', 0))
                all_win_rates.append(backtest_result.get('win_rate', 0))
                all_total_trades.append(backtest_result.get('total_trades', 0))

                print(f"   ✅ {symbol} backtest completed")
                print(f"      Return: {backtest_result.get('total_return', 0):.2%}")
                print(f"      Sharpe: {backtest_result.get('sharpe_ratio', 0):.2f}")
                print(f"      Max DD: {backtest_result.get('max_drawdown', 0):.2%}")
                print(f"      Trades: {backtest_result.get('total_trades', 0)}")

                # Print signal audit results
                if signal_audit:
                    print(f"      Signal Audit - Generated: {signal_audit.get('signals_generated', 0)}, "
                          f"Filtered: {signal_audit.get('signals_filtered', 0)}, "
                          f"Entries: {signal_audit.get('entries_taken', 0)}")
            else:
                results['backtest_results'][symbol] = {
                    'status': 'error',
                    'error': backtest_result['error'],
                    'timestamp': datetime.now().isoformat()
                }
                results['summary']['failed_backtests'] += 1
                print(f"   ❌ {symbol} backtest failed: {backtest_result['error']}")

        except Exception as e:
            print(f"   ❌ Error during backtest for {symbol}: {e}")
            results['backtest_results'][symbol] = {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            results['summary']['failed_backtests'] += 1

    # Calculate aggregate metrics
    if all_returns:
        results['summary']['aggregate_metrics'] = {
            'avg_total_return': sum(all_returns) / len(all_returns) if all_returns else 0,
            'avg_sharpe_ratio': sum(all_sharpes) / len(all_sharpes) if all_sharpes else 0,
            'avg_max_drawdown': sum(all_drawdowns) / len(all_drawdowns) if all_drawdowns else 0,
            'avg_win_rate': sum(all_win_rates) / len(all_win_rates) if all_win_rates else 0,
            'total_trades': sum(all_total_trades),
            'symbols_backtested': len(all_returns)
        }

    # Add end time and duration
    end_time = datetime.now()
    results['end_time'] = end_time.isoformat()
    results['duration_seconds'] = (end_time - start_time).total_seconds()

    # Print summary
    print(f"\n📊 BACKTEST SUMMARY")
    print(f"   Strategy: {strategy_name}")
    print(f"   Symbols processed: {results['summary']['total_symbols']}")
    print(f"   Successful: {results['summary']['successful_backtests']}")
    print(f"   Failed: {results['summary']['failed_backtests']}")

    agg_metrics = results['summary']['aggregate_metrics']
    if agg_metrics:
        print(f"   Average Return: {agg_metrics.get('avg_total_return', 0):.2%}")
        print(f"   Average Sharpe: {agg_metrics.get('avg_sharpe_ratio', 0):.2f}")
        print(f"   Average Max DD: {agg_metrics.get('avg_max_drawdown', 0):.2%}")
        print(f"   Average Win Rate: {agg_metrics.get('avg_win_rate', 0):.2%}")
        print(f"   Total Trades: {agg_metrics.get('total_trades', 0):,}")

    print(f"   Duration: {results['duration_seconds']:.2f}s")

    # The validation is already performed inside the backtester, so we just report status
    print(f"\n✅ Backtest completed with validation")
    return results


def _run_multiple_strategies_backtest(symbols: List[str],
                                     strategy_names: List[str],
                                     start_date: datetime,
                                     end_date: datetime,
                                     initial_capital: float = 10000.0,
                                     fee_rate: float = 0.001,
                                     slippage_factor: float = 0.0005,
                                     strategy_params: Dict[str, Any] = None,
                                     file_repository=None,
                                     backtester_factory=None,
                                     strategy_provider=None,
                                     csv_history_loader=None) -> Dict[str, Any]:
    """Run backtests for multiple strategies and compare results."""
    logger = EnhancedLogger("MultiStrategyBacktest")

    print(f"📈 Running backtests for {len(strategy_names)} strategies on {symbols}")
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Initial Capital: ${initial_capital:,.2f}")

    results = {
        'multi_strategy_results': {},
        'strategy_comparison': [],
        'best_performing': None,
        'summary': {
            'total_strategies': len(strategy_names),
            'successful_backtests': 0,
            'failed_backtests': 0
        }
    }

    for strategy_name in strategy_names:
        print(f"\n🔍 Running backtest for strategy: {strategy_name}")

        try:
            # Run individual backtest for this strategy
            strategy_result = _run_backtest_process(
                symbols=symbols,
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                fee_rate=fee_rate,
                slippage_factor=slippage_factor,
                strategy_params=strategy_params,
                file_repository=file_repository,
                backtester_factory=backtester_factory,
                strategy_provider=strategy_provider,
                csv_history_loader=csv_history_loader,
            )

            results['multi_strategy_results'][strategy_name] = strategy_result

            # Extract key metrics for comparison
            if strategy_result['summary']['aggregate_metrics']:
                agg_metrics = strategy_result['summary']['aggregate_metrics']

                comparison_entry = {
                    'strategy': strategy_name,
                    'avg_return': agg_metrics.get('avg_total_return', 0),
                    'avg_sharpe': agg_metrics.get('avg_sharpe_ratio', 0),
                    'avg_drawdown': agg_metrics.get('avg_max_drawdown', 0),
                    'avg_win_rate': agg_metrics.get('avg_win_rate', 0),
                    'total_trades': agg_metrics.get('total_trades', 0),
                    'symbols_backtested': agg_metrics.get('symbols_backtested', 0)
                }

                results['strategy_comparison'].append(comparison_entry)

                # Track best performing strategy by return
                if (results['best_performing'] is None or
                        comparison_entry['avg_return'] > results['best_performing']['avg_return']):
                    results['best_performing'] = comparison_entry

            results['summary']['successful_backtests'] += 1
            print(f"   ✅ {strategy_name} backtest completed")

        except Exception as e:
            print(f"   ❌ {strategy_name} backtest failed: {e}")
            results['summary']['failed_backtests'] += 1

    # Sort strategies by return for easy comparison
    results['strategy_comparison'].sort(key=lambda x: x['avg_return'], reverse=True)

    # Print comparison summary
    print(f"\n🏆 STRATEGY COMPARISON RESULTS")
    if results['best_performing']:
        print(f"   Best Performing Strategy: {results['best_performing']['strategy']} "
              f"(Return: {results['best_performing']['avg_return']:.2%})")
    else:
        print(f"   Best Performing Strategy: None (no successful backtests)")

    print(f"\n   All Strategies Ranked by Return:")
    if results['strategy_comparison']:
        for i, comp in enumerate(results['strategy_comparison'], 1):
            print(f"   {i}. {comp['strategy']:<20} "
                  f"Return: {comp['avg_return']:.2%}, "
                  f"Sharpe: {comp['avg_sharpe']:.2f}, "
                  f"Drawdown: {comp['avg_drawdown']:.2%}, "
                  f"Trades: {comp['total_trades']}")
    else:
        print("   No strategies completed successfully")

    return results


class RunBacktestUseCase:
    """Wire-and-run the backtest feature using container-provided ports."""

    def __init__(self,
                 file_repository: Optional[Any] = None,
                 backtester_factory: Optional[Any] = None,
                 strategy_provider: Optional[Any] = None,
                 csv_history_loader: Optional[Any] = None) -> None:
        self._file_repository = file_repository
        self._backtester_factory = backtester_factory
        self._strategy_provider = strategy_provider
        self._csv_history_loader = csv_history_loader

    def execute(self, request: BacktestRequest) -> Dict[str, Any]:
        if len(request.strategy_names) > 1:
            return _run_multiple_strategies_backtest(
                symbols=request.symbols,
                strategy_names=request.strategy_names,
                start_date=request.start_date,
                end_date=request.end_date,
                initial_capital=request.initial_capital,
                fee_rate=request.fee_rate,
                slippage_factor=request.slippage_factor,
                strategy_params=request.strategy_params,
                file_repository=self._file_repository,
                backtester_factory=self._backtester_factory,
                strategy_provider=self._strategy_provider,
                csv_history_loader=self._csv_history_loader,
            )

        return _run_backtest_process(
            symbols=request.symbols,
            strategy_name=request.strategy_names[0],
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            fee_rate=request.fee_rate,
            slippage_factor=request.slippage_factor,
            strategy_params=request.strategy_params,
            file_repository=self._file_repository,
            backtester_factory=self._backtester_factory,
            strategy_provider=self._strategy_provider,
            csv_history_loader=self._csv_history_loader,
        )

    def validate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        return validate_backtest_results(results)
