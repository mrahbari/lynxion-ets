from .base_watcher import BaseWatcher
from domain.entities.signal_entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import Dict, List
from decimal import Decimal
from application.configs.configs import Configs


class LiquidityWatcher(BaseWatcher):
    """Liquidity Watcher - analyzes market liquidity conditions, returns raw market observations"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 20):
        # Convert symbol string to Symbol object if needed
        symbol_obj = Symbol(symbol) if isinstance(symbol, str) else symbol
        super().__init__(name, symbol_obj)

        # Store broker service and other parameters separately
        self.broker_service = broker_service
        self.target_broker = target_broker

        # Configuration from environment with defaults
        self.enabled = Configs.watcher.liquidity_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'liquidity_watcher_enabled') else True

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

        # Order book data - with timestamped liquidity levels
        self.bids = []  # [(price, volume, timestamp), ...]
        self.asks = []  # [(price, volume, timestamp), ...]
        self.spread_history = []  # [(spread_pct, timestamp), ...]
        self.depth_history = []  # [(depth_score, timestamp), ...]
        self.liquidity_score_history = []  # [(liquidity_score, timestamp), ...]

        # Liquidity metrics
        self.avg_spread = 0
        self.liquidity_ratio = 0  # Ratio of bid/ask volume
        self.depth_score = 0  # Measure of order book depth

        # Thresholds
        self.low_liquidity_threshold = 0.3
        self.high_liquidity_threshold = 0.7

    def update_data(self, data: Dict):
        """Update with new market data (order book)"""
        if not self.enabled:
            return

        if 'bids' in data and 'asks' in data:
            # Update order book with timestamp
            current_time = datetime.now()
            self.bids = [(float(price), float(vol), current_time) for price, vol in data['bids']]
            self.asks = [(float(price), float(vol), current_time) for price, vol in data['asks']]

            # Calculate liquidity metrics
            spread = self.calculate_spread()
            depth = self.calculate_depth()
            liquidity_score = self.calculate_liquidity_score()

            # Add to history with timestamp
            self.spread_history.append((spread, current_time))
            self.depth_history.append((depth, current_time))
            self.liquidity_score_history.append((liquidity_score, current_time))

            # Keep history within limits
            max_history = self.lookback * 3
            if len(self.spread_history) > max_history:
                self.spread_history = self.spread_history[-max_history:]
            if len(self.depth_history) > max_history:
                self.depth_history = self.depth_history[-max_history:]
            if len(self.liquidity_score_history) > max_history:
                self.liquidity_score_history = self.liquidity_score_history[-max_history:]

    def _analyze_impl(self, symbol: Symbol) -> MarketObservation:
        """Analyze market liquidity and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        if not self.liquidity_score_history:
            return None

        # Get current liquidity metrics
        current_liquidity_score = self.liquidity_score_history[-1][0] if self.liquidity_score_history else 0
        current_spread = self.spread_history[-1][0] if self.spread_history else 0
        current_depth = self.depth_history[-1][0] if self.depth_history else 0

        # Calculate average liquidity for comparison
        avg_liquidity = np.mean([score for score, _ in self.liquidity_score_history]) if self.liquidity_score_history else 0

        # Determine observation type based on liquidity conditions
        if current_liquidity_score < self.low_liquidity_threshold:
            observation_type = 'liquidity_low'
            observation_value = -abs(current_liquidity_score)  # Negative for low liquidity
            confidence = min(0.9, abs(current_liquidity_score))
        elif current_liquidity_score > self.high_liquidity_threshold:
            observation_type = 'liquidity_high'
            observation_value = current_liquidity_score  # Positive for high liquidity
            confidence = min(0.9, current_liquidity_score)
        else:
            observation_type = 'liquidity_normal'
            observation_value = 0.0
            # For neutral state, confidence is based on how close to normal we are
            liquidity_magnitude = abs(current_liquidity_score)
            confidence = min(0.6, (1.0 - liquidity_magnitude))

        # Adjust confidence based on how different from average
        if avg_liquidity != 0:
            deviation = abs(current_liquidity_score - avg_liquidity) / avg_liquidity
            confidence = min(0.9, confidence + deviation * 0.2)

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
                'current_liquidity_score': current_liquidity_score,
                'current_spread': current_spread,
                'current_depth': current_depth,
                'average_liquidity': avg_liquidity,
                'liquidity_regime': self.get_liquidity_regime(current_liquidity_score),
                'bid_volume_top5': sum(vol for _, vol, _ in self.bids[:5]) if self.bids else 0,
                'ask_volume_top5': sum(vol for _, vol, _ in self.asks[:5]) if self.asks else 0,
                'best_bid': self.bids[0][0] if self.bids else 0,
                'best_ask': self.asks[0][0] if self.asks else 0,
                'liquidity_source': self.name,
                'liquidity_score_history_length': len(self.liquidity_score_history)
            }
        )

        return observation

    def analyze(self, symbol: Symbol) -> MarketObservation:
        """Analyze market conditions and return a raw market observation"""
        return self._analyze_impl(symbol)

    def calculate_spread(self) -> float:
        """Calculate bid-ask spread as percentage"""
        if not self.bids or not self.asks:
            return 0.0

        best_bid = self.bids[0][0]
        best_ask = self.asks[0][0]

        if best_bid == 0:
            return 0.0

        spread = (best_ask - best_bid) / best_bid
        return spread

    def calculate_depth(self) -> float:
        """Calculate order book depth score"""
        if not self.bids or not self.asks:
            return 0.0

        # Calculate total volume in top levels
        top_bid_vol = sum(vol for _, vol, _ in self.bids[:5])  # Top 5 bid levels
        top_ask_vol = sum(vol for _, vol, _ in self.asks[:5])  # Top 5 ask levels

        # Calculate average price for normalization
        avg_price = ((self.bids[0][0] if self.bids else 0) + (self.asks[0][0] if self.asks else 0)) / 2
        if avg_price == 0:
            return 0.0

        # Calculate dollar depth
        dollar_depth = (top_bid_vol + top_ask_vol) * avg_price

        # Normalize depth score (logarithmic to handle wide range)
        depth_score = min(1.0, np.log1p(dollar_depth / 10000) / 5)  # Adjust divisor as needed
        return depth_score

    def calculate_liquidity_score(self) -> float:
        """Calculate overall liquidity score from 0 to 1"""
        if not self.bids or not self.asks:
            return 0.0

        # Calculate spread factor (lower spread = higher liquidity)
        spread = self.calculate_spread()
        spread_factor = max(0, 1 - spread * 100)  # Assuming max spread of 1% = 0.01

        # Calculate depth factor (higher depth = higher liquidity)
        depth_factor = self.calculate_depth()

        # Combine factors with weights
        liquidity_score = (spread_factor * 0.4) + (depth_factor * 0.6)

        # Clamp between 0 and 1
        return max(0.0, min(1.0, liquidity_score))

    def get_liquidity_regime(self, liquidity_score: float) -> str:
        """Get current liquidity regime"""
        if liquidity_score < self.low_liquidity_threshold:
            return "low"
        elif liquidity_score > self.high_liquidity_threshold:
            return "high"
        else:
            return "normal"