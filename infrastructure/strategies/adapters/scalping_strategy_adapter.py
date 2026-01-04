"""
Infrastructure implementation of the Scalping Strategy following hexagonal architecture.
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


class ScalpingStrategyAdapter(BaseStrategyAdapter):
    """Infrastructure implementation of scalping strategy with technical analysis"""

    def __init__(self, lookback_period: int = 5, profit_target: float = 0.005, stop_loss: float = 0.003, rsi_period: int = 14):
        super().__init__("Scalper")
        self.lookback_period = lookback_period
        self.profit_target = profit_target
        self.stop_loss = stop_loss
        self.rsi_period = rsi_period
        self.momentum_period = 3
        self.ma_fast = 5
        self.ma_slow = 10

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate a signal using scalping logic with real market analysis"""
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

            # Calculate fast and slow moving averages for crossover
            calculated_ma_fast = self.calculate_ema(closes, self.ma_fast)
            calculated_ma_slow = self.calculate_ema(closes, self.ma_slow)

            # Calculate short-term momentum
            momentum_period = min(self.momentum_period, len(closes) - 1)
            if momentum_period > 0 and len(closes) > momentum_period:
                calculated_momentum = (current_price - closes[-momentum_period - 1]) / closes[-momentum_period - 1]
            else:
                calculated_momentum = 0

            # Calculate RSI for overbought/oversold conditions
            calculated_rsi = self.calculate_rsi(closes, self.rsi_period)

            # Calculate volume if available (volume might not always be present)
            recent_volumes = [item['volume'] for item in self.data_buffer[-5:] if 'volume' in item]
            avg_volume = np.mean(recent_volumes) if recent_volumes else 0
            current_volume = self.data_buffer[-1].get('volume', 0) if len(self.data_buffer) > 0 else 0
            volume_spike = current_volume > avg_volume * 1.5 if avg_volume > 0 else False

            # Determine signal based on multiple scalping indicators
            final_signal_type = SignalType.HOLD
            final_confidence_factor = 0.3
            final_score = 0.0

            ma_crossover_signal = None
            if calculated_ma_fast and calculated_ma_slow:
                if calculated_ma_fast > calculated_ma_slow:  # Bullish crossover
                    ma_crossover_signal = SignalType.BUY
                elif calculated_ma_fast < calculated_ma_slow:  # Bearish crossover
                    ma_crossover_signal = SignalType.SELL

            # Combine signals with volume confirmation
            if ma_crossover_signal == SignalType.BUY and calculated_momentum > 0 and (not calculated_rsi or calculated_rsi < 70):  # Not overbought
                final_signal_type = SignalType.BUY
                final_confidence_factor = min(1.0, (calculated_momentum + 0.5) / 1.5)  # Higher confidence with positive momentum
                final_score = min(1.0, calculated_momentum * 5)
            elif ma_crossover_signal == SignalType.SELL and calculated_momentum < 0 and (not calculated_rsi or calculated_rsi > 30):  # Not oversold
                final_signal_type = SignalType.SELL
                final_confidence_factor = min(1.0, (abs(calculated_momentum) + 0.5) / 1.5)
                final_score = max(-1.0, calculated_momentum * 5)

            # Enhance confidence if volume spike confirms signal
            if volume_spike and final_signal_type != SignalType.HOLD:
                final_confidence_factor = min(1.0, final_confidence_factor * 1.2)

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                strategy_name=self.name,
                timestamp=datetime.now(),
                source_engine="ScalpingTechnical",
                metadata={
                    "ma_fast": calculated_ma_fast,
                    "ma_slow": calculated_ma_slow,
                    "momentum": calculated_momentum,
                    "rsi": calculated_rsi,
                    "volume_spike": volume_spike,
                    "current_price": current_price
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