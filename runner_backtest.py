#!/usr/bin/env python3
"""
Backtest Runner - Execute backtesting for trading strategies.

This script runs comprehensive backtests for trading strategies with
different parameters, data sets, and risk management configurations.
"""
import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
from enum import Enum

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import StrategyType enum from domain
from domain.enums.strategy_type import StrategyType

from infrastructure.backtest.realistic_backtester import RealisticBacktester
from application.data_sync.watcher_retune import WatcherRetuneUseCase
from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
from shared.logger import EnhancedLogger


def load_symbols_from_env() -> List[str]:
    """Load symbols from environment variable."""
    symbols_str = os.getenv("WFO_COINS", "BTCUSDT,ETHUSDT")
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def load_sample_strategy(strategy_name: str):
    """Load a sample strategy function based on the strategy name."""
    def simple_rsi_strategy(row, params):
        """Simple RSI-based strategy."""
        rsi = row.get('rsi', 50)
        rsi_oversold = params.get('rsi_oversold', 30)
        rsi_overbought = params.get('rsi_overbought', 70)

        if rsi < rsi_oversold:
            return 1  # Buy
        elif rsi > rsi_overbought:
            return -1  # Sell
        else:
            return 0  # Hold

    def simple_ma_crossover_strategy(row, params):
        """Simple moving average crossover strategy."""
        sma_fast = row.get('sma_10', 0)
        sma_slow = row.get('sma_20', 0)

        if pd.isna(sma_fast) or pd.isna(sma_slow):
            return 0

        if sma_fast > sma_slow:  # Golden cross
            return 1  # Buy
        elif sma_fast < sma_slow:  # Death cross
            return -1  # Sell
        else:
            return 0  # Hold

    def trend_following_strategy(row, params):
        """Trend following strategy based on moving averages."""
        sma_20 = row.get('sma_20', 0)
        sma_50 = row.get('sma_50', 0)
        close = row.get('close', 0)

        if pd.isna(sma_20) or pd.isna(sma_50) or pd.isna(close):
            return 0

        # Bullish trend: price above both SMAs and short-term above long-term
        if close > sma_20 > sma_50:
            return 1  # Buy
        # Bearish trend: price below both SMAs and short-term below long-term
        elif close < sma_20 < sma_50:
            return -1  # Sell
        else:
            return 0  # Hold

    def mean_reversion_strategy(row, params):
        """Mean reversion strategy using RSI and Bollinger Bands."""
        rsi = row.get('rsi', 50)
        bb_upper = row.get('bb_upper', 0)
        bb_lower = row.get('bb_lower', 0)
        close = row.get('close', 0)

        if pd.isna(rsi) or pd.isna(bb_upper) or pd.isna(bb_lower) or pd.isna(close):
            return 0

        # Oversold condition with potential bounce from lower band
        if rsi < 30 and close < bb_lower * 1.01:  # Within 1% of lower band
            return 1  # Buy
        # Overbought condition with potential drop from upper band
        elif rsi > 70 and close > bb_upper * 0.99:  # Within 1% of upper band
            return -1  # Sell
        else:
            return 0  # Hold

    def volatility_breakout_strategy(row, params):
        """Volatility breakout strategy using ATR and price movement."""
        atr = row.get('atr', 0)
        high = row.get('high', 0)
        low = row.get('low', 0)
        close = row.get('close', 0)
        sma_20 = row.get('sma_20', 0)

        if pd.isna(atr) or pd.isna(high) or pd.isna(low) or pd.isna(close) or pd.isna(sma_20):
            return 0

        # Define breakout thresholds based on ATR
        breakout_threshold = atr * 1.5

        # Bullish breakout: price moves significantly above recent range
        if close > max(high, sma_20) + breakout_threshold:
            return 1  # Buy
        # Bearish breakout: price moves significantly below recent range
        elif close < min(low, sma_20) - breakout_threshold:
            return -1  # Sell
        else:
            return 0  # Hold

    def momentum_strategy(row, params):
        """Momentum strategy using rate of change and volume."""
        roc = row.get('roc_10', 0)  # Rate of change over 10 periods
        volume = row.get('volume', 0)
        sma_volume = row.get('sma_volume_20', 0)
        rsi = row.get('rsi', 50)

        if pd.isna(roc) or pd.isna(volume) or pd.isna(sma_volume):
            return 0

        # Strong positive momentum with increasing volume
        if roc > 0.02 and volume > sma_volume * 1.2 and 30 < rsi < 70:  # Not overbought
            return 1  # Buy
        # Strong negative momentum with increasing volume
        elif roc < -0.02 and volume > sma_volume * 1.2 and 30 < rsi < 70:  # Not oversold
            return -1  # Sell
        else:
            return 0  # Hold

    def scalping_strategy(row, params):
        """Scalping strategy using short-term indicators."""
        rsi = row.get('rsi', 50)
        sma_fast = row.get('sma_5', 0)
        sma_slow = row.get('sma_10', 0)
        close = row.get('close', 0)

        if pd.isna(rsi) or pd.isna(sma_fast) or pd.isna(sma_slow) or pd.isna(close):
            return 0

        # Fast MA crosses above slow MA with RSI not overbought
        if sma_fast > sma_slow and sma_fast > close * 0.999 and rsi < 65:  # Close to fast MA, not overbought
            return 1  # Buy
        # Fast MA crosses below slow MA with RSI not oversold
        elif sma_fast < sma_slow and sma_fast < close * 1.001 and rsi > 35:  # Close to fast MA, not oversold
            return -1  # Sell
        else:
            return 0  # Hold

    def breakout_strategy(row, params):
        """Breakout strategy identifying resistance/support breakouts."""
        high_20 = row.get('high_20', 0)  # 20-period high
        low_20 = row.get('low_20', 0)   # 20-period low
        close = row.get('close', 0)
        atr = row.get('atr', 0)

        if pd.isna(high_20) or pd.isna(low_20) or pd.isna(close) or pd.isna(atr):
            return 0

        # Clear breakout above resistance with ATR confirmation
        if close > high_20 + atr * 0.5:
            return 1  # Buy
        # Clear breakdown below support with ATR confirmation
        elif close < low_20 - atr * 0.5:
            return -1  # Sell
        else:
            return 0  # Hold

    def liquidity_strategy(row, params):
        """Liquidity-based strategy using volume and spread."""
        volume = row.get('volume', 0)
        sma_volume = row.get('sma_volume_20', 0)
        bid_ask_spread = row.get('bid_ask_spread', 0)
        rsi = row.get('rsi', 50)

        if pd.isna(volume) or pd.isna(sma_volume):
            return 0

        # High volume with moderate RSI for liquidity entry
        if volume > sma_volume * 1.5 and 40 < rsi < 60:
            return 1  # Buy (when bullish bias)
        elif volume > sma_volume * 1.5 and (rsi < 30 or rsi > 70):
            # High volume during extreme conditions might indicate reversal
            return -1 if rsi > 70 else 1  # Sell if overbought, buy if oversold
        else:
            return 0  # Hold

    def mtf_trend_strategy(row, params):
        """Multi-timeframe trend strategy combining different timeframes."""
        sma_20_short = row.get('sma_20_short', 0)  # Short-term trend
        sma_50_short = row.get('sma_50_short', 0)
        sma_20_long = row.get('sma_20_long', 0)   # Long-term trend
        sma_50_long = row.get('sma_50_long', 0)
        close = row.get('close', 0)

        if any(pd.isna(x) for x in [sma_20_short, sma_50_short, sma_20_long, sma_50_long, close]):
            return 0

        # Align trends across timeframes
        short_trend_bullish = sma_20_short > sma_50_short
        long_trend_bullish = sma_20_long > sma_50_long

        if short_trend_bullish and long_trend_bullish and close > sma_20_short:
            return 1  # Buy
        elif not short_trend_bullish and not long_trend_bullish and close < sma_20_short:
            return -1  # Sell
        else:
            return 0  # Hold

    def oi_footprint_strategy(row, params):
        """OI (Open Interest) footprint strategy - simplified version."""
        # Since we don't have real OI data in this simplified version,
        # we'll simulate using volume and volatility as proxies
        volume = row.get('volume', 0)
        sma_volume = row.get('sma_volume_20', 0)
        atr = row.get('atr', 0)
        sma_atr = row.get('sma_atr_20', 0)
        rsi = row.get('rsi', 50)

        if pd.isna(volume) or pd.isna(sma_volume) or pd.isna(atr) or pd.isna(sma_atr):
            return 0

        # High volume and high volatility often correspond to high OI activity
        volume_spike = volume > sma_volume * 1.5
        volatilty_spike = atr > sma_atr * 1.2

        if volume_spike and volatilty_spike and 30 < rsi < 70:
            # Potential institutional activity detected
            return 1 if rsi < 50 else -1  # Buy if oversold, sell if overbought
        else:
            return 0  # Hold

    def sweep_scalper_strategy(row, params):
        """Sweep scalper strategy targeting liquidity."""
        bid = row.get('bid', 0)
        ask = row.get('ask', 0)
        high = row.get('high', 0)
        low = row.get('low', 0)
        volume = row.get('volume', 0)
        sma_volume = row.get('sma_volume_20', 0)

        if any(pd.isna(x) for x in [bid, ask, high, low, volume, sma_volume]):
            return 0

        # Look for high volume near recent highs/lows (potential liquidity sweeps)
        if volume > sma_volume * 2 and high >= row.get('high_5', 0) * 0.999:
            # High volume near recent high - potential bullish sweep
            return 1  # Buy
        elif volume > sma_volume * 2 and low <= row.get('low_5', 0) * 1.001:
            # High volume near recent low - potential bearish sweep
            return -1  # Sell
        else:
            return 0  # Hold

    def vwap_reversal_strategy(row, params):
        """VWAP reversal strategy."""
        close = row.get('close', 0)
        vwap = row.get('vwap', 0)
        rsi = row.get('rsi', 50)

        if pd.isna(close) or pd.isna(vwap) or pd.isna(rsi):
            return 0

        # Price significantly above VWAP with overbought RSI - potential reversal down
        if close > vwap * 1.02 and rsi > 70:
            return -1  # Sell
        # Price significantly below VWAP with oversold RSI - potential reversal up
        elif close < vwap * 0.98 and rsi < 30:
            return 1  # Buy
        else:
            return 0  # Hold

    strategies = {
        'rsi_strategy': simple_rsi_strategy,
        'ma_crossover_strategy': simple_ma_crossover_strategy,
        'crypto_breakout': simple_rsi_strategy,  # Default fallback
        'trend_following': trend_following_strategy,
        'mean_reversion': mean_reversion_strategy,
        'volatility_breakout': volatility_breakout_strategy,
        'momentum': momentum_strategy,
        'scalping': scalping_strategy,
        'breakout': breakout_strategy,
        'liquidity': liquidity_strategy,
        'mtf_trend': mtf_trend_strategy,
        'oi_footprint': oi_footprint_strategy,
        'sweep_scalper': sweep_scalper_strategy,
        'vwap_reversal': vwap_reversal_strategy
    }

    return strategies.get(strategy_name, simple_rsi_strategy)


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
    low_close = abs(df['low'] - df['close'].shift(1))    # Use previous close
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean().shift(1)

    # Rate of Change (ROC) with shifting
    df['roc_10'] = ((df['close'] - df['close'].shift(11)) / df['close'].shift(11)).shift(1)

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
    df['vwap'] = (typical_price * df['volume']).rolling(window=20).sum().shift(1) / df['volume'].rolling(window=20).sum().shift(1)

    # Bid-Ask Spread approximation (using high-low as proxy)
    df['bid_ask_spread'] = (df['high'] - df['low']) / df['close']

    # Multi-timeframe indicators (simulated)
    # For demonstration purposes, we'll create slower moving averages as "longer timeframe" indicators
    df['sma_20_short'] = df['close'].rolling(window=20).mean().shift(1)  # Shorter timeframe
    df['sma_50_short'] = df['close'].rolling(window=50).mean().shift(1)  # Shorter timeframe
    df['sma_20_long'] = df['close'].rolling(window=20).mean().shift(1)   # Longer timeframe (simulated)
    df['sma_50_long'] = df['close'].rolling(window=50).mean().shift(1)   # Longer timeframe (simulated)

    return df


def run_backtest_process(symbols: List[str], 
                        strategy_name: str,
                        start_date: datetime,
                        end_date: datetime,
                        initial_capital: float = 10000.0,
                        fee_rate: float = 0.001,
                        slippage_factor: float = 0.0005,
                        strategy_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Run the backtest process for specified symbols and strategy."""
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
    backtester = RealisticBacktester(
        initial_capital=initial_capital,
        fee_rate=fee_rate,
        slippage_factor=slippage_factor
    )
    
    # Load strategy function
    strategy_function = load_sample_strategy(strategy_name)
    
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
        }
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
            # Load data for the symbol
            file_repo = FileRepositoryAdapter()
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

                # Ensure index is datetime type
                df.index = pd.to_datetime(df.index)

                # Filter data by date range
                df = df[(df.index >= start_date) & (df.index <= end_date)]

                if len(df) < 10:  # Need minimum data for backtest
                    print(f"   ⚠️  Insufficient data for {symbol} (only {len(df)} rows), skipping...")
                    continue
            else:
                # Try to use the CSV history loader
                from infrastructure.data.csv_history_loader import CSVHistoryLoaderAdapter
                data_loader = CSVHistoryLoaderAdapter()
                
                try:
                    df = data_loader.load(symbol=symbol)
                    if df.empty:
                        print(f"   ⚠️  No data found for {symbol}, skipping...")
                        continue
                    
                    # Ensure index is datetime type for CSV loader too
                    df.index = pd.to_datetime(df.index)

                    # Filter data by date range
                    df = df[(df.index >= start_date) & (df.index <= end_date)]

                    if len(df) < 10:
                        print(f"   ⚠️  Insufficient data for {symbol} (only {len(df)} rows), skipping...")
                        continue
                        
                except Exception as e:
                    print(f"   ❌ Error loading data for {symbol}: {e}")
                    continue
            
            # Calculate indicators with proper shifting
            df_with_indicators = calculate_indicators_with_shifting(df)
            
            # Remove rows with NaN values (from shifting)
            df_with_indicators = df_with_indicators.dropna()
            
            if len(df_with_indicators) < 10:
                print(f"   ⚠️  Insufficient data after indicator calculation for {symbol}, skipping...")
                continue
            
            # Run backtest
            backtest_result = backtester.run_backtest(
                data=df_with_indicators,
                strategy_function=strategy_function,
                strategy_params=strategy_params
            )
            
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
    
    return results


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


def run_multiple_strategies_backtest(symbols: List[str],
                                   strategy_names: List[str],
                                   start_date: datetime,
                                   end_date: datetime,
                                   initial_capital: float = 10000.0,
                                   fee_rate: float = 0.001,
                                   slippage_factor: float = 0.0005,
                                   strategy_params: Dict[str, Any] = None) -> Dict[str, Any]:
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
            strategy_result = run_backtest_process(
                symbols=symbols,
                strategy_name=strategy_name,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                fee_rate=fee_rate,
                slippage_factor=slippage_factor,
                strategy_params=strategy_params
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
    print(f"   Best Performing Strategy: {results['best_performing']['strategy']} "
          f"(Return: {results['best_performing']['avg_return']:.2%})")
    print(f"\n   All Strategies Ranked by Return:")
    for i, comp in enumerate(results['strategy_comparison'], 1):
        print(f"   {i}. {comp['strategy']:<20} "
              f"Return: {comp['avg_return']:.2%}, "
              f"Sharpe: {comp['avg_sharpe']:.2f}, "
              f"Drawdown: {comp['avg_drawdown']:.2%}, "
              f"Trades: {comp['total_trades']}")

    return results


def main():
    """Main entry point for the backtest runner."""
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

    # Mutually exclusive group for single vs multiple strategies
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

    # Determine which strategies to run
    if args.all_strategies:
        # Run all available strategies using the StrategyType enum
        all_available_strategies = [strategy.value for strategy in StrategyType]
        # Add the crypto_breakout strategy which is used in examples
        all_available_strategies.append('crypto_breakout')
        strategy_names = all_available_strategies
        print(f"🚀 Multi-Strategy Backtest Runner Started")
        print(f"   Strategies: {strategy_names}")
    elif args.strategies:
        # Run specific strategies provided by user
        strategy_names = args.strategies
        print(f"🚀 Multi-Strategy Backtest Runner Started")
        print(f"   Strategies: {strategy_names}")
    else:
        # Run single strategy
        strategy_names = [args.strategy]
        print(f"🚀 Backtest Runner Started")
        print(f"   Strategy: {args.strategy}")

    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Symbols: {symbols}")
    print(f"   Initial Capital: ${args.capital:,.2f}")

    try:
        if len(strategy_names) > 1:
            # Run multiple strategies
            results = run_multiple_strategies_backtest(
                symbols=symbols,
                strategy_names=strategy_names,
                start_date=start_date,
                end_date=end_date,
                initial_capital=args.capital,
                fee_rate=args.fee,
                slippage_factor=args.slippage
            )
        else:
            # Run single strategy
            results = run_backtest_process(
                symbols=symbols,
                strategy_name=args.strategy,
                start_date=start_date,
                end_date=end_date,
                initial_capital=args.capital,
                fee_rate=args.fee,
                slippage_factor=args.slippage
            )

        # Validate results if requested
        if args.validate:
            validation_results = validate_backtest_results(results)
            results['validation'] = validation_results

        # Save results if output file specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n💾 Results saved to {args.output}")

        # Check for backtest failures
        failed_count = results['summary']['failed_backtests']
        if failed_count > 0:
            print(f"\n⚠️  Process completed with {failed_count} failed backtests")
            return min(failed_count, 1)  # Return 1 if any failed, but cap at 1
        else:
            print(f"\n🎉 All backtests completed successfully!")
            return 0

    except KeyboardInterrupt:
        print(f"\n⚠️  Process interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Backtest process failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())