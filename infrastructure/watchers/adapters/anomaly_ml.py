from .base_watcher import BaseWatcher
from domain.entities.signal_entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import List, Optional
from decimal import Decimal
from infrastructure.logging.forensic_logger import forensic_logger
from application.configs.configs import Configs


class AnomalyMLWatcher(BaseWatcher):
    """ML-based Anomaly Detection Watcher - detects unusual market patterns, returns raw market observations"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 50,
                 contamination: float = 0.1):
        # Convert symbol string to Symbol object if needed
        self.volume_history = []  # Initialize as empty list instead of None
        symbol_obj = Symbol(symbol) if isinstance(symbol, str) else symbol
        super().__init__(name, symbol_obj)

        # Store broker service and other parameters separately
        self.broker_service = broker_service
        self.target_broker = target_broker

        # Configuration from environment with defaults
        self.enabled = Configs.watcher.anomaly_ml_watcher_enabled if Configs.watcher and hasattr(Configs.watcher, 'anomaly_ml_watcher_enabled') else True

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
        self.contamination = contamination  # Expected proportion of anomalies
        self.price_history = []
        self.feature_history = []  # Store calculated features
        self.anomaly_threshold = 0.6  # Lowered threshold to allow more signals (was 0.7)
        self.suppression_threshold = 0.7  # Lowered threshold to allow more trading signals (was 0.95)
        self.model_fitted = False
        self.last_anomaly_timestamp = None
        self.anomaly_cooldown = 20  # Cooldown period after anomaly detection

        # Model parameters for anomaly detection
        self.feature_means = None
        self.feature_stds = None

        # Counters for deterministic behavior
        self.data_point_counter = 0

    def update_data(self, data: dict):
        """Update with new market data"""
        if not self.enabled:
            return

        if 'close' in data:
            self.price_history.append(data['close'])
            if len(self.price_history) > self.lookback * 3:  # Keep more data for stability
                self.price_history.pop(0)

        # Handle volume data if available
        if 'volume' in data:
            self.volume_history.append(data['volume'])
            if len(self.volume_history) > self.lookback * 3:  # Keep more data for stability
                self.volume_history.pop(0)

        # Calculate features based on available data
        if len(self.price_history) >= 2:
            features = self.calculate_features()
            self.feature_history.append(features)
            if len(self.feature_history) > self.lookback * 3:
                self.feature_history.pop(0)

    def _analyze_impl(self, symbol: Symbol) -> MarketObservation:
        """Analyze market for anomalies with enhanced momentum spike detection and return a raw market observation"""
        if not self.enabled:
            return None

        if len(self.feature_history) < 2:  # Require only 2 data points to start generating observations
            return None

        # Calculate anomaly score based on current features
        anomaly_score = self.calculate_anomaly_score()

        # Extract current features to identify momentum spikes specifically
        current_features = self.feature_history[-1] if self.feature_history else [0.0] * 7
        recent_change, short_momentum, medium_momentum, roc, volatility, vol_acceleration, momentum_acceleration = current_features

        # Calculate momentum-specific metrics
        momentum_intensity = abs(recent_change) + abs(short_momentum) + abs(momentum_acceleration)
        volume_pressure = abs(vol_acceleration) if len(current_features) > 5 else 0

        # Determine if this is a momentum spike based on specific criteria
        is_momentum_spike = (
                abs(recent_change) > 0.03 or  # 3%+ price move
                abs(short_momentum) > 0.04 or  # Strong short-term momentum
                abs(momentum_acceleration) > 0.02 or  # Accelerating momentum
                (abs(recent_change) > 0.015 and volume_pressure > 0.5)  # Price move with volume confirmation
        )

        # Determine observation type based on anomaly score and momentum characteristics
        # Calculate confidence based on the strength of the anomaly and momentum features
        anomaly_magnitude = abs(anomaly_score)

        if is_momentum_spike and anomaly_magnitude > 0.15:
            # Classify as momentum spike if specific momentum criteria are met
            if recent_change > 0:
                observation_type = 'momentum_spike_upward'
                observation_value = min(1.0, momentum_intensity)  # Cap at 1.0
            else:
                observation_type = 'momentum_spike_downward'
                observation_value = -min(1.0, momentum_intensity)  # Cap at -1.0

            # Higher confidence for momentum spikes
            confidence = min(0.98, max(0.6, anomaly_magnitude + (momentum_intensity * 0.3)))
        elif abs(anomaly_score) < 0.1:  # Normal market conditions
            observation_type = 'anomaly_normal'
            observation_value = 0.0
            # For neutral state, confidence is based on how close to normal we are
            confidence = min(0.5, (1.0 - anomaly_magnitude))
        elif anomaly_score > 0:
            observation_type = 'anomaly_positive'  # General positive anomaly
            observation_value = abs(anomaly_score)
            
            # 🛡️ DYNAMIC CONFIDENCE: Better granularity for ML anomalies
            if anomaly_magnitude <= 0.8:
                confidence = 0.2 + (0.7 * anomaly_magnitude)
            else:
                # Asymptotic approach to 0.95
                confidence = 0.8 + 0.15 * (1.0 - (1.0 / (anomaly_magnitude * 5)))
            
            confidence = min(0.95, max(0.15, confidence))
        else:
            observation_type = 'anomaly_negative'  # General negative anomaly
            observation_value = -abs(anomaly_score)
            
            # Same dynamic logic for negative anomalies
            if anomaly_magnitude <= 0.8:
                confidence = 0.2 + (0.7 * anomaly_magnitude)
            else:
                confidence = 0.8 + 0.15 * (1.0 - (1.0 / (anomaly_magnitude * 5)))
                
            confidence = min(0.95, max(0.15, confidence))

        # Convert confidence to Percentage object for domain compatibility
        confidence_percentage = Percentage(Decimal(str(confidence)))

        # Create and return a MarketObservation with enhanced momentum metadata
        observation = MarketObservation(
            symbol=symbol,
            observation_type=observation_type,
            observation_value=observation_value,
            confidence=confidence_percentage,
            timestamp=datetime.now(),
            metadata={
                'anomaly_score': anomaly_score,
                'momentum_intensity': momentum_intensity,
                'recent_price_change': recent_change,
                'short_term_momentum': short_momentum,
                'medium_term_momentum': medium_momentum,
                'rate_of_change': roc,
                'volatility_level': volatility,
                'volume_acceleration': volume_pressure,
                'momentum_acceleration': momentum_acceleration,
                'is_momentum_spike': is_momentum_spike,
                'feature_vector': current_features,
                'feature_history_length': len(self.feature_history),
                'price_history_length': len(self.price_history),
                'model_fitted': self.model_fitted if hasattr(self, 'model_fitted') else True,
                'last_anomaly_timestamp': self.last_anomaly_timestamp if hasattr(self,
                                                                                 'last_anomaly_timestamp') else None,
                'anomaly_source': self.name,
                'lookback_period': self.lookback
            }
        )

        # Log the watcher observation to forensic log
        forensic_logger.log_watcher_observation(
            watcher=self.name,
            symbol=symbol.value,
            exchange=getattr(self, 'target_broker', 'BINANCE'),  # Use target broker if available, otherwise default
            observation_type=observation_type,
            value=observation_value,
            confidence=float(confidence_percentage.value),
            timestamp=observation.timestamp
        )

        return observation

    def analyze(self, symbol: Symbol) -> MarketObservation:
        """Analyze market conditions and return a raw market observation"""
        return self._analyze_impl(symbol)

    def calculate_features(self) -> List[float]:
        """Calculate features for anomaly detection with enhanced momentum spike detection"""
        if len(self.price_history) < 2:
            return [0.0] * 7  # Return 7 features with default values

        # Feature 1: Recent price change percentage (emphasizes short-term momentum)
        recent_change = (self.price_history[-1] - self.price_history[-2]) / self.price_history[-2]

        # Feature 2: Short-term momentum (last 3 periods)
        lookback_short = min(3, len(self.price_history) - 1)
        if lookback_short > 0:
            avg_short = np.mean(self.price_history[-lookback_short - 1:-1])
            short_momentum = (self.price_history[-1] - avg_short) / avg_short if avg_short != 0 else 0
        else:
            short_momentum = 0

        # Feature 3: Medium-term momentum (last 5 periods)
        lookback_medium = min(5, len(self.price_history) - 1)
        if lookback_medium > 0:
            avg_medium = np.mean(self.price_history[-lookback_medium - 1:-1])
            medium_momentum = (self.price_history[-1] - avg_medium) / avg_medium if avg_medium != 0 else 0
        else:
            medium_momentum = 0

        # Feature 4: Rate of change with emphasis on recent acceleration
        lookback_roc = min(3, len(self.price_history) - 1)
        if lookback_roc > 0:
            roc = (self.price_history[-1] - self.price_history[-lookback_roc - 1]) / self.price_history[
                -lookback_roc - 1] if self.price_history[-lookback_roc - 1] != 0 else 0
        else:
            roc = 0

        # Feature 5: Volatility (standard deviation of recent prices)
        lookback_vol = min(10, len(self.price_history))
        if len(self.price_history) >= lookback_vol:
            recent_prices = self.price_history[-lookback_vol:]
            volatility = np.std(recent_prices) / np.mean(recent_prices) if np.mean(recent_prices) != 0 else 0
        else:
            volatility = 0

        # Feature 6: Volume acceleration (if volume data is available in the data dict)
        # We'll store volume data separately since it comes with market updates
        if hasattr(self, 'volume_history') and self.volume_history:
            # Calculate volume acceleration
            if len(self.volume_history) >= 2:
                recent_vol_change = (self.volume_history[-1] - self.volume_history[-2]) / self.volume_history[-2] if \
                self.volume_history[-2] != 0 else 0
                avg_vol = np.mean(self.volume_history[-5:]) if len(self.volume_history) >= 5 else self.volume_history[
                    -1]
                vol_acceleration = (self.volume_history[-1] - avg_vol) / avg_vol if avg_vol != 0 else 0
            else:
                recent_vol_change = 0
                vol_acceleration = 0
        else:
            # Initialize volume history if not present
            self.volume_history = []
            recent_vol_change = 0
            vol_acceleration = 0

        # Feature 7: Momentum acceleration (acceleration of momentum)
        if len(self.price_history) >= 3:
            # Calculate momentum of momentum
            prev_momentum = (self.price_history[-2] - self.price_history[-3]) / self.price_history[-3] if \
            self.price_history[-3] != 0 else 0
            current_momentum = recent_change
            momentum_acceleration = current_momentum - prev_momentum
        else:
            momentum_acceleration = 0

        return [recent_change, short_momentum, medium_momentum, roc, volatility, vol_acceleration,
                momentum_acceleration]

    def calculate_anomaly_score(self) -> float:
        """Calculate anomaly score based on features with enhanced sensitivity to momentum spikes"""
        if not self.feature_history:
            return 0.0

        current_features = self.feature_history[-1]

        # If we don't have enough history to establish a baseline, return 0
        if len(self.feature_history) < 10:
            return 0.0

        # Calculate baseline statistics from historical features
        historical_features = np.array(self.feature_history[:-1])  # Exclude current
        if historical_features.size == 0:
            return 0.0

        # Calculate mean and std for each feature
        feature_means = np.mean(historical_features, axis=0)
        feature_stds = np.std(historical_features, axis=0)

        # Avoid division by zero
        feature_stds = np.where(feature_stds == 0, 1, feature_stds)

        # Calculate z-scores for each feature
        z_scores = np.abs((np.array(current_features) - feature_means) / feature_stds)

        # Enhance sensitivity to momentum-related features (indices 0, 1, 2, 3, 6)
        # These correspond to: recent_change, short_momentum, medium_momentum, roc, momentum_acceleration
        momentum_feature_weights = np.array([1.5, 1.5, 1.3, 1.3, 1.0, 1.2, 1.4])  # Higher weights for momentum features

        # Apply weights to z-scores
        weighted_z_scores = z_scores * momentum_feature_weights

        # Calculate overall anomaly score as weighted average of z-scores
        anomaly_score = np.mean(weighted_z_scores)

        # Normalize to [-1, 1] range by using tanh or similar function
        # But keep it positive for anomalies, negative for unusual stability
        # Increase sensitivity by using a scaled version before tanh
        scaled_score = anomaly_score * 1.5  # Amplify the score to make it more sensitive to momentum spikes

        return float(np.tanh(scaled_score - 1))  # Center around 0, positive for anomalies above baseline
