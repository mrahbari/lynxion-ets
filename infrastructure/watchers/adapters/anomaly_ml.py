from .base_watcher import BaseWatcher
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
from domain.value_objects import Symbol
import numpy as np
import os
from typing import List, Optional


class AnomalyMLWatcher(BaseWatcher):
    """ML-based Anomaly Detection Watcher - detects unusual market patterns"""

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
        self.anomaly_threshold = 0.7  # Higher threshold to reduce frequent triggers
        self.suppression_threshold = 0.95  # Very high threshold for actual anomaly detection
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
            if len(self.price_history) > self.lookback * 3:
                self.price_history.pop(0)

        # Calculate and store features if we have enough price data
        if len(self.price_history) >= 5:
            features = self.calculate_features()
            if features is not None:
                self.feature_history.append(features)
                if len(self.feature_history) > self.lookback * 3:
                    self.feature_history.pop(0)

    def calculate_features(self) -> Optional[np.ndarray]:
        """Calculate features for anomaly detection - simplified and explainable"""
        if len(self.price_history) < 5:
            return None

        prices = np.array(self.price_history[-5:])  # Use last 5 prices

        # Calculate simple, explainable features that deviate from recent distribution
        features = []

        # Price returns (the most important indicator of unusual movement)
        returns = np.diff(prices) / prices[:-1] if len(prices) > 1 else [0]
        if len(returns) > 0:
            features.extend([
                returns[-1],  # Latest return - most recent price change
                np.mean(returns),  # Average return - baseline trend
                np.std(returns),  # Return volatility - recent volatility level
            ])
        else:
            features.extend([0, 0, 0])

        # Price position in recent range (how extreme the current price is)
        if len(prices) > 1:
            price_range = np.max(prices) - np.min(prices)
            if price_range != 0:
                position_in_range = (prices[-1] - np.min(prices)) / price_range
            else:
                position_in_range = 0.5  # Neutral if all prices are the same
        else:
            position_in_range = 0.5

        features.append(position_in_range)

        # Add a measure of acceleration (change in returns)
        if len(returns) >= 2:
            acceleration = returns[-1] - returns[-2] if len(returns) >= 2 else 0
        else:
            acceleration = 0
        features.append(acceleration)

        return np.array(features)

    def fit_model(self):
        """Fit the anomaly detection model to historical data"""
        if len(self.feature_history) < 15:  # Require more data for stability
            return False

        features_matrix = np.array(self.feature_history)

        # Calculate statistics for anomaly detection
        self.feature_means = np.mean(features_matrix, axis=0)
        self.feature_stds = np.std(features_matrix, axis=0)

        # Prevent division by zero - use a minimum standard deviation
        self.feature_stds = np.where(self.feature_stds == 0, 0.001, self.feature_stds)

        self.model_fitted = True
        logger.info(f"AnomalyMLWatcher {self.name} model fitted with {len(self.feature_history)} data points")
        return True

    def calculate_anomaly_score(self, features: np.ndarray) -> float:
        """Calculate anomaly score based on deviation from normal patterns - strict bounds"""
        if not self.model_fitted:
            # If model not fitted yet, return a neutral score
            return 0.0

        # Calculate z-scores for each feature
        z_scores = np.abs((features - self.feature_means) / self.feature_stds)

        # Calculate combined anomaly score (average of z-scores)
        # This represents "deviation from recent distribution by X sigma"
        raw_anomaly_score = np.mean(z_scores)

        # Normalize to 0-1 range with strict bounds
        # Use a sigmoid-like function to ensure very high scores only for extreme anomalies
        normalized_score = 1.0 / (1.0 + np.exp(-raw_anomaly_score + 3))  # Center around 3 sigma
        normalized_score = min(1.0, max(0.0, normalized_score))  # Ensure strict bounds

        return normalized_score

    def _analyze_impl(self, symbol: Symbol) -> Signal:
        """Analyze for anomalies and return a signal"""
        if not self.enabled:
            return None

        if len(self.feature_history) < 15:  # Require more data
            if not self.model_fitted:
                # Try to fit the model if we have enough data
                self.fit_model()
            return None

        # Get the latest features
        if not self.feature_history:
            return None

        latest_features = self.feature_history[-1]

        # Calculate anomaly score
        anomaly_score = self.calculate_anomaly_score(latest_features)

        # Update model periodically with fresh data
        if not self.model_fitted or len(self.feature_history) % 30 == 0:  # Update every 30 new data points
            self.fit_model()

        # Check if we're in cooldown period after last anomaly
        if (self.last_anomaly_timestamp is not None and
            len(self.feature_history) < self.data_point_counter + self.anomaly_cooldown):
            # During cooldown, only return HOLD signals with low confidence
            signal = Signal(
                symbol=symbol,
                signal_type=SignalType.HOLD,
                confidence=0.1,  # Very low confidence during cooldown
                score=0.0,
                strategy=self.name,
                timestamp=datetime.now(),
                metadata={
                    'anomaly_score': anomaly_score,
                    'explanation': f"Anomaly cooldown period, score: {anomaly_score:.3f}",
                    'anomaly_type': 'cooldown'
                }
            )
            return signal

        # Determine signal based on strict anomaly detection
        if anomaly_score > self.suppression_threshold:
            # Only very significant anomalies trigger signals
            # Determine direction based on recent price action
            recent_returns = np.diff(self.price_history[-5:]) if len(self.price_history) >= 5 else [0]
            avg_return = np.mean(recent_returns) if recent_returns.size > 0 else 0

            if avg_return > 0:
                # Positive momentum with significant anomaly - potential reversal (SELL)
                signal_type = SignalType.SELL
                anomaly_type = 'momentum_reversal'
            else:
                # Negative momentum with significant anomaly - potential reversal (BUY)
                signal_type = SignalType.BUY
                anomaly_type = 'momentum_reversal'

            # High confidence for very significant anomalies
            confidence = min(1.0, anomaly_score)

            # Update last anomaly timestamp
            self.last_anomaly_timestamp = len(self.feature_history)
            self.data_point_counter = len(self.feature_history)

        elif anomaly_score > self.anomaly_threshold:
            # Moderate anomalies - potential but not confirmed
            signal_type = SignalType.HOLD
            confidence = 0.4  # Low-medium confidence
            anomaly_type = 'potential_anomaly'
        else:
            # Normal conditions
            signal_type = SignalType.HOLD
            confidence = 0.9  # High confidence in normal conditions
            anomaly_type = 'normal'

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=anomaly_score if signal_type != SignalType.HOLD else -anomaly_score,
            strategy=self.name,
            timestamp=datetime.now(),
            metadata={
                'anomaly_score': anomaly_score,
                'anomaly_type': anomaly_type,
                'explanation': f"This deviates from recent distribution by approximately {np.mean(np.abs((latest_features - self.feature_means) / self.feature_stds)):.2f} sigma",
                'features': latest_features.tolist() if isinstance(latest_features, np.ndarray) else latest_features
            }
        )

        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            logger.debug(f"AnomalyMLWatcher {self.name} generated signal: {signal_type} with anomaly score {anomaly_score:.3f}, type: {anomaly_type}")

        return signal

    def get_anomaly_features(self) -> dict:
        """Get information about anomaly detection"""
        if not self.feature_history or not self.model_fitted:
            return {}

        latest_features = self.feature_history[-1]
        z_scores = np.abs((latest_features - self.feature_means) / self.feature_stds)

        return {
            'anomaly_score': self.calculate_anomaly_score(latest_features),
            'z_scores': z_scores.tolist(),
            'feature_means': self.feature_means.tolist() if self.feature_means is not None else [],
            'feature_stds': self.feature_stds.tolist() if self.feature_stds is not None else [],
            'model_fitted': self.model_fitted,
            'data_points': len(self.feature_history),
            'anomaly_threshold': self.anomaly_threshold,
            'suppression_threshold': self.suppression_threshold
        }