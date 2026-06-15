from .base_watcher import BaseWatcher
from domain.entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
from decimal import Decimal


class HistoricalCandleWatcherAdapter(BaseWatcher):
    """Historical Candle Watcher - analyzes historical candlestick patterns, returns raw market observations"""

    def __init__(self, settings, name: str, symbol: str, broker_service=None, lookback: int = 50):
        # Settings injected by the watcher factory (E1.T4); read the same fields off
        # self._settings instead of importing bootstrap.settings.loaders.
        self._settings = settings
        # Convert symbol string to Symbol object if needed
        symbol_obj = Symbol(symbol) if isinstance(symbol, str) else symbol
        super().__init__(name, symbol_obj)

        # Store broker service and other parameters separately
        self.broker_service = broker_service

        # Configuration from environment with defaults
        self.enabled = self._settings.watcher.historical_candle_watcher_enabled if self._settings.watcher and hasattr(self._settings.watcher, 'historical_candle_watcher_enabled') else True

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

        # Pattern detection thresholds (more sensitive for improved detection)
        self.doji_threshold = 0.003  # Increased threshold for more doji detection
        self.engulfing_threshold = 0.002  # Reduced threshold for more engulfing detection
        self.hammer_threshold = 0.005  # Reduced threshold for more hammer detection
        self.small_body_threshold = 0.002  # For detecting indecision patterns
        self.spinning_top_threshold = 0.004  # For detecting spinning tops

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
            confidence = max(self._settings.watcher.watcher_min_confidence_threshold if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_min_confidence_threshold') else 0.05, self._settings.watcher.watcher_neutral_confidence if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_neutral_confidence') else 0.05)

        # If confidence is too low (meaning no significant patterns detected),
        # but we have trend or momentum, still generate an observation with lower confidence
        min_confidence_threshold = self._settings.watcher.watcher_min_confidence_threshold if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_min_confidence_threshold') else 0.05  # Lowered from 0.15 to 0.05
        max_confidence_with_patterns = self._settings.watcher.watcher_max_confidence_with_patterns if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_max_confidence_with_patterns') else 0.3
        min_price_change_threshold = self._settings.watcher.watcher_min_price_change_threshold if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_min_price_change_threshold') else 0.0001  # Lowered from 0.0005 to 0.0001
        max_confidence_with_movement = self._settings.watcher.watcher_max_confidence_with_movement if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_max_confidence_with_movement') else 0.35

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
                        confidence = max(min_confidence_threshold, self._settings.watcher.watcher_neutral_confidence if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_neutral_confidence') else 0.05)  # Use min threshold as fallback
                else:
                    # If we only have 1 candle, we can still generate a basic observation
                    observation_type = 'single_candle_observation'
                    observation_value = recent_closes[0]  # Use the single price value
                    confidence = max(min_confidence_threshold, self._settings.watcher.watcher_neutral_confidence if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_neutral_confidence') else 0.05)  # Use min threshold as fallback

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

    def analyze(self, symbol: Symbol) -> MarketObservation:
        """Analyze market conditions and return a raw market observation"""
        return self._analyze_impl(symbol)

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

            # Hammer pattern (more sensitive)
            if candle_range != 0:
                lower_shadow = min(current['open'], current['close']) - current['low']
                upper_shadow = current['high'] - max(current['open'], current['close'])
                body_size = abs(current['close'] - current['open'])

                lower_shadow_ratio = lower_shadow / candle_range if candle_range != 0 else 0
                upper_shadow_ratio = upper_shadow / candle_range if candle_range != 0 else 0

                # Hammer (bullish reversal) - more sensitive
                if lower_shadow_ratio >= self.hammer_threshold and upper_shadow_ratio <= lower_shadow_ratio * 0.3:
                    patterns.append({
                        'type': 'hammer',
                        'position': i,
                        'strength': lower_shadow_ratio
                    })
                    strength += lower_shadow_ratio

                # Shooting star (bearish reversal) - more sensitive
                if upper_shadow_ratio >= self.hammer_threshold and lower_shadow_ratio <= upper_shadow_ratio * 0.3:
                    patterns.append({
                        'type': 'shooting_star',
                        'position': i,
                        'strength': upper_shadow_ratio
                    })
                    strength += upper_shadow_ratio

            # Spinning top detection (sign of indecision)
            if candle_range != 0:
                body_ratio = body_size / candle_range
                if body_ratio <= self.spinning_top_threshold and body_size > 0:
                    patterns.append({
                        'type': 'spinning_top',
                        'position': i,
                        'strength': body_ratio
                    })
                    strength += body_ratio * 0.5  # Lower weight for indecision patterns

            # Marubozu (long day without shadows - strong trend)
            if candle_range != 0:
                upper_shadow = current['high'] - max(current['open'], current['close'])
                lower_shadow = min(current['open'], current['close']) - current['low']

                total_shadows = upper_shadow + lower_shadow
                shadow_ratio = total_shadows / candle_range if candle_range != 0 else 0

                if shadow_ratio <= 0.1:  # Very small shadows
                    if current['close'] > current['open']:  # Bullish marubozu
                        patterns.append({
                            'type': 'marubozu_bullish',
                            'position': i,
                            'strength': 0.8
                        })
                        strength += 0.8
                    elif current['close'] < current['open']:  # Bearish marubozu
                        patterns.append({
                            'type': 'marubozu_bearish',
                            'position': i,
                            'strength': 0.8
                        })
                        strength += 0.8

        return {
            'patterns': patterns,
            'total_strength': min(1.0, strength / len(self.candles)) if self.candles else 0.0
        }

    def _analyze_trend(self):
        """Analyze trend based on recent candles with more sensitivity"""
        if len(self.candles) < 2:
            return {'direction': 0, 'strength': 0}

        # Use shorter lookback for more responsive trend detection
        lookback = min(self.lookback, len(self.candles))
        recent_candles = self.candles[-lookback:] if len(self.candles) >= lookback else self.candles

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

            # Calculate trend strength (R-squared) - more sensitive calculation
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
                'strength': min(1.0, abs(trend_strength))  # Use absolute value for strength
            }

        return {'direction': 0, 'strength': 0}

    def _analyze_volatility(self):
        """Analyze volatility based on historical candles with more sensitivity"""
        if len(self.candles) < 3:  # Need at least 3 for meaningful volatility
            return {'volatility': 0, 'regime': 'normal'}

        # Calculate returns
        closes = [c['close'] for c in self.candles]
        returns = np.diff(closes) / np.array(closes[:-1])

        # Calculate volatility
        volatility = np.std(returns) if len(returns) > 0 else 0

        # Determine volatility regime (more sensitive thresholds)
        if volatility > 0.015:  # Reduced threshold for more sensitivity
            regime = 'high'
        elif volatility < 0.003:  # Reduced threshold for more sensitivity
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

        # Get configuration from Configs
        pattern_weight = self._settings.watcher.watcher_pattern_weight if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_pattern_weight') else 0.4
        momentum_weight = self._settings.watcher.watcher_momentum_weight if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_momentum_weight') else 0.3
        high_volatility_boost = self._settings.watcher.watcher_high_volatility_boost if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_high_volatility_boost') else 0.2
        low_volatility_boost = self._settings.watcher.watcher_low_volatility_boost if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_low_volatility_boost') else 0.05
        normal_volatility_boost = self._settings.watcher.watcher_normal_volatility_boost if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_normal_volatility_boost') else 0.1
        min_confidence_when_signals_detected = self._settings.watcher.watcher_min_confidence_when_signals_detected if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_min_confidence_when_signals_detected') else 0.15
        max_confidence_cap = self._settings.watcher.watcher_max_confidence_cap if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_max_confidence_cap') else 0.95

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
        """Determine observation type based on pattern, trend and momentum analysis with more variety"""
        patterns = pattern_analysis.get('patterns', [])
        trend_direction = trend_analysis.get('direction', 0)
        momentum_value = momentum_analysis.get('momentum', 0) if momentum_analysis else 0

        # Count different pattern types
        reversal_patterns = [p for p in patterns if p['type'] in ['hammer', 'shooting_star', 'doji']]
        bullish_patterns = [p for p in patterns if p['type'] in ['hammer', 'bullish_engulfing', 'marubozu_bullish']]
        bearish_patterns = [p for p in patterns if p['type'] in ['shooting_star', 'bearish_engulfing', 'marubozu_bearish']]

        # Enhanced logic with more observation types
        if len(bullish_patterns) > 0 and trend_direction <= 0:  # Bullish patterns in neutral/down trend
            return 'candle_reversal_bullish_emerging'
        elif len(bearish_patterns) > 0 and trend_direction >= 0:  # Bearish patterns in neutral/up trend
            return 'candle_reversal_bearish_emerging'
        elif len(bullish_patterns) > 0 and trend_direction > 0:  # Bullish patterns in up trend
            return 'candle_confirmation_bullish'
        elif len(bearish_patterns) > 0 and trend_direction < 0:  # Bearish patterns in down trend
            return 'candle_confirmation_bearish'
        elif trend_direction > 0.0005:  # Mild uptrend
            return 'trend_bullish_weak'
        elif trend_direction < -0.0005:  # Mild downtrend
            return 'trend_bearish_weak'
        elif abs(trend_direction) < 0.0005 and len(reversal_patterns) > 0:  # Neutral trend with reversal patterns
            return 'candle_indecision_reversal_signals'
        elif abs(trend_direction) < 0.0005 and len(patterns) == 0:  # Truly neutral
            return 'market_neutral_no_signals'
        elif abs(trend_direction) < 0.0005 and len(patterns) > 0:  # Neutral with patterns
            return 'candle_pattern_signals_only'
        elif momentum_value > 0.002:  # Positive momentum
            return 'momentum_bullish'
        elif momentum_value < -0.002:  # Negative momentum
            return 'momentum_bearish'
        else:
            return 'market_pulse_subtle'

    def _analyze_momentum(self):
        """Analyze momentum based on recent price movements"""
        if len(self.candles) < 5:
            return {'momentum': 0, 'strength': 0}

        # Calculate momentum using last few candles
        lookback = min(5, len(self.candles))
        recent_closes = [c['close'] for c in self.candles[-lookback:]]

        if len(recent_closes) < 2:
            return {'momentum': 0, 'strength': 0}

        # Calculate rate of change
        roc = (recent_closes[-1] - recent_closes[0]) / recent_closes[0] if recent_closes[0] != 0 else 0

        # Calculate momentum strength based on consistency
        momentum_changes = []
        for i in range(1, len(recent_closes)):
            if recent_closes[i-1] != 0:
                change = (recent_closes[i] - recent_closes[i-1]) / recent_closes[i-1]
                momentum_changes.append(change)

        avg_change = np.mean(momentum_changes) if momentum_changes else 0
        momentum_strength = min(1.0, abs(avg_change) * 10)  # Amplify for sensitivity

        return {
            'momentum': roc,
            'strength': momentum_strength
        }

    def _calculate_confidence(self, pattern_analysis, volatility_analysis, momentum_analysis):
        """Calculate confidence based on pattern, volatility, and momentum analysis"""
        pattern_strength = pattern_analysis.get('total_strength', 0.0)
        volatility_regime = volatility_analysis.get('regime', 'normal')
        momentum_strength = momentum_analysis.get('strength', 0.0)

        # Get configuration from Configs
        pattern_weight = self._settings.watcher.watcher_pattern_weight if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_pattern_weight') else 0.4
        momentum_weight = self._settings.watcher.watcher_momentum_weight if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_momentum_weight') else 0.3
        high_volatility_boost = self._settings.watcher.watcher_high_volatility_boost if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_high_volatility_boost') else 0.2
        low_volatility_boost = self._settings.watcher.watcher_low_volatility_boost if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_low_volatility_boost') else 0.05
        normal_volatility_boost = self._settings.watcher.watcher_normal_volatility_boost if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_normal_volatility_boost') else 0.1
        min_confidence_when_signals_detected = self._settings.watcher.watcher_min_confidence_when_signals_detected if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_min_confidence_when_signals_detected') else 0.25  # Increased for more responsive signals
        max_confidence_cap = self._settings.watcher.watcher_max_confidence_cap if self._settings.watcher and hasattr(self._settings.watcher, 'watcher_max_confidence_cap') else 0.95

        # Base confidence on pattern strength
        confidence = pattern_strength * pattern_weight  # Configurable weight to allow other factors to contribute

        # Add momentum contribution
        confidence += momentum_strength * momentum_weight

        # Adjust for volatility regime
        if volatility_regime == 'high':
            confidence += high_volatility_boost  # Configurable boost for high volatility
        elif volatility_regime == 'low':
            confidence += low_volatility_boost  # Configurable boost for low volatility
        else:  # normal
            confidence += normal_volatility_boost  # Configurable boost for normal volatility

        # Ensure minimum confidence for any detected signal
        if pattern_strength > 0 or momentum_strength > 0:
            confidence = max(min_confidence_when_signals_detected, confidence)  # Configurable minimum when signals are detected

        return min(max_confidence_cap, confidence)  # Configurable clamp upper bound