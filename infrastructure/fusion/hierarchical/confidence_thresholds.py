"""
Confidence Threshold System for Hierarchical Multi-Watcher Architecture
Implements the required confidence thresholds for each watcher type.
"""
from typing import Dict, Optional
from decimal import Decimal
from domain.value_objects import Percentage
from .watcher_classifier import WatcherClassifier, WatcherRole


class ConfidenceThresholds:
    """Manages confidence thresholds for different watcher types"""
    
    # Define confidence thresholds as specified in the task requirements
    CONFIDENCE_THRESHOLDS = {
        # Regime
        "market_pulse": 0.60,
        "volatility": 0.55,
        "funding_rate": 0.60,
        "cmc_screener": 0.65,

        # Discovery
        "anomaly_ml": 0.70,

        # Direction
        "trend_mtf": 0.55,
        "liquidity": 0.65,
        "historical_candle": 0.60,

        # Execution
        "orderflow_ws": 0.50,
        "tick_watcher": 0.45,
    }
    
    @classmethod
    def get_threshold(cls, watcher_name: str) -> float:
        """Get the confidence threshold for a specific watcher"""
        return cls.CONFIDENCE_THRESHOLDS.get(watcher_name, 0.50)  # Default threshold
    
    @classmethod
    def get_threshold_by_role(cls, role: WatcherRole) -> float:
        """Get a representative threshold for a role (using the lowest for that role)"""
        role_watchers = {
            WatcherRole.REGIME: ['market_pulse', 'volatility', 'funding_rate', 'cmc_screener'],
            WatcherRole.DISCOVERY: ['anomaly_ml'],
            WatcherRole.DIRECTION: ['trend_mtf', 'liquidity', 'historical_candle'],
            WatcherRole.EXECUTION: ['orderflow_ws', 'tick_watcher']
        }
        
        watchers_for_role = role_watchers.get(role, [])
        if not watchers_for_role:
            return 0.50  # Default
        
        # Return the highest threshold for the role (most restrictive)
        thresholds = [cls.CONFIDENCE_THRESHOLDS.get(w, 0.50) for w in watchers_for_role]
        return max(thresholds) if thresholds else 0.50
    
    @classmethod
    def is_confident_enough(cls, watcher_name: str, confidence: Percentage) -> bool:
        """Check if a confidence level meets the threshold for a watcher"""
        threshold = cls.get_threshold(watcher_name)
        return float(confidence.value) >= threshold
    
    @classmethod
    def get_all_thresholds(cls) -> Dict[str, float]:
        """Get all confidence thresholds"""
        return cls.CONFIDENCE_THRESHOLDS.copy()


class ConfidenceValidator:
    """Validates observations against confidence thresholds"""
    
    @staticmethod
    def validate_observation(observation, watcher_name: str) -> Dict[str, any]:
        """Validate an observation against confidence thresholds"""
        threshold = ConfidenceThresholds.get_threshold(watcher_name)
        current_confidence = float(observation.confidence.value)
        meets_threshold = current_confidence >= threshold
        
        return {
            'watcher_name': watcher_name,
            'confidence': current_confidence,
            'threshold': threshold,
            'meets_threshold': meets_threshold,
            'action': 'ACCEPT' if meets_threshold else 'DISCARD',
            'message': f"Confidence {current_confidence:.2%} {'meets' if meets_threshold else 'does not meet'} threshold {threshold:.2%}"
        }
    
    @staticmethod
    def filter_confident_observations(observations_with_watchers):
        """Filter out observations that don't meet confidence thresholds"""
        confident_observations = []
        discarded_observations = []
        
        for obs_data in observations_with_watchers:
            observation = obs_data['observation']
            watcher_name = obs_data['watcher_name']
            
            is_confident = ConfidenceThresholds.is_confident_enough(watcher_name, observation.confidence)
            
            if is_confident:
                confident_observations.append(obs_data)
            else:
                discarded_observations.append({
                    **obs_data,
                    'reason': 'confidence_below_threshold',
                    'threshold': ConfidenceThresholds.get_threshold(watcher_name)
                })
        
        return confident_observations, discarded_observations


class RegimeConfidenceManager:
    """Special manager for regime-level confidence requirements"""
    
    @staticmethod
    def get_regime_state_from_observations(observations_with_watchers):
        """Determine regime state based on regime watcher observations"""
        regime_observations = []
        
        for obs_data in observations_with_watchers:
            watcher_name = obs_data['watcher_name']
            if WatcherClassifier.is_regime_watcher(watcher_name):
                validation = ConfidenceValidator.validate_observation(
                    obs_data['observation'], watcher_name
                )
                if validation['meets_threshold']:
                    regime_observations.append({
                        **obs_data,
                        'validation': validation
                    })
        
        if not regime_observations:
            return 'NEUTRAL', 0.5  # Default regime if no valid regime observations
        
        # Aggregate regime observations to determine overall regime state
        return RegimeConfidenceManager._aggregate_regime_state(regime_observations)
    
    @staticmethod
    def _aggregate_regime_state(regime_observations):
        """Aggregate multiple regime observations into a single regime state"""
        # Calculate weighted average of regime signals
        total_weight = 0.0
        weighted_value = 0.0
        
        for obs_data in regime_observations:
            observation = obs_data['observation']
            confidence = float(observation.confidence.value)
            # Map observation types to numerical values
            value = RegimeConfidenceManager._observation_to_regime_value(observation.observation_type)
            
            weighted_value += value * confidence
            total_weight += confidence
        
        if total_weight == 0:
            return 'NEUTRAL', 0.5
        
        avg_value = weighted_value / total_weight
        
        # Map the average value to regime states
        if avg_value > 0.3:
            regime = 'RISK_ON' if avg_value > 0.1 else 'WEAK_RISK_ON'
        elif avg_value > -0.1:
            regime = 'NEUTRAL'
        elif avg_value > -0.3:
            regime = 'RISK_OFF'
        else:
            regime = 'OVERHEATED'
        
        return regime, abs(avg_value)
    
    @staticmethod
    def _observation_to_regime_value(obs_type: str) -> float:
        """Convert observation type to a numerical regime value"""
        # Positive indicators
        if any(indicator in obs_type.lower() for indicator in ['positive', 'bullish', 'risk_on', 'market_pulse_positive']):
            return 0.8
        elif any(indicator in obs_type.lower() for indicator in ['neutral', 'stable', 'balanced']):
            return 0.0
        elif any(indicator in obs_type.lower() for indicator in ['negative', 'bearish', 'risk_off', 'volatile', 'overheated']):
            return -0.8
        else:
            return 0.0  # Default neutral