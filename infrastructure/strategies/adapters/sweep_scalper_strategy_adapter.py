"""
Infrastructure implementation of the Sweep Scalper Strategy following hexagonal architecture.
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


class SweepScalperAdapter(BaseStrategyAdapter):
    """Liquidity sweep scalping strategy"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("SweepScalper")
        self.config = config or {}
        self.killzone = self.config.get("killzone", ["UTC-13:00", "UTC-01:00"])
        self.lookback = self.config.get("lookback", 4)

    def detect_sweep(self, df):
        """Detect liquidity sweeps"""
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
        """Generate signal using liquidity sweep scalping with real market data"""
        if len(self.data_buffer) < 10:  # Need sufficient data for analysis
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least 10")
            return None

        try:
            # Extract data for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]
            highs = [item.get('high', item['close']) for item in self.data_buffer if 'close' in item]
            lows = [item.get('low', item['close']) for item in self.data_buffer if 'close' in item]
            volumes = [item['volume'] for item in self.data_buffer if 'volume' in item]

            if len(closes) < 10 or len(volumes) < 10:
                self.logger.debug(f"Not enough data for {self.name}: closes={len(closes)}, volumes={len(volumes)}")
                return None

            current_price = closes[-1]
            current_volume = volumes[-1] if volumes else 0

            # Calculate volatility measures to detect potential sweeps
            recent_highs = highs[-self.lookback:]
            recent_lows = lows[-self.lookback:]
            calculated_recent_range = max(recent_highs) - min(recent_lows) if recent_highs and recent_lows else 0

            historical_range = np.std(closes[-20:]) if len(closes) >= 20 else 0

            # Detect potential liquidity sweep patterns
            # Based on price movement exceeding recent volatility
            computed_is_potential_sweep = calculated_recent_range > historical_range * 1.5 if historical_range > 0 else False

            # Calculate momentum to confirm direction
            momentum_period = min(3, len(closes) - 1)
            if momentum_period > 0:
                computed_momentum = (current_price - closes[-momentum_period - 1]) / closes[-momentum_period - 1]
            else:
                computed_momentum = 0

            # Determine signal based on sweep detection and momentum
            final_signal_type = SignalType.HOLD
            final_confidence_factor = 0.5
            final_score = 0.0

            if computed_is_potential_sweep and computed_momentum > 0:
                # Potential upward sweep with positive momentum - scalping opportunity
                final_signal_type = SignalType.BUY
                final_confidence_factor = min(1.0, 0.7 + abs(computed_momentum) * 0.5)
                final_score = min(1.0, computed_momentum * 5)
            elif computed_is_potential_sweep and computed_momentum < 0:
                # Potential downward sweep with negative momentum - scalping opportunity
                final_signal_type = SignalType.SELL
                final_confidence_factor = min(1.0, 0.7 + abs(computed_momentum) * 0.5)
                final_score = max(-1.0, computed_momentum * 5)

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                strategy_name=self.name,
                timestamp=datetime.now(),
                source_engine="SweepScalperTechnical",
                metadata={
                    "current_price": current_price,
                    "current_volume": current_volume,
                    "recent_range": calculated_recent_range,
                    "historical_range": historical_range,
                    "is_potential_sweep": computed_is_potential_sweep,
                    "momentum": computed_momentum
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
        """Calculate appropriate position size for a signal"""
        # Base implementation - use a percentage of account balance based on signal confidence
        risk_per_trade = 0.02  # Risk 2% of account per trade
        position_risk = risk_per_trade * float(signal.confidence.value)
        return account_balance * position_risk

    def get_strategy_name(self) -> str:
        """Get the name of the strategy"""
        return self.name