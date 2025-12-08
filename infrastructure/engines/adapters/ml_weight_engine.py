from ..base_engine import BaseEngine
from shared.types import Signal, SignalType
from shared.logger import logger
from datetime import datetime
import numpy as np
from typing import Dict, List, Optional
from collections import deque


class MLWeightEngine(BaseEngine):
    """ML Weight Engine - uses machine learning to dynamically weight and combine signals"""
    
    def __init__(self, name: str, lookback: int = 50, learning_rate: float = 0.01):
        super().__init__(name)
        self.lookback = lookback
        self.learning_rate = learning_rate
        
        # Historical performance tracking
        self.signal_performance_history = deque(maxlen=lookback)
        self.weights = {}  # Strategy name -> weight
        self.feature_history = deque(maxlen=lookback)
        
        # Performance metrics
        self.profitable_signals = 0
        self.total_signals = 0
        self.cumulative_pnl = 0.0
        
        # ML model parameters (simple linear model for this example)
        self.model_weights = np.zeros(5)  # [bias, signal_strength, confidence, volatility, trend]
        self.model_bias = 0.0
        
    def update_data(self, data: Dict):
        """Update with new market data"""
        # In a real implementation, this would update features for ML model
        # For this example, we'll just log that we received data
        pass
    
    def record_signal_performance(self, signal: Signal, realized_pnl: float):
        """Record the performance of a signal for learning"""
        self.total_signals += 1
        if realized_pnl > 0:
            self.profitable_signals += 1
        self.cumulative_pnl += realized_pnl
        
        # Store signal performance for ML model
        performance_record = {
            'signal': signal,
            'pnl': realized_pnl,
            'timestamp': datetime.now()
        }
        self.signal_performance_history.append(performance_record)
        
        # Update weights based on performance
        self.update_weights(signal, realized_pnl > 0)
    
    def update_weights(self, signal: Signal, profitable: bool):
        """Update weights based on signal performance"""
        strategy = signal.strategy
        if strategy not in self.weights:
            self.weights[strategy] = 1.0  # Start with neutral weight
        
        # Adjust weight based on performance
        if profitable:
            self.weights[strategy] = min(2.0, self.weights[strategy] * (1 + self.learning_rate))
        else:
            self.weights[strategy] = max(0.1, self.weights[strategy] * (1 - self.learning_rate))
    
    def process_signal(self, signal: Signal) -> Signal:
        """Process a signal through ML-based weighting"""
        if not self.weights:
            # If no learned weights yet, use original signal
            return Signal(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence=signal.confidence,
                score=signal.score,
                strategy=f"{signal.strategy}_ml_weighted",
                timestamp=datetime.now(),
                metadata=signal.metadata
            )
            
        # Get the weight for this strategy
        strategy_weight = self.weights.get(signal.strategy, 1.0)
        
        # Calculate adjusted confidence and score based on learned weights
        adjusted_confidence = max(0.05, min(1.0, signal.confidence * strategy_weight))
        adjusted_score = signal.score * strategy_weight
        
        # Use additional ML features if available
        if signal.metadata:
            # Adjust based on market regime if available in metadata
            volatility_regime = signal.metadata.get('volatility_regime', 'normal')
            if volatility_regime == 'high':
                # Reduce confidence in high volatility
                adjusted_confidence = max(0.05, adjusted_confidence * 0.8)
                adjusted_score = adjusted_score * 0.8
            elif volatility_regime == 'low':
                # Slightly increase confidence in low volatility
                adjusted_confidence = min(1.0, adjusted_confidence * 1.1)
                adjusted_score = adjusted_score * 1.1
                
            # Adjust based on trend alignment
            trend_aligned = signal.metadata.get('trend_aligned', True)
            if not trend_aligned:
                # Reduce confidence for counter-trend signals
                adjusted_confidence = max(0.05, adjusted_confidence * 0.9)
                adjusted_score = adjusted_score * 0.9
        
        # Generate enhanced signal with ML-adjusted values
        enhanced_signal = Signal(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence=adjusted_confidence,
            score=adjusted_score,
            strategy=f"{signal.strategy}_ml_weighted",
            timestamp=datetime.now(),
            metadata=signal.metadata or {}
        )
        
        # Add ML-specific metadata
        enhanced_signal.metadata.update({
            'original_confidence': signal.confidence,
            'original_score': signal.score,
            'strategy_weight': strategy_weight,
            'ml_adjusted_confidence': adjusted_confidence,
            'ml_adjusted_score': adjusted_score,
            'total_signals_processed': self.total_signals,
            'win_rate': self.profitable_signals / self.total_signals if self.total_signals > 0 else 0,
            'cumulative_pnl': self.cumulative_pnl
        })
        
        logger.debug(f"MLWeightEngine {self.name} processed signal: original={signal.signal_type}, "
                    f"strat_weight={strategy_weight:.3f}, "
                    f"new_conf={adjusted_confidence:.3f}")
        
        # Add to history
        self.add_signal_to_history(enhanced_signal)
        
        return enhanced_signal
        
    def get_strategy_weights(self) -> Dict[str, float]:
        """Get the current learned weights for each strategy"""
        return self.weights.copy()
        
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get current performance metrics"""
        return {
            'total_signals': self.total_signals,
            'profitable_signals': self.profitable_signals,
            'win_rate': self.profitable_signals / self.total_signals if self.total_signals > 0 else 0,
            'cumulative_pnl': self.cumulative_pnl,
            'avg_pnl_per_signal': self.cumulative_pnl / self.total_signals if self.total_signals > 0 else 0
        }
        
    def update_model(self, features: List[float], target: float):
        """Update the ML model with new data"""
        # This is a simplified linear model update
        if len(features) != len(self.model_weights):
            # Initialize model weights if needed
            self.model_weights = np.zeros(len(features))
        
        # Convert features to numpy array
        x = np.array(features)
        
        # Calculate prediction
        prediction = np.dot(self.model_weights, x) + self.model_bias
        
        # Calculate error
        error = target - prediction
        
        # Update weights using gradient descent
        self.model_weights += self.learning_rate * error * x
        self.model_bias += self.learning_rate * error
        
    def predict_signal_success(self, signal: Signal) -> float:
        """Predict the probability of signal success"""
        # This is a simplified prediction based on signal features
        # In a real implementation, you'd use a more sophisticated model
        
        # Create features from signal (simplified example)
        features = [
            signal.score,           # Signal strength
            signal.confidence,      # Original confidence
            1.0 if signal.signal_type == SignalType.BUY else -1.0,  # Signal type
            1.0 if signal.signal_type == SignalType.HOLD else 0.0,  # Hold indicator
            0.5  # Placeholder for other features
        ]
        
        # Calculate prediction
        x = np.array(features[:len(self.model_weights)])
        prediction = np.dot(self.model_weights[:len(x)], x) + self.model_bias
        
        # Use sigmoid to convert to probability (0-1)
        success_probability = 1 / (1 + np.exp(-prediction))
        
        return success_probability