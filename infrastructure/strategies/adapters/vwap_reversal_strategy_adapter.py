"""
Infrastructure implementation of the VWAP Reversal Strategy following hexagonal architecture.
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


class VWAPReversalStrategyAdapter(BaseStrategyAdapter):
    """VWAP reversal strategy"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("VWAPReversal")
        self.config = config or {}
        self.lookback = self.config.get("lookback", 200)
        self.std_mult = self.config.get("std_mult", 2.0)

    def compute_vwap(self, df):
        """Compute VWAP for a dataframe"""
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
        """Generate signal using VWAP reversal analysis with real market data"""
        if len(self.data_buffer) < 50:  # Need sufficient data for VWAP calculation
            self.logger.debug(f"Not enough data for {self.name}: {len(self.data_buffer)}, need at least 50")
            return None

        try:
            # Extract data for analysis
            closes = [item['close'] for item in self.data_buffer if 'close' in item]
            highs = [item.get('high', item['close']) for item in self.data_buffer if 'close' in item]
            lows = [item.get('low', item['close']) for item in self.data_buffer if 'close' in item]
            volumes = [item['volume'] for item in self.data_buffer if 'volume' in item]

            if len(closes) < 50 or len(volumes) < 50:
                self.logger.debug(f"Not enough data for {self.name}: closes={len(closes)}, volumes={len(volumes)}")
                return None

            current_price = closes[-1]

            # Calculate a simplified VWAP equivalent using price and volume
            # In real implementation, VWAP requires intraday high-frequency data
            # Here we'll use a volume-weighted average price proxy
            if volumes and sum(volumes) > 0:
                # Calculate volume-weighted price for recent data
                recent_closes = closes[-self.lookback:]
                recent_volumes = volumes[-self.lookback:]
                if len(recent_closes) == len(recent_volumes):
                    total_pv = sum(c * v for c, v in zip(recent_closes, recent_volumes))
                    total_v = sum(recent_volumes)
                    if total_v > 0:
                        calculated_vwap_proxy = total_pv / total_v
                    else:
                        calculated_vwap_proxy = sum(recent_closes) / len(recent_closes)  # Use simple average as fallback
                else:
                    calculated_vwap_proxy = sum(recent_closes) / len(recent_closes)  # Use simple average as fallback
            else:
                calculated_vwap_proxy = sum(closes[-self.lookback:]) / min(self.lookback, len(closes))  # Use simple average as fallback

            # Calculate deviation from VWAP proxy
            price_deviation = (current_price - calculated_vwap_proxy) / calculated_vwap_proxy if calculated_vwap_proxy != 0 else 0

            # Calculate standard deviation for band construction
            price_std = np.std(closes[-self.lookback:]) if len(closes) >= self.lookback else np.std(closes)
            calculated_upper_band = calculated_vwap_proxy + (price_std * self.std_mult)
            calculated_lower_band = calculated_vwap_proxy - (price_std * self.std_mult)

            # Determine signal based on deviation from VWAP and bands
            final_signal_type = SignalType.HOLD
            final_confidence_factor = 0.5
            final_score = 0.0

            if current_price > calculated_upper_band:
                # Price significantly above VWAP - potential reversal down
                final_signal_type = SignalType.SELL
                strength = (current_price - calculated_vwap_proxy) / calculated_vwap_proxy if calculated_vwap_proxy != 0 else 0
                final_confidence_factor = min(1.0, 0.6 + abs(strength) * 0.3)
                final_score = max(-1.0, -abs(strength) * 5)
            elif current_price < calculated_lower_band:
                # Price significantly below VWAP - potential reversal up
                final_signal_type = SignalType.BUY
                strength = (calculated_vwap_proxy - current_price) / calculated_vwap_proxy if calculated_vwap_proxy != 0 else 0
                final_confidence_factor = min(1.0, 0.6 + abs(strength) * 0.3)
                final_score = min(1.0, abs(strength) * 5)
            else:
                # Price within bands - no reversal expected
                final_signal_type = SignalType.HOLD
                final_confidence_factor = 0.3
                final_score = 0.0

            confidence = Percentage(Decimal(str(min(1.0, max(0.1, final_confidence_factor)))))

            signal = Signal(
                symbol=symbol,
                signal_type=final_signal_type,
                confidence=confidence,
                score=final_score,
                strategy_name=self.name,
                timestamp=datetime.now(),
                source_engine="VWAPReversalTechnical",
                metadata={
                    "current_price": current_price,
                    "vwap_proxy": calculated_vwap_proxy,
                    "price_deviation": price_deviation,
                    "upper_band": calculated_upper_band,
                    "lower_band": calculated_lower_band,
                    "price_std": price_std
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