"""
Randomness Exposure Firewall for Enterprise Hedge Fund Trading System
Prevents capital exposure to random market fluctuations and statistical illusions
"""
import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


@dataclass
class RandomnessExposureAlert:
    """Represents a randomness exposure alert"""
    component: str
    risk_type: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    metric_value: float
    threshold: float
    timestamp: datetime
    mitigation_action: str


class RandomnessExposureFirewall:
    """
    Prevents capital exposure to randomness by implementing statistical controls
    across all system components
    """
    
    def __init__(self):
        # Risk thresholds
        self.correlation_threshold = 0.7  # Maximum allowed correlation between signals
        self.significance_level = 0.05  # Statistical significance threshold
        self.min_sample_size = 30  # Minimum sample size for statistical validity
        self.overfitting_threshold = 0.1  # Maximum acceptable overfitting probability
        self.noise_ratio_threshold = 0.3  # Maximum acceptable noise ratio
        
        # Tracking for adaptive thresholds
        self.component_performance_history = {}
        self.adaptive_buffer = 0.05  # Buffer for adaptive thresholds
    
    def check_watcher_randomness(self, 
                                watcher_data: Dict[str, Any], 
                                historical_data: List[Dict[str, Any]]) -> List[RandomnessExposureAlert]:
        """
        Check for randomness exposure in watcher component
        """
        alerts = []
        
        # Check for statistical significance of current observation
        if 'confidence' in watcher_data:
            confidence = watcher_data['confidence']
            
            # Check if confidence is based on insufficient historical data
            if len(historical_data) < self.min_sample_size:
                alerts.append(RandomnessExposureAlert(
                    component="WATCHER",
                    risk_type="INSUFFICIENT_HISTORICAL_DATA",
                    severity="HIGH",
                    metric_value=len(historical_data),
                    threshold=self.min_sample_size,
                    timestamp=datetime.utcnow(),
                    mitigation_action="BLOCK_OBSERVATION"
                ))
            
            # Check for potential overfitting if confidence is unusually high
            if confidence > 0.95 and len(historical_data) < 50:
                alerts.append(RandomnessExposureAlert(
                    component="WATCHER",
                    risk_type="POTENTIAL_OVERFITTING",
                    severity="MEDIUM",
                    metric_value=confidence,
                    threshold=0.90,
                    timestamp=datetime.utcnow(),
                    mitigation_action="REDUCE_CONFIDENCE"
                ))
        
        # Check for signal consistency over time
        if len(historical_data) >= self.min_sample_size:
            recent_changes = []
            for i in range(1, min(10, len(historical_data))):
                if 'value' in historical_data[-i] and 'value' in historical_data[-i-1]:
                    change = abs(historical_data[-i]['value'] - historical_data[-i-1]['value'])
                    recent_changes.append(change)
            
            if recent_changes:
                avg_change = np.mean(recent_changes)
                std_change = np.std(recent_changes)
                
                # If changes are too volatile, signal may be capturing noise
                if std_change > avg_change * 2:
                    alerts.append(RandomnessExposureAlert(
                        component="WATCHER",
                        risk_type="HIGH_VOLATILITY_NOISE",
                        severity="MEDIUM",
                        metric_value=std_change / avg_change if avg_change > 0 else float('inf'),
                        threshold=2.0,
                        timestamp=datetime.utcnow(),
                        mitigation_action="INCREASE_CAUTION"
                    ))
        
        return alerts
    
    def check_engine_randomness(self, 
                              engine_data: Dict[str, Any], 
                              historical_data: List[Dict[str, Any]]) -> List[RandomnessExposureAlert]:
        """
        Check for randomness exposure in engine component
        """
        alerts = []
        
        # Check for correlation between consecutive interpretations
        if len(historical_data) >= 2:
            current_interp = engine_data.get('interpreted_signal')
            prev_interp = historical_data[-1].get('interpreted_signal')
            
            # If interpretations are flipping frequently, may be capturing noise
            if current_interp and prev_interp and current_interp != prev_interp:
                flip_count = 0
                for i in range(1, min(5, len(historical_data))):
                    if (historical_data[-i].get('interpreted_signal') != 
                        historical_data[-i-1].get('interpreted_signal')):
                        flip_count += 1
                
                if flip_count >= 3:  # 3 out of 5 flips
                    alerts.append(RandomnessExposureAlert(
                        component="ENGINE",
                        risk_type="HIGH_FLIP_RATE",
                        severity="MEDIUM",
                        metric_value=flip_count/5.0,
                        threshold=0.5,
                        timestamp=datetime.utcnow(),
                        mitigation_action="REDUCE_SIGNAL_STRENGTH"
                    ))
        
        # Check for confidence consistency
        if 'confidence' in engine_data and 'strength' in engine_data:
            confidence = engine_data['confidence']
            strength = engine_data['strength']
            
            # If confidence is high but strength is low, may be overconfident
            if confidence > 0.7 and strength < 0.3:
                alerts.append(RandomnessExposureAlert(
                    component="ENGINE",
                    risk_type="CONFIDENCE_STRENGTH_MISMATCH",
                    severity="HIGH",
                    metric_value=confidence - strength,
                    threshold=0.4,
                    timestamp=datetime.utcnow(),
                    mitigation_action="ADJUST_CONFIDENCE_DOWNWARD"
                ))
        
        return alerts
    
    def check_fusion_randomness(self, 
                              fusion_data: Dict[str, Any], 
                              historical_data: List[Dict[str, Any]]) -> List[RandomnessExposureAlert]:
        """
        Check for randomness exposure in fusion component
        """
        alerts = []
        
        # Check for correlation between contributing signals
        if 'contributors' in fusion_data:
            contributor_weights = list(fusion_data['contributors'].values())
            
            # If one contributor dominates, fusion may not be adding value
            if len(contributor_weights) > 1:
                max_weight = max(contributor_weights)
                if max_weight > 0.8:  # One contributor dominates
                    alerts.append(RandomnessExposureAlert(
                        component="FUSION",
                        risk_type="CONTRIBUTOR_DOMINANCE",
                        severity="MEDIUM",
                        metric_value=max_weight,
                        threshold=0.8,
                        timestamp=datetime.utcnow(),
                        mitigation_action="VALIDATE_SINGLE_SOURCE"
                    ))
        
        # Check for fusion stability over time
        if len(historical_data) >= 3:
            recent_directions = []
            for item in historical_data[-3:]:
                if 'direction' in item:
                    recent_directions.append(item['direction'])
            
            if len(recent_directions) >= 2:
                # Check for excessive direction changes
                direction_changes = sum(1 for i in range(1, len(recent_directions)) 
                                      if np.sign(recent_directions[i]) != np.sign(recent_directions[i-1]))
                
                if direction_changes >= 2:  # 2 out of 3 changes direction
                    alerts.append(RandomnessExposureAlert(
                        component="FUSION",
                        risk_type="INSTABLE_DIRECTIONS",
                        severity="HIGH",
                        metric_value=direction_changes/len(recent_directions),
                        threshold=0.6,
                        timestamp=datetime.utcnow(),
                        mitigation_action="INCREASE_FUSION_CAUTION"
                    ))
        
        # Check for correlation between inputs (avoid amplifying correlated noise)
        if 'contributors' in fusion_data and len(fusion_data['contributors']) > 1:
            weights = list(fusion_data['contributors'].values())
            if len(weights) > 1:
                avg_weight = np.mean(weights)
                weight_std = np.std(weights)
                
                # If weights are too similar, signals might be correlated
                if weight_std < avg_weight * 0.1 and len(weights) > 2:
                    alerts.append(RandomnessExposureAlert(
                        component="FUSION",
                        risk_type="EQUAL_WEIGHT_CORRELATION_RISK",
                        severity="MEDIUM",
                        metric_value=weight_std / avg_weight if avg_weight > 0 else float('inf'),
                        threshold=0.1,
                        timestamp=datetime.utcnow(),
                        mitigation_action="CHECK_INPUT_CORRELATIONS"
                    ))
        
        return alerts
    
    def check_strategy_randomness(self, 
                                strategy_data: Dict[str, Any], 
                                historical_data: List[Dict[str, Any]]) -> List[RandomnessExposureAlert]:
        """
        Check for randomness exposure in strategy component
        """
        alerts = []
        
        # Check for strategy overfitting indicators
        if 'decision_reasons' in strategy_data:
            decision_reasons = strategy_data['decision_reasons']
            
            # Check if strategy selection is based on too many coincidental factors
            if 'fused_signal_confidence' in decision_reasons:
                fused_conf = decision_reasons['fused_signal_confidence']
                
                # If fused confidence is low but strategy is selected anyway, may be overfitting
                if fused_conf < 0.5 and strategy_data.get('confidence', 0) > 0.7:
                    alerts.append(RandomnessExposureAlert(
                        component="STRATEGY",
                        risk_type="LOW_FUSED_HIGH_STRATEGY_CONFIDENCE",
                        severity="HIGH",
                        metric_value=strategy_data.get('confidence', 0) - fused_conf,
                        threshold=0.2,
                        timestamp=datetime.utcnow(),
                        mitigation_action="REJECT_STRATEGY_DECISION"
                    ))
        
        # Check for strategy consistency
        if len(historical_data) >= 5:
            recent_strategies = [item.get('strategy') for item in historical_data[-5:] if 'strategy' in item]
            
            if len(set(recent_strategies)) == len(recent_strategies) and len(recent_strategies) > 3:
                # All recent strategies are different - may be chasing noise
                alerts.append(RandomnessExposureAlert(
                    component="STRATEGY",
                    risk_type="STRATEGY_CHURNING",
                    severity="MEDIUM",
                    metric_value=1.0,  # All different
                    threshold=0.7,  # Max allowed uniqueness
                    timestamp=datetime.utcnow(),
                    mitigation_action="MAINTAIN_CURRENT_STRATEGY"
                ))
        
        # Check for risk parameter consistency with strategy selection
        if 'risk_parameters' in strategy_data and 'decision' in strategy_data:
            risk_params = strategy_data['risk_parameters']
            decision = strategy_data['decision']
            
            # Check if risk parameters are appropriate for decision type
            if decision in ['BUY', 'SELL'] and risk_params.get('max_position_size', 0) > 0.1:
                # Large position for uncertain market conditions
                alerts.append(RandomnessExposureAlert(
                    component="STRATEGY",
                    risk_type="HIGH_RISK_LOW_CONFIDENCE",
                    severity="HIGH",
                    metric_value=risk_params.get('max_position_size', 0),
                    threshold=0.1,
                    timestamp=datetime.utcnow(),
                    mitigation_action="REDUCE_POSITION_SIZE"
                ))
        
        return alerts
    
    def check_broker_randomness(self, 
                              broker_data: Dict[str, Any], 
                              historical_data: List[Dict[str, Any]]) -> List[RandomnessExposureAlert]:
        """
        Check for randomness exposure in broker component
        """
        alerts = []
        
        # Check for execution quality consistency
        if 'slippage' in broker_data:
            slippage = broker_data['slippage']
            
            # If slippage is unexpectedly high, may be poor execution timing
            if slippage > 2.0:  # 2% slippage threshold
                alerts.append(RandomnessExposureAlert(
                    component="BROKER",
                    risk_type="HIGH_SLIPPAGE",
                    severity="HIGH",
                    metric_value=slippage,
                    threshold=2.0,
                    timestamp=datetime.utcnow(),
                    mitigation_action="REJECT_ORDER"
                ))
        
        # Check for execution timing randomness
        if len(historical_data) >= 10:
            recent_slippages = [item.get('slippage', 0) for item in historical_data[-10:] if 'slippage' in item]
            
            if len(recent_slippages) >= 5:
                avg_slippage = np.mean(recent_slippages)
                current_slippage = broker_data.get('slippage', 0)
                
                # If current slippage is much worse than average, execution may be random
                if current_slippage > avg_slippage * 2 and avg_slippage > 0.5:
                    alerts.append(RandomnessExposureAlert(
                        component="BROKER",
                        risk_type="POOR_EXECUTION_RELATIVE_TO_HISTORY",
                        severity="MEDIUM",
                        metric_value=current_slippage / avg_slippage if avg_slippage > 0 else float('inf'),
                        threshold=2.0,
                        timestamp=datetime.utcnow(),
                        mitigation_action="DELAY_EXECUTION"
                    ))
        
        return alerts
    
    def check_broker_close_randomness(self, 
                                    close_data: Dict[str, Any], 
                                    historical_data: List[Dict[str, Any]]) -> List[RandomnessExposureAlert]:
        """
        Check for randomness exposure in broker close component
        """
        alerts = []
        
        # Check for exit reason consistency
        if 'exit_reason' in close_data:
            exit_reason = close_data['exit_reason']
            
            # If exit is due to timeout, may indicate poor exit timing
            if exit_reason == 'TIMEOUT':
                alerts.append(RandomnessExposureAlert(
                    component="BROKER_CLOSE",
                    risk_type="TIMEOUT_EXIT",
                    severity="MEDIUM",
                    metric_value=1.0,
                    threshold=0.0,
                    timestamp=datetime.utcnow(),
                    mitigation_action="REVIEW_EXIT_TIMING"
                ))
        
        # Check for PnL distribution
        if 'pnl' in close_data and len(historical_data) >= 10:
            current_pnl = close_data['pnl']
            recent_pnls = [item.get('pnl', 0) for item in historical_data[-10:] if 'pnl' in item]
            
            if len(recent_pnls) >= 5:
                avg_pnl = np.mean(recent_pnls)
                std_pnl = np.std(recent_pnls)
                
                # If current PnL is an outlier, may indicate random exit timing
                if std_pnl > 0 and abs(current_pnl - avg_pnl) > 2 * std_pnl:
                    alerts.append(RandomnessExposureAlert(
                        component="BROKER_CLOSE",
                        risk_type="PnL_OUTLIER",
                        severity="MEDIUM",
                        metric_value=abs(current_pnl - avg_pnl) / std_pnl if std_pnl > 0 else 0,
                        threshold=2.0,
                        timestamp=datetime.utcnow(),
                        mitigation_action="REVIEW_EXIT_DECISION"
                    ))
        
        return alerts
    
    def apply_firewall_controls(self, component: str, data: Dict[str, Any], 
                              historical_data: List[Dict[str, Any]]) -> Tuple[bool, List[RandomnessExposureAlert]]:
        """
        Apply firewall controls to determine if component action should proceed
        """
        # Get alerts for the specific component
        if component == "WATCHER":
            alerts = self.check_watcher_randomness(data, historical_data)
        elif component == "ENGINE":
            alerts = self.check_engine_randomness(data, historical_data)
        elif component == "FUSION":
            alerts = self.check_fusion_randomness(data, historical_data)
        elif component == "STRATEGY":
            alerts = self.check_strategy_randomness(data, historical_data)
        elif component == "BROKER":
            alerts = self.check_broker_randomness(data, historical_data)
        elif component == "BROKER_CLOSE":
            alerts = self.check_broker_close_randomness(data, historical_data)
        else:
            return True, []  # Unknown component, allow by default with warning
        
        # Determine if action should be blocked based on alerts
        block_action = any(alert.severity in ["HIGH", "CRITICAL"] for alert in alerts)
        
        return not block_action, alerts


# Global instance
randomness_firewall = RandomnessExposureFirewall()