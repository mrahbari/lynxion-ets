"""
Machine Learning-based signal fusion implementation for the enterprise hedge fund trading system.
This service uses ML algorithms to intelligently combine multiple signals.
"""
from typing import List, Dict, Any, Optional
from enum import Enum
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, mean_squared_error
from datetime import datetime

from domain.entities import Signal
from domain.value_objects import Symbol, Percentage
from domain.ports.engine_ports import FusionPort
from shared.logger import logger


class MLFusionMethod(Enum):
    """Types of ML fusion methods available"""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    LOGISTIC_REGRESSION = "logistic_regression"
    ENSEMBLE = "ensemble"


class MLSignalFusionService(FusionPort):
    """Machine Learning-based signal fusion service"""

    def __init__(self, 
                 method: MLFusionMethod = MLFusionMethod.RANDOM_FOREST,
                 training_window: int = 252,  # Training window in days
                 feature_horizon: int = 5):  # Predict return over next 5 periods
        self.method = method
        self.training_window = training_window
        self.feature_horizon = feature_horizon
        
        # Initialize ML models based on selected method
        self.models = {}
        self.scalers = {}
        self.feature_columns = []
        self.is_trained = False
        self._initialize_models()
        
        # Training data buffers
        self.signal_buffer: List[Dict[str, Any]] = []
        self.outcome_buffer: List[float] = []  # Future returns for supervised learning
        
    def _initialize_models(self):
        """Initialize ML models based on selected method"""
        self.feature_columns = [
            'signal_strength', 'confidence', 'strategy_type', 'time_of_day',
            'volatility_regime', 'trend_strength', 'correlation_with_portfolio',
            'historical_accuracy', 'signal_frequency', 'market_regime'
        ]
        
        if self.method in [MLFusionMethod.RANDOM_FOREST, MLFusionMethod.ENSEMBLE]:
            self.models['random_forest_classifier'] = RandomForestClassifier(n_estimators=100, random_state=42)
            self.models['random_forest_regressor'] = RandomForestRegressor(n_estimators=100, random_state=42)
            
        if self.method in [MLFusionMethod.GRADIENT_BOOSTING, MLFusionMethod.ENSEMBLE]:
            self.models['gradient_boosting_classifier'] = GradientBoostingClassifier(random_state=42)
            self.models['gradient_boosting_regressor'] = GradientBoostingRegressor(random_state=42)
            
        if self.method in [MLFusionMethod.LOGISTIC_REGRESSION, MLFusionMethod.ENSEMBLE]:
            self.models['logistic_regression'] = LogisticRegression(random_state=42)
        
        # Initialize scalers for numerical features
        self.scalers['signal_features'] = StandardScaler()
    
    def fuse_signals(self, signals: List[Signal]) -> Optional[Signal]:
        """Fuse multiple signals using ML-based methods"""
        if not signals:
            logger.warning("No signals to fuse using ML fusion")
            return None
            
        if len(signals) < 2:
            logger.info("Single signal provided, returning as-is for ML fusion")
            return signals[0]
        
        # Extract features from signals
        features_df = self._extract_signal_features(signals)
        
        # If we have trained models, use them to predict fused signal
        if self.is_trained:
            try:
                # Transform features using the fitted scaler
                feature_array = self.scalers['signal_features'].transform(features_df.values)
                
                # Get predictions from all available models
                predictions = self._get_ml_predictions(feature_array)
                
                # Combine predictions based on model performance
                fused_signal = self._combine_ml_predictions(signals, predictions, features_df)
                logger.info(f"ML fusion completed for {len(signals)} signals, result: {fused_signal.signal_type.name}")
                return fused_signal
            except Exception as e:
                logger.error(f"Error in ML fusion prediction: {e}")
                # Fallback to traditional fusion if ML fails
                return self._fallback_traditional_fusion(signals)
        else:
            logger.info("ML models not trained yet, using traditional fusion as fallback")
            return self._fallback_traditional_fusion(signals)
    
    def _extract_signal_features(self, signals: List[Signal]) -> pd.DataFrame:
        """Extract features from signals for ML models"""
        features = []
        
        for i, signal in enumerate(signals):
            signal_features = {
                'signal_strength': signal.score,
                'confidence': float(signal.confidence.value),
                'strategy_type': self._hash_strategy_type(signal.strategy_name),
                'time_of_day': self._get_time_feature(signal.timestamp),
                'volatility_regime': self._get_volatility_regime(signal),
                'trend_strength': self._get_trend_strength(signal),
                'correlation_with_portfolio': self._get_correlation_with_portfolio(signal),
                'historical_accuracy': self._get_historical_accuracy(signal.strategy_name),
                'signal_frequency': self._get_signal_frequency(signal.strategy_name),
                'market_regime': self._get_market_regime(signal),
                'signal_type_encoded': 1 if signal.signal_type.name == 'BUY' else (-1 if signal.signal_type.name == 'SELL' else 0),
            }
            
            # Calculate differences with other signals
            signal_differences = []
            for j, other_signal in enumerate(signals):
                if i != j:
                    difference = abs(signal.confidence.value - other_signal.confidence.value)
                    signal_differences.append(float(difference))
            
            # Average difference with other signals
            if signal_differences:
                signal_features['avg_confidence_difference'] = np.mean(signal_differences)
                signal_features['max_confidence_difference'] = np.max(signal_differences)
            else:
                signal_features['avg_confidence_difference'] = 0.0
                signal_features['max_confidence_difference'] = 0.0
            
            features.append(signal_features)
        
        # Convert to DataFrame and ensure all columns exist
        df = pd.DataFrame(features)
        
        # Add aggregated features across all signals
        df['avg_confidence'] = df['confidence'].mean()
        df['std_confidence'] = df['confidence'].std()
        df['max_confidence'] = df['confidence'].max()
        df['signal_count'] = len(signals)
        df['majority_signal'] = 1 if df['signal_type_encoded'].sum() > 0 else (-1 if df['signal_type_encoded'].sum() < 0 else 0)
        
        return df
    
    def _hash_strategy_type(self, strategy_name: str) -> int:
        """Convert strategy name to a consistent integer value"""
        return hash(strategy_name) % 10000
    
    def _get_time_feature(self, timestamp: datetime) -> int:
        """Extract time-based feature (hour of day)"""
        return timestamp.hour if timestamp else 12  # Default to noon if no timestamp
    
    def _get_volatility_regime(self, signal: Signal) -> float:
        """Extract volatility regime from signal metadata if available"""
        metadata = signal.metadata or {}
        return float(metadata.get('volatility_regime', 0.5))  # Default to 0.5 if not provided
    
    def _get_trend_strength(self, signal: Signal) -> float:
        """Extract trend strength from signal metadata if available"""
        metadata = signal.metadata or {}
        return float(metadata.get('trend_strength', 0.5))  # Default to 0.5 if not provided
    
    def _get_correlation_with_portfolio(self, signal: Signal) -> float:
        """Extract correlation with portfolio from signal metadata if available"""
        metadata = signal.metadata or {}
        return float(metadata.get('correlation_with_portfolio', 0.0))  # Default to 0.0 if not provided
    
    def _get_historical_accuracy(self, strategy_name: str) -> float:
        """Get historical accuracy of the strategy (placeholder)"""
        # In a real implementation, this would look up historical performance
        return 0.55  # Default to 55% accuracy
    
    def _get_signal_frequency(self, strategy_name: str) -> float:
        """Get frequency of signals from this strategy (placeholder)"""
        # In a real implementation, this would track signal frequency
        return 0.4  # Default to 40% frequency
    
    def _get_market_regime(self, signal: Signal) -> int:
        """Extract market regime from signal metadata if available"""
        metadata = signal.metadata or {}
        regime_map = {'bull': 1, 'bear': -1, 'sideways': 0, 'normal': 0, 'volatile': 2, 'trending': 1}
        return regime_map.get(str(metadata.get('market_regime', 'normal')).lower(), 0)
    
    def _get_ml_predictions(self, feature_array: np.ndarray) -> Dict[str, Any]:
        """Get predictions from all trained ML models"""
        predictions = {}
        
        for model_name, model in self.models.items():
            try:
                if 'classifier' in model_name:
                    # Classification model predicts signal direction
                    pred_proba = model.predict_proba(feature_array)
                    # Assuming binary classification [BUY, SELL], take probability of BUY
                    predictions[f"{model_name}_probabilities"] = pred_proba
                    predictions[f"{model_name}_prediction"] = model.predict(feature_array)
                
                elif 'regressor' in model_name:
                    # Regression model predicts signal strength
                    predictions[f"{model_name}_prediction"] = model.predict(feature_array)
            
            except Exception as e:
                logger.warning(f"Error getting prediction from {model_name}: {e}")
        
        return predictions
    
    def _combine_ml_predictions(self, signals: List[Signal], predictions: Dict[str, Any], features_df: pd.DataFrame) -> Signal:
        """Combine predictions from ML models to form final signal"""
        # For demonstration purposes, let's create a simplified combination
        # In a real implementation, this would be more sophisticated
        
        # Calculate ensemble prediction by averaging different models
        direction_prediction = 0
        strength_prediction = 0
        confidence_prediction = 0
        
        # Weight different model predictions
        prediction_counter = 0
        for key, value in predictions.items():
            if 'classifier' in key and '_prediction' in key and len(value) > 0:
                # Classifier prediction (direction)
                direction_prediction += float(value[0])
                prediction_counter += 1
            elif 'regressor' in key and '_prediction' in key and len(value) > 0:
                # Regressor prediction (strength)
                strength_prediction += float(value[0])
        
        if prediction_counter > 0:
            direction_prediction /= prediction_counter
            strength_prediction /= max(prediction_counter, 1)  # Avoid division by zero
        
        # Determine signal type based on direction prediction
        if direction_prediction > 0.5:
            signal_type = signals[0].signal_type.__class__.BUY  # type: ignore
        elif direction_prediction < -0.5:
            signal_type = signals[0].signal_type.__class__.SELL  # type: ignore
        else:
            signal_type = signals[0].signal_type.__class__.NEUTRAL  # type: ignore
        
        # Calculate confidence based on prediction certainty and number of agreeing models
        agreement_level = abs(direction_prediction) if abs(direction_prediction) <= 1 else 1
        avg_confidence = np.mean([float(s.confidence.value) for s in signals])
        final_confidence = (agreement_level * 0.7 + avg_confidence * 0.3)
        
        # Calculate final score
        final_score = strength_prediction if abs(strength_prediction) <= 1 else np.sign(strength_prediction)
        
        # Create the fused signal
        fused_signal = Signal(
            symbol=signals[0].symbol,  # Use first signal's symbol (should all be the same)
            signal_type=signal_type,
            confidence=Percentage(str(max(0.1, min(1.0, final_confidence)))),  # Clamp between 0.1 and 1.0
            score=max(-1.0, min(1.0, final_score)),  # Clamp between -1.0 and 1.0
            source_layer="fusion",
            timestamp=datetime.now(),
            metadata={
                'strategy_name': "MLFusionService",
                'original_signals_count': len(signals),
                'ml_fusion_method': self.method.value,
                'ml_direction_prediction': direction_prediction,
                'ml_strength_prediction': strength_prediction,
                'ml_predictions_used': len([k for k in predictions.keys() if 'prediction' in k]),
                'ml_fusion_applied': True
            }
        )
        
        return fused_signal
    
    def _fallback_traditional_fusion(self, signals: List[Signal]) -> Signal:
        """Fallback to traditional weighted fusion when ML models aren't available"""
        # Calculate weighted average of scores
        total_weight = 0.0
        weighted_scores = []
        
        for signal in signals:
            weight = float(signal.confidence.value)
            weighted_score = signal.score * weight
            weighted_scores.append(weighted_score)
            total_weight += weight
        
        # Calculate the fused score
        fused_score = sum(weighted_scores) / total_weight if total_weight > 0 else 0.0
        
        # Determine signal type based on the sign of the fused score
        if fused_score > 0.1:  # Threshold to avoid neutral signals
            fused_signal_type = signals[0].signal_type.__class__.BUY  # type: ignore
        elif fused_score < -0.1:
            fused_signal_type = signals[0].signal_type.__class__.SELL  # type: ignore
        else:
            fused_signal_type = signals[0].signal_type.__class__.NEUTRAL  # type: ignore
        
        # Calculate fused confidence as the weighted average of confidences
        confidence_values = [float(s.confidence.value) for s in signals]
        weighted_confidences = [conf * float(signals[i].confidence.value) for i, conf in enumerate(confidence_values)]
        fused_confidence = sum(weighted_confidences) / total_weight if total_weight > 0 else 0.5
        
        # Create the fused signal
        from domain.entities import Signal as DomainSignal
        from domain.value_objects import Percentage as DomainPercentage
        from decimal import Decimal
        
        return DomainSignal(
            symbol=signals[0].symbol,
            signal_type=fused_signal_type,
            confidence=DomainPercentage(Decimal(str(max(0.1, min(1.0, fused_confidence))))),  # Clamp to [0.1, 1.0]
            score=max(-1.0, min(1.0, fused_score)),  # Clamp to [-1, 1]
            source_layer="fusion",
            timestamp=datetime.now(),
            metadata={
                'strategy_name': "FallbackFusionService",
                'original_signals_count': len(signals),
                'fusion_method': 'traditional_weighted',
                'ml_fusion_failed': True
            }
        )
    
    def train_with_feedback(self, signals: List[Signal], actual_outcome: float):
        """Train ML models with feedback about actual outcomes"""
        try:
            # Extract features from signals
            features_df = self._extract_signal_features(signals)
            
            # Add this to the training buffer
            self.signal_buffer.append({
                'features': features_df,
                'outcome': actual_outcome
            })
            
            # Keep training window limited
            if len(self.signal_buffer) > self.training_window:
                self.signal_buffer = self.signal_buffer[-self.training_window:]
            
            # Retrain models if we have enough data
            if len(self.signal_buffer) >= 50:  # Minimum samples to retrain
                self._perform_retraining()
                logger.info(f"ML fusion models retrained with {len(self.signal_buffer)} samples")
            
        except Exception as e:
            logger.error(f"Error in ML fusion training: {e}")
    
    def _perform_retraining(self):
        """Perform actual model retraining"""
        if not self.signal_buffer:
            return
            
        # Prepare training data
        X_list = []
        y_direction_list = []
        y_strength_list = []
        
        for item in self.signal_buffer:
            features_df = item['features']
            outcome = item['outcome']  # Actual return/price movement
            
            # Flatten features (taking mean of multiple signals' features)
            for _, row in features_df.iterrows():
                X_list.append(row.values)
                # Direction: positive outcome = BUY, negative = SELL
                y_direction_list.append(1 if outcome > 0 else (-1 if outcome < 0 else 0))
                # Strength: magnitude of outcome
                y_strength_list.append(outcome)
        
        if len(X_list) < 10:  # Need minimum samples to train
            return
            
        X = np.array(X_list)
        y_direction = np.array(y_direction_list)
        y_strength = np.array(y_strength_list)
        
        # Fit scalers and transform data
        X_scaled = self.scalers['signal_features'].fit_transform(X)
        
        # Train models based on selected method
        if self.method in [MLFusionMethod.RANDOM_FOREST, MLFusionMethod.ENSEMBLE]:
            try:
                self.models['random_forest_classifier'].fit(X_scaled, y_direction)
                self.models['random_forest_regressor'].fit(X_scaled, y_strength)
            except Exception as e:
                logger.error(f"Error training Random Forest models: {e}")
        
        if self.method in [MLFusionMethod.GRADIENT_BOOSTING, MLFusionMethod.ENSEMBLE]:
            try:
                self.models['gradient_boosting_classifier'].fit(X_scaled, y_direction)
                self.models['gradient_boosting_regressor'].fit(X_scaled, y_strength)
            except Exception as e:
                logger.error(f"Error training Gradient Boosting models: {e}")
        
        if self.method in [MLFusionMethod.LOGISTIC_REGRESSION, MLFusionMethod.ENSEMBLE]:
            try:
                self.models['logistic_regression'].fit(X_scaled, y_direction)
            except Exception as e:
                logger.error(f"Error training Logistic Regression model: {e}")
        
        self.is_trained = True
        logger.info(f"ML fusion models retrained successfully with {len(X_list)} samples")
    
    def get_model_performance(self) -> Dict[str, Any]:
        """Get performance metrics for the ML models"""
        if not self.is_trained:
            return {"error": "Models not trained yet"}
        
        # This would return actual performance metrics in a real implementation
        # For now, we'll return placeholder values
        return {
            "models_trained": [name for name in self.models.keys()],
            "training_samples": len(self.signal_buffer),
            "is_trained": self.is_trained,
            "feature_count": len(self.feature_columns) if self.feature_columns else 0
        }