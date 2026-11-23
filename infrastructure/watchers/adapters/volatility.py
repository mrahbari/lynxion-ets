from .base_watcher import BaseWatcher
from domain.entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
from decimal import Decimal


class VolatilityWatcher(BaseWatcher):
    """Volatility Watcher - analyzes market volatility patterns, returns raw market observations"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 20, period: int = 14, watcher_config=None):
        # Convert symbol string to Symbol object if needed
        symbol_obj = Symbol(symbol) if isinstance(symbol, str) else symbol
        super().__init__(name, symbol_obj)

        # Store broker service and other parameters separately
        self.broker_service = broker_service
        self.target_broker = target_broker

        # Configuration injected via constructor (E1.T4); falls back to the
        # typed settings aggregate (same values as the legacy Configs.watcher).
        self.enabled = watcher_config.volatility_watcher_enabled if watcher_config and hasattr(watcher_config, 'volatility_watcher_enabled') else True

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
        self.period = period
        self.price_history = []
        self.atr_history = []

        # Use more conservative thresholds to reduce constant firing
        self.volatility_expansion_threshold = 1.5  # 50% above average
        self.volatility_compression_threshold = 0.5  # 50% below average

        # Track previous regime to detect changes
        self.previous_regime = "normal"
        self.regime_change_detected = False
        self.signal_cooldown = 0
        self.max_cooldown = 5  # Prevent signal spamming

        # Regime definition: realized volatility of the last hour (60 x 1m log returns) vs the
        # last 24h baseline. Previously it compared the stdev of raw price differences of the last
        # 20 minutes with the 20 minutes before (noise), and the Engine read expansion as BUY.
        self.regime_short_bars = 60
        self.regime_baseline_bars = 1440
        self.regime_min_baseline_bars = 240
        self.expansion_ratio = 1.5
        self.compression_ratio = 0.67

    def update_data(self, data: dict):
        """Update with new market data"""
        if not self.enabled:
            return

        if 'close' in data:
            self.price_history.append(data['close'])
            if len(self.price_history) > max(self.lookback * 3, self.regime_baseline_bars + 1):
                self.price_history.pop(0)

        # Calculate ATR if we have high/low data
        if 'high' in data and 'low' in data and 'close' in data:
            # Calculate True Range
            high = data['high']
            low = data['low']
            prev_close = self.price_history[-2] if len(self.price_history) > 1 else data['close']
            
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            self.atr_history.append(tr)
            if len(self.atr_history) > self.period * 3:
                self.atr_history.pop(0)

    def _analyze_impl(self, symbol: Symbol) -> MarketObservation:
        """Analyze market volatility and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        if len(self.price_history) < 2:  # Require only 2 data points to start generating observations
            return None

        if len(self.price_history) < self.regime_min_baseline_bars + 1:
            return None
        px = np.asarray(self.price_history[-(self.regime_baseline_bars + 1):], dtype=float)
        if np.any(px <= 0):
            return None
        rets = np.diff(np.log(px))
        short = float(np.std(rets[-self.regime_short_bars:]))
        base = float(np.std(rets))
        ratio = short / base if base > 0 else 1.0
        if ratio >= self.expansion_ratio:
            obs_type, value = 'volatility_expansion', min(1.0, ratio / 3.0)
        elif ratio <= self.compression_ratio:
            obs_type, value = 'volatility_compression', -min(1.0, 1.0 / max(ratio, 1e-9) / 3.0)
        else:
            obs_type, value = 'volatility_normal', 0.0
        if obs_type == 'volatility_normal':
            conf = 0.3
        else:
            conf = min(0.9, 0.6 + 0.3 * min(1.0, abs(np.log(ratio)) / np.log(3.0)))
        regime = {'volatility_expansion': 'high', 'volatility_compression': 'low'}.get(obs_type, 'normal')
        observation = MarketObservation(
            symbol=symbol, observation_type=obs_type, observation_value=value,
            confidence=Percentage(Decimal(str(round(conf, 6)))), timestamp=datetime.now(),
            metadata={'realized_vol_1h': short, 'realized_vol_baseline': base, 'vol_ratio': ratio,
                      'current_regime': regime, 'previous_regime': self.previous_regime,
                      'baseline_bars': len(rets), 'volatility_source': self.name, 'mode': 'realized_ratio'})
        self.previous_regime = regime
        return observation

        # Calculate volatility metrics
        volatility_score = self.calculate_volatility_score()
        regime = self.get_current_regime(volatility_score)
        
        # Determine observation type based on volatility regime
        # Calculate confidence based on how far from neutral the volatility is
        volatility_magnitude = abs(volatility_score)

        if regime == "high":
            observation_type = 'volatility_expansion'
            observation_value = abs(volatility_score)  # Positive for expansion
            # Confidence increases with volatility magnitude
            confidence = min(0.95, max(0.2, volatility_magnitude))  # Lowered minimum confidence
        elif regime == "low":
            observation_type = 'volatility_compression'
            observation_value = -abs(volatility_score)  # Negative for compression
            # Confidence increases with volatility magnitude
            confidence = min(0.95, max(0.2, volatility_magnitude))  # Lowered minimum confidence
        else:
            observation_type = 'volatility_normal'
            observation_value = 0.0
            # For neutral state, confidence is lower but not fixed at 0.3
            # It's based on how close to neutral we are (smaller deviations = higher confidence in neutrality)
            confidence = min(0.4, (1.0 - volatility_magnitude))  # Lowered neutral confidence

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
                'volatility_score': volatility_score,
                'current_regime': regime,
                'previous_regime': self.previous_regime,
                'regime_change_detected': self.regime_change_detected,
                'atr_value': self.get_current_atr(),
                'volatility_source': self.name,
                'lookback_period': self.lookback,
                'price_history_length': len(self.price_history),
                'atr_history_length': len(self.atr_history)
            }
        )

        # Update previous regime for next iteration
        self.previous_regime = regime

        return observation

    def analyze(self, symbol: Symbol) -> MarketObservation:
        """Analyze market conditions and return a raw market observation"""
        return self._analyze_impl(symbol)

    def calculate_volatility_score(self) -> float:
        """Calculate a normalized volatility score"""
        if len(self.price_history) < 2:
            return 0.0

        # Calculate returns
        returns = np.diff(self.price_history[-self.lookback:])
        if len(returns) == 0:
            return 0.0

        # Calculate volatility (standard deviation of returns)
        volatility = np.std(returns)
        
        # Calculate average volatility for normalization
        if len(self.price_history) >= self.lookback * 2:
            historical_returns = np.diff(self.price_history[-self.lookback*2:-self.lookback])
            avg_volatility = np.std(historical_returns) if len(historical_returns) > 0 else volatility
        else:
            avg_volatility = volatility

        if avg_volatility == 0:
            return 0.0

        # Calculate relative volatility (how much above/below normal)
        relative_vol = (volatility - avg_volatility) / avg_volatility
        
        # Normalize to [-1, 1] range
        return max(-1.0, min(1.0, relative_vol))

    def get_current_regime(self, volatility_score: float) -> str:
        """Get current volatility regime"""
        if volatility_score > 0.2:  # Lowered threshold for high volatility
            return "high"
        elif volatility_score < -0.2:  # Lowered threshold for low volatility
            return "low"
        else:
            return "normal"

    def get_current_atr(self) -> float:
        """Get current ATR value"""
        if self.atr_history:
            return np.mean(self.atr_history[-self.period:])
        return 0.0