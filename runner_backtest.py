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
import numpy as np
from enum import Enum

# Add project root to path to import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import StrategyType enum from domain
from domain.enums.strategy_type import StrategyType

from infrastructure.backtest.realistic_backtester import RealisticBacktester
from application.data_sync.watcher_retune import WatcherRetuneUseCase
from infrastructure.data_sync.file_repository_adapter import FileRepositoryAdapter
from shared.logger import EnhancedLogger
from application.configs.configs import Configs


def load_symbols_from_env() -> List[str]:
    """Load symbols from configuration."""
    symbols_str = Configs.wfo.wfo_coins if Configs.wfo and Configs.wfo.wfo_coins else "BTCUSDT,ETHUSDT"
    return [s.strip() for s in symbols_str.split(',') if s.strip()]


def load_sample_strategy(strategy_name: str):
    """Load a sample strategy function based on the strategy name."""

    def simple_rsi_strategy(row, params):
        """Simple RSI-based strategy."""
        rsi = row.get('rsi', 50)
        rsi_oversold = params.get('rsi_oversold', 30)
        rsi_overbought = params.get('rsi_overbought', 70)

        if pd.isna(rsi):
            return 0

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
        """Regime-aware trend following strategy based on moving averages and momentum."""
        sma_20 = row.get('sma_20', 0)
        sma_50 = row.get('sma_50', 0)
        close = row.get('close', 0)
        roc = row.get('roc_10', 0)  # Rate of change for momentum
        adx = row.get('adx', 20)  # ADX for trend strength
        trend_strength = row.get('trend_strength', 0)

        if pd.isna(sma_20) or pd.isna(sma_50) or pd.isna(close):
            return 0

        # Basic trend conditions
        trend_bullish = close > sma_20 > sma_50 * 0.99  # Less strict trend condition
        trend_bearish = close < sma_20 < sma_50 * 1.01  # Less strict trend condition

        # Add momentum confirmation
        momentum_bullish = pd.notna(roc) and roc > 0.0005  # Even smaller threshold
        momentum_bearish = pd.notna(roc) and roc < -0.0005  # Even smaller threshold

        # Regime: Only trade in strong trend conditions
        strong_trend = pd.isna(adx) or adx > 25  # ADX > 25 indicates trend
        sufficient_trend_strength = pd.isna(trend_strength) or trend_strength > 0.1

        if trend_bullish and (strong_trend or sufficient_trend_strength) and (pd.isna(roc) or momentum_bullish):
            return 1  # Buy
        elif trend_bearish and (strong_trend or sufficient_trend_strength) and (pd.isna(roc) or momentum_bearish):
            return -1  # Sell
        else:
            return 0  # Hold

    def mean_reversion_strategy(row, params):
        """Regime-aware mean reversion strategy using RSI and Bollinger Bands."""
        rsi = row.get('rsi', 50)
        bb_upper = row.get('bb_upper', 0)
        bb_lower = row.get('bb_lower', 0)
        close = row.get('close', 0)
        atr = row.get('atr', 0)
        adx = row.get('adx', 20)  # ADX for trend strength
        volatility_regime = row.get('volatility_regime', 0)

        if pd.isna(rsi) or pd.isna(bb_upper) or pd.isna(bb_lower) or pd.isna(close) or pd.isna(atr):
            return 0

        # Calculate how far price is from bands (relative position)
        if bb_upper != bb_lower:  # Avoid division by zero
            bb_position = (close - bb_lower) / (bb_upper - bb_lower)  # 0-1 scale
        else:
            bb_position = 0.5  # Neutral if bands are equal

        # More sensitive thresholds for entry
        rsi_oversold = 35  # More sensitive than 30
        rsi_overbought = 65  # More sensitive than 70

        # Regime: Only trade in ranging markets (weak trend)
        weak_trend = pd.isna(adx) or adx < 30  # ADX < 30 indicates ranging market

        # Oversold condition with potential bounce from lower band
        if rsi < rsi_oversold and bb_position < 0.4 and weak_trend:  # Near lower band in ranging market
            return 1  # Buy
        # Overbought condition with potential drop from upper band
        elif rsi > rsi_overbought and bb_position > 0.6 and weak_trend:  # Near upper band in ranging market
            return -1  # Sell
        else:
            return 0  # Hold

    def volatility_breakout_strategy(row, params):
        """Regime-aware volatility breakout strategy using ATR and price movement."""
        atr = row.get('atr', 0)
        high = row.get('high', 0)
        low = row.get('low', 0)
        close = row.get('close', 0)
        sma_20 = row.get('sma_20', 0)
        volume = row.get('volume', 0)
        sma_volume = row.get('sma_volume_20', 0)
        adx = row.get('adx', 20)  # ADX for trend strength
        volatility_percentile = row.get('volatility_percentile', 0.5)  # Volatility regime

        if any(pd.isna(x) for x in [atr, high, low, close, sma_20]):
            return 0

        # Define breakout thresholds based on ATR
        breakout_threshold = atr * 0.5  # Even more sensitive

        # Bullish breakout: price moves above recent range with volume confirmation
        bullish_breakout = close > max(high, sma_20) + breakout_threshold
        bearish_breakout = close < min(low, sma_20) - breakout_threshold

        # Volume confirmation (only if volume data available)
        volume_confirmation = True
        if pd.notna(volume) and pd.notna(sma_volume):
            volume_confirmation = volume > sma_volume * 0.9  # Less strict volume requirement

        # Regime: Only trade during high volatility periods
        high_volatility = pd.isna(volatility_percentile) or volatility_percentile > 0.5

        if bullish_breakout and volume_confirmation and high_volatility:
            return 1  # Buy
        elif bearish_breakout and volume_confirmation and high_volatility:
            return -1  # Sell
        else:
            return 0  # Hold

    def momentum_strategy(row, params):
        """Regime-aware momentum strategy using rate of change and volume."""
        roc = row.get('roc_10', 0)  # Rate of change over 10 periods
        volume = row.get('volume', 0)
        sma_volume = row.get('sma_volume_20', 0)
        rsi = row.get('rsi', 50)
        atr = row.get('atr', 0)
        adx = row.get('adx', 20)  # ADX for trend strength
        volatility_regime = row.get('volatility_regime', 0)

        if pd.isna(roc):
            return 0

        # Volume confirmation (only if available)
        volume_ok = True
        if pd.notna(volume) and pd.notna(sma_volume):
            volume_ok = volume > sma_volume * 0.8  # Less strict volume requirement

        # Regime: Only trade in trending markets where momentum is more effective
        trending_market = pd.isna(adx) or adx > 20  # Allow trading in mild trends

        # More sensitive momentum thresholds
        if roc > 0.001 and volume_ok and trending_market and (pd.isna(rsi) or 20 < rsi < 80):  # Less restrictive RSI
            return 1  # Buy
        elif roc < -0.001 and volume_ok and trending_market and (pd.isna(rsi) or 20 < rsi < 80):  # Less restrictive RSI
            return -1  # Sell
        else:
            return 0  # Hold

    def scalping_strategy(row, params):
        """Regime-aware scalping strategy using short-term indicators."""
        rsi = row.get('rsi', 50)
        sma_fast = row.get('sma_5', 0)
        sma_slow = row.get('sma_10', 0)
        close = row.get('close', 0)
        roc = row.get('roc_10', 0)  # For momentum confirmation
        adx = row.get('adx', 20)  # ADX for trend strength
        volatility_regime = row.get('volatility_regime', 0)

        if any(pd.isna(x) for x in [rsi, sma_fast, sma_slow, close]):
            return 0

        # Fast MA crosses above slow MA with momentum confirmation
        ma_bullish_cross = sma_fast > sma_slow  # Removed tight constraint
        ma_bearish_cross = sma_fast < sma_slow  # Removed tight constraint

        # Momentum confirmation
        mom_bullish = pd.isna(roc) or roc > 0
        mom_bearish = pd.isna(roc) or roc < 0

        # Regime: Scalping works better in higher volatility environments
        high_volatility = pd.isna(volatility_regime) or volatility_regime > 0.01  # Adjusted threshold

        if ma_bullish_cross and mom_bullish and high_volatility and 25 < rsi < 75:  # Wider RSI range
            return 1  # Buy
        elif ma_bearish_cross and mom_bearish and high_volatility and 25 < rsi < 75:  # Wider RSI range
            return -1  # Sell
        else:
            return 0  # Hold

    def breakout_strategy(row, params):
        """Regime-aware breakout strategy identifying resistance/support breakouts."""
        high_20 = row.get('high_20', 0)  # 20-period high
        low_20 = row.get('low_20', 0)  # 20-period low
        close = row.get('close', 0)
        atr = row.get('atr', 0)
        volume = row.get('volume', 0)
        sma_volume = row.get('sma_volume_20', 0)
        adx = row.get('adx', 20)  # ADX for trend strength
        volatility_percentile = row.get('volatility_percentile', 0.5)  # Volatility regime

        if any(pd.isna(x) for x in [high_20, low_20, close, atr]):
            return 0

        # More sensitive breakout thresholds
        breakout_sensitivity = atr * 0.2  # Even more sensitive

        # Clear breakout above resistance with ATR confirmation
        bullish_breakout = close > high_20 + breakout_sensitivity
        bearish_breakout = close < low_20 - breakout_sensitivity

        # Volume confirmation (only if available)
        volume_ok = True
        if pd.notna(volume) and pd.notna(sma_volume):
            volume_ok = volume > sma_volume * 0.8  # Less strict volume requirement

        # Regime: Only trade during high volatility periods where breakouts are more likely
        high_volatility = pd.isna(volatility_percentile) or volatility_percentile > 0.4

        if bullish_breakout and volume_ok and high_volatility:
            return 1  # Buy
        elif bearish_breakout and volume_ok and high_volatility:
            return -1  # Sell
        else:
            return 0  # Hold

    def liquidity_strategy(row, params):
        """Regime-aware liquidity-based strategy using volume and volatility."""
        volume = row.get('volume', 0)
        sma_volume = row.get('sma_volume_20', 0)
        atr = row.get('atr', 0)
        sma_atr = row.get('sma_atr_20', 0)
        rsi = row.get('rsi', 50)
        close = row.get('close', 0)
        adx = row.get('adx', 20)  # ADX for trend strength
        volatility_regime = row.get('volatility_regime', 0)

        if pd.isna(volume) or pd.isna(sma_volume):
            return 0

        # Calculate volume and volatility ratios
        volume_ratio = volume / sma_volume if sma_volume > 0 else 1
        vol_ratio = atr / sma_atr if pd.notna(atr) and pd.notna(sma_atr) and sma_atr > 0 else 1

        # Look for high volume and high volatility (liquidity events)
        high_liquidity = volume_ratio > 1.2 and (pd.isna(vol_ratio) or vol_ratio > 1.0)  # Less strict thresholds

        # Regime: Consider market conditions
        trending_market = pd.isna(adx) or adx > 25

        if high_liquidity and pd.notna(rsi):
            # In oversold territory - potential buying opportunity
            if rsi < 40 and trending_market:  # More sensitive RSI and trending market
                return 1  # Buy
            # In overbought territory - potential selling opportunity
            elif rsi > 60 and trending_market:  # More sensitive RSI and trending market
                return -1  # Sell
            else:
                return 0  # Hold in neutral zone
        elif high_liquidity:
            # If no RSI, use price action - if price is relatively low in recent range, buy
            return 1  # Default to buy in high liquidity situations if no other info
        else:
            return 0  # Hold if not high liquidity

    def mtf_trend_strategy(row, params):
        """Regime-aware multi-timeframe trend strategy combining different timeframes."""
        sma_20_short = row.get('sma_20_short', 0)  # Short-term trend
        sma_50_short = row.get('sma_50_short', 0)
        sma_20_long = row.get('sma_20_long', 0)  # Long-term trend
        sma_50_long = row.get('sma_50_long', 0)
        close = row.get('close', 0)
        roc_short = row.get('roc_10', 0)  # Short-term momentum
        adx = row.get('adx', 20)  # ADX for trend strength
        volatility_regime = row.get('volatility_regime', 0)

        if any(pd.isna(x) for x in [sma_20_short, sma_50_short, sma_20_long, sma_50_long, close]):
            return 0

        # Align trends across timeframes
        short_trend_bullish = sma_20_short > sma_50_short * 0.99  # Less strict
        long_trend_bullish = sma_20_long > sma_50_long * 0.99  # Less strict

        # Momentum confirmation
        mom_bullish = pd.isna(roc_short) or roc_short > 0.0001  # Very small positive momentum
        mom_bearish = pd.isna(roc_short) or roc_short < -0.0001  # Very small negative momentum

        # Regime: Only trade in strong trend conditions
        strong_trend = pd.isna(adx) or adx > 20  # Allow trading in mild trends

        if short_trend_bullish and long_trend_bullish and close > sma_20_short and mom_bullish and strong_trend:
            return 1  # Buy
        elif not short_trend_bullish and not long_trend_bullish and close < sma_20_short and mom_bearish and strong_trend:
            return -1  # Sell
        else:
            return 0  # Hold

    def oi_footprint_strategy(row, params):
        """Regime-aware OI (Open Interest) footprint strategy - using volume/volatility as proxy."""
        # Using volume and volatility as proxies for open interest
        volume = row.get('volume', 0)
        sma_volume = row.get('sma_volume_20', 0)
        atr = row.get('atr', 0)
        sma_atr = row.get('sma_atr_20', 0)
        rsi = row.get('rsi', 50)
        roc = row.get('roc_10', 0)
        adx = row.get('adx', 20)  # ADX for trend strength
        volatility_regime = row.get('volatility_regime', 0)

        if pd.isna(volume) or pd.isna(sma_volume):
            return 0

        # Calculate volume and volatility ratios (proxy for OI changes)
        volume_ratio = volume / sma_volume if sma_volume > 0 else 1
        vol_ratio = atr / sma_atr if pd.notna(atr) and pd.notna(sma_atr) and sma_atr > 0 else 1

        # High volume and high volatility often indicate institutional activity
        oi_increasing = volume_ratio > 1.5 and (pd.isna(vol_ratio) or vol_ratio > 1.2)  # Less strict thresholds

        # Regime: Consider market conditions
        trending_market = pd.isna(adx) or adx > 20

        if oi_increasing and pd.notna(rsi):
            # If OI proxy is increasing and RSI is oversold - potential accumulation
            if rsi < 45 and trending_market and (pd.notna(roc) and roc > -0.001):  # Less strict momentum
                return 1  # Buy
            # If OI proxy is increasing and RSI is overbought - potential distribution
            elif rsi > 55 and trending_market and (pd.notna(roc) and roc < 0.001):  # Less strict momentum
                return -1  # Sell
            else:
                return 0  # Hold
        else:
            return 0  # Hold if no clear OI signal

    def sweep_scalper_strategy(row, params):
        """Regime-aware sweep scalper strategy targeting liquidity."""
        high = row.get('high', 0)
        low = row.get('low', 0)
        close = row.get('close', 0)
        volume = row.get('volume', 0)
        sma_volume = row.get('sma_volume_20', 0)
        high_5 = row.get('high_5', 0)
        low_5 = row.get('low_5', 0)
        atr = row.get('atr', 0)
        adx = row.get('adx', 20)  # ADX for trend strength
        volatility_regime = row.get('volatility_regime', 0)

        if any(pd.isna(x) for x in [high, low, close, volume, high_5, low_5]):
            return 0

        # Look for high volume near recent highs/lows (potential liquidity sweeps)
        volume_spike = pd.notna(volume) and pd.notna(sma_volume) and volume > sma_volume * 1.2  # Less strict threshold

        # Check if price is near recent extremes
        near_high = high >= high_5 * 0.99  # Less strict - within 1% of 5-period high
        near_low = low <= low_5 * 1.01  # Less strict - within 1% of 5-period low

        # Check for potential sweep scenarios
        bullish_sweep = volume_spike and near_low and close > low  # Price moved away from low
        bearish_sweep = volume_spike and near_high and close < high  # Price moved away from high

        # Regime: Scalping works better in higher volatility environments
        high_volatility = pd.isna(volatility_regime) or volatility_regime > 0.005  # Adjusted threshold

        if bullish_sweep and high_volatility:
            return 1  # Buy - potential bullish sweep completed
        elif bearish_sweep and high_volatility:
            return -1  # Sell - potential bearish sweep completed
        else:
            return 0  # Hold

    def vwap_reversal_strategy(row, params):
        """Regime-aware VWAP reversal strategy."""
        close = row.get('close', 0)
        vwap = row.get('vwap', 0)
        rsi = row.get('rsi', 50)
        atr = row.get('atr', 0)
        adx = row.get('adx', 20)  # ADX for trend strength
        volatility_regime = row.get('volatility_regime', 0)

        if pd.isna(close) or pd.isna(vwap):
            return 0

        # Calculate distance from VWAP as percentage
        if vwap != 0:
            vwap_distance = (close - vwap) / vwap
        else:
            vwap_distance = 0

        # More sensitive thresholds for VWAP distance
        vwap_deviation_threshold = 0.003  # 0.3% instead of 0.5% - even more sensitive

        # Regime: Mean reversion works better in ranging markets
        ranging_market = pd.isna(adx) or adx < 35  # Allow in ranging markets

        # Price significantly above VWAP with overbought RSI - potential reversal down
        if vwap_distance > vwap_deviation_threshold and ranging_market and pd.notna(rsi) and rsi > 60:
            return -1  # Sell
        # Price significantly below VWAP with oversold RSI - potential reversal up
        elif vwap_distance < -vwap_deviation_threshold and ranging_market and pd.notna(rsi) and rsi < 40:
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

            # Fill NaN values with reasonable defaults instead of dropping all rows
            # This preserves more data for backtesting
            df_with_indicators = df_with_indicators.fillna(method='ffill').fillna(method='bfill')

            # If still have NaN values, fill with defaults
            df_with_indicators = df_with_indicators.fillna(0)

            if len(df_with_indicators) < 10:
                print(f"   ⚠️  Insufficient data after indicator calculation for {symbol}, skipping...")
                continue

            # Classify market regime based on indicators
            regime_info = classify_market_regime(df_with_indicators)
            results['regime_classification'][symbol] = regime_info

            # Run backtest
            backtest_result = backtester.run_backtest(
                data=df_with_indicators,
                strategy_function=strategy_function,
                strategy_params=strategy_params
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

    return results


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
