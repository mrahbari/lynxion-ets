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

        if len(self.candles) < 1:  # Need at least 1 candle to generate any observation
            return None

        # Analyze candlestick patterns
        pattern_analysis = self._analyze_candlestick_patterns()

        # Calculate trend based on recent candles
        trend_analysis = self._analyze_trend()

        # Calculate volatility based on historical candles
        volatility_analysis = self._analyze_volatility()

        # Calculate momentum
        momentum_analysis = self._analyze_momentum()

        # Determine initial observation type based on pattern, trend, and momentum
        # Only call these if we have enough data for meaningful analysis
        if len(self.candles) >= 2:  # Need at least 2 candles for meaningful analysis
            # Calculate confidence with fallback for when no patterns are detected
            confidence = self._calculate_confidence(pattern_analysis, volatility_analysis, momentum_analysis)

            # Determine initial observation type based on pattern, trend, and momentum
            observation_type = self._determine_observation_type(pattern_analysis, trend_analysis)
            observation_value = self._calculate_observation_value(pattern_analysis, trend_analysis, volatility_analysis)
        else:
            # For single candle, use fallback logic
            observation_type = 'single_candle_observation'
            observation_value = self.candles[0]['close'] if self.candles else 0.0
            confidence = max(float(os.getenv('WATCHER_MIN_CONFIDENCE_THRESHOLD', '0.05')), float(os.getenv('WATCHER_NEUTRAL_CONFIDENCE', '0.05')))

        # If confidence is too low (meaning no significant patterns detected),
        # but we have trend or momentum, still generate an observation with lower confidence
        min_confidence_threshold = float(os.getenv('WATCHER_MIN_CONFIDENCE_THRESHOLD', '0.05'))  # Lowered from 0.15 to 0.05
        max_confidence_with_patterns = float(os.getenv('WATCHER_MAX_CONFIDENCE_WITH_PATTERNS', '0.3'))
        min_price_change_threshold = float(os.getenv('WATCHER_MIN_PRICE_CHANGE_THRESHOLD', '0.0001'))  # Lowered from 0.0005 to 0.0001
        max_confidence_with_movement = float(os.getenv('WATCHER_MAX_CONFIDENCE_WITH_MOVEMENT', '0.35'))

        if confidence < min_confidence_threshold and (abs(trend_analysis.get('direction', 0)) > 0.0001 or abs(momentum_analysis.get('momentum', 0)) > 0.0001):
            # Generate a basic trend/momentum observation even without specific patterns
            if abs(trend_analysis.get('direction', 0)) > 0.0001:
                observation_type = 'trend_detected'
                observation_value = trend_analysis['direction']
                confidence = max(min_confidence_threshold, min(max_confidence_with_patterns, abs(trend_analysis['direction']) * 5))  # Scale confidence with trend strength
            elif abs(momentum_analysis.get('momentum', 0)) > 0.0001:
                observation_type = 'momentum_detected'
                observation_value = momentum_analysis['momentum']
                confidence = max(min_confidence_threshold, min(max_confidence_with_patterns, abs(momentum_analysis['momentum']) * 5))  # Scale confidence with momentum strength

        # If we still have no observation type or very low confidence, create a basic one based on price movement
        if (not observation_type or confidence < min_confidence_threshold) and len(self.candles) >= 1:  # Changed from >= 2 to >= 1
            # Generate basic trend observation based on simple price movement
            recent_closes = [c['close'] for c in self.candles[-5:]]  # Last 5 candles
            if len(recent_closes) >= 1:  # Changed from >= 2 to >= 1
                if len(recent_closes) >= 2:  # Need at least 2 for price change calculation
                    price_change = (recent_closes[-1] - recent_closes[0]) / recent_closes[0] if recent_closes[0] != 0 else 0
                    if abs(price_change) > min_price_change_threshold:  # Configurable change threshold
                        observation_type = 'price_trend_basic'
                        observation_value = price_change
                        confidence = max(min_confidence_threshold, min(max_confidence_with_movement, abs(price_change) * 10))  # Scale confidence with change magnitude
                    else:
                        # Even if no significant movement, we can still generate a neutral observation
                        observation_type = 'market_neutral'
                        observation_value = 0.0
                        confidence = max(min_confidence_threshold, float(os.getenv('WATCHER_NEUTRAL_CONFIDENCE', '0.05')))  # Use min threshold as fallback
                else:
                    # If we only have 1 candle, we can still generate a basic observation
                    observation_type = 'single_candle_observation'
                    observation_value = recent_closes[0]  # Use the single price value
                    confidence = max(min_confidence_threshold, float(os.getenv('WATCHER_NEUTRAL_CONFIDENCE', '0.05')))  # Use min threshold as fallback

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
                'momentum_analysis': momentum_analysis,
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

    def _calculate_confidence_original(self, pattern_analysis, volatility_analysis):
        """Original confidence calculation based on pattern and volatility analysis"""
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

    def _calculate_confidence(self, pattern_analysis, volatility_analysis, momentum_analysis=None):
        """Calculate confidence based on pattern, volatility, and momentum analysis"""
        pattern_strength = pattern_analysis.get('total_strength', 0.0)
        volatility_regime = volatility_analysis.get('regime', 'normal')
        momentum_strength = momentum_analysis.get('strength', 0.0) if momentum_analysis else 0.0

        # Get configuration from environment variables
        pattern_weight = float(os.getenv('WATCHER_PATTERN_WEIGHT', '0.4'))
        momentum_weight = float(os.getenv('WATCHER_MOMENTUM_WEIGHT', '0.3'))
        high_volatility_boost = float(os.getenv('WATCHER_HIGH_VOLATILITY_BOOST', '0.2'))
        low_volatility_boost = float(os.getenv('WATCHER_LOW_VOLATILITY_BOOST', '0.05'))
        normal_volatility_boost = float(os.getenv('WATCHER_NORMAL_VOLATILITY_BOOST', '0.1'))
        min_confidence_when_signals_detected = float(os.getenv('WATCHER_MIN_CONFIDENCE_WHEN_SIGNALS_DETECTED', '0.15'))
        max_confidence_cap = float(os.getenv('WATCHER_MAX_CONFIDENCE_CAP', '0.95'))

        # Base confidence on pattern strength
        confidence = pattern_strength * pattern_weight  # Configurable weight to allow other factors to contribute

        # Add momentum contribution if provided
        if momentum_analysis:
            confidence += momentum_strength * momentum_weight

        # Adjust for volatility regime
        if volatility_regime == 'high':
            confidence += high_volatility_boost  # Configurable boost for high volatility
        elif volatility_regime == 'low':
            confidence += low_volatility_boost  # Configurable boost for low volatility
        else:  # normal
            confidence += normal_volatility_boost  # Configurable boost for normal volatility

        # Ensure minimum confidence for any detected signal
        if pattern_strength > 0 or (momentum_analysis and momentum_strength > 0):
            confidence = max(min_confidence_when_signals_detected, confidence)  # Configurable minimum when signals are detected

        return min(max_confidence_cap, confidence)  # Configurable clamp upper bound

    def _determine_observation_type(self, pattern_analysis, trend_analysis, momentum_analysis=None):
        """Determine observation type based on pattern, trend, and momentum analysis"""
        patterns = pattern_analysis.get('patterns', [])
        trend_direction = trend_analysis.get('direction', 0)
        momentum_value = momentum_analysis.get('momentum', 0) if momentum_analysis else 0

        # Count different pattern types
        bullish_patterns = [p for p in patterns if p['type'] in ['doji', 'bullish_engulfing', 'hammer', 'morning_star']]
        bearish_patterns = [p for p in patterns if p['type'] in ['bearish_engulfing', 'shooting_star', 'evening_star']]
        reversal_patterns = [p for p in patterns if p['type'] in ['doji', 'hammer', 'shooting_star', 'morning_star', 'evening_star']]

        # Determine observation type based on analysis
        if len(bullish_patterns) > 0 and trend_direction > 0:
            return 'bullish_pattern_trend_aligned'
        elif len(bearish_patterns) > 0 and trend_direction < 0:
            return 'bearish_pattern_trend_aligned'
        elif len(reversal_patterns) > 0 and ((trend_direction < 0 and momentum_value > 0) or (trend_direction > 0 and momentum_value < 0)):
            return 'potential_reversal_detected'
        elif abs(trend_direction) > 0.001:  # Significant trend
            return 'trend_following_signal'
        elif abs(momentum_value) > 0.001:  # Significant momentum
            return 'momentum_signal'
        elif len(patterns) > 0:  # Any pattern detected
            return 'pattern_detected'
        else:
            # If no specific patterns but we have data, return a basic trend observation
            if abs(trend_direction) > 0.0001:
                return 'basic_trend_signal'
            else:
                return 'market_condition_neutral'

    def _analyze_momentum(self):
        """Analyze momentum based on recent price movements"""
        if len(self.candles) < 3:
            return {'momentum': 0.0, 'strength': 0.0}

        # Get configuration from environment variables
        momentum_lookback_period = int(os.getenv('WATCHER_MOMENTUM_LOOKBACK_PERIOD', '10'))
        momentum_sensitivity_factor = float(os.getenv('WATCHER_MOMENTUM_SENSITIVITY_FACTOR', '10'))

        # Calculate momentum using configurable number of recent candles
        recent_closes = [c['close'] for c in self.candles[-momentum_lookback_period:]]  # Configurable lookback for momentum
        if len(recent_closes) < 2:
            return {'momentum': 0.0, 'strength': 0.0}

        # Calculate rate of change over the period
        initial_price = recent_closes[0]
        final_price = recent_closes[-1]

        if initial_price != 0:
            roc = (final_price - initial_price) / initial_price
        else:
            roc = 0.0

        # Calculate momentum strength based on consistency of movement
        momentum_changes = []
        for i in range(1, len(recent_closes)):
            if recent_closes[i-1] != 0:
                change = (recent_closes[i] - recent_closes[i-1]) / recent_closes[i-1]
                momentum_changes.append(change)

        avg_change = sum(momentum_changes) / len(momentum_changes) if momentum_changes else 0.0
        momentum_strength = min(1.0, abs(avg_change) * momentum_sensitivity_factor)  # Configurable amplification for sensitivity

        return {
            'momentum': roc,
            'strength': momentum_strength
        }

    def _calculate_confidence(self, pattern_analysis, volatility_analysis, momentum_analysis):
        """Calculate confidence based on pattern, volatility, and momentum analysis"""
        pattern_strength = pattern_analysis.get('total_strength', 0.0)
        volatility_regime = volatility_analysis.get('regime', 'normal')
        momentum_strength = momentum_analysis.get('strength', 0.0)

        # Base confidence on pattern strength
        confidence = pattern_strength * 0.4  # Reduced weight to allow other factors to contribute

        # Add momentum contribution
        confidence += momentum_strength * 0.3

        # Adjust for volatility regime
        if volatility_regime == 'high':
            confidence += 0.2  # High volatility can confirm patterns and momentum
        elif volatility_regime == 'low':
            confidence += 0.05  # Low volatility is still informative
        else:  # normal
            confidence += 0.1

        # Ensure minimum confidence for any detected signal
        if pattern_strength > 0 or momentum_strength > 0:
            confidence = max(0.15, confidence)  # Minimum confidence when signals are detected

        return min(0.95, confidence)  # Clamp upper bound