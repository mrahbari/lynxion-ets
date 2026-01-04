from .base_watcher import BaseWatcher
from domain.entities.signal_entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
import os
from decimal import Decimal


class TickWatcherAdapter(BaseWatcher):
    """Tick Watcher - analyzes tick-by-tick market data, returns raw market observations"""

    def __init__(self, name: str, symbol: str, broker_service=None, lookback: int = 1000):
        super().__init__(name, symbol, broker_service, None)

        # Configuration from environment with defaults
        self.enabled = os.getenv('TICK_WATCHER_ENABLED', 'true').lower() == 'true'

        # Only set logger if enabled, otherwise use mock logger
        if self.enabled:
            self.logger = logger
        else:
            # Create a mock logger that doesn't log anything when disabled
            class MockLogger:
                def debug(self, msg): pass
                def info(self, msg): pass
                def warning(self, msg): pass
                def error(self, msg): pass
            self.logger = MockLogger()

        self.lookback = lookback
        self.tick_history = []  # [(price, volume, timestamp, side), ...]
        self.price_changes = []
        self.tick_sizes = []
        self.tick_directions = []  # ['up', 'down', 'same']
        self.volume_history = []

        # Tick analysis metrics
        self.tick_imbalance_ratio = 0.0
        self.tick_intensity = 0.0
        self.price_momentum = 0.0

        # Thresholds for different market conditions
        self.high_intensity_threshold = 50  # High tick intensity
        self.low_intensity_threshold = 5   # Low tick intensity
        self.momentum_threshold = 0.001    # Price momentum threshold

    def update_data(self, data: dict):
        """Update with new tick data"""
        if not self.enabled:
            return

        if 'tick' in data:
            tick = data['tick']
            current_time = datetime.now()

            # Add tick to history
            tick_entry = {
                'price': float(tick.get('price', 0)),
                'volume': float(tick.get('volume', tick.get('size', 0))),
                'timestamp': current_time,
                'side': tick.get('side', 'unknown')
            }

            self.tick_history.append(tick_entry)
            self.volume_history.append(tick_entry['volume'])

            # Calculate price change if we have previous tick
            if len(self.tick_history) > 1:
                prev_price = self.tick_history[-2]['price']
                current_price = tick_entry['price']
                price_change = current_price - prev_price
                self.price_changes.append(price_change)

                # Calculate tick direction
                if price_change > 0:
                    self.tick_directions.append('up')
                elif price_change < 0:
                    self.tick_directions.append('down')
                else:
                    self.tick_directions.append('same')

                # Calculate tick size
                self.tick_sizes.append(abs(price_change))

            # Keep history within limits
            if len(self.tick_history) > self.lookback * 3:
                self.tick_history.pop(0)
                if len(self.price_changes) > self.lookback * 3:
                    self.price_changes.pop(0)
                if len(self.tick_sizes) > self.lookback * 3:
                    self.tick_sizes.pop(0)
                if len(self.tick_directions) > self.lookback * 3:
                    self.tick_directions.pop(0)
                if len(self.volume_history) > self.lookback * 3:
                    self.volume_history.pop(0)

    def _analyze_impl(self, symbol: Symbol) -> MarketObservation:
        """Analyze tick data and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        if len(self.tick_history) < 10:  # Need sufficient ticks for analysis
            return None

        # Calculate tick analysis metrics
        tick_intensity = self._calculate_tick_intensity()
        tick_imbalance = self._calculate_tick_imbalance()
        price_momentum = self._calculate_price_momentum()
        volatility = self._calculate_tick_volatility()

        # Determine observation type based on tick analysis
        observation_type = self._determine_observation_type(tick_intensity, tick_imbalance, price_momentum)
        observation_value = self._calculate_observation_value(tick_imbalance, price_momentum, volatility)
        confidence = self._calculate_confidence(tick_intensity, volatility)

        # Convert confidence to Percentage object for domain compatibility
        confidence_percentage = Percentage(Decimal(str(confidence)))

        # Create and return a MarketObservation instead of a Signal
        observation = MarketObservation(
            symbol=symbol,
            observation_type=observation_type,
            observation_value=observation_value,
            confidence=confidence_percentage,
            timestamp=datetime.now(),
            metadata={
                'tick_intensity': tick_intensity,
                'tick_imbalance': tick_imbalance,
                'price_momentum': price_momentum,
                'tick_volatility': volatility,
                'total_ticks_analyzed': len(self.tick_history),
                'tick_frequency': tick_intensity,
                'tick_regime': self._get_tick_regime(tick_intensity),
                'momentum_regime': self._get_momentum_regime(price_momentum),
                'latest_tick_price': self.tick_history[-1]['price'] if self.tick_history else 0,
                'latest_tick_volume': self.tick_history[-1]['volume'] if self.tick_history else 0,
                'tick_source': self.name,
                'lookback_period': self.lookback
            }
        )

        return observation

    def _calculate_tick_intensity(self) -> float:
        """Calculate tick intensity (ticks per unit time)"""
        if len(self.tick_history) < 2:
            return 0.0

        # Calculate time difference between first and last tick
        first_time = self.tick_history[0]['timestamp']
        last_time = self.tick_history[-1]['timestamp']
        time_diff = (last_time - first_time).total_seconds()

        if time_diff > 0:
            intensity = len(self.tick_history) / time_diff
            return min(100.0, intensity)  # Cap at 100 ticks per second
        else:
            return 0.0

    def _calculate_tick_imbalance(self) -> float:
        """Calculate tick imbalance (up ticks vs down ticks)"""
        if not self.tick_directions:
            return 0.0

        up_ticks = self.tick_directions.count('up')
        down_ticks = self.tick_directions.count('down')
        total_ticks = len(self.tick_directions)

        if total_ticks == 0:
            return 0.0

        imbalance = (up_ticks - down_ticks) / total_ticks
        return max(-1.0, min(1.0, imbalance))  # Clamp between -1 and 1

    def _calculate_price_momentum(self) -> float:
        """Calculate price momentum based on recent price changes"""
        if len(self.price_changes) < 2:
            return 0.0

        # Calculate average price change
        avg_change = np.mean(self.price_changes[-20:]) if len(self.price_changes) >= 20 else np.mean(self.price_changes)
        
        # Calculate volatility of price changes for normalization
        if len(self.price_changes) > 1:
            vol_of_changes = np.std(self.price_changes[-20:]) if len(self.price_changes) >= 20 else np.std(self.price_changes)
            if vol_of_changes != 0:
                momentum = avg_change / vol_of_changes
            else:
                momentum = avg_change
        else:
            momentum = avg_change

        return max(-1.0, min(1.0, momentum))  # Clamp between -1 and 1

    def _calculate_tick_volatility(self) -> float:
        """Calculate volatility based on tick sizes"""
        if len(self.tick_sizes) < 2:
            return 0.0

        # Calculate volatility of tick sizes
        vol = np.std(self.tick_sizes[-50:]) if len(self.tick_sizes) >= 50 else np.std(self.tick_sizes)
        return min(1.0, vol * 1000)  # Scale appropriately

    def _determine_observation_type(self, tick_intensity: float, tick_imbalance: float, price_momentum: float) -> str:
        """Determine observation type based on tick analysis"""
        if tick_intensity < self.low_intensity_threshold:
            return 'tick_low_activity'
        elif tick_intensity > self.high_intensity_threshold:
            if tick_imbalance > 0.3:
                return 'tick_high_activity_buy_pressure'
            elif tick_imbalance < -0.3:
                return 'tick_high_activity_sell_pressure'
            else:
                return 'tick_high_activity_neutral'
        else:
            # Moderate tick intensity
            if abs(price_momentum) > self.momentum_threshold:
                if price_momentum > 0:
                    return 'tick_momentum_up'
                else:
                    return 'tick_momentum_down'
            elif tick_imbalance > 0.2:
                return 'tick_buy_imbalance'
            elif tick_imbalance < -0.2:
                return 'tick_sell_imbalance'
            else:
                return 'tick_normal'

    def _calculate_observation_value(self, tick_imbalance: float, price_momentum: float, volatility: float) -> float:
        """Calculate observation value based on tick metrics"""
        # Combine tick imbalance and price momentum with weights
        combined_value = (tick_imbalance * 0.6 + price_momentum * 0.4)
        
        # Normalize to [-1, 1] range
        return max(-1.0, min(1.0, combined_value))

    def _calculate_confidence(self, tick_intensity: float, volatility: float) -> float:
        """Calculate confidence based on tick metrics"""
        # Base confidence on tick intensity (more ticks = more reliable)
        intensity_factor = min(1.0, tick_intensity / 50.0)  # Normalize against 50 ticks/sec baseline

        # Adjust for volatility (higher volatility can indicate stronger signals)
        vol_factor = min(0.5, volatility * 2)  # Cap volatility contribution

        # Combine factors (dynamic, no hardcoded base)
        confidence = intensity_factor * 0.6 + vol_factor * 0.4

        return max(0.1, min(0.95, confidence))  # Clamp between 0.1 and 0.95

    def _get_tick_regime(self, tick_intensity: float) -> str:
        """Get current tick regime"""
        if tick_intensity > self.high_intensity_threshold:
            return 'high'
        elif tick_intensity < self.low_intensity_threshold:
            return 'low'
        else:
            return 'normal'

    def _get_momentum_regime(self, momentum: float) -> str:
        """Get current momentum regime"""
        if abs(momentum) > self.momentum_threshold * 3:
            return 'strong'
        elif abs(momentum) > self.momentum_threshold:
            return 'moderate'
        else:
            return 'weak'