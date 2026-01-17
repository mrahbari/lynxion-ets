from .base_watcher import BaseWatcher
from domain.entities.signal_entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import os
from decimal import Decimal


class FundingRateWatcher(BaseWatcher):
    """Funding Rate Watcher - analyzes funding rates for perpetual contracts, returns raw market observations"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 24):
        # Convert symbol string to Symbol object if needed
        symbol_obj = Symbol(symbol) if isinstance(symbol, str) else symbol
        super().__init__(name, symbol_obj)

        # Store broker service and other parameters separately
        self.broker_service = broker_service
        self.target_broker = target_broker

        # Configuration from environment with defaults
        self.enabled = os.getenv('FUNDING_RATE_WATCHER_ENABLED', 'true').lower() == 'true'

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
        self.funding_rates_history = []
        self.funding_rate_timestamps = []

        # Thresholds for different market conditions
        self.high_funding_threshold = 0.005  # 0.5% per funding period
        self.low_funding_threshold = -0.005  # -0.5% per funding period
        self.extreme_funding_threshold = 0.01  # 1% per funding period

    def update_data(self, data: dict):
        """Update with new funding rate data"""
        if not self.enabled:
            return

        if 'funding_rate' in data:
            # Add new funding rate with timestamp
            self.funding_rates_history.append(data['funding_rate'])
            self.funding_rate_timestamps.append(datetime.now())

            # Keep history within limits
            if len(self.funding_rates_history) > self.lookback * 3:
                self.funding_rates_history.pop(0)
                self.funding_rate_timestamps.pop(0)

    def _analyze_impl(self, symbol: Symbol) -> MarketObservation:
        """Analyze funding rates and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        if not self.funding_rates_history:
            return None

        # Get current and historical funding rates
        current_funding_rate = self.funding_rates_history[-1] if self.funding_rates_history else 0
        avg_funding_rate = sum(self.funding_rates_history) / len(self.funding_rates_history) if self.funding_rates_history else 0

        # Calculate funding rate metrics
        funding_rate_change = current_funding_rate - avg_funding_rate
        funding_rate_volatility = self._calculate_funding_rate_volatility()

        # Determine observation type based on funding rate conditions
        if abs(current_funding_rate) > self.extreme_funding_threshold:
            if current_funding_rate > 0:
                observation_type = 'funding_rate_extremely_positive'  # Longs paying high funding
                observation_value = abs(current_funding_rate)
            else:
                observation_type = 'funding_rate_extremely_negative'  # Shorts paying high funding
                observation_value = -abs(current_funding_rate)
            confidence = min(0.95, abs(current_funding_rate) * 50)  # Higher confidence for extreme rates
        elif current_funding_rate > self.high_funding_threshold:
            observation_type = 'funding_rate_positive'  # Longs paying funding
            observation_value = abs(current_funding_rate)
            confidence = min(0.8, abs(current_funding_rate) * 20)
        elif current_funding_rate < self.low_funding_threshold:
            observation_type = 'funding_rate_negative'  # Shorts paying funding
            observation_value = -abs(current_funding_rate)
            confidence = min(0.8, abs(current_funding_rate) * 20)
        else:
            observation_type = 'funding_rate_normal'  # Balanced market
            observation_value = 0.0
            # For neutral state, confidence is based on how close to neutral we are
            funding_magnitude = abs(current_funding_rate)
            confidence = min(0.6, (1.0 - funding_magnitude))

        # Adjust confidence based on volatility and change from average
        if funding_rate_volatility > 0.001:  # If there's significant volatility
            confidence = min(0.9, confidence + 0.1)
        if abs(funding_rate_change) > 0.001:  # If there's significant change from average
            confidence = min(0.9, confidence + 0.1)

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
                'current_funding_rate': current_funding_rate,
                'average_funding_rate': avg_funding_rate,
                'funding_rate_change_from_avg': funding_rate_change,
                'funding_rate_volatility': funding_rate_volatility,
                'funding_rate_history_length': len(self.funding_rates_history),
                'latest_funding_timestamp': self.funding_rate_timestamps[-1].isoformat() if self.funding_rate_timestamps else None,
                'funding_regime': self._get_funding_regime(current_funding_rate),
                'funding_source': self.name,
                'lookback_period': self.lookback
            }
        )

        return observation

    def analyze(self, symbol: Symbol) -> MarketObservation:
        """Analyze market conditions and return a raw market observation"""
        return self._analyze_impl(symbol)

    def _calculate_funding_rate_volatility(self) -> float:
        """Calculate volatility of funding rates"""
        if len(self.funding_rates_history) < 2:
            return 0.0

        import numpy as np
        rates = self.funding_rates_history
        return float(np.std(rates))

    def _get_funding_regime(self, funding_rate: float) -> str:
        """Get current funding rate regime"""
        if abs(funding_rate) > self.extreme_funding_threshold:
            return "extreme"
        elif funding_rate > self.high_funding_threshold:
            return "positive"
        elif funding_rate < self.low_funding_threshold:
            return "negative"
        else:
            return "normal"