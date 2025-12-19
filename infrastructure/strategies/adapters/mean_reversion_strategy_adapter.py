"""
Infrastructure implementation of the Mean Reversion Strategy following hexagonal architecture.
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


class MeanReversionStrategyAdapter(BaseStrategyAdapter):
    """Infrastructure implementation of mean reversion strategy with technical analysis"""

    def __init__(self, lookback_period: int = 20, std_dev_threshold: float = 1.5, rsi_oversold: int = 30, rsi_overbought: int = 70):
        super().__init__("MeanReversion")
        self.lookback_period = lookback_period
        self.std_dev_threshold = std_dev_threshold
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_period = 20
        self.bb_std_dev = 2.0

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal using mean reversion logic with real market analysis"""
        if len(self.data_buffer) < max(self.lookback_period, 15):
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least {max(self.lookback_period, 15)}")
            return None

        try:
            # Extract closing prices for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]

            if len(closes) < max(self.lookback_period, 15):
                self.logger.debug(f"Not enough close prices for {self.name}: {len(closes)}")
                return None

            current_price = closes[-1]

            # Calculate RSI
            calculated_rsi = self.calculate_rsi(closes, 14)

            # Calculate Bollinger Bands
            calculated_bb_upper, calculated_bb_middle, calculated_bb_lower = self.calculate_bollinger_bands(closes, self.bb_period, self.bb_std_dev)

            # Check for oversold condition (potential BUY signal)
            is_oversold = calculated_rsi is not None and calculated_rsi < self.rsi_oversold
            is_below_lower_bb = calculated_bb_lower is not None and current_price < calculated_bb_lower

            # Check for overbought condition (potential SELL signal)
            is_overbought = calculated_rsi is not None and calculated_rsi > self.rsi_overbought
            is_above_upper_bb = calculated_bb_upper is not None and current_price > calculated_bb_upper

            # Determine signal based on multiple indicators
            final_signal_type = SignalType.HOLD
            final_confidence_factor = 0.2
            final_score = 0.0

            if is_oversold and is_below_lower_bb:
                final_signal_type = SignalType.BUY
                # Confidence increases as RSI gets lower and price is deeper below lower band
                confidence_rsi = min(1.0, (self.rsi_oversold - calculated_rsi) / self.rsi_oversold) if calculated_rsi is not None else 0.5
                confidence_bb = min(1.0, (calculated_bb_middle - current_price) / (calculated_bb_middle - calculated_bb_lower if calculated_bb_lower and calculated_bb_middle-calculated_bb_lower > 0 else 1))
                final_confidence_factor = (confidence_rsi + confidence_bb) / 2
                final_score = -min(1.0, (calculated_bb_middle - current_price) / (calculated_bb_middle - calculated_bb_lower if calculated_bb_lower and calculated_bb_middle-calculated_bb_lower > 0 else 1))
            elif is_overbought and is_above_upper_bb:
                final_signal_type = SignalType.SELL
                # Confidence increases as RSI gets higher and price is higher above upper band
                confidence_rsi = min(1.0, (calculated_rsi - self.rsi_overbought) / (100 - self.rsi_overbought)) if calculated_rsi is not None else 0.5
                confidence_bb = min(1.0, (current_price - calculated_bb_middle) / (calculated_bb_upper - calculated_bb_middle if calculated_bb_upper and calculated_bb_upper-calculated_bb_middle > 0 else 1))
                final_confidence_factor = (confidence_rsi + confidence_bb) / 2
                final_score = min(1.0, (current_price - calculated_bb_middle) / (calculated_bb_upper - calculated_bb_middle if calculated_bb_upper and calculated_bb_upper-calculated_bb_middle > 0 else 1))

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                strategy_name=self.name,
                timestamp=datetime.now(),
                source_engine="MeanReversionTechnical",
                metadata={
                    "rsi": calculated_rsi,
                    "bb_upper": calculated_bb_upper,
                    "bb_middle": calculated_bb_middle,
                    "bb_lower": calculated_bb_lower,
                    "current_price": current_price,
                    "is_oversold": is_oversold,
                    "is_overbought": is_overbought,
                    "is_below_lower_bb": is_below_lower_bb,
                    "is_above_upper_bb": is_above_upper_bb
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