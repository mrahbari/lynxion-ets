"""
Infrastructure implementation of Base Strategy Adapter.
This file provides the minimal base infrastructure adapter that implements domain StrategyPort interface.
"""
from typing import List, Optional, Dict, Any
from domain.entities.trading_entities import Signal, Order
from domain.value_objects import Symbol, Percentage, Money
from domain.ports.engine_ports import StrategyPort
from shared.logger import logger
from datetime import datetime
from decimal import Decimal
import numpy as np


class BaseStrategyAdapter(StrategyPort):
    """Base class for strategy adapters implementing StrategyPort"""

    def __init__(self, name: str):
        self.name = name
        self.last_signal_time = None
        self.logger = logger
        # Initialize data buffer for market data storage
        self.data_buffer = []
        self.buffer_size_limit = 1000

    def update_with_market_data(self, data: Dict[str, Any]):
        """Update strategy with new market data"""
        # Buffer recent market data for analysis
        if isinstance(data, list):
            self.data_buffer.extend(data)
        elif isinstance(data, dict):
            self.data_buffer.append(data)

        # Limit buffer size to prevent memory issues
        if len(self.data_buffer) > self.buffer_size_limit:
            self.data_buffer = self.data_buffer[-self.buffer_size_limit:]

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate signal - base implementation returns None"""
        # Base implementation - should be overridden by specific strategies
        return None

    def calculate_position_size(self, signal: Signal, account_balance: float) -> float:
        """Calculate appropriate position size for a signal"""
        # Base implementation - use a percentage of account balance based on signal confidence
        risk_per_trade = 0.02  # Risk 2% of account per trade
        position_risk = risk_per_trade * float(signal.confidence.value)
        return account_balance * position_risk

    def get_strategy_name(self) -> str:
        """Get the name of the strategy"""
        return self.name

    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return None

        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        # Calculate initial average gain/loss
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        # Calculate subsequent average gain/loss using Wilder's smoothing method
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return None

        multiplier = 2 / (period + 1)
        ema = prices[0]

        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average"""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0):
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return None, None, None

        sma = self.calculate_sma(prices, period)
        if sma is None:
            return None, None, None

        std = np.std(prices[-period:])
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return upper_band, sma, lower_band

    def calculate_atr(self, data: List[Dict], period: int = 14) -> Optional[float]:
        """Calculate Average True Range"""
        if len(data) < period + 1:
            return None

        true_ranges = []
        for i in range(1, min(len(data), period + 1)):
            item = data[-i]
            prev_item = data[-i-1] if i+1 < len(data) else data[-i]

            high = item.get('high', item.get('close', 0))
            low = item.get('low', item.get('close', 0))
            prev_close = prev_item.get('close', item.get('close', 0))

            tr = max(
                abs(high - low),
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)

        if not true_ranges:
            return None

        return sum(true_ranges) / len(true_ranges)