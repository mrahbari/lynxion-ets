from .base_watcher import BaseWatcher
from domain.entities.signal_entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
from decimal import Decimal
from infrastructure.logging.forensic_logger import forensic_logger
from application.configs.configs import Configs
from utils.config_helper import cfg_get, cfg_get_bool, cfg_get_int, cfg_get_float, cfg_get_list, cfg_get_str


class TrendMTFWatcher(BaseWatcher):
    """Multi-Timeframe Trend Watcher - analyzes trends across multiple timeframes, returns raw market observations"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, short_period: int = 5, medium_period: int = 15, long_period: int = 30):
        # Convert symbol string to Symbol object if needed
        symbol_obj = Symbol(symbol) if isinstance(symbol, str) else symbol
        super().__init__(name, symbol_obj)

        # Store broker service and other parameters separately
        self.broker_service = broker_service
        self.target_broker = target_broker

        # Configuration from environment with defaults
        self.enabled = cfg_get_bool(Configs.watcher, 'trend_mtf_watcher_enabled', True)

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

        self.short_period = short_period
        self.medium_period = medium_period
        self.long_period = long_period

        # Stores for different timeframes - each with independent state
        self.short_trend_state = {'direction': 0, 'strength': 0, 'timestamp': None}
        self.medium_trend_state = {'direction': 0, 'strength': 0, 'timestamp': None}
        self.long_trend_state = {'direction': 0, 'strength': 0, 'timestamp': None}

        self.price_history = []

        # Trend thresholds
        self.trend_threshold = 0.005  # 0.5% threshold for trend significance

    def update_data(self, data: dict):
        """Update with new market data"""
        if not self.enabled:
            return

        if 'close' in data:
            self.price_history.append(data['close'])
            if len(self.price_history) > self.long_period * 3:  # Keep more data for longer periods
                self.price_history.pop(0)

    def _analyze_impl(self, symbol: Symbol) -> MarketObservation:
        """Analyze multi-timeframe trends and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        if len(self.price_history) < 2:  # Require only 2 data points to start generating observations
            return None

        # Calculate trends for each timeframe
        short_trend = self.calculate_trend(self.price_history[-self.short_period:])
        medium_trend = self.calculate_trend(self.price_history[-self.medium_period:])
        long_trend = self.calculate_trend(self.price_history[-self.long_period:])

        # Update trend states
        self.short_trend_state = {'direction': short_trend[0], 'strength': short_trend[1], 'timestamp': datetime.now()}
        self.medium_trend_state = {'direction': medium_trend[0], 'strength': medium_trend[1], 'timestamp': datetime.now()}
        self.long_trend_state = {'direction': long_trend[0], 'strength': long_trend[1], 'timestamp': datetime.now()}

        # Calculate overall trend score (combination of all timeframes)
        overall_trend_score = self.calculate_overall_trend_score(short_trend, medium_trend, long_trend)

        # Determine observation type based on trend alignment
        # Calculate confidence based on trend alignment and strength
        trend_alignment = self.calculate_trend_alignment(short_trend, medium_trend, long_trend)
        trend_strength = max(abs(short_trend[1]), abs(medium_trend[1]), abs(long_trend[1]))

        # Lowered threshold for trend detection
        lowered_threshold = 0.001  # Much lower threshold to detect trends faster

        # 🛡️ DYNAMIC CONFIDENCE: Better granularity for MTF trends
        raw_confidence = (trend_alignment * 0.6 + trend_strength * 0.4)
        
        # Base confidence on alignment and strength, with higher confidence for clearer signals
        if abs(overall_trend_score) < lowered_threshold:
            observation_type = 'trend_neutral'
            observation_value = 0.0
            # For neutral trends, confidence is based on alignment
            confidence = min(0.6, trend_alignment * 0.6)
        elif overall_trend_score > 0:
            observation_type = 'trend_positive'  # Bullish trend
            observation_value = abs(overall_trend_score)
            
            if raw_confidence <= 0.8:
                confidence = 0.3 + (0.5 * raw_confidence)
            else:
                # Asymptotic approach to 0.95
                confidence = 0.8 + 0.15 * (1.0 - (1.0 / (raw_confidence * 5)))
                
            confidence = min(0.95, max(0.2, confidence))
        else:
            observation_type = 'trend_negative'  # Bearish trend
            observation_value = -abs(overall_trend_score)
            
            if raw_confidence <= 0.8:
                confidence = 0.3 + (0.5 * raw_confidence)
            else:
                confidence = 0.8 + 0.15 * (1.0 - (1.0 / (raw_confidence * 5)))
                
            confidence = min(0.95, max(0.2, confidence))

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
                'short_trend': {
                    'direction': short_trend[0],
                    'strength': short_trend[1]
                },
                'medium_trend': {
                    'direction': medium_trend[0],
                    'strength': medium_trend[1]
                },
                'long_trend': {
                    'direction': long_trend[0],
                    'strength': long_trend[1]
                },
                'overall_trend_score': overall_trend_score,
                'trend_alignment': self.calculate_trend_alignment(short_trend, medium_trend, long_trend),
                'trend_source': self.name,
                'price_history_length': len(self.price_history)
            }
        )

        # Log the watcher observation to forensic log
        forensic_logger.log_watcher_observation(
            watcher=self.name,
            symbol=symbol.value,
            exchange=getattr(self, 'target_broker', 'BINANCE'),  # Use target broker if available, otherwise default
            observation_type=observation_type,
            value=observation_value,
            confidence=float(confidence),
            timestamp=observation.timestamp
        )

        return observation

    def analyze(self, symbol: Symbol) -> MarketObservation:
        """Analyze market conditions and return a raw market observation"""
        return self._analyze_impl(symbol)

    def calculate_trend(self, prices):
        """Calculate trend direction and strength using linear regression"""
        if len(prices) < 2:
            return (0, 0)  # No trend if not enough data

        # Convert to numpy array
        prices = np.array(prices)
        x = np.arange(len(prices))

        # Calculate linear regression
        if len(x) > 1:
            slope = (len(x) * np.sum(x * prices) - np.sum(x) * np.sum(prices)) / \
                    (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)

            # Calculate average price for normalization
            avg_price = np.mean(prices)
            if avg_price != 0:
                normalized_slope = slope / avg_price
            else:
                normalized_slope = 0

            # Calculate trend strength (R-squared or similar measure)
            if len(prices) > 2:
                # Calculate R-squared as a measure of trend strength
                y_pred = slope * x + (np.mean(prices) - slope * np.mean(x))
                ss_res = np.sum((prices - y_pred) ** 2)
                ss_tot = np.sum((prices - np.mean(prices)) ** 2)
                if ss_tot != 0:
                    r_squared = 1 - (ss_res / ss_tot)
                    trend_strength = r_squared * abs(normalized_slope)
                else:
                    trend_strength = abs(normalized_slope)
            else:
                trend_strength = abs(normalized_slope)

            return (normalized_slope, min(1.0, trend_strength))
        else:
            return (0, 0)

    def calculate_overall_trend_score(self, short_trend, medium_trend, long_trend):
        """Calculate an overall trend score combining all timeframes"""
        # Weight different timeframes (longer timeframes might be more reliable)
        short_weight = 0.2
        medium_weight = 0.3
        long_weight = 0.5

        overall_score = (short_trend[0] * short_weight + 
                        medium_trend[0] * medium_weight + 
                        long_trend[0] * long_weight)

        return overall_score

    def calculate_trend_alignment(self, short_trend, medium_trend, long_trend):
        """Calculate how aligned the trends are across timeframes"""
        directions = [short_trend[0], medium_trend[0], long_trend[0]]
        
        # Count how many timeframes have the same direction
        positive_count = sum(1 for d in directions if d > 0)
        negative_count = sum(1 for d in directions if d < 0)
        
        # Alignment score (0-1, where 1 is perfect alignment)
        if positive_count == 3 or negative_count == 3:
            alignment = 1.0
        elif positive_count == 0 or negative_count == 0:
            alignment = 0.0
        else:
            # Partial alignment
            alignment = max(positive_count, negative_count) / 3.0

        return alignment