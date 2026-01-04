"""
Infrastructure implementation of the MTF Trend Strategy following hexagonal architecture.
"""
from typing import Dict, Any, Optional, List
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from domain.ports.engine_ports import StrategyPort
from shared.logger import logger
from datetime import datetime
from decimal import Decimal
import numpy as np
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class MTFTrendStrategyAdapter(BaseStrategyAdapter):
    """Multi-timeframe trend strategy"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("MTFTrend")
        self.config = config or {}
        self.timeframes = ["3m", "15m", "1h", "4h", "1D"]
        self.trend_period = self.config.get("trend_period", 50)
        self.weighting = self.config.get("tf_weights", {
            "3m": 0.10,
            "15m": 0.20,
            "1h": 0.25,
            "4h": 0.25,
            "1D": 0.20
        })

    def compute_trend(self, df):
        """Compute trend for a dataframe"""
        # This method would operate on actual market data when available
        # For now, returning neutral as mock
        return 0

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
        """Generate signal using multi-timeframe trend analysis with real market data"""
        if len(self.data_buffer) < 50:  # Need sufficient data for analysis
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least 50")
            return None

        try:
            # Extract closing prices for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]

            if len(closes) < 50:
                self.logger.debug(f"Not enough close prices for {self.name}: {len(closes)}")
                return None

            current_price = closes[-1]

            # Calculate moving averages with different periods to represent different timeframes
            ma_short = self.calculate_ema(closes, 20)  # Short timeframe
            ma_medium = self.calculate_ema(closes, 50)  # Medium timeframe
            ma_long = self.calculate_ema(closes, 100)  # Long timeframe

            if not (ma_short and ma_medium and ma_long):
                self.logger.debug(f"Could not calculate all moving averages for {self.name}")
                return None

            # Determine trend alignment across timeframes (multi-timeframe confirmation)
            trend_aligned = (ma_short > ma_medium > ma_long) or (ma_short < ma_medium < ma_long)
            trend_direction = "BULLISH" if ma_short > ma_long else "BEARISH"

            # Calculate momentum to confirm trend direction
            momentum_period = min(10, len(closes) - 1)
            if momentum_period > 0:
                momentum = (current_price - closes[-momentum_period - 1]) / closes[-momentum_period - 1]
            else:
                momentum = 0

            # Determine signal based on multi-timeframe alignment and momentum
            final_signal_type = SignalType.HOLD
            final_confidence_factor = 0.5  # Default for neutral strategy
            final_score = 0.0

            if trend_aligned and trend_direction == "BULLISH" and momentum > 0:
                final_signal_type = SignalType.BUY
                final_confidence_factor = min(1.0, 0.6 + (momentum * 5))  # Higher confidence in aligned trend with positive momentum
                final_score = min(1.0, momentum * 10)
            elif trend_aligned and trend_direction == "BEARISH" and momentum < 0:
                final_signal_type = SignalType.SELL
                final_confidence_factor = min(1.0, 0.6 + (abs(momentum) * 5))  # Higher confidence in aligned trend with negative momentum
                final_score = max(-1.0, momentum * 10)

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                strategy_name=self.name,
                timestamp=datetime.now(),
                source_engine="MTFTrendTechnical",
                metadata={
                    "ma_short": ma_short,
                    "ma_medium": ma_medium,
                    "ma_long": ma_long,
                    "trend_aligned": trend_aligned,
                    "trend_direction": trend_direction,
                    "momentum": momentum,
                    "current_price": current_price
                }
            )

            if final_signal_type != SignalType.HOLD:
                self.logger.info(f"{self.name} generated signal: {signal.signal_type.name} with confidence {float(signal.confidence.value):.3f} for {symbol.value}")

            return signal

        except Exception as e:
            self.logger.error(f"Error in {self.name} strategy: {e}")
            import traceback
            traceback.print_exc()
            return None

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

    def calculate_position_size(self, signal: Signal, account_balance: float) -> float:
        """Calculate appropriate position size for a signal"""
        # Base implementation - use a percentage of account balance based on signal confidence
        risk_per_trade = 0.02  # Risk 2% of account per trade
        position_risk = risk_per_trade * float(signal.confidence.value)
        return account_balance * position_risk

    def get_strategy_name(self) -> str:
        """Get the name of the strategy"""
        return self.name