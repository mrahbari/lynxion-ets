from .base_watcher import BaseWatcher
from domain.entities.trading_entities import Signal, SignalType
from domain.value_objects import Percentage
from decimal import Decimal
from domain.value_objects import Symbol
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import Dict, List
import os


class LiquidityWatcher(BaseWatcher):
    """Liquidity Watcher - analyzes market liquidity conditions"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 20):
        super().__init__(name, symbol, broker_service, target_broker)

        # Configuration from environment with defaults
        self.enabled = os.getenv('LIQUIDITY_WATCHER_ENABLED', 'true').lower() == 'true'

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
        self.spread_threshold_factor = 2.0  # Factor to determine abnormal spreads

        # For liquidity sweep detection
        self.price_volatility_history = []
        self.sweep_detection_window = 10  # Window to detect potential sweeps

    def update_data(self, data: Dict):
        """Update with new market data (order book)"""
        if not self.enabled:
            return

        if 'bids' in data and 'asks' in data:
            current_time = datetime.now()

            # Store bid and ask levels with timestamps for reproducibility
            self.bids = [(float(price), float(vol), current_time) for price, vol in data['bids']]
            self.asks = [(float(price), float(vol), current_time) for price, vol in data['asks']]

            # Calculate spread
            if self.bids and self.asks:
                best_bid = self.bids[0][0]
                best_ask = self.asks[0][0]
                spread = best_ask - best_bid
                spread_pct = spread / best_bid if best_bid != 0 else 0

                self.spread_history.append((spread_pct, current_time))
                if len(self.spread_history) > self.lookback * 2:
                    self.spread_history.pop(0)

                # Calculate average spread
                if self.spread_history:
                    spreads = [item[0] for item in self.spread_history]
                    self.avg_spread = np.mean(spreads)

            # Calculate order book depth
            depth_score = self.calculate_depth_score()
            self.depth_history.append((depth_score, current_time))
            if len(self.depth_history) > self.lookback * 2:
                self.depth_history.pop(0)

            # Calculate liquidity score
            liquidity_score = self.calculate_liquidity_score()
            self.liquidity_score_history.append((liquidity_score, current_time))
            if len(self.liquidity_score_history) > self.lookback * 2:
                self.liquidity_score_history.pop(0)

            # Track price volatility for sweep detection
            if 'close' in data:
                self.price_volatility_history.append((data['close'], current_time))
                if len(self.price_volatility_history) > self.sweep_detection_window * 2:
                    self.price_volatility_history.pop(0)

    def calculate_depth_score(self) -> float:
        """Calculate a score based on order book depth - derived and reproducible"""
        if not self.bids or not self.asks:
            return 0.0

        # Calculate total volume in top levels
        top_bid_volume = sum(vol for price, vol, timestamp in self.bids[:5])  # Top 5 bid levels
        top_ask_volume = sum(vol for price, vol, timestamp in self.asks[:5])  # Top 5 ask levels

        # Calculate depth score based on available liquidity
        total_top_volume = top_bid_volume + top_ask_volume

        if total_top_volume == 0:
            return 0.0

        # Calculate average price level to normalize volume
        avg_price = (self.bids[0][0] + self.asks[0][0]) / 2 if self.bids and self.asks else 1.0

        # Normalize the volume by price (to get dollar value)
        total_dollar_depth = (top_bid_volume + top_ask_volume) * avg_price

        # Return a score proportional to the depth (capped to reasonable range)
        # Using logarithmic scaling to prevent extreme scores for very deep books
        depth_score = min(1.0, np.log1p(total_dollar_depth / 10000) / 5.0)  # Adjust scaling factor as needed

        return depth_score

    def calculate_liquidity_score(self) -> float:
        """Calculate overall liquidity score - derived and reproducible"""
        if not self.spread_history or not self.depth_history:
            return 0.0

        # Get current values
        current_spread = self.spread_history[-1][0] if self.spread_history else 0
        current_depth = self.depth_history[-1][0] if self.depth_history else 0

        # Get historical averages
        spreads = [item[0] for item in self.spread_history]
        avg_spread = np.mean(spreads) if spreads else 0.001  # Default to 0.1%

        depths = [item[0] for item in self.depth_history]
        avg_depth = np.mean(depths) if depths else 0.1

        if avg_spread == 0:
            avg_spread = 0.001

        # Calculate spread-based liquidity (inverse - lower spread = higher liquidity)
        spread_liquidity = max(0, 1 - (current_spread / avg_spread))

        # Combine spread and depth liquidity scores
        combined_liquidity = (spread_liquidity * 0.6) + (current_depth * 0.4)

        # Normalize to -1 to 1 range
        return combined_liquidity * 2 - 1  # Convert from 0-1 to -1-1 range

    def _analyze_impl(self, symbol: Symbol) -> Signal:
        """Analyze liquidity conditions and return a signal"""
        if not self.enabled:
            return None

        if len(self.liquidity_score_history) < 5:
            # If we don't have enough liquidity data, return a HOLD signal with low confidence
            # rather than None to ensure the flow continues
            from domain.entities.trading_entities import SignalType
            from domain.value_objects import Percentage
            from decimal import Decimal

            confidence_percentage = Percentage(Decimal("0.1"))  # Low confidence

            signal = Signal(
                symbol=symbol,
                signal_type=SignalType.HOLD,
                confidence=confidence_percentage,
                score=0.0,
                strategy_name=self.name,
                timestamp=datetime.now(),
                source_engine=self.name,
                metadata={
                    'liquidity_regime': 'insufficient_data',
                    'sweep_detected': False,
                    'current_liquidity_score': 0.0,
                    'explanation': 'Insufficient data to determine liquidity conditions'
                }
            )
            return signal

        # Separate liquidity identification from sweep detection
        liquidity_regime = self.identify_liquidity_regime()
        sweep_detected = self.detect_liquidity_sweep()

        # Get current liquidity score
        current_liquidity = self.liquidity_score_history[-1][0] if self.liquidity_score_history else 0

        # Calculate signal based on liquidity conditions
        signal_type = SignalType.HOLD
        confidence = 0.5  # Default confidence

        if liquidity_regime == "low":
            # Low liquidity: potentially dangerous to trade, suggest hold
            signal_type = SignalType.HOLD
            confidence = 0.9  # High confidence in hold during low liquidity
        elif liquidity_regime == "high" and sweep_detected:
            # High liquidity with sweep detected - potential opportunity
            # Determine direction based on recent price action during sweep
            recent_price_changes = []
            if len(self.price_volatility_history) >= 2:
                recent_price_changes = [self.price_volatility_history[-i][0] - self.price_volatility_history[-i-1][0]
                                       for i in range(1, min(3, len(self.price_volatility_history)))]
                avg_price_change = np.mean(recent_price_changes) if recent_price_changes else 0
            else:
                avg_price_change = 0

            if avg_price_change > 0:
                # Price rising during liquidity sweep - potential for continuation (BUY)
                signal_type = SignalType.BUY
                confidence = 0.8
            else:
                # Price falling during liquidity sweep - potential for bounce (SELL)
                signal_type = SignalType.SELL
                confidence = 0.8
        elif liquidity_regime == "high":
            # High liquidity: generally favorable conditions for trading
            # Use liquidity score to determine direction
            if current_liquidity > 0.8:
                # Very high liquidity - potential for large moves
                signal_type = SignalType.BUY  # High liquidity often supports bullish moves
                confidence = 0.6
            elif current_liquidity < -0.8:
                # Very low liquidity score (negative) - potential for bearish moves
                signal_type = SignalType.SELL
                confidence = 0.6
            else:
                # Moderate high liquidity - hold
                signal_type = SignalType.HOLD
                confidence = 0.4
        elif liquidity_regime == "normal":
            # Normal liquidity: check for subtle changes
            if current_liquidity > 0.3:
                # Increasing liquidity - potential for bullish move
                signal_type = SignalType.BUY
                confidence = 0.5
            elif current_liquidity < -0.3:
                # Decreasing liquidity - potential for bearish move
                signal_type = SignalType.SELL
                confidence = 0.5
            else:
                # Stable normal liquidity - hold
                signal_type = SignalType.HOLD
                confidence = 0.5
        else:
            # Unknown liquidity: hold
            signal_type = SignalType.HOLD
            confidence = 0.5

        # Score represents liquidity level (-1 for very low, +1 for very high)
        # Convert confidence to Percentage object for domain compatibility
        confidence_percentage = Percentage(Decimal(str(confidence)))

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence_percentage,
            score=current_liquidity,
            strategy_name=self.name,  # Changed from 'strategy' to 'strategy_name' for domain compatibility
            timestamp=datetime.now(),
            source_engine=self.name,  # Add source engine for tracking
            metadata={
                'liquidity_regime': liquidity_regime,
                'sweep_detected': sweep_detected,
                'current_liquidity_score': current_liquidity,
                'explanation': f"Liquidity regime: {liquidity_regime}, sweep detected: {sweep_detected}"
            }
        )

        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            logger.debug(f"LiquidityWatcher {self.name} generated signal: {signal_type} with liquidity score {current_liquidity:.3f}, regime: {liquidity_regime}, sweep: {sweep_detected}")

        return signal

    def identify_liquidity_regime(self) -> str:
        """Separately identify current liquidity regime - derived, reproducible, timestamped"""
        if not self.liquidity_score_history:
            return "unknown"

        current_liquidity = self.liquidity_score_history[-1][0] if self.liquidity_score_history else 0

        if current_liquidity < self.low_liquidity_threshold:
            return "low"
        elif current_liquidity > self.high_liquidity_threshold:
            return "high"
        else:
            return "normal"

    def detect_liquidity_sweep(self) -> bool:
        """Detect potential liquidity sweeps separately from general liquidity identification"""
        if len(self.price_volatility_history) < 3 or len(self.liquidity_score_history) < 3:
            return False

        # Get recent price changes and liquidity changes
        recent_prices = [item[0] for item in self.price_volatility_history[-5:]]
        recent_liquidity = [item[0] for item in self.liquidity_score_history[-5:]]

        if len(recent_prices) < 2 or len(recent_liquidity) < 2:
            return False

        # Calculate price volatility
        price_changes = [abs(recent_prices[i] - recent_prices[i-1]) for i in range(1, len(recent_prices))]
        avg_price_change = np.mean(price_changes) if price_changes else 0

        # Calculate liquidity volatility
        liquidity_changes = [abs(recent_liquidity[i] - recent_liquidity[i-1]) for i in range(1, len(recent_liquidity))]
        avg_liquidity_change = np.mean(liquidity_changes) if liquidity_changes else 0

        # A potential sweep might be indicated by high price volatility combined with changing liquidity
        # This is a simplified detection - in practice, you'd look for specific patterns
        high_price_volatility = avg_price_change > (np.std([item[0] for item in self.price_volatility_history]) * 2)
        liquidity_drop = avg_liquidity_change > (np.std([item[0] for item in self.liquidity_score_history]) * 2)

        return high_price_volatility and liquidity_drop

    def get_liquidity_regime(self) -> str:
        """Get current liquidity regime"""
        return self.identify_liquidity_regime()

    def get_liquidity_metrics(self) -> Dict:
        """Get current liquidity metrics - all derived, reproducible, timestamped"""
        if not self.liquidity_score_history:
            return {}

        current_score, current_timestamp = self.liquidity_score_history[-1]
        current_spread, spread_timestamp = self.spread_history[-1] if self.spread_history else (0, None)
        current_depth, depth_timestamp = self.depth_history[-1] if self.depth_history else (0, None)

        # Calculate historical averages
        scores = [item[0] for item in self.liquidity_score_history]
        avg_liquidity = np.mean(scores) if scores else 0

        spreads = [item[0] for item in self.spread_history]
        avg_spread = np.mean(spreads) if spreads else 0

        return {
            'current_liquidity_score': current_score,
            'current_liquidity_timestamp': current_timestamp,
            'average_liquidity_score': avg_liquidity,
            'current_spread_pct': current_spread,
            'current_spread_timestamp': spread_timestamp,
            'average_spread_pct': avg_spread,
            'current_depth_score': current_depth,
            'current_depth_timestamp': depth_timestamp,
            'regime': self.identify_liquidity_regime(),
            'sweep_detected': self.detect_liquidity_sweep(),
            'data_points': len(self.liquidity_score_history)
        }