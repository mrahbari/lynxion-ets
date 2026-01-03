from .base_watcher import BaseWatcher
from domain.entities.signal_entities import MarketObservation
from domain.value_objects import Symbol, Percentage
from shared.logger import logger
from datetime import datetime
import numpy as np
import os
from typing import List, Optional
from decimal import Decimal


class AnomalyMLWatcher(BaseWatcher):
    """ML-based Anomaly Detection Watcher - detects unusual market patterns, returns raw market observations"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 50, contamination: float = 0.1):
        super().__init__(name, symbol, broker_service, target_broker)

        # Configuration from environment with defaults
        self.enabled = os.getenv('ANOMALY_ML_WATCHER_ENABLED', 'true').lower() == 'true'

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

        # Calculate features based on available data
        if len(self.price_history) >= 2:
            features = self.calculate_features()
            self.feature_history.append(features)
            if len(self.feature_history) > self.lookback * 3:
                self.feature_history.pop(0)

    def _analyze_impl(self, symbol: Symbol) -> MarketObservation:
        """Analyze market for anomalies and return a raw market observation (no strategy selection)"""
        if not self.enabled:
            return None

        if len(self.feature_history) < self.lookback:
            return None

        # Calculate anomaly score based on current features
        anomaly_score = self.calculate_anomaly_score()
        
        # Determine observation type based on anomaly score
        # Calculate confidence based on the strength of the anomaly
        anomaly_magnitude = abs(anomaly_score)

        if abs(anomaly_score) < 0.3:  # Threshold for normal market conditions
            observation_type = 'anomaly_normal'
            observation_value = 0.0
            # For neutral state, confidence is based on how close to normal we are
            confidence = min(0.6, (1.0 - anomaly_magnitude))
        elif anomaly_score > 0:
            observation_type = 'anomaly_positive'  # Positive anomaly (unusual upward movement)
            observation_value = abs(anomaly_score)
            # Confidence increases with anomaly magnitude
            confidence = min(0.95, max(0.3, anomaly_magnitude))
        else:
            observation_type = 'anomaly_negative'  # Negative anomaly (unusual downward movement)
            observation_value = -abs(anomaly_score)
            # Confidence increases with anomaly magnitude
            confidence = min(0.95, max(0.3, anomaly_magnitude))

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
                'anomaly_score': anomaly_score,
                'feature_vector': self.feature_history[-1] if self.feature_history else [],
                'feature_history_length': len(self.feature_history),
                'price_history_length': len(self.price_history),
                'model_fitted': self.model_fitted,
                'last_anomaly_timestamp': self.last_anomaly_timestamp,
                'anomaly_source': self.name,
                'lookback_period': self.lookback
            }
        )

        return observation

    def calculate_features(self) -> List[float]:
        """Calculate features for anomaly detection"""
        if len(self.price_history) < 2:
            return [0.0] * 5  # Return 5 features with default values

        # Feature 1: Price change percentage
        recent_change = (self.price_history[-1] - self.price_history[-2]) / self.price_history[-2]

        # Feature 2: Volatility (standard deviation of recent prices)
        lookback_vol = min(10, len(self.price_history))
        if len(self.price_history) >= lookback_vol:
            recent_prices = self.price_history[-lookback_vol:]
            volatility = np.std(recent_prices) / np.mean(recent_prices) if np.mean(recent_prices) != 0 else 0
        else:
            volatility = 0

        # Feature 3: Momentum (difference between current price and average of previous n prices)
        lookback_mom = min(5, len(self.price_history) - 1)
        if lookback_mom > 0:
            avg_prev = np.mean(self.price_history[-lookback_mom-1:-1])
            momentum = (self.price_history[-1] - avg_prev) / avg_prev if avg_prev != 0 else 0
        else:
            momentum = 0

        # Feature 4: Rate of change
        lookback_roc = min(3, len(self.price_history) - 1)
        if lookback_roc > 0:
            roc = (self.price_history[-1] - self.price_history[-lookback_roc-1]) / self.price_history[-lookback_roc-1] if self.price_history[-lookback_roc-1] != 0 else 0
        else:
            roc = 0

        # Feature 5: Volume change (if available)
        # For now, we'll use a placeholder since volume data might not be available in update_data
        volume_change = 0.0  # Placeholder - would use actual volume data if available

        return [recent_change, volatility, momentum, roc, volume_change]

    def calculate_anomaly_score(self) -> float:
        """Calculate anomaly score based on features"""
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

        # Calculate overall anomaly score as average of z-scores
        anomaly_score = np.mean(z_scores)

        # Normalize to [-1, 1] range by using tanh or similar function
        # But keep it positive for anomalies, negative for unusual stability
        return float(np.tanh(anomaly_score - 1))  # Center around 0, positive for anomalies above baseline