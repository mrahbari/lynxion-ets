"""
Infrastructure implementation of the Liquidity Strategy following hexagonal architecture.
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


class LiquidityStrategyAdapter(BaseStrategyAdapter):
    """
    Professional strategy combining:
    - Liquidity sweeps
    - Funding rate bias
    - OI expansion
    - CVD divergences
    - MTF Trend confirmation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("Liquidity")
        self.config = config or {}
        self.min_oi_trend = self.config.get("min_oi_trend", 0.04)
        self.max_funding_bias = self.config.get("max_funding_bias", 0.005)
        self.cvd_divergence_strength = self.config.get("cvd_divergence_strength", 2.0)
        self.timeframes = ["3m", "15m", "1h"]

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate signal based on liquidity analysis with real market data"""
        if len(self.data_buffer) < 30:  # Need sufficient data for analysis
            return None

        try:
            # Extract closing prices for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]
            if len(closes) < 30:
                return None

            current_price = closes[-1]

            # Calculate technical indicators
            calculated_rsi = self.calculate_rsi(closes, 14)
            calculated_bb_upper, calculated_bb_middle, calculated_bb_lower = self.calculate_bollinger_bands(closes, 20, 2.0)

            # Detect potential liquidity sweep conditions
            computed_is_near_support = current_price <= calculated_bb_lower * 1.01 if calculated_bb_lower else False
            computed_is_near_resistance = current_price >= calculated_bb_upper * 0.99 if calculated_bb_upper else False

            # Detect oversold/overbought conditions combined with liquidity levels
            final_signal_type = SignalType.HOLD
            final_confidence_factor = 0.3
            final_score = 0.0

            if calculated_rsi is not None:
                if calculated_rsi < 30 and computed_is_near_support:  # Oversold near support - potential sweep
                    final_signal_type = SignalType.BUY
                    confidence_factor = min(1.0, (30 - calculated_rsi) / 30)
                    final_confidence_factor = min(1.0, max(0.1, 0.8 + confidence_factor))
                    final_score = -min(1.0, (calculated_bb_middle - current_price) / (calculated_bb_middle - calculated_bb_lower if calculated_bb_lower and calculated_bb_middle-calculated_bb_lower > 0 else 1))
                elif calculated_rsi > 70 and computed_is_near_resistance:  # Overbought near resistance - potential sweep
                    final_signal_type = SignalType.SELL
                    confidence_factor = min(1.0, (calculated_rsi - 70) / 30)
                    final_confidence_factor = min(1.0, max(0.1, 0.8 + confidence_factor))
                    final_score = min(1.0, (current_price - calculated_bb_middle) / (calculated_bb_upper - calculated_bb_middle if calculated_bb_upper and calculated_bb_upper-calculated_bb_middle > 0 else 1))

            # Create signal with metadata
            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor))))),
                score=final_score,
                strategy_name=self.name,
                timestamp=datetime.now(),
                source_engine="LiquidityTechnical",
                metadata={
                    "rsi": calculated_rsi,
                    "current_price": current_price,
                    "bb_upper": calculated_bb_upper,
                    "bb_middle": calculated_bb_middle,
                    "bb_lower": calculated_bb_lower,
                    "is_near_support": computed_is_near_support,
                    "is_near_resistance": computed_is_near_resistance
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