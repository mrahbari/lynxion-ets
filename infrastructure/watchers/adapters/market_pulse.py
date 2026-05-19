from .base_watcher import BaseWatcher
from domain.entities.signal_entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
from decimal import Decimal
from application.configs.configs import Configs


class MarketPulseWatcher(BaseWatcher):
    """Market PulseWatcher - analyzes market sentiment and momentum, returns raw market observations"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 15):  # Reduced for more responsive signals
        # Convert symbol string to Symbol object if needed
        symbol_obj = Symbol(symbol) if isinstance(symbol, str) else symbol
        super().__init__(name, symbol_obj)

        # Store broker service and other parameters separately
        self.broker_service = broker_service
        self.target_broker = target_broker

        # Configuration from environment with defaults
        self.enabled = Configs.watcher.market_pulse_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'market_pulse_watcher_enabled') else True

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

        # Sensitivity parameters for more responsive detection
        self.volume_spike_threshold = 1.5  # Volume multiplier for spike detection
        self.rsi_overbought = 65  # Reduced from 70 for more sensitivity
        self.rsi_oversold = 35   # Increased from 30 for more sensitivity
        self.macd_threshold = 0.0005  # Reduced for more sensitivity

        # Initialize sub-components
        self.momentum_subscore = 0.0
        self.trend_subscore = 0.0
        self.volume_subscore = 0.0

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
        """Analyze market pulse and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        if len(self.candles) < 5:  # Need at least 5 candles for meaningful analysis
            return self._generate_basic_pulse_observation(symbol)

        # Analyze various market indicators
        price_analysis = self._analyze_price_action()
        volume_analysis = self._analyze_volume()
        momentum_analysis = self._analyze_momentum_indicators()
        volatility_analysis = self._analyze_volatility()

        # Determine observation type based on analysis
        observation_type = self._determine_observation_type(price_analysis, volume_analysis, momentum_analysis)
        observation_value = self._calculate_observation_value(price_analysis, volume_analysis, momentum_analysis)
        confidence = self._calculate_confidence(price_analysis, volume_analysis, momentum_analysis, volatility_analysis)

        # Convert confidence to Percentage object for domain compatibility
        confidence_percentage = Percentage(Decimal(str(confidence)))

        # Create and return a MarketObservation
        observation = MarketObservation(
            symbol=symbol,
            observation_type=observation_type,
            observation_value=observation_value,
            confidence=confidence_percentage,
            timestamp=datetime.now(),
            metadata={
                'price_analysis': price_analysis,
                'volume_analysis': volume_analysis,
                'momentum_analysis': momentum_analysis,
                'volatility_analysis': volatility_analysis,
                'candle_history_length': len(self.candles),
                'latest_candle': self.candles[-1] if self.candles else None,
                'market_pulse_source': self.name,
                'lookback_period': self.lookback
            }
        )

        return observation

    def analyze(self, symbol: Symbol) -> MarketObservation:
        """Analyze market conditions and return a raw market observation"""
        return self._analyze_impl(symbol)

    def _generate_basic_pulse_observation(self, symbol: Symbol) -> MarketObservation:
        """Generate a basic pulse observation when we have limited data"""
        if len(self.candles) < 2:
            return None

        # Calculate basic price action from limited data
        prev_close = self.candles[-2]['close']
        curr_close = self.candles[-1]['close']

        if prev_close != 0:
            change = (curr_close - prev_close) / prev_close
        else:
            change = 0

        # Determine basic pulse
        if abs(change) > 0.0005:  # Even small changes can indicate pulse
            if change > 0:
                obs_type = 'market_pulse_bullish_weak'
                obs_value = min(0.2, abs(change) * 5)  # Amplify small changes
            else:
                obs_type = 'market_pulse_bearish_weak'
                obs_value = max(-0.2, abs(change) * -5)  # Amplify small changes
        else:
            obs_type = 'market_pulse_neutral'
            obs_value = 0.0

        confidence = Percentage(Decimal('0.25'))  # Moderate confidence with limited data

        observation = MarketObservation(
            symbol=symbol,
            observation_type=obs_type,
            observation_value=obs_value,
            confidence=confidence,
            timestamp=datetime.now(),
            metadata={
                'basic_pulse': True,
                'change_percent': change,
                'candle_history_length': len(self.candles),
                'latest_candle': self.candles[-1] if self.candles else None,
                'market_pulse_source': self.name
            }
        )

        return observation

    def _analyze_price_action(self):
        """Analyze price action for momentum and direction"""
        if len(self.candles) < 3:
            return {'trend': 0, 'momentum': 0, 'strength': 0}

        closes = [c['close'] for c in self.candles[-self.lookback:]]
        highs = [c['high'] for c in self.candles[-self.lookback:]]
        lows = [c['low'] for c in self.candles[-self.lookback:]]

        if len(closes) < 2:
            return {'trend': 0, 'momentum': 0, 'strength': 0}

        # Calculate trend direction
        recent_change = (closes[-1] - closes[0]) / closes[0] if closes[0] != 0 else 0

        # Calculate momentum (rate of change)
        if len(closes) > 1:
            momentum = (closes[-1] - closes[-2]) / closes[-2] if closes[-2] != 0 else 0
        else:
            momentum = 0

        # Calculate trend strength using linear regression
        x = np.arange(len(closes))
        if len(x) > 1:
            slope = (len(x) * np.sum(x * closes) - np.sum(x) * np.sum(closes)) / \
                    (len(x) * np.sum(x * x) - (np.sum(x)) ** 2)

            avg_price = np.mean(closes)
            if avg_price != 0:
                normalized_slope = slope / avg_price
            else:
                normalized_slope = 0

            # R-squared for trend strength
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
        else:
            normalized_slope = 0
            trend_strength = 0

        return {
            'trend': normalized_slope,
            'momentum': momentum,
            'strength': min(1.0, abs(trend_strength))
        }

    def _analyze_volume(self):
        """Analyze volume patterns for confirmation"""
        if len(self.candles) < 3:
            return {'volume_trend': 0, 'spike_detected': False, 'strength': 0}

        volumes = [c['volume'] for c in self.candles[-self.lookback:]]

        if len(volumes) < 2:
            return {'volume_trend': 0, 'spike_detected': False, 'strength': 0}

        # Calculate volume trend
        recent_avg_volume = np.mean(volumes[-3:]) if len(volumes) >= 3 else np.mean(volumes)
        historical_avg_volume = np.mean(volumes[:-3]) if len(volumes) > 3 else np.mean(volumes)

        if historical_avg_volume != 0:
            volume_trend = (recent_avg_volume - historical_avg_volume) / historical_avg_volume
        else:
            volume_trend = 0

        # Check for volume spikes
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[:-1]) if len(volumes) > 1 else current_volume
        spike_detected = current_volume > avg_volume * self.volume_spike_threshold

        # Volume strength based on deviation from average
        volume_deviation = abs(current_volume - avg_volume) / avg_volume if avg_volume != 0 else 0
        volume_strength = min(1.0, volume_deviation)

        return {
            'volume_trend': volume_trend,
            'spike_detected': spike_detected,
            'strength': volume_strength
        }

    def _analyze_momentum_indicators(self):
        """Analyze momentum indicators like RSI, MACD, Bollinger Bands"""
        if len(self.candles) < 10:  # Need more data for momentum indicators
            return {'rsi': 50, 'macd': 0, 'bb_position': 0.5, 'signals': []}

        closes = [c['close'] for c in self.candles[-self.lookback:]]

        if len(closes) < 5:
            return {'rsi': 50, 'macd': 0, 'bb_position': 0.5, 'signals': []}

        # Calculate RSI
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains) if len(gains) > 0 else 0
        avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses) if len(losses) > 0 else 0

        if avg_loss != 0:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50

        # Calculate MACD-like indicator (simplified)
        ema_fast = self._ema(closes, 5)[-1] if len(closes) >= 5 else closes[-1]
        ema_slow = self._ema(closes, 10)[-1] if len(closes) >= 10 else closes[-1]
        macd = ema_fast - ema_slow

        # Calculate Bollinger Band position
        sma = np.mean(closes[-20:]) if len(closes) >= 20 else np.mean(closes)
        std = np.std(closes[-20:]) if len(closes) >= 20 else np.std(closes)

        if std != 0:
            bb_position = (closes[-1] - (sma - 2 * std)) / (4 * std) if std != 0 else 0.5
            bb_position = max(0, min(1, bb_position))  # Clamp between 0 and 1
        else:
            bb_position = 0.5

        # Identify momentum signals
        signals = []
        if rsi > self.rsi_overbought:
            signals.append('overbought')
        elif rsi < self.rsi_oversold:
            signals.append('oversold')

        if macd > self.macd_threshold:
            signals.append('bullish_momentum')
        elif macd < -self.macd_threshold:
            signals.append('bearish_momentum')

        if bb_position > 0.8:
            signals.append('upper_band')
        elif bb_position < 0.2:
            signals.append('lower_band')

        return {
            'rsi': rsi,
            'macd': macd,
            'bb_position': bb_position,
            'signals': signals
        }

    def _analyze_volatility(self):
        """Analyze market volatility"""
        if len(self.candles) < 3:
            return {'volatility': 0, 'regime': 'normal'}

        closes = [c['close'] for c in self.candles[-self.lookback:]]
        if len(closes) < 2:
            return {'volatility': 0, 'regime': 'normal'}

        # Calculate returns
        returns = np.diff(closes) / np.array(closes[:-1])

        # Calculate volatility
        volatility = np.std(returns) if len(returns) > 0 else 0

        # Determine volatility regime
        if volatility > 0.012:  # Reduced threshold for more sensitivity
            regime = 'high'
        elif volatility < 0.0025:  # Reduced threshold for more sensitivity
            regime = 'low'
        else:
            regime = 'normal'

        return {
            'volatility': volatility,
            'regime': regime
        }

    def _ema(self, prices, period):
        """Calculate exponential moving average"""
        if len(prices) < period:
            return prices
        ema = [prices[0]]
        multiplier = 2 / (period + 1)
        for price in prices[1:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])
        return ema

    def _determine_observation_type(self, price_analysis, volume_analysis, momentum_analysis):
        """Determine observation type based on all analyses with more variety"""
        trend = price_analysis['trend']
        momentum = price_analysis['momentum']
        volume_spike = volume_analysis['spike_detected']
        rsi = momentum_analysis['rsi']
        macd = momentum_analysis['macd']
        bb_position = momentum_analysis['bb_position']
        signals = momentum_analysis['signals']

        # Enhanced logic with more observation types
        if 'bullish_momentum' in signals and trend > 0:
            return 'market_pulse_bullish_strong'
        elif 'bearish_momentum' in signals and trend < 0:
            return 'market_pulse_bearish_strong'
        elif 'overbought' in signals and trend > 0:
            return 'market_pulse_bullish_overbought_caution'
        elif 'oversold' in signals and trend < 0:
            return 'market_pulse_bearish_oversold_caution'
        elif 'upper_band' in signals and rsi > 60:
            return 'market_pulse_near_resistance'
        elif 'lower_band' in signals and rsi < 40:
            return 'market_pulse_near_support'
        elif volume_spike and trend > 0.001:
            return 'market_pulse_bullish_with_volume_confirmation'
        elif volume_spike and trend < -0.001:
            return 'market_pulse_bearish_with_volume_confirmation'
        elif trend > 0.002:  # Stronger uptrend
            return 'market_pulse_bullish_trending'
        elif trend < -0.002:  # Stronger downtrend
            return 'market_pulse_bearish_trending'
        elif abs(trend) <= 0.002 and abs(momentum) > 0.0015:  # Neutral trend but strong momentum
            return 'market_pulse_momentum_without_direction'
        elif abs(trend) <= 0.001 and abs(momentum) <= 0.001:  # Very neutral
            return 'market_pulse_neutral_low_momentum'
        elif abs(trend) <= 0.001 and abs(momentum) > 0.001:  # Neutral trend but some momentum
            return 'market_pulse_subtle_momentum'
        elif momentum > 0.001:  # Positive momentum
            return 'market_pulse_bullish_momentum'
        elif momentum < -0.001:  # Negative momentum
            return 'market_pulse_bearish_momentum'
        else:
            return 'market_pulse_very_subtle'

    def _calculate_observation_value(self, price_analysis, volume_analysis, momentum_analysis):
        """Calculate observation value based on all analyses"""
        trend = price_analysis['trend']
        momentum = price_analysis['momentum']
        volume_trend = volume_analysis['volume_trend']
        macd = momentum_analysis['macd']

        # Weight different factors
        trend_component = trend * 0.4
        momentum_component = momentum * 0.3
        volume_component = volume_trend * 0.2
        macd_component = macd * 0.1  # Smaller weight for MACD

        # Combine components
        combined_value = trend_component + momentum_component + volume_component + macd_component

        # Normalize to [-1, 1] range
        return max(-1.0, min(1.0, combined_value))

    def _calculate_confidence(self, price_analysis, volume_analysis, momentum_analysis, volatility_analysis):
        """Calculate confidence based on multiple factors"""
        trend_strength = price_analysis['strength']
        volume_strength = volume_analysis['strength']
        signals = momentum_analysis['signals']
        volatility_regime = volatility_analysis['regime']

        # Base confidence on trend and volume strength
        confidence = (trend_strength * 0.4) + (volume_strength * 0.3)

        # Boost confidence if momentum signals are present
        if len(signals) > 0:
            confidence += 0.2 * len(signals) / 5  # Up to 0.2 for multiple signals

        # Adjust for volatility regime
        if volatility_regime == 'high':
            confidence += 0.1  # High volatility can confirm signals
        elif volatility_regime == 'low':
            confidence += 0.05  # Low volatility is still informative
        else:  # normal
            confidence += 0.1

        # Ensure minimum confidence for any detected signal
        if trend_strength > 0.1 or volume_strength > 0.1 or len(signals) > 0:
            confidence = max(0.25, confidence)  # Minimum confidence when signals are detected

        return max(0.2, min(0.95, confidence))  # Clamp between 0.2 and 0.95 for more responsive signals