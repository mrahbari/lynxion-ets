from .base_watcher import BaseWatcher
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
from domain.value_objects import Symbol
import numpy as np
from typing import List, Optional


class AnomalyMLWatcher(BaseWatcher):
    """ML-based Anomaly Detection Watcher - detects unusual market patterns"""

    def __init__(self, name: str, symbol: str, broker_service=None, target_broker=None, lookback: int = 50, contamination: float = 0.1):
        super().__init__(name, symbol, broker_service, target_broker)
        self.lookback = lookback
        self.contamination = contamination  # Expected proportion of anomalies
        self.price_history = []
        self.feature_history = []  # Store calculated features
        self.anomaly_threshold = 0.5  # Threshold for anomaly detection
        self.model_fitted = False

        # Model parameters for anomaly detection
        self.feature_means = None
        self.feature_stds = None
        
    def update_data(self, data: dict):
        """Update with new market data"""
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
        """Calculate features for anomaly detection"""
        if len(self.price_history) < 5:
            return None
            
        prices = np.array(self.price_history[-5:])  # Use last 5 prices
        
        # Calculate various features that might indicate anomalies
        features = []
        
        # Price-based features
        returns = np.diff(prices) / prices[:-1] if len(prices) > 1 else [0]
        if len(returns) > 0:
            features.extend([
                returns[-1],  # Latest return
                np.mean(returns),  # Average return
                np.std(returns),  # Return volatility
                np.max(returns) if len(returns) > 0 else 0,  # Max return
                np.min(returns) if len(returns) > 0 else 0,  # Min return
            ])
        else:
            features.extend([0, 0, 0, 0, 0])
            
        # Price level features
        features.extend([
            (prices[-1] - np.min(prices)) / (np.max(prices) - np.min(prices)) if np.max(prices) != np.min(prices) else 0,  # Position in range
            prices[-1] / np.mean(prices) - 1,  # Price vs average
        ])
        
        # Volume features (if available in data)
        # Placeholder - would use actual volume data if available
        features.extend([0, 0])  # Placeholder for volume features
        
        return np.array(features)
        
    def fit_model(self):
        """Fit the anomaly detection model to historical data"""
        if len(self.feature_history) < 10:  # Need minimum data to fit
            return False
            
        features_matrix = np.array(self.feature_history)
        
        # Calculate statistics for anomaly detection
        self.feature_means = np.mean(features_matrix, axis=0)
        self.feature_stds = np.std(features_matrix, axis=0)
        
        # Prevent division by zero
        self.feature_stds = np.where(self.feature_stds == 0, 1, self.feature_stds)
        
        self.model_fitted = True
        logger.info(f"AnomalyMLWatcher {self.name} model fitted with {len(self.feature_history)} data points")
        return True
        
    def calculate_anomaly_score(self, features: np.ndarray) -> float:
        """Calculate anomaly score based on deviation from normal patterns"""
        if not self.model_fitted:
            # If model not fitted yet, just return a neutral score
            return 0.0
            
        # Calculate z-scores for each feature
        z_scores = np.abs((features - self.feature_means) / self.feature_stds)
        
        # Calculate combined anomaly score (average of z-scores)
        anomaly_score = np.mean(z_scores)
        
        # Normalize to 0-1 range based on threshold
        normalized_score = min(1.0, anomaly_score / 3.0)  # 3.0 is arbitrary scaling factor
        
        return normalized_score
        
    def analyze(self, symbol: Symbol) -> Signal:
        """Analyze for anomalies and return a signal"""
        if len(self.feature_history) < 10:
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

        # Update model if we have enough new data
        if not self.model_fitted or len(self.feature_history) % 20 == 0:  # Update every 20 new data points
            self.fit_model()

        # Determine signal based on anomaly detection
        if anomaly_score > self.anomaly_threshold:
            # Anomaly detected - this could be either a buying or selling opportunity
            # depending on the nature of the anomaly
            recent_returns = np.diff(self.price_history[-5:]) if len(self.price_history) >= 5 else [0]
            avg_return = np.mean(recent_returns) if recent_returns.size > 0 else 0

            if avg_return > 0:
                # Positive momentum with anomaly - potential reversal signal (SELL)
                signal_type = SignalType.SELL
            else:
                # Negative momentum with anomaly - potential reversal signal (BUY)
                signal_type = SignalType.BUY

            confidence = min(1.0, anomaly_score)
        elif anomaly_score < 0.1:
            # Very normal conditions - possible consolidation
            signal_type = SignalType.HOLD
            confidence = 0.7  # High confidence in hold signal during low anomaly periods
        else:
            # Normal conditions - hold
            signal_type = SignalType.HOLD
            confidence = max(0.3, 1.0 - anomaly_score)  # Lower confidence for hold as anomaly increases

        signal = Signal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            score=anomaly_score if signal_type != SignalType.HOLD else -anomaly_score,
            strategy=self.name,
            timestamp=datetime.now()
        )

        # Update last signal if it's different enough
        if self.should_emit_signal(signal):
            self.last_signal = signal
            logger.debug(f"AnomalyMLWatcher {self.name} generated signal: {signal_type} with anomaly score {anomaly_score:.3f}")

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
            'data_points': len(self.feature_history)
        }