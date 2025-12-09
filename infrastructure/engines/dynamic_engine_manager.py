"""
Dynamic engine weight adjustment system for the enterprise hedge fund trading system.
Implements regime detection and ML-based engine selection based on market conditions.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from enum import Enum
from shared.logger import logger
from shared.metrics import metrics_collector
from shared.signal_correlation_analyzer import signal_correlation_analyzer
from domain.entities.engine_entities import EngineResult
from domain.entities.trading_entities import Signal


class MarketRegime(Enum):
    """Market regime classifications"""
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    CHOPPY = "choppy"
    BREAKOUT = "breakout"
    NORMAL = "normal"


class EngineWeightManager:
    """Manages dynamic adjustment of engine weights based on market conditions"""
    
    def __init__(self):
        self.engine_weights: Dict[str, float] = {}  # engine_name -> weight
        self.engine_performance_history: Dict[str, List[Dict[str, Any]]] = {}  # engine_name -> performance history
        self.current_regime = MarketRegime.NORMAL
        self.regime_weights: Dict[MarketRegime, Dict[str, float]] = self._initialize_regime_weights()
        
    def _initialize_regime_weights(self) -> Dict[MarketRegime, Dict[str, float]]:
        """Initialize default weights for different market regimes"""
        return {
            MarketRegime.TRENDING: {
                'trend': 0.4,
                'regime': 0.3,
                'volatility': 0.2,
                'order_flow': 0.1
            },
            MarketRegime.MEAN_REVERTING: {
                'volatility': 0.4,
                'order_flow': 0.3,
                'regime': 0.2,
                'trend': 0.1
            },
            MarketRegime.HIGH_VOLATILITY: {
                'volatility': 0.4,
                'order_flow': 0.3,
                'regime': 0.2,
                'liquidity': 0.1
            },
            MarketRegime.LOW_VOLATILITY: {
                'trend': 0.3,
                'regime': 0.3,
                'order_flow': 0.25,
                'volatility': 0.15
            },
            MarketRegime.CHOPPY: {
                'regime': 0.4,
                'volatility': 0.3,
                'order_flow': 0.2,
                'trend': 0.1
            },
            MarketRegime.BREAKOUT: {
                'order_flow': 0.4,
                'volatility': 0.3,
                'trend': 0.2,
                'liquidity': 0.1
            },
            MarketRegime.NORMAL: {
                'trend': 0.25,
                'volatility': 0.25,
                'order_flow': 0.25,
                'regime': 0.25
            }
        }
    
    def detect_market_regime(self, market_data: Dict[str, Any]) -> MarketRegime:
        """Detect current market regime based on market data"""
        # Extract key indicators from market data
        volatility = market_data.get('volatility', 0.02)
        trend_strength = abs(market_data.get('trend_strength', 0))
        volume_trend = market_data.get('volume_trend', 0)
        price_range = market_data.get('price_range', 0.01)
        atr = market_data.get('atr', 0.01)
        
        # Regime detection logic
        if volatility > 0.035:  # High volatility condition
            return MarketRegime.HIGH_VOLATILITY
        elif volatility < 0.008:  # Low volatility condition
            return MarketRegime.LOW_VOLATILITY
        elif trend_strength > 0.03 and price_range > 0.02:  # Strong trend with good range
            return MarketRegime.TRENDING
        elif trend_strength < 0.01 and price_range < 0.01:  # Weak trend with low range
            return MarketRegime.CHOPPY
        elif volume_trend > 0.5 and price_range > 0.015:  # High volume with movement
            return MarketRegime.BREAKOUT
        else:
            # Check if mean reverting based on z-score or other indicators
            z_score = market_data.get('z_score', 0)
            if abs(z_score) > 2:  # Extreme price level
                return MarketRegime.MEAN_REVERTING
            else:
                return MarketRegime.NORMAL
    
    def update_engine_weights(self, market_data: Dict[str, Any]):
        """Update engine weights based on current market regime"""
        self.current_regime = self.detect_market_regime(market_data)
        
        # Get weights for current regime
        regime_weights = self.regime_weights.get(self.current_regime, self.regime_weights[MarketRegime.NORMAL])
        self.engine_weights = regime_weights.copy()
        
        # Adjust weights based on recent performance
        self._adjust_weights_by_performance()
        
        # Normalize weights to sum to 1.0
        total_weight = sum(self.engine_weights.values())
        if total_weight > 0:
            self.engine_weights = {k: v/total_weight for k, v in self.engine_weights.items()}
        
        logger.info(f"Updated engine weights for regime: {self.current_regime.value}",
                   weights=self.engine_weights,
                   regime=self.current_regime.value)
    
    def _adjust_weights_by_performance(self):
        """Adjust weights based on recent engine performance"""
        # For each engine, check its recent performance
        for engine_name in self.engine_weights.keys():
            performance_data = self.engine_performance_history.get(engine_name, [])
            
            if len(performance_data) >= 5:  # Need at least 5 data points
                recent_performance = performance_data[-5:]  # Last 5 performances
                avg_accuracy = np.mean([p.get('accuracy', 0) for p in recent_performance])
                avg_profit = np.mean([p.get('profit_factor', 1.0) for p in recent_performance])
                
                # Calculate performance score
                performance_score = (avg_accuracy * 0.6) + (avg_profit * 0.4)
                
                # Adjust weight based on performance (between 0.5 and 1.5 of original weight)
                original_weight = self.regime_weights[self.current_regime][engine_name]
                if performance_score > 1.1:  # Good performance
                    adjustment = min(1.5, 1.0 + (performance_score - 1.0))
                elif performance_score < 0.9:  # Poor performance
                    adjustment = max(0.5, performance_score)
                else:  # Average performance
                    adjustment = 1.0
                
                # Apply adjustment
                self.engine_weights[engine_name] = original_weight * adjustment
    
    def get_engine_weights(self) -> Dict[str, float]:
        """Get current engine weights"""
        return self.engine_weights.copy()
    
    def record_engine_performance(self, engine_name: str, accuracy: float, 
                                 profit_factor: float, other_metrics: Dict[str, Any] = None):
        """Record engine performance for future weight adjustments"""
        if engine_name not in self.engine_performance_history:
            self.engine_performance_history[engine_name] = []
        
        performance_record = {
            'timestamp': datetime.now(),
            'accuracy': accuracy,
            'profit_factor': profit_factor,
            'other_metrics': other_metrics or {}
        }
        
        self.engine_performance_history[engine_name].append(performance_record)
        
        # Keep only recent performance data (last 20 records)
        if len(self.engine_performance_history[engine_name]) > 20:
            self.engine_performance_history[engine_name] = self.engine_performance_history[engine_name][-10:]
    
    def apply_weights_to_signals(self, engine_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply current weights to engine outputs for weighted fusion"""
        weighted_outputs = {}
        
        for engine_name, output in engine_outputs.items():
            weight = self.engine_weights.get(engine_name, 1.0/len(engine_outputs) if engine_outputs else 1.0)
            
            # Weight the output
            if isinstance(output, (int, float)):
                weighted_outputs[engine_name] = output * weight
            elif isinstance(output, dict) and 'score' in output:
                weighted_outputs[engine_name] = {
                    **output,
                    'weighted_score': output['score'] * weight,
                    'weight_used': weight
                }
            else:
                # For complex objects, just store with weight
                weighted_outputs[engine_name] = {
                    'output': output,
                    'weight': weight
                }
        
        return weighted_outputs


class MLBasedEngineSelector:
    """Uses machine learning to select the best engine based on market regime"""
    
    def __init__(self):
        self.performance_history: List[Dict[str, Any]] = []
        self.feature_importance: Dict[str, float] = {}
        self.most_accurate_engine_history: List[str] = []
    
    def record_selection_outcome(self, selected_engine: str, actual_outcome: bool, 
                                market_features: Dict[str, float]):
        """Record the outcome of engine selection with market features"""
        record = {
            'timestamp': datetime.now(),
            'selected_engine': selected_engine,
            'was_correct': actual_outcome,
            'features': market_features,
            'regime': self._classify_regime(market_features)
        }
        
        self.performance_history.append(record)
        
        # Keep only recent history
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-50:]
    
    def _classify_regime(self, features: Dict[str, float]) -> str:
        """Classify market regime based on features"""
        volatility = features.get('volatility', 0.02)
        trend_strength = abs(features.get('trend_strength', 0))
        volume_ratio = features.get('volume_ratio', 1.0)
        
        if volatility > 0.035:
            return 'high_volatility'
        elif trend_strength > 0.03:
            return 'trending'
        elif volume_ratio > 2.0:
            return 'high_volume'
        else:
            return 'normal'
    
    def select_best_engine(self, available_engines: List[str], 
                          market_features: Dict[str, float]) -> str:
        """Select the best engine based on historical performance and current features"""
        if not available_engines:
            return "default_engine"
        
        # If we don't have history yet, use basic rules
        if len(self.performance_history) < 10:
            return self._fallback_engine_selection(available_engines, market_features)
        
        # Group performance by regime and engine
        regime_engine_performance = {}
        for record in self.performance_history[-20:]:  # Look at recent performance
            regime = record['regime']
            engine = record['selected_engine']
            correct = record['was_correct']
            
            if regime not in regime_engine_performance:
                regime_engine_performance[regime] = {}
            if engine not in regime_engine_performance[regime]:
                regime_engine_performance[regime][engine] = []
            
            regime_engine_performance[regime][engine].append(correct)
        
        # Get current regime
        current_regime = self._classify_regime(market_features)
        
        # Find best engine for current regime
        if current_regime in regime_engine_performance:
            best_engine = None
            best_accuracy = -1
            
            for engine in available_engines:
                if engine in regime_engine_performance[current_regime]:
                    accuracy = np.mean(regime_engine_performance[current_regime][engine])
                    if accuracy > best_accuracy:
                        best_accuracy = accuracy
                        best_engine = engine
            
            if best_engine:
                return best_engine
        
        # If no data for current regime, use overall best for available engines
        all_performance = {}
        for record in self.performance_history[-30:]:
            engine = record['selected_engine']
            if engine in available_engines:
                if engine not in all_performance:
                    all_performance[engine] = []
                all_performance[engine].append(record['was_correct'])
        
        if all_performance:
            best_engine = None
            best_accuracy = -1
            for engine, results in all_performance.items():
                accuracy = np.mean(results)
                if accuracy > best_accuracy:
                    best_accuracy = accuracy
                    best_engine = engine
            
            if best_engine:
                return best_engine
        
        # Fallback
        return self._fallback_engine_selection(available_engines, market_features)
    
    def _fallback_engine_selection(self, available_engines: List[str], 
                                  market_features: Dict[str, float]) -> str:
        """Fallback engine selection based on simple rules"""
        volatility = market_features.get('volatility', 0.02)
        trend_strength = abs(market_features.get('trend_strength', 0))
        
        if volatility > 0.03 and 'volatility_engine' in available_engines:
            return 'volatility_engine'
        elif trend_strength > 0.02 and 'trend_engine' in available_engines:
            return 'trend_engine'
        elif 'regime_engine' in available_engines:
            return 'regime_engine'
        else:
            return available_engines[0]  # Default to first available engine


class EnsembleEngineFusion:
    """Combines engine outputs using ensemble methods"""
    
    def __init__(self):
        self.weight_manager = EngineWeightManager()
        self.ml_selector = MLBasedEngineSelector()
    
    def fuse_engine_outputs(self, engine_outputs: Dict[str, Any], 
                           market_features: Dict[str, float],
                           fusion_method: str = "weighted_average") -> Dict[str, Any]:
        """Fuse outputs from multiple engines using ensemble methods"""
        if not engine_outputs:
            return {}
        
        # Update weights based on market conditions
        self.weight_manager.update_engine_weights(market_features)
        
        # Apply weights to outputs
        weighted_outputs = self.weight_manager.apply_weights_to_signals(engine_outputs)
        
        # Apply fusion method
        if fusion_method == "weighted_average":
            return self._weighted_average_fusion(weighted_outputs)
        elif fusion_method == "ml_based_selection":
            return self._ml_based_fusion(weighted_outputs, engine_outputs, market_features)
        elif fusion_method == "confidence_weighted":
            return self._confidence_weighted_fusion(weighted_outputs)
        else:
            return self._simple_majority_fusion(weighted_outputs)
    
    def _weighted_average_fusion(self, weighted_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Simple weighted average fusion"""
        total_weighted_score = 0
        total_weight = 0
        individual_scores = {}
        
        for engine, output in weighted_outputs.items():
            if isinstance(output, dict) and 'weighted_score' in output:
                score = output['weighted_score'] / output.get('weight_used', 1.0)  # Unweight to get original
                weight = output.get('weight_used', 1.0)
            elif isinstance(output, (int, float)):
                score = output
                weight = self.weight_manager.engine_weights.get(engine, 1.0/len(weighted_outputs))
            else:
                continue
            
            total_weighted_score += score * weight
            total_weight += weight
            individual_scores[engine] = score
        
        if total_weight > 0:
            final_score = total_weighted_score / total_weight
        else:
            final_score = 0.5  # Default score
        
        return {
            'fused_score': final_score,
            'total_weight': total_weight,
            'individual_scores': individual_scores,
            'weights_used': self.weight_manager.get_engine_weights()
        }
    
    def _ml_based_fusion(self, weighted_outputs: Dict[str, Any], 
                        original_outputs: Dict[str, Any], 
                        market_features: Dict[str, float]) -> Dict[str, Any]:
        """Fusion based on ML engine selection"""
        available_engines = list(original_outputs.keys())
        selected_engine = self.ml_selector.select_best_engine(available_engines, market_features)
        
        # Use the selected engine's output
        selected_output = original_outputs.get(selected_engine, {})
        
        return {
            'selected_engine': selected_engine,
            'engine_output': selected_output,
            'weights': self.weight_manager.get_engine_weights(),
            'regime': self.weight_manager.current_regime.value
        }
    
    def _confidence_weighted_fusion(self, weighted_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Fusion based on confidence scores"""
        total_score = 0
        total_confidence = 0
        engine_confidences = {}
        
        for engine, output in weighted_outputs.items():
            # Extract confidence from output
            if isinstance(output, dict):
                confidence = output.get('confidence', output.get('score', 0.5))
            else:
                confidence = 0.5  # Default confidence
            
            score = output.get('score', 0.5) if isinstance(output, dict) else output
            weighted_score = score * abs(confidence)  # Use absolute confidence
            
            total_score += weighted_score
            total_confidence += abs(confidence)
            engine_confidences[engine] = confidence
        
        if total_confidence > 0:
            final_score = total_score / total_confidence
        else:
            final_score = 0.5
        
        return {
            'fused_score': final_score,
            'total_confidence': total_confidence,
            'engine_confidences': engine_confidences
        }
    
    def _simple_majority_fusion(self, weighted_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Simple majority vote fusion"""
        positive_votes = 0
        negative_votes = 0
        engine_votes = {}
        
        for engine, output in weighted_outputs.items():
            if isinstance(output, dict):
                score = output.get('score', 0.5)
            else:
                score = output
            
            weight = self.weight_manager.engine_weights.get(engine, 1.0/len(weighted_outputs))
            scaled_score = score * weight
            
            if scaled_score > 0.5:
                positive_votes += 1 * weight
                engine_votes[engine] = 'positive'
            else:
                negative_votes += 1 * weight
                engine_votes[engine] = 'negative'
        
        final_decision = 'positive' if positive_votes > negative_votes else 'negative'
        confidence = max(positive_votes, negative_votes) / (positive_votes + negative_votes) if (positive_votes + negative_votes) > 0 else 0.5
        
        return {
            'decision': final_decision,
            'confidence': confidence,
            'engine_votes': engine_votes,
            'positive_weight': positive_votes,
            'negative_weight': negative_votes
        }


# Global instances
engine_weight_manager = EngineWeightManager()
ml_engine_selector = MLBasedEngineSelector()
ensemble_fusion = EnsembleEngineFusion()