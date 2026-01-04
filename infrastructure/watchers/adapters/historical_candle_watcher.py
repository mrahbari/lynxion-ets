from .base_watcher import BaseWatcher
from domain.entities.signal_entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
import os
from decimal import Decimal


class HistoricalCandleWatcherAdapter(BaseWatcher):
    """Historical Candle Watcher - analyzes historical candlestick patterns, returns raw market observations"""

    def __init__(self, name: str, symbol: str, broker_service=None, lookback: int = 50):
        super().__init__(name, symbol, broker_service, None)

        # Configuration from environment with defaults
        self.enabled = os.getenv('HISTORICAL_CANDLE_WATCHER_ENABLED', 'true').lower() == 'true'

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
        self.candles = []  # Store candle data: [{'open': o, 'high': h, 'low': l, 'close': c, 'volume': v, 'timestamp': ts}, ...]

        # Pattern detection thresholds
        self.doji_threshold = 0.001  # Max body size for doji pattern
        self.engulfing_threshold = 0.005  # Min size for engulfing pattern
        self.hammer_threshold = 0.01  # Min lower shadow for hammer pattern

    def update_data(self, data: dict):
        """Update with new candle data"""
        if not self.enabled:
            return

        if 'candle' in data:
            candle = data['candle']
            # Add candle data to history
            self.candles.append({
                'open': candle.get('open', 0),
                'high': candle.get('high', 0),
                'low': candle.get('low', 0),
                'close': candle.get('close', 0),
                'volume': candle.get('volume', 0),
                'timestamp': candle.get('timestamp', datetime.now())
            })

            # Keep history within limits
            if len(self.candles) > self.lookback * 3:
                self.candles.pop(0)

    def _analyze_impl(self, symbol: Symbol) -> MarketObservation:
        """Analyze historical candles and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        if len(self.candles) < 3:  # Need at least 3 candles for pattern analysis
            return None

        # Analyze candlestick patterns
        pattern_analysis = self._analyze_candlestick_patterns()

        # Calculate trend based on recent candles
        trend_analysis = self._analyze_trend()

        # Calculate volatility based on historical candles
        volatility_analysis = self._analyze_volatility()

        # Determine observation type based on pattern and trend
        observation_type = self._determine_observation_type(pattern_analysis, trend_analysis)
        observation_value = self._calculate_observation_value(pattern_analysis, trend_analysis, volatility_analysis)
        confidence = self._calculate_confidence(pattern_analysis, volatility_analysis)

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
                'pattern_analysis': pattern_analysis,
                'trend_analysis': trend_analysis,
                'volatility_analysis': volatility_analysis,
                'candle_history_length': len(self.candles),
                'latest_candle': self.candles[-1] if self.candles else None,
                'candle_pattern_source': self.name,
                'lookback_period': self.lookback
            }
        )

        return observation

    def _analyze_candlestick_patterns(self):
        """Analyze candlestick patterns in the historical data"""
        if len(self.candles) < 2:
            return {'patterns': [], 'strength': 0.0}

        patterns = []
        strength = 0.0

        # Analyze recent candles for patterns
        for i in range(1, len(self.candles)):
            current = self.candles[i]
            previous = self.candles[i-1]

            # Doji pattern detection
            body_size = abs(current['close'] - current['open'])
            candle_range = current['high'] - current['low']
            if candle_range != 0:
                body_ratio = body_size / candle_range
                if body_ratio <= self.doji_threshold:
                    patterns.append({
                        'type': 'doji',
                        'position': i,
                        'strength': body_ratio
                    })
                    strength += body_ratio

            # Bullish engulfing pattern
            if (current['close'] > current['open'] and  # Current is bullish
                previous['close'] < previous['open'] and  # Previous was bearish
                current['close'] > previous['open'] and  # Current closes above previous open
                current['open'] < previous['close']):  # Current opens below previous close
                patterns.append({
                    'type': 'bullish_engulfing',
                    'position': i,
                    'strength': 0.8
                })
                strength += 0.8

            # Bearish engulfing pattern
            if (current['close'] < current['open'] and  # Current is bearish
                previous['close'] > previous['open'] and  # Previous was bullish
                current['open'] > previous['close'] and  # Current opens above previous close
                current['close'] < previous['open']):  # Current closes below previous open
                patterns.append({
                    'type': 'bearish_engulfing',
                    'position': i,
                    'strength': 0.8
                })
                strength += 0.8

            # Hammer pattern
            if candle_range != 0:
                lower_shadow = current['low'] - min(current['open'], current['close'])
                upper_shadow = current['high'] - max(current['open'], current['close'])
                body_size = abs(current['close'] - current['open'])

                lower_shadow_ratio = lower_shadow / candle_range
                upper_shadow_ratio = upper_shadow / candle_range

                # Hammer (bullish reversal)
                if lower_shadow_ratio >= self.hammer_threshold and upper_shadow_ratio <= lower_shadow_ratio * 0.2:
                    patterns.append({
                        'type': 'hammer',
                        'position': i,
                        'strength': lower_shadow_ratio
                    })
                    strength += lower_shadow_ratio

                # Shooting star (bearish reversal)
                if upper_shadow_ratio >= self.hammer_threshold and lower_shadow_ratio <= upper_shadow_ratio * 0.2:
                    patterns.append({
                        'type': 'shooting_star',
                        'position': i,
                        'strength': upper_shadow_ratio
                    })
                    strength += upper_shadow_ratio

        return {
            'patterns': patterns,
            'total_strength': min(1.0, strength / len(self.candles)) if self.candles else 0.0
        }

    def _analyze_trend(self):
        """Analyze trend based on recent candles"""
        if len(self.candles) < self.lookback:
            recent_candles = self.candles
        else:
            recent_candles = self.candles[-self.lookback:]

        if len(recent_candles) < 2:
            return {'direction': 0, 'strength': 0}

        # Calculate trend using closing prices
        closes = [c['close'] for c in recent_candles]
        x = np.arange(len(closes))

        if len(x) > 1:
            slope = (len(x) * np.sum(x * closes) - np.sum(x) * np.sum(closes)) / \
                    (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)

            avg_price = np.mean(closes)
            if avg_price != 0:
                normalized_slope = slope / avg_price
            else:
                normalized_slope = 0

            # Calculate trend strength (R-squared)
            if len(closes) > 2:
                y_pred = slope * x + (np.mean(closes) - slope * np.mean(x))
                ss_res = np.sum((np.array(closes) - y_pred) ** 2)
                ss_tot = np.sum((np.array(closes) - np.mean(closes)) ** 2)
                if ss_tot != 0:
                    r_squared = 1 - (ss_res / ss_tot)
                    trend_strength = r_squared * abs(normalized_slope)
                else:
                    trend_strength = abs(normalized_slope)
            else:
                trend_strength = abs(normalized_slope)

            return {
                'direction': normalized_slope,
                'strength': min(1.0, trend_strength)
            }

        return {'direction': 0, 'strength': 0}

    def _analyze_volatility(self):
        """Analyze volatility based on historical candles"""
        if len(self.candles) < 2:
            return {'volatility': 0, 'regime': 'normal'}

        # Calculate returns
        closes = [c['close'] for c in self.candles]
        returns = np.diff(closes) / np.array(closes[:-1])

        # Calculate volatility
        volatility = np.std(returns) if len(returns) > 0 else 0

        # Determine volatility regime
        if volatility > 0.02:  # High volatility threshold
            regime = 'high'
        elif volatility < 0.005:  # Low volatility threshold
            regime = 'low'
        else:
            regime = 'normal'

        return {
            'volatility': volatility,
            'regime': regime
        }

    def _determine_observation_type(self, pattern_analysis, trend_analysis):
        """Determine observation type based on pattern and trend analysis"""
        patterns = pattern_analysis['patterns']
        trend_direction = trend_analysis['direction']

        # Check for reversal patterns
        reversal_patterns = [p for p in patterns if p['type'] in ['hammer', 'shooting_star', 'doji']]
        bullish_patterns = [p for p in patterns if p['type'] in ['hammer', 'bullish_engulfing']]
        bearish_patterns = [p for p in patterns if p['type'] in ['shooting_star', 'bearish_engulfing']]

        if bullish_patterns and trend_direction < 0:  # Bullish patterns in downtrend
            return 'candle_reversal_bullish'
        elif bearish_patterns and trend_direction > 0:  # Bearish patterns in uptrend
            return 'candle_reversal_bearish'
        elif bullish_patterns and trend_direction >= 0:  # Bullish patterns in uptrend
            return 'candle_continuation_bullish'
        elif bearish_patterns and trend_direction <= 0:  # Bearish patterns in downtrend
            return 'candle_continuation_bearish'
        elif trend_direction > 0.001:  # Strong uptrend
            return 'candle_trend_up'
        elif trend_direction < -0.001:  # Strong downtrend
            return 'candle_trend_down'
        else:
            return 'candle_neutral'

    def _calculate_observation_value(self, pattern_analysis, trend_analysis, volatility_analysis):
        """Calculate observation value based on analysis"""
        pattern_strength = pattern_analysis['total_strength']
        trend_direction = trend_analysis['direction']
        trend_strength = trend_analysis['strength']

        # Combine pattern and trend information
        combined_value = (trend_direction * 0.7) + (pattern_strength * 0.3)

        # Normalize to [-1, 1] range
        return max(-1.0, min(1.0, combined_value))

    def _calculate_confidence(self, pattern_analysis, volatility_analysis):
        """Calculate confidence based on pattern and volatility analysis"""
        pattern_strength = pattern_analysis['total_strength']
        volatility_regime = volatility_analysis['regime']

        # Base confidence on pattern strength (dynamic, no hardcoded base)
        confidence = pattern_strength * 0.7  # 0.0 to 0.7 based on patterns

        # Adjust for volatility regime
        if volatility_regime == 'high':
            confidence += 0.2  # High volatility can confirm patterns
        elif volatility_regime == 'low':
            confidence -= 0.1  # Low volatility may make patterns less reliable

        return max(0.1, min(0.95, confidence))  # Clamp between 0.1 and 0.95