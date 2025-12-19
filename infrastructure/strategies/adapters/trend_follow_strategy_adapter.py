"""
Infrastructure implementation of the Trend Follow Strategy following hexagonal architecture.
"""
from typing import List, Optional, Dict, Any
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from domain.ports.engine_ports import StrategyPort
from shared.logger import logger
from datetime import datetime
from decimal import Decimal
import numpy as np
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class TrendFollowStrategyAdapter(BaseStrategyAdapter):
    """Infrastructure implementation of trend following strategy with technical analysis"""

    def __init__(self, lookback_period: int = 50, ma_type: str = "EMA", ma_period: int = 20):
        super().__init__("TrendFollow")
        self.lookback_period = lookback_period
        self.ma_type = ma_type
        self.ma_period = ma_period
        self.trend_strength_threshold = 0.01

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal using trend following logic with real market analysis"""
        if len(self.data_buffer) < self.ma_period + 1:
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least {self.ma_period + 1}")
            return None

        try:
            # Extract closing prices for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]

            if len(closes) < self.ma_period + 1:
                self.logger.debug(f"Not enough close prices for {self.name}: {len(closes)}")
                return None

            # Calculate trend indicators
            current_price = closes[-1]

            # Calculate moving averages (short and long term)
            calculated_ma_short = self.calculate_ema(closes, self.ma_period)
            calculated_ma_long = self.calculate_ema(closes, min(self.lookback_period, len(closes)))

            if not calculated_ma_short or not calculated_ma_long:
                self.logger.debug(f"Could not calculate moving averages for {self.name}")
                return None

            # Determine trend direction based on moving average crossover
            computed_trend_direction = "BULLISH" if calculated_ma_short > calculated_ma_long else "BEARISH"

            # Calculate trend strength
            recent_prices = closes[-20:] if len(closes) >= 20 else closes
            if len(recent_prices) < 2:
                return None

            # Calculate linear regression to determine trend strength
            x = np.arange(len(recent_prices))
            slope, _ = np.polyfit(x, recent_prices, 1) if len(recent_prices) > 1 else (0, 0)
            computed_trend_strength = abs(slope) / current_price if current_price > 0 else 0  # Normalize by current price

            # Calculate momentum
            momentum_period = min(10, len(closes) - 1)
            if momentum_period > 0 and len(closes) > momentum_period:
                computed_momentum = (current_price - closes[-momentum_period - 1]) / closes[-momentum_period - 1]
            else:
                computed_momentum = 0

            # Determine signal type based on trend and momentum
            final_signal_type = SignalType.HOLD
            final_confidence_factor = 0.3
            final_score = 0.0

            if computed_trend_direction == "BULLISH" and computed_trend_strength > self.trend_strength_threshold and computed_momentum > 0:
                final_signal_type = SignalType.BUY
                final_confidence_factor = min(1.0, computed_trend_strength * 50)  # Scale confidence based on trend strength
                final_score = min(1.0, computed_momentum * 10)  # Scale score based on momentum
            elif computed_trend_direction == "BEARISH" and computed_trend_strength > self.trend_strength_threshold and computed_momentum < 0:
                final_signal_type = SignalType.SELL
                final_confidence_factor = min(1.0, computed_trend_strength * 50)
                final_score = max(-1.0, computed_momentum * 10)

            # Calculate confidence based on multiple factors
            calculated_atr = self.calculate_atr(self.data_buffer, 14)
            if calculated_atr and current_price > 0:
                volatility_confidence = 1.0 if calculated_atr / current_price < 0.05 else 0.7  # Lower confidence in high volatility
                final_confidence_factor = min(final_confidence_factor, volatility_confidence)

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                strategy_name=self.name,
                timestamp=datetime.now(),
                source_engine="TrendFollowTechnical",
                metadata={
                    "trend_direction": computed_trend_direction,
                    "trend_strength": computed_trend_strength,
                    "momentum": computed_momentum,
                    "ma_short": calculated_ma_short,
                    "ma_long": calculated_ma_long,
                    "current_price": current_price,
                    "atr": calculated_atr
                }
            )

            # Log signal if generated
            if final_signal_type != SignalType.HOLD:
                self.logger.info(f"{self.name} generated signal: {signal.signal_type.name} with confidence {float(signal.confidence.value):.3f} for {symbol.value}")

            return signal

        except Exception as e:
            self.logger.error(f"Error in {self.name} strategy: {e}")
            import traceback
            traceback.print_exc()
            return None