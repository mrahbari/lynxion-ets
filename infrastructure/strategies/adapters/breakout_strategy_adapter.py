"""
Infrastructure implementation of the Breakout Strategy following hexagonal architecture.
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


class BreakoutStrategyAdapter(BaseStrategyAdapter):
    """Infrastructure implementation of breakout strategy with technical analysis"""

    def __init__(self, lookback_period: int = 20, consolidation_period: int = 10, breakout_threshold: float = 0.02):
        super().__init__("Breakout")
        self.lookback_period = lookback_period
        self.consolidation_period = consolidation_period
        self.breakout_threshold = breakout_threshold
        self.atr_period = 14

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal using breakout logic with real market analysis"""
        if len(self.data_buffer) < max(self.lookback_period, self.consolidation_period, 15):
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least {max(self.lookback_period, self.consolidation_period, 15)}")
            return None

        try:
            # Extract data for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]
            highs = [item.get('high', item['close']) for item in self.data_buffer if 'close' in item]
            lows = [item.get('low', item['close']) for item in self.data_buffer if 'close' in item]

            if len(closes) < max(self.lookback_period, self.consolidation_period, 15):
                self.logger.debug(f"Not enough prices for {self.name}: {len(closes)}")
                return None

            current_price = closes[-1]

            # Calculate consolidation: recent price range vs historical range
            recent_highs = highs[-self.consolidation_period:]
            recent_lows = lows[-self.consolidation_period:]
            calculated_recent_range = max(recent_highs) - min(recent_lows) if recent_highs and recent_lows else 0

            historical_highs = highs[-self.lookback_period:]
            historical_lows = lows[-self.lookback_period:]
            calculated_historical_range = max(historical_highs) - min(historical_lows) if historical_highs and historical_lows else 0

            # Calculate ATR for volatility normalization
            calculated_atr_value = self.calculate_atr(self.data_buffer, self.atr_period)

            # Calculate resistance (highest high in lookback period) and support (lowest low in lookback period)
            calculated_resistance = max(historical_highs) if historical_highs else 0
            calculated_support = min(historical_lows) if historical_lows else 0

            # Check for breakout conditions
            is_bullish_breakout = current_price > calculated_resistance * (1 + self.breakout_threshold) if calculated_resistance > 0 else False
            is_bearish_breakout = current_price < calculated_support * (1 - self.breakout_threshold) if calculated_support > 0 else False

            # Check for consolidation condition (price range is relatively narrow compared to historical range)
            is_consolidating = calculated_recent_range < (calculated_historical_range * 0.5) if calculated_historical_range > 0 else False

            # Calculate momentum to confirm breakout direction
            momentum_period = min(5, len(closes) - 1)
            if momentum_period > 0:
                calculated_momentum = (current_price - closes[-momentum_period - 1]) / closes[-momentum_period - 1]
            else:
                calculated_momentum = 0

            # Determine signal based on breakout conditions
            final_signal_type = SignalType.HOLD
            final_confidence_factor = 0.3
            final_score = 0.0

            if is_bullish_breakout and is_consolidating and calculated_momentum > 0:
                # Bullish breakout from consolidation with positive momentum
                final_signal_type = SignalType.BUY
                # Confidence based on how far the breakout is beyond resistance and recent momentum
                strength = (current_price - calculated_resistance) / calculated_resistance if calculated_resistance > 0 else 0
                final_confidence_factor = min(1.0, (strength + abs(calculated_momentum)) / 2)
                final_score = min(1.0, strength * 10)
            elif is_bearish_breakout and is_consolidating and calculated_momentum < 0:
                # Bearish breakout from consolidation with negative momentum
                final_signal_type = SignalType.SELL
                strength = (calculated_support - current_price) / calculated_support if calculated_support > 0 else 0
                final_confidence_factor = min(1.0, (strength + abs(calculated_momentum)) / 2)
                final_score = max(-1.0, -strength * 10)

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                strategy_name=self.name,
                timestamp=datetime.now(),
                source_engine="BreakoutTechnical",
                metadata={
                    "resistance": calculated_resistance,
                    "support": calculated_support,
                    "current_price": current_price,
                    "is_bullish_breakout": is_bullish_breakout,
                    "is_bearish_breakout": is_bearish_breakout,
                    "is_consolidating": is_consolidating,
                    "momentum": calculated_momentum,
                    "recent_range": calculated_recent_range,
                    "historical_range": calculated_historical_range,
                    "atr": calculated_atr_value
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