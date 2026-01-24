"""
Advanced Fusion Weighting with performance-adaptive, correlation-penalizing, stability-rewarding, and noise-suppressing features.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


@dataclass
class SignalWeight:
    """Container for signal weights and metadata"""
    weight: float
    performance_factor: float
    correlation_penalty: float
    stability_factor: float
    noise_suppression: float
    timestamp: datetime


class AdvancedFusionWeighting:
    """
    Advanced fusion weighting system with:
    - Performance-adaptive weights
    - Correlation penalty mechanism
    - Stability rewards
    - Noise suppression
    """
    
    def __init__(self,
                 performance_decay_factor: float = 0.95,  # How quickly past performance is devalued
                 correlation_penalty_factor: float = 0.5,  # How much to penalize correlation
                 stability_bonus_factor: float = 0.3,      # Bonus for stable signals
                 noise_suppression_threshold: float = 0.1, # Threshold for noise suppression
                 min_weight: float = 0.01,                # Minimum weight to prevent elimination
                 max_weight: float = 0.5):                # Maximum weight to prevent dominance
        
        self.performance_decay_factor = performance_decay_factor
        self.correlation_penalty_factor = correlation_penalty_factor
        self.stability_bonus_factor = stability_bonus_factor
        self.noise_suppression_threshold = noise_suppression_threshold
        self.min_weight = min_weight
        self.max_weight = max_weight
        
        # Track signal performance over time
        self.signal_performance: Dict[str, List[Tuple[float, datetime]]] = {}
        self.signal_correlations: Dict[str, Dict[str, float]] = {}
        self.signal_stability: Dict[str, float] = {}
        self.signal_weights: Dict[str, SignalWeight] = {}
        self.weight_history: Dict[str, List[Tuple[float, datetime]]] = {}

    def update_signal_performance(self, signal_name: str, performance: float, timestamp: Optional[datetime] = None):
        """Update performance record for a signal."""
        if timestamp is None:
            timestamp = datetime.now()
            
        if signal_name not in self.signal_performance:
            self.signal_performance[signal_name] = []
            
        self.signal_performance[signal_name].append((performance, timestamp))
        
        # Keep only recent performance data (last 30 days)
        cutoff = timestamp - timedelta(days=30)
        self.signal_performance[signal_name] = [
            (perf, ts) for perf, ts in self.signal_performance[signal_name] 
            if ts >= cutoff
        ]

    def update_signal_correlation(self, signal1: str, signal2: str, correlation: float):
        """Update correlation between two signals."""
        if signal1 not in self.signal_correlations:
            self.signal_correlations[signal1] = {}
        if signal2 not in self.signal_correlations:
            self.signal_correlations[signal2] = {}
            
        self.signal_correlations[signal1][signal2] = correlation
        self.signal_correlations[signal2][signal1] = correlation

    def calculate_stability_score(self, signal_name: str) -> float:
        """Calculate stability score for a signal based on performance consistency."""
        if signal_name not in self.signal_performance or len(self.signal_performance[signal_name]) < 3:
            return 0.5  # Default medium stability for insufficient data
            
        performances = [perf for perf, _ in self.signal_performance[signal_name]]
        
        # Calculate coefficient of variation (lower is more stable)
        mean_perf = np.mean(performances)
        if mean_perf == 0:
            std_perf = np.std(performances)
            if std_perf == 0:
                return 1.0  # Perfectly stable if no variation
            else:
                # If mean is 0 but there's variation, it's unstable
                return 0.0
        
        std_perf = np.std(performances)
        cv = abs(std_perf / mean_perf)  # Coefficient of variation
        
        # Convert to stability score (lower CV = higher stability)
        # Use exponential decay: more stable signals get higher scores
        stability = np.exp(-cv * 2)  # Adjust multiplier as needed
        return min(1.0, max(0.0, stability))

    def calculate_performance_factor(self, signal_name: str) -> float:
        """Calculate performance factor based on recent performance."""
        if signal_name not in self.signal_performance or not self.signal_performance[signal_name]:
            return 1.0  # Default factor for no data
            
        # Calculate weighted average of recent performance, with more weight on recent data
        total_weighted_performance = 0.0
        total_weights = 0.0
        
        performances = self.signal_performance[signal_name]
        n = len(performances)
        
        for i, (perf, timestamp) in enumerate(performances):
            # Weight based on recency (more recent = higher weight)
            time_weight = self.performance_decay_factor ** (n - i - 1)
            # Also weight by actual performance value
            performance_weight = max(0.1, perf + 1.0)  # Shift to positive range, min 0.1
            
            total_weighted_performance += perf * time_weight * performance_weight
            total_weights += time_weight * performance_weight
        
        if total_weights == 0:
            return 1.0
            
        avg_weighted_performance = total_weighted_performance / total_weights
        
        # Convert to factor (positive performance increases weight, negative decreases)
        # Map performance range to factor range
        factor = 1.0 + avg_weighted_performance * 0.5  # Adjust sensitivity as needed
        return max(0.1, factor)  # Don't let it go too low

    def calculate_correlation_penalty(self, signal_name: str, all_signals: List[str]) -> float:
        """Calculate correlation penalty for a signal based on correlation with others."""
        if not all_signals or len(all_signals) <= 1:
            return 1.0  # No penalty if no other signals
            
        total_correlation = 0.0
        correlation_count = 0
        
        for other_signal in all_signals:
            if other_signal != signal_name and signal_name in self.signal_correlations:
                if other_signal in self.signal_correlations[signal_name]:
                    correlation = abs(self.signal_correlations[signal_name][other_signal])
                    total_correlation += correlation
                    correlation_count += 1
        
        if correlation_count == 0:
            return 1.0  # No correlation data, no penalty
            
        avg_correlation = total_correlation / correlation_count
        
        # Calculate penalty: higher correlation = lower weight
        penalty = avg_correlation * self.correlation_penalty_factor
        penalty_factor = max(0.1, 1.0 - penalty)  # Don't go below 10% of original weight
        
        return penalty_factor

    def calculate_noise_suppression(self, signal_name: str) -> float:
        """Calculate noise suppression factor for a signal."""
        if signal_name not in self.signal_performance or len(self.signal_performance[signal_name]) < 2:
            return 1.0  # No suppression for insufficient data
            
        performances = [perf for perf, _ in self.signal_performance[signal_name]]
        
        # Calculate performance volatility (higher volatility = more noise)
        perf_volatility = np.std(performances) if len(performances) > 1 else 0.0
        
        # If volatility is above threshold, apply suppression
        if perf_volatility > self.noise_suppression_threshold:
            suppression = min(1.0, self.noise_suppression_threshold / perf_volatility)
            return max(0.1, suppression)  # Don't suppress too much
        else:
            return 1.0  # No suppression needed

    def calculate_signal_weight(self, signal_name: str, all_signals: List[str]) -> SignalWeight:
        """Calculate comprehensive weight for a signal."""
        # Calculate individual factors
        performance_factor = self.calculate_performance_factor(signal_name)
        stability_factor = self.calculate_stability_score(signal_name)
        correlation_penalty = self.calculate_correlation_penalty(signal_name, all_signals)
        noise_suppression = self.calculate_noise_suppression(signal_name)
        
        # Combine factors (multiplicative approach)
        raw_weight = (performance_factor * 
                     (1 + stability_factor * self.stability_bonus_factor) * 
                     correlation_penalty * 
                     noise_suppression)
        
        # Apply bounds
        bounded_weight = max(self.min_weight, min(self.max_weight, raw_weight))
        
        # Create signal weight object
        weight_obj = SignalWeight(
            weight=bounded_weight,
            performance_factor=performance_factor,
            correlation_penalty=correlation_penalty,
            stability_factor=stability_factor,
            noise_suppression=noise_suppression,
            timestamp=datetime.now()
        )
        
        # Store for tracking
        self.signal_weights[signal_name] = weight_obj
        
        # Add to history
        if signal_name not in self.weight_history:
            self.weight_history[signal_name] = []
        self.weight_history[signal_name].append((bounded_weight, datetime.now()))
        
        return weight_obj

    def calculate_normalized_weights(self, signal_names: List[str]) -> Dict[str, float]:
        """Calculate and normalize weights for all signals."""
        weights = {}
        
        # Calculate individual weights
        for signal_name in signal_names:
            weight_obj = self.calculate_signal_weight(signal_name, signal_names)
            weights[signal_name] = weight_obj.weight
        
        # Normalize so they sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            normalized_weights = {name: weight / total_weight for name, weight in weights.items()}
        else:
            # If all weights are zero, assign equal weights
            equal_weight = 1.0 / len(signal_names) if signal_names else 0
            normalized_weights = {name: equal_weight for name in signal_names}
        
        return normalized_weights

    def update_weight_history(self, signal_name: str, weight: float):
        """Update weight history for tracking."""
        if signal_name not in self.weight_history:
            self.weight_history[signal_name] = []
        self.weight_history[signal_name].append((weight, datetime.now()))
        
        # Keep only recent history (last 30 days)
        cutoff = datetime.now() - timedelta(days=30)
        self.weight_history[signal_name] = [
            (w, ts) for w, ts in self.weight_history[signal_name]
            if ts >= cutoff
        ]

    def get_signal_analysis(self, signal_name: str) -> Dict[str, Any]:
        """Get detailed analysis of a signal's weighting factors."""
        if signal_name not in self.signal_weights:
            return {}
            
        weight_obj = self.signal_weights[signal_name]
        
        return {
            'current_weight': weight_obj.weight,
            'performance_factor': weight_obj.performance_factor,
            'correlation_penalty': weight_obj.correlation_penalty,
            'stability_factor': weight_obj.stability_factor,
            'noise_suppression': weight_obj.noise_suppression,
            'last_updated': weight_obj.timestamp,
            'performance_history': self.signal_performance.get(signal_name, []),
            'weight_trend': self._calculate_weight_trend(signal_name)
        }

    def _calculate_weight_trend(self, signal_name: str) -> str:
        """Calculate trend of weight changes."""
        if signal_name not in self.weight_history or len(self.weight_history[signal_name]) < 2:
            return "neutral"
            
        weights = [w for w, _ in self.weight_history[signal_name][-5:]]  # Last 5 weights
        
        if len(weights) < 2:
            return "neutral"
            
        # Calculate trend
        if len(weights) == 2:
            trend = weights[1] - weights[0]
        else:
            # Use linear regression for trend
            x = np.arange(len(weights))
            slope, _, _, _, _ = stats.linregress(x, weights)
            trend = slope
            
        if trend > 0.01:
            return "increasing"
        elif trend < -0.01:
            return "decreasing"
        else:
            return "neutral"

    def get_top_signals(self, signal_names: List[str], n: int = 5) -> List[Tuple[str, float]]:
        """Get top N signals by weight."""
        weights = self.calculate_normalized_weights(signal_names)
        sorted_signals = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        return sorted_signals[:n]

    def get_bottom_signals(self, signal_names: List[str], n: int = 5) -> List[Tuple[str, float]]:
        """Get bottom N signals by weight."""
        weights = self.calculate_normalized_weights(signal_names)
        sorted_signals = sorted(weights.items(), key=lambda x: x[1])
        return sorted_signals[:n]

    def reset_signal_weights(self):
        """Reset all signal weights (for retraining scenarios)."""
        self.signal_performance = {}
        self.signal_correlations = {}
        self.signal_stability = {}
        self.signal_weights = {}
        self.weight_history = {}


class AdaptiveFusionService:
    """Service to manage adaptive fusion weighting."""
    
    def __init__(self):
        self.weighting_system = AdvancedFusionWeighting()
        self.fusion_history: List[Dict[str, Any]] = []
    
    def fuse_signals_with_weights(self, 
                                 signals: List[Dict[str, Any]], 
                                 values: List[float]) -> float:
        """
        Fuse signals using adaptive weights.
        
        Args:
            signals: List of signal dictionaries with 'name' field
            values: Corresponding signal values to be fused
        
        Returns:
            Fused signal value
        """
        if not signals or not values or len(signals) != len(values):
            return 0.0 if values else 0.0
        
        signal_names = [sig.get('name', f'signal_{i}') for i, sig in enumerate(signals)]
        
        # Calculate adaptive weights
        weights = self.weighting_system.calculate_normalized_weights(signal_names)
        
        # Apply weights to values
        weighted_sum = sum(values[i] * weights[signal_names[i]] for i in range(len(values)))
        total_weight = sum(weights.values())
        
        fused_value = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Record fusion for analysis
        fusion_record = {
            'timestamp': datetime.now(),
            'signals': signal_names,
            'input_values': values,
            'weights': weights,
            'fused_value': fused_value
        }
        self.fusion_history.append(fusion_record)
        
        return fused_value
    
    def update_signal_feedback(self, 
                             signal_name: str, 
                             performance: float, 
                             correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None):
        """
        Update signal weights based on feedback.
        """
        # Update performance
        self.weighting_system.update_signal_performance(signal_name, performance)
        
        # Update correlations if provided
        if correlation_matrix:
            for sig1, corrs in correlation_matrix.items():
                for sig2, corr in corrs.items():
                    self.weighting_system.update_signal_correlation(sig1, sig2, corr)
    
    def get_fusion_analysis(self) -> Dict[str, Any]:
        """Get analysis of fusion performance."""
        if not self.fusion_history:
            return {}
        
        recent_fusions = self.fusion_history[-20:]  # Last 20 fusions
        
        # Calculate various metrics
        fused_values = [f['fused_value'] for f in recent_fusions]
        weights_over_time = {}
        
        for fusion in recent_fusions:
            for signal, weight in fusion['weights'].items():
                if signal not in weights_over_time:
                    weights_over_time[signal] = []
                weights_over_time[signal].append(weight)
        
        # Calculate average weights
        avg_weights = {sig: np.mean(weights) for sig, weights in weights_over_time.items()}
        
        return {
            'total_fusions': len(self.fusion_history),
            'recent_fusions_count': len(recent_fusions),
            'avg_fused_value': np.mean(fused_values) if fused_values else 0,
            'std_fused_value': np.std(fused_values) if fused_values else 0,
            'avg_weights': avg_weights,
            'weight_stability': {sig: np.std(weights) for sig, weights in weights_over_time.items()}
        }


# Global instance
adaptive_fusion_service = AdaptiveFusionService()