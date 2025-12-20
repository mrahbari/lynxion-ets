from .base_watcher import BaseWatcher
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
from domain.value_objects import Symbol
import numpy as np
import os


class TrendMTFWatcher(BaseWatcher):
    """Multi-Timeframe Trend Watcher - analyzes trends across multiple timeframes"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, short_period: int = 5, medium_period: int = 15, long_period: int = 30):
        super().__init__(name, symbol, broker_service, target_broker)

        # Configuration from environment with defaults
        self.enabled = os.getenv('TREND_MTF_WATCHER_ENABLED', 'true').lower() == 'true'

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
            if len(self.price_history) > self.long_period * 3:  # Keep more than the longest period
                self.price_history.pop(0)

        # Update trends if we have enough data
        if len(self.price_history) >= self.long_period:
            self.update_trends()

    def update_trends(self):
        """Update trend values for different timeframes - each with independent state"""
        if len(self.price_history) < self.long_period:
            return

        current_price = self.price_history[-1]
        current_time = datetime.now()

        # Calculate short-term trend independently
        if len(self.price_history) >= self.short_period:
            short_ma = np.mean(self.price_history[-self.short_period:])
            short_deviation = (current_price - short_ma) / short_ma if short_ma != 0 else 0
            self.short_trend_state = {
                'direction': 1 if short_deviation > self.trend_threshold else (-1 if short_deviation < -self.trend_threshold else 0),
                'strength': abs(short_deviation),
                'timestamp': current_time
            }

        # Calculate medium-term trend independently
        if len(self.price_history) >= self.medium_period:
            medium_ma = np.mean(self.price_history[-self.medium_period:])
            medium_deviation = (current_price - medium_ma) / medium_ma if medium_ma != 0 else 0
            self.medium_trend_state = {
                'direction': 1 if medium_deviation > self.trend_threshold else (-1 if medium_deviation < -self.trend_threshold else 0),
                'strength': abs(medium_deviation),
                'timestamp': current_time
            }

        # Calculate long-term trend independently
        if len(self.price_history) >= self.long_period:
            long_ma = np.mean(self.price_history[-self.long_period:])
            long_deviation = (current_price - long_ma) / long_ma if long_ma != 0 else 0
            self.long_trend_state = {
                'direction': 1 if long_deviation > self.trend_threshold else (-1 if long_deviation < -self.trend_threshold else 0),
                'strength': abs(long_deviation),
                'timestamp': current_time
            }

    def analyze(self, symbol: Symbol) -> Signal:
        """Analyze multi-timeframe trends and return a signal"""
        if not self.enabled:
            return None

        if len(self.price_history) < self.long_period:
            return None

        # Determine alignment state explicitly
        alignment_state = self.determine_alignment_state()

        # Check for divergences explicitly
        divergence_detected = self.check_divergence()

        # Calculate score based on alignment and divergence
        score = self.calculate_alignment_score()

        # Determine signal based on explicit alignment state
        signal_type = self.determine_signal_type_explicit(alignment_state, divergence_detected)

        # Calculate confidence based on alignment clarity
        confidence = self.calculate_alignment_confidence(alignment_state, divergence_detected)

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=score,
            strategy=self.name,
            timestamp=datetime.now(),
            metadata={
                'alignment_state': alignment_state,
                'divergence_detected': divergence_detected,
                'timeframe_states': {
                    'long': self.long_trend_state,
                    'medium': self.medium_trend_state,
                    'short': self.short_trend_state
                },
                'explanation': f"Trend alignment: {alignment_state}, divergence: {divergence_detected}"
            }
        )

        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            logger.debug(f"TrendMTFWatcher {self.name} generated signal: {signal_type} with alignment: {alignment_state}, divergence: {divergence_detected}")

        return signal

    def determine_alignment_state(self) -> str:
        """Explicitly determine the alignment state of all timeframes"""
        long_dir = self.long_trend_state['direction']
        medium_dir = self.medium_trend_state['direction']
        short_dir = self.short_trend_state['direction']

        # Count aligned directions
        directions = [long_dir, medium_dir, short_dir]
        bullish_count = sum(1 for d in directions if d == 1)
        bearish_count = sum(1 for d in directions if d == -1)
        neutral_count = sum(1 for d in directions if d == 0)

        if bullish_count == 3:
            return "ALIGNED_BULLISH"  # All aligned bullish
        elif bearish_count == 3:
            return "ALIGNED_BEARISH"  # All aligned bearish
        elif bullish_count >= 2 and neutral_count <= 1:
            return "MAINLY_BULLISH"  # At least 2 bullish
        elif bearish_count >= 2 and neutral_count <= 1:
            return "MAINLY_BEARISH"  # At least 2 bearish
        elif long_dir != 0 and short_dir != 0 and long_dir != short_dir:
            # Divergence between long and short term
            return "DIVERGENT"
        else:
            return "MIXED"  # Mixed signals

    def check_divergence(self) -> bool:
        """Explicitly check for trend divergences"""
        long_dir = self.long_trend_state['direction']
        short_dir = self.short_trend_state['direction']

        # Check for major divergence between long and short term
        if long_dir != 0 and short_dir != 0 and long_dir != short_dir:
            return True

        # Check for medium-short divergence
        medium_dir = self.medium_trend_state['direction']
        if medium_dir != 0 and short_dir != 0 and medium_dir != short_dir:
            return True

        return False

    def calculate_alignment_score(self) -> float:
        """Calculate score based on explicit alignment - deterministic and explainable"""
        long_dir = self.long_trend_state['direction']
        medium_dir = self.medium_trend_state['direction']
        short_dir = self.short_trend_state['direction']

        # Calculate a score based on direction alignment
        # All weights are fixed to ensure deterministic behavior
        direction_alignment = 0
        if long_dir == medium_dir == short_dir and long_dir != 0:
            # Perfect alignment
            direction_alignment = long_dir * 0.8  # Strong alignment
        elif long_dir == medium_dir != 0 or medium_dir == short_dir != 0 or long_dir == short_dir != 0:
            # Partial alignment
            # Use the direction of the majority or long-term trend
            if long_dir != 0:
                direction_alignment = long_dir * 0.5
            elif medium_dir != 0:
                direction_alignment = medium_dir * 0.5
            else:
                direction_alignment = short_dir * 0.5
        else:
            # No clear alignment
            direction_alignment = 0.0

        # Add strength component (how strong the trends are)
        avg_strength = (self.long_trend_state['strength'] +
                       self.medium_trend_state['strength'] +
                       self.short_trend_state['strength']) / 3

        strength_component = avg_strength * 0.2  # Smaller weight for strength

        # Final score bounded between -1 and 1
        score = direction_alignment + strength_component
        return max(-1.0, min(1.0, score))

    def determine_signal_type_explicit(self, alignment_state: str, divergence_detected: bool) -> SignalType:
        """Determine signal type based on explicit alignment state"""
        if alignment_state == "ALIGNED_BULLISH" or alignment_state == "MAINLY_BULLISH":
            return SignalType.BUY
        elif alignment_state == "ALIGNED_BEARISH" or alignment_state == "MAINLY_BEARISH":
            return SignalType.SELL
        elif divergence_detected:
            # When there's a divergence, the signal is less clear
            # Often indicates potential reversal, so we return HOLD
            return SignalType.HOLD
        else:
            # Mixed signals or weak trends
            return SignalType.HOLD

    def calculate_alignment_confidence(self, alignment_state: str, divergence_detected: bool) -> float:
        """Calculate confidence based on explicit alignment state"""
        if divergence_detected:
            # Lower confidence when there's divergence
            return 0.3

        if alignment_state in ["ALIGNED_BULLISH", "ALIGNED_BEARISH"]:
            # Highest confidence when all timeframes align
            return 0.9
        elif alignment_state in ["MAINLY_BULLISH", "MAINLY_BEARISH"]:
            # High confidence when at least 2 timeframes align
            return 0.7
        else:
            # Lower confidence for mixed signals
            return 0.4

    def get_trend_alignment(self) -> dict:
        """Get the current alignment of trends with explicit states"""
        alignment_state = self.determine_alignment_state()
        divergence_detected = self.check_divergence()

        return {
            'alignment_state': alignment_state,
            'divergence_detected': divergence_detected,
            'long': {
                'direction': 'bullish' if self.long_trend_state['direction'] > 0 else ('bearish' if self.long_trend_state['direction'] < 0 else 'neutral'),
                'strength': self.long_trend_state['strength']
            },
            'medium': {
                'direction': 'bullish' if self.medium_trend_state['direction'] > 0 else ('bearish' if self.medium_trend_state['direction'] < 0 else 'neutral'),
                'strength': self.medium_trend_state['strength']
            },
            'short': {
                'direction': 'bullish' if self.short_trend_state['direction'] > 0 else ('bearish' if self.short_trend_state['direction'] < 0 else 'neutral'),
                'strength': self.short_trend_state['strength']
            },
            'explanation': f"Long-term: {'bullish' if self.long_trend_state['direction'] > 0 else ('bearish' if self.long_trend_state['direction'] < 0 else 'neutral')}, " +
                          f"Medium-term: {'bullish' if self.medium_trend_state['direction'] > 0 else ('bearish' if self.medium_trend_state['direction'] < 0 else 'neutral')}, " +
                          f"Short-term: {'bullish' if self.short_trend_state['direction'] > 0 else ('bearish' if self.short_trend_state['direction'] < 0 else 'neutral')}, " +
                          f"Alignment: {alignment_state}"
        }