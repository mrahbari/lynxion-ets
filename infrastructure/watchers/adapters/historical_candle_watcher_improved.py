from .base_watcher import BaseWatcher
from domain.entities.signal_entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
import os
from decimal import Decimal


class HistoricalCandleWatcherImprovedAdapter(BaseWatcher):
    """Improved Historical Candle Watcher - analyzes historical candlestick patterns with more sensitive detection, returns raw market observations"""

    def __init__(self, name: str, symbol: str, broker_service=None, lookback: int = 20, target_broker=None):  # Reduced lookback for more responsive signals
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

        # More sensitive pattern detection thresholds
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
            if len(self.candles) > self.lookback * 5:  # Increased buffer
                self.candles = self.candles[-(self.lookback * 5):]

    def _analyze_impl(self, symbol: Symbol) -> MarketObservation:
        """Analyze historical candles and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        if len(self.candles) < 3:  # Need at least 3 candles for pattern analysis
            # Even with limited data, we can still generate trend observations
            if len(self.candles) >= 2:
                return self._generate_basic_trend_observation(symbol)
            return None

        # Analyze candlestick patterns
        pattern_analysis = self._analyze_candlestick_patterns()

        # Calculate trend based on recent candles
        trend_analysis = self._analyze_trend()

        # Calculate volatility based on historical candles
        volatility_analysis = self._analyze_volatility()

        # Calculate momentum
        momentum_analysis = self._analyze_momentum()

        # Determine observation type based on pattern and trend
        observation_type = self._determine_observation_type(pattern_analysis, trend_analysis, momentum_analysis)
        observation_value = self._calculate_observation_value(pattern_analysis, trend_analysis, volatility_analysis, momentum_analysis)
        confidence = self._calculate_confidence(pattern_analysis, volatility_analysis, momentum_analysis)

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

    def _generate_basic_trend_observation(self, symbol: Symbol) -> MarketObservation:
        """Generate a basic trend observation when we have limited data"""
        if len(self.candles) < 2:
            return None

        # Calculate basic trend from just 2 candles
        prev_close = self.candles[-2]['close']
        curr_close = self.candles[-1]['close']
        
        if prev_close != 0:
            change = (curr_close - prev_close) / prev_close
        else:
            change = 0
            
        # Determine basic trend
        if change > 0.001:  # 0.1% increase
            obs_type = 'trend_bullish_weak'
            obs_value = min(0.3, abs(change) * 10)  # Scale the value
        elif change < -0.001:  # 0.1% decrease
            obs_type = 'trend_bearish_weak'
            obs_value = max(-0.3, abs(change) * -10)  # Scale the value
        else:
            obs_type = 'trend_neutral'
            obs_value = 0.0

        confidence = Percentage(Decimal('0.2'))  # Lower confidence with limited data

        observation = MarketObservation(
            symbol=symbol,
            observation_type=obs_type,
            observation_value=obs_value,
            confidence=confidence,
            timestamp=datetime.now(),
            metadata={
                'basic_trend': True,
                'change_percent': change,
                'candle_history_length': len(self.candles),
                'latest_candle': self.candles[-1] if self.candles else None,
                'candle_pattern_source': self.name
            }
        )

        return observation

    def _analyze_candlestick_patterns(self):
        """Analyze candlestick patterns in the historical data with more sensitivity"""
        if len(self.candles) < 2:
            return {'patterns': [], 'strength': 0.0}

        patterns = []
        strength = 0.0

        # Analyze recent candles for patterns
        for i in range(1, len(self.candles)):
            current = self.candles[i]
            previous = self.candles[i-1]

            # Doji pattern detection (more sensitive)
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

            # Bullish engulfing pattern (more sensitive)
            if (current['close'] > current['open'] and  # Current is bullish
                previous['close'] < previous['open'] and  # Previous was bearish
                current['close'] >= previous['open'] and  # Current closes at or above previous open (changed from > to >=)
                current['open'] <= previous['close']):  # Current opens at or below previous close (changed from < to <=
                patterns.append({
                    'type': 'bullish_engulfing',
                    'position': i,
                    'strength': 0.7  # Slightly reduced for sensitivity
                })
                strength += 0.7

            # Bearish engulfing pattern (more sensitive)
            if (current['close'] < current['open'] and  # Current is bearish
                previous['close'] > previous['open'] and  # Previous was bullish
                current['open'] >= previous['close'] and  # Current opens at or above previous close (changed from > to >=)
                current['close'] <= previous['open']):  # Current closes at or below previous open (changed from < to <=)
                patterns.append({
                    'type': 'bearish_engulfing',
                    'position': i,
                    'strength': 0.7  # Slightly reduced for sensitivity
                })
                strength += 0.7

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
        """Analyze volatility based on historical candles"""
        if len(self.candles) < 3:  # Need at least 3 for meaningful volatility
            return {'volatility': 0, 'regime': 'normal'}

        # Calculate returns
        closes = [c['close'] for c in self.candles]
        returns = np.diff(closes) / np.array(closes[:-1])

        # Calculate volatility
        volatility = np.std(returns) if len(returns) > 0 else 0

        # Determine volatility regime
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

    def _determine_observation_type(self, pattern_analysis, trend_analysis, momentum_analysis):
        """Determine observation type based on pattern, trend and momentum analysis with more variety"""
        patterns = pattern_analysis['patterns']
        trend_direction = trend_analysis['direction']
        momentum = momentum_analysis['momentum']

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
        elif momentum > 0.002:  # Positive momentum
            return 'momentum_bullish'
        elif momentum < -0.002:  # Negative momentum
            return 'momentum_bearish'
        else:
            return 'market_pulse_subtle'

    def _calculate_observation_value(self, pattern_analysis, trend_analysis, volatility_analysis, momentum_analysis):
        """Calculate observation value based on all analyses"""
        pattern_strength = pattern_analysis['total_strength']
        trend_direction = trend_analysis['direction']
        trend_strength = trend_analysis['strength']
        volatility = volatility_analysis['volatility']
        momentum = momentum_analysis['momentum']

        # Weight different factors
        trend_component = trend_direction * min(0.7, trend_strength * 2)  # Amplify trend effect
        pattern_component = pattern_strength * 0.5 * (1 if trend_direction >= 0 else -1)  # Patterns reinforce trend
        momentum_component = momentum * 0.3  # Momentum adds to the mix
        volatility_component = volatility * 0.1 * (1 if trend_direction >= 0 else -1)  # Volatility affects trend

        # Combine components
        combined_value = trend_component + pattern_component + momentum_component + volatility_component

        # Normalize to [-1, 1] range
        return max(-1.0, min(1.0, combined_value))

    def _calculate_confidence(self, pattern_analysis, volatility_analysis, momentum_analysis):
        """Calculate confidence based on multiple factors"""
        pattern_strength = pattern_analysis['total_strength']
        volatility_regime = volatility_analysis['regime']
        momentum_strength = momentum_analysis['strength']

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
            confidence = max(0.25, confidence)  # Minimum confidence when signals are detected

        return max(0.15, min(0.95, confidence))  # Clamp between 0.15 and 0.95 for more responsive signals