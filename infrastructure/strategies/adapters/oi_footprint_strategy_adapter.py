"""
Infrastructure implementation of the OI Footprint Strategy following hexagonal architecture.
"""
from typing import Dict, Any, Optional, List
from domain.entities import Signal, SignalType
from domain.value_objects import Symbol, Percentage
from domain.ports.engine_ports import StrategyPort
from shared.logger import logger
from datetime import datetime
from decimal import Decimal
import numpy as np
from infrastructure.strategies.strategy_adapters import BaseStrategyAdapter


class OIFootprintStrategyAdapter(BaseStrategyAdapter):
    """Open Interest and volume footprint strategy"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("OIFootprint")
        # Get configuration from the centralized config system
        from infrastructure.strategies.strategy_config import get_oi_footprint_config
        system_config = get_oi_footprint_config()

        # NOTE: system_config contains execution settings (like min_confidence, max_position_size)
        # at the top level, and mathematical model params inside the nested 'parameters' dict.
        # We must extract and merge both so that key settings are correctly loaded into self.config
        # and do not fall back to obsolete system defaults.
        params = system_config.get('parameters', {})
        top_level = {k: v for k, v in system_config.items() if k != 'parameters'}
        self.config = {**top_level, **params, **(config or {})}
        self.oi_expansion = self.config.get("oi_expansion", 0.05)
        self.delta_strength = self.config.get("delta_strength", 5)

    def generate_signal(self, symbol: Symbol) -> Optional[Signal]:
        """Generate signal using OI and volume footprint analysis"""
        if len(self.data_buffer) < 25:  # Need sufficient data for analysis
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least 25")
            return None

        try:
            # Extract data for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]
            volumes = [item['volume'] for item in self.data_buffer if 'volume' in item]

            if len(closes) < 25 or len(volumes) < 25:
                self.logger.debug(f"Not enough data for {self.name}: closes={len(closes)}, volumes={len(volumes)}")
                return None

            current_price = closes[-1]
            current_volume = volumes[-1] if volumes else 0

            # Calculate volume indicators
            avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
            volume_spike = current_volume > avg_volume * 1.5 if avg_volume > 0 else False

            # Calculate price momentum to check for volume-price divergences
            momentum_period = min(5, len(closes) - 1)
            if momentum_period > 0:
                price_momentum = (current_price - closes[-momentum_period - 1]) / closes[-momentum_period - 1]
            else:
                price_momentum = 0

            # Calculate technical indicators in addition to volume analysis
            computed_rsi = self.calculate_rsi(closes, 14)
            computed_atr = self.calculate_atr(self.data_buffer, 14)

            # Look for volume-price divergences or unusual footprints combined with technical indicators
            final_signal_type = SignalType.HOLD
            final_confidence_factor = 0.5
            final_score = 0.0

            if volume_spike and price_momentum > 0 and (not computed_rsi or computed_rsi < 75):
                # High volume with positive price movement and not overbought - confirms trend
                final_signal_type = SignalType.BUY
                final_confidence_factor = min(1.0, 0.6 + abs(price_momentum))
                final_score = min(1.0, price_momentum * 5)
            elif volume_spike and price_momentum < 0 and (not computed_rsi or computed_rsi > 25):
                # High volume with negative price movement and not oversold - confirms trend
                final_signal_type = SignalType.SELL
                final_confidence_factor = min(1.0, 0.6 + abs(price_momentum))
                final_score = max(-1.0, price_momentum * 5)
            # Additional condition for mean reversion in high volume with opposing RSI
            elif volume_spike and computed_rsi and computed_rsi < 30 and price_momentum > 0:
                # High volume with positive momentum but RSI showing oversold - potential reversal
                final_signal_type = SignalType.BUY
                final_confidence_factor = min(1.0, 0.7 + (abs(price_momentum) + (70 - computed_rsi)/100) / 2)
                final_score = min(1.0, abs(price_momentum) * 3)
            elif volume_spike and computed_rsi and computed_rsi > 70 and price_momentum < 0:
                # High volume with negative momentum but RSI showing overbought - potential reversal
                final_signal_type = SignalType.SELL
                final_confidence_factor = min(1.0, 0.7 + (abs(price_momentum) + (computed_rsi - 30)/100) / 2)
                final_score = max(-1.0, price_momentum * 3)

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                timestamp=datetime.now(),
                source_layer="OIFootprintTechnical",
                metadata={
                    "current_price": current_price,
                    "current_volume": current_volume,
                    "avg_volume": avg_volume,
                    "volume_spike": volume_spike,
                    "price_momentum": price_momentum,
                    "rsi": computed_rsi,
                    "atr": computed_atr
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

    def calculate_position_size(self, signal: Signal, account_balance: float) -> float:
        """Request position size - this should be handled by the risk manager"""
        # According to the risk governance rules, the Strategy module should only
        # request risk parameters but not calculate them. The actual calculation
        # must be done by the Risk module.

        # Return a default value that will be overridden by the risk manager
        # This is just a placeholder to maintain interface compatibility
        return 0.0

    def get_strategy_name(self) -> str:
        """Get the name of the strategy"""
        return self.name