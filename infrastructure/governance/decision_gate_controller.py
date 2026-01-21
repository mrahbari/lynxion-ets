"""
Decision Gate Controller for Enterprise Hedge Fund Trading System
Implements mandatory statistical validation gates between system layers
"""
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import logging

from infrastructure.statistical_validation.statistical_authority_engine import (
    statistical_authority_engine, StatisticalAuthorityScore
)
from infrastructure.statistical_validation.randomness_exposure_firewall import (
    randomness_firewall, RandomnessExposureAlert
)
from infrastructure.statistical_validation.decision_defensibility_validator import (
    decision_validator, DecisionDefensibilityReport
)
from infrastructure.statistical_validation.historical_data_tracker import historical_data_tracker


class DecisionGateResult(Enum):
    REJECTED_INSUFFICIENT_EVIDENCE = "rejected_insufficient_evidence"
    REJECTED_RANDOMNESS_DETECTED = "rejected_randomness_detected"
    REJECTED_DEFENSIBILITY_FAILED = "rejected_defensibility_failed"
    REJECTED_STATISTICAL_INVALID = "rejected_statistical_invalid"
    APPROVED_SCIENTIFIC = "approved_scientific"
    APPROVED_PROBATIONARY = "approved_probationary"


class DecisionGateController:
    """
    Controls the flow of decisions between system layers based on statistical validity
    Implements the PRE-FORENSIC and FORENSIC requirements
    """

    def __init__(self):
        # Statistical thresholds
        self.minimum_sample_size = 30
        self.minimum_statistical_significance = 0.05  # p-value threshold
        self.minimum_authority_score = 0.7  # Authority score threshold
        self.maximum_contributor_correlation = 0.7  # For fusion layer
        self.minimum_defensibility_score = 0.7  # Defensibility threshold
        
        # Maturity periods (in number of decisions)
        self.watcher_maturity_period = 50
        self.engine_maturity_period = 50
        self.fusion_maturity_period = 50
        self.strategy_maturity_period = 100
        
        # Logger
        self.logger = logging.getLogger(__name__)

    def evaluate_watcher_decision(self, 
                                watcher_data: Dict[str, Any], 
                                symbol: str) -> Tuple[DecisionGateResult, Dict[str, Any]]:
        """
        Evaluate watcher decision against statistical requirements
        """
        # Get historical data
        historical_observations = historical_data_tracker.get_watcher_history(symbol, limit=100)
        
        # Check sample size
        if len(historical_observations) < self.minimum_sample_size:
            return DecisionGateResult.REJECTED_INSUFFICIENT_EVIDENCE, {
                "reason": "insufficient_sample_size",
                "current_sample_size": len(historical_observations),
                "required_sample_size": self.minimum_sample_size,
                "maturity_status": f"immature ({len(historical_observations)}/{self.watcher_maturity_period})"
            }
        
        # Calculate statistical authority
        authority_score = statistical_authority_engine.calculate_watcher_authority(
            historical_observations, watcher_data
        )
        
        # Check statistical validity
        if authority_score.validation_status == "INSUFFICIENT_DATA":
            return DecisionGateResult.REJECTED_INSUFFICIENT_EVIDENCE, {
                "reason": "insufficient_data_for_authority_calculation",
                "sample_size": authority_score.sample_size
            }
        
        if authority_score.validation_status == "FAIL":
            return DecisionGateResult.REJECTED_STATISTICAL_INVALID, {
                "reason": "statistical_test_failure",
                "p_value": authority_score.p_value,
                "significance_threshold": self.minimum_statistical_significance,
                "authority_score": authority_score.score
            }
        
        # Check for randomness exposure
        randomness_alerts = randomness_firewall.check_watcher_randomness(watcher_data, historical_observations)
        if any(alert.severity in ["HIGH", "CRITICAL"] for alert in randomness_alerts):
            return DecisionGateResult.REJECTED_RANDOMNESS_DETECTED, {
                "reason": "high_randomness_exposure",
                "alerts": [alert.__dict__ for alert in randomness_alerts]
            }
        
        # Check defensibility
        defensibility_report = decision_validator.validate_watcher_decision(watcher_data, historical_observations)
        if not defensibility_report.is_defensible:
            return DecisionGateResult.REJECTED_DEFENSIBILITY_FAILED, {
                "reason": "defensibility_validation_failed",
                "defensibility_score": len(defensibility_report.supporting_evidence) / len(defensibility_report.validation_results) if defensibility_report.validation_results else 0
            }
        
        # Determine approval level based on authority score
        if authority_score.score >= self.minimum_authority_score and len(historical_observations) >= self.watcher_maturity_period:
            return DecisionGateResult.APPROVED_SCIENTIFIC, {
                "authority_score": authority_score.score,
                "p_value": authority_score.p_value,
                "sample_size": authority_score.sample_size,
                "maturity_status": "mature"
            }
        else:
            return DecisionGateResult.APPROVED_PROBATIONARY, {
                "authority_score": authority_score.score,
                "p_value": authority_score.p_value,
                "sample_size": authority_score.sample_size,
                "maturity_status": f"probationary ({len(historical_observations)}/{self.watcher_maturity_period})"
            }

    def evaluate_engine_decision(self, 
                               engine_data: Dict[str, Any], 
                               symbol: str) -> Tuple[DecisionGateResult, Dict[str, Any]]:
        """
        Evaluate engine decision against statistical requirements
        """
        # Get historical data
        historical_interpretations = historical_data_tracker.get_engine_history(symbol, limit=100)
        
        # Check sample size
        if len(historical_interpretations) < self.minimum_sample_size:
            return DecisionGateResult.REJECTED_INSUFFICIENT_EVIDENCE, {
                "reason": "insufficient_sample_size",
                "current_sample_size": len(historical_interpretations),
                "required_sample_size": self.minimum_sample_size,
                "maturity_status": f"immature ({len(historical_interpretations)}/{self.engine_maturity_period})"
            }
        
        # Calculate statistical authority
        authority_score = statistical_authority_engine.calculate_engine_authority(
            historical_interpretations, engine_data
        )
        
        # Check statistical validity
        if authority_score.validation_status == "INSUFFICIENT_DATA":
            return DecisionGateResult.REJECTED_INSUFFICIENT_EVIDENCE, {
                "reason": "insufficient_data_for_authority_calculation",
                "sample_size": authority_score.sample_size
            }
        
        if authority_score.validation_status == "FAIL":
            return DecisionGateResult.REJECTED_STATISTICAL_INVALID, {
                "reason": "statistical_test_failure",
                "p_value": authority_score.p_value,
                "significance_threshold": self.minimum_statistical_significance,
                "authority_score": authority_score.score
            }
        
        # Check for randomness exposure
        randomness_alerts = randomness_firewall.check_engine_randomness(engine_data, historical_interpretations)
        if any(alert.severity in ["HIGH", "CRITICAL"] for alert in randomness_alerts):
            return DecisionGateResult.REJECTED_RANDOMNESS_DETECTED, {
                "reason": "high_randomness_exposure",
                "alerts": [alert.__dict__ for alert in randomness_alerts]
            }
        
        # Check defensibility
        defensibility_report = decision_validator.validate_engine_decision(engine_data, historical_interpretations)
        if not defensibility_report.is_defensible:
            return DecisionGateResult.REJECTED_DEFENSIBILITY_FAILED, {
                "reason": "defensibility_validation_failed",
                "defensibility_score": len(defensibility_report.supporting_evidence) / len(defensibility_report.validation_results) if defensibility_report.validation_results else 0
            }
        
        # Determine approval level based on authority score
        if authority_score.score >= self.minimum_authority_score and len(historical_interpretations) >= self.engine_maturity_period:
            return DecisionGateResult.APPROVED_SCIENTIFIC, {
                "authority_score": authority_score.score,
                "p_value": authority_score.p_value,
                "sample_size": authority_score.sample_size,
                "maturity_status": "mature"
            }
        else:
            return DecisionGateResult.APPROVED_PROBATIONARY, {
                "authority_score": authority_score.score,
                "p_value": authority_score.p_value,
                "sample_size": authority_score.sample_size,
                "maturity_status": f"probationary ({len(historical_interpretations)}/{self.engine_maturity_period})"
            }

    def evaluate_fusion_decision(self, 
                               fusion_data: Dict[str, Any], 
                               symbol: str) -> Tuple[DecisionGateResult, Dict[str, Any]]:
        """
        Evaluate fusion decision against statistical requirements
        """
        # Get historical data
        historical_fusions = historical_data_tracker.get_fusion_history(symbol, limit=100)
        
        # Check sample size
        if len(historical_fusions) < self.minimum_sample_size:
            return DecisionGateResult.REJECTED_INSUFFICIENT_EVIDENCE, {
                "reason": "insufficient_sample_size",
                "current_sample_size": len(historical_fusions),
                "required_sample_size": self.minimum_sample_size,
                "maturity_status": f"immature ({len(historical_fusions)}/{self.fusion_maturity_period})"
            }
        
        # Check contributor diversity (if contributors are provided)
        if 'contributors' in fusion_data:
            contributors = fusion_data['contributors']
            if len(contributors) < 2:
                return DecisionGateResult.REJECTED_INSUFFICIENT_EVIDENCE, {
                    "reason": "insufficient_contributors_diversity",
                    "num_contributors": len(contributors),
                    "minimum_required": 2
                }
            
            # Check for high correlation between contributors
            weights = list(contributors.values())
            if len(weights) > 1:
                # Calculate correlation proxy - if weights are too similar, signals may be correlated
                avg_weight = np.mean(weights)
                weight_std = np.std(weights)
                
                if avg_weight > 0 and (weight_std / avg_weight) < 0.1:
                    return DecisionGateResult.REJECTED_RANDOMNESS_DETECTED, {
                        "reason": "high_contributor_correlation",
                        "weight_std": weight_std,
                        "avg_weight": avg_weight,
                        "correlation_proxy": weight_std / avg_weight if avg_weight > 0 else float('inf')
                    }
        
        # Calculate statistical authority
        authority_score = statistical_authority_engine.calculate_fusion_authority(
            historical_fusions, fusion_data
        )
        
        # Check statistical validity
        if authority_score.validation_status == "INSUFFICIENT_DATA":
            return DecisionGateResult.REJECTED_INSUFFICIENT_EVIDENCE, {
                "reason": "insufficient_data_for_authority_calculation",
                "sample_size": authority_score.sample_size
            }
        
        if authority_score.validation_status == "FAIL":
            return DecisionGateResult.REJECTED_STATISTICAL_INVALID, {
                "reason": "statistical_test_failure",
                "p_value": authority_score.p_value,
                "significance_threshold": self.minimum_statistical_significance,
                "authority_score": authority_score.score
            }
        
        # Check for randomness exposure
        randomness_alerts = randomness_firewall.check_fusion_randomness(fusion_data, historical_fusions)
        if any(alert.severity in ["HIGH", "CRITICAL"] for alert in randomness_alerts):
            return DecisionGateResult.REJECTED_RANDOMNESS_DETECTED, {
                "reason": "high_randomness_exposure",
                "alerts": [alert.__dict__ for alert in randomness_alerts]
            }
        
        # Check defensibility
        defensibility_report = decision_validator.validate_fusion_decision(fusion_data, historical_fusions)
        if not defensibility_report.is_defensible:
            return DecisionGateResult.REJECTED_DEFENSIBILITY_FAILED, {
                "reason": "defensibility_validation_failed",
                "defensibility_score": len(defensibility_report.supporting_evidence) / len(defensibility_report.validation_results) if defensibility_report.validation_results else 0
            }
        
        # Determine approval level based on authority score
        if authority_score.score >= self.minimum_authority_score and len(historical_fusions) >= self.fusion_maturity_period:
            return DecisionGateResult.APPROVED_SCIENTIFIC, {
                "authority_score": authority_score.score,
                "p_value": authority_score.p_value,
                "sample_size": authority_score.sample_size,
                "maturity_status": "mature"
            }
        else:
            return DecisionGateResult.APPROVED_PROBATIONARY, {
                "authority_score": authority_score.score,
                "p_value": authority_score.p_value,
                "sample_size": authority_score.sample_size,
                "maturity_status": f"probationary ({len(historical_fusions)}/{self.fusion_maturity_period})"
            }

    def evaluate_strategy_decision(self, 
                                 strategy_data: Dict[str, Any], 
                                 symbol: str) -> Tuple[DecisionGateResult, Dict[str, Any]]:
        """
        Evaluate strategy decision against statistical requirements
        """
        # Get historical data
        historical_decisions = historical_data_tracker.get_strategy_history(symbol, limit=100)
        
        # Check sample size
        if len(historical_decisions) < self.minimum_sample_size:
            return DecisionGateResult.REJECTED_INSUFFICIENT_EVIDENCE, {
                "reason": "insufficient_sample_size",
                "current_sample_size": len(historical_decisions),
                "required_sample_size": self.minimum_sample_size,
                "maturity_status": f"immature ({len(historical_decisions)}/{self.strategy_maturity_period})"
            }
        
        # Check for out-of-sample validation
        if not strategy_data.get('out_of_sample_validated', False):
            return DecisionGateResult.REJECTED_INSUFFICIENT_EVIDENCE, {
                "reason": "missing_out_of_sample_validation",
                "oos_validated": False
            }
        
        # Calculate statistical authority
        authority_score = statistical_authority_engine.calculate_strategy_authority(
            historical_decisions, strategy_data
        )
        
        # Check statistical validity
        if authority_score.validation_status == "INSUFFICIENT_DATA":
            return DecisionGateResult.REJECTED_INSUFFICIENT_EVIDENCE, {
                "reason": "insufficient_data_for_authority_calculation",
                "sample_size": authority_score.sample_size
            }
        
        if authority_score.validation_status == "FAIL":
            return DecisionGateResult.REJECTED_STATISTICAL_INVALID, {
                "reason": "statistical_test_failure",
                "p_value": authority_score.p_value,
                "significance_threshold": self.minimum_statistical_significance,
                "authority_score": authority_score.score
            }
        
        # Check for randomness exposure
        randomness_alerts = randomness_firewall.check_strategy_randomness(strategy_data, historical_decisions)
        if any(alert.severity in ["HIGH", "CRITICAL"] for alert in randomness_alerts):
            return DecisionGateResult.REJECTED_RANDOMNESS_DETECTED, {
                "reason": "high_randomness_exposure",
                "alerts": [alert.__dict__ for alert in randomness_alerts]
            }
        
        # Check defensibility
        defensibility_report = decision_validator.validate_strategy_decision(strategy_data, historical_decisions)
        if not defensibility_report.is_defensible:
            return DecisionGateResult.REJECTED_DEFENSIBILITY_FAILED, {
                "reason": "defensibility_validation_failed",
                "defensibility_score": len(defensibility_report.supporting_evidence) / len(defensibility_report.validation_results) if defensibility_report.validation_results else 0
            }
        
        # Determine approval level based on authority score
        if authority_score.score >= self.minimum_authority_score and len(historical_decisions) >= self.strategy_maturity_period:
            return DecisionGateResult.APPROVED_SCIENTIFIC, {
                "authority_score": authority_score.score,
                "p_value": authority_score.p_value,
                "sample_size": authority_score.sample_size,
                "maturity_status": "mature"
            }
        else:
            return DecisionGateResult.APPROVED_PROBATIONARY, {
                "authority_score": authority_score.score,
                "p_value": authority_score.p_value,
                "sample_size": authority_score.sample_size,
                "maturity_status": f"probationary ({len(historical_decisions)}/{self.strategy_maturity_period})"
            }

    def evaluate_broker_decision(self, 
                               broker_data: Dict[str, Any], 
                               symbol: str) -> Tuple[DecisionGateResult, Dict[str, Any]]:
        """
        Evaluate broker decision against statistical requirements
        """
        # Get historical data
        historical_executions = historical_data_tracker.get_broker_history(symbol, limit=100)
        
        # Check execution quality
        slippage = broker_data.get('slippage', 0)
        if abs(slippage) > 2.0:  # More than 2% slippage
            return DecisionGateResult.REJECTED_RANDOMNESS_DETECTED, {
                "reason": "excessive_slippage",
                "slippage_pct": slippage,
                "threshold": 2.0
            }
        
        # Calculate statistical authority
        authority_score = statistical_authority_engine.calculate_broker_authority(
            historical_executions, broker_data
        )
        
        # Check statistical validity
        if authority_score.validation_status == "INSUFFICIENT_DATA":
            # For broker, we might allow some flexibility as execution quality can vary
            # But still track as probationary
            return DecisionGateResult.APPROVED_PROBATIONARY, {
                "reason": "low_execution_history",
                "sample_size": authority_score.sample_size,
                "authority_score": authority_score.score
            }
        
        if authority_score.validation_status == "FAIL":
            return DecisionGateResult.REJECTED_STATISTICAL_INVALID, {
                "reason": "poor_execution_quality_statistics",
                "p_value": authority_score.p_value,
                "authority_score": authority_score.score
            }
        
        # Check for randomness exposure
        randomness_alerts = randomness_firewall.check_broker_randomness(broker_data, historical_executions)
        if any(alert.severity in ["HIGH", "CRITICAL"] for alert in randomness_alerts):
            return DecisionGateResult.REJECTED_RANDOMNESS_DETECTED, {
                "reason": "high_execution_randomness",
                "alerts": [alert.__dict__ for alert in randomness_alerts]
            }
        
        # Check defensibility
        defensibility_report = decision_validator.validate_broker_decision(broker_data, historical_executions)
        if not defensibility_report.is_defensible:
            return DecisionGateResult.REJECTED_DEFENSIBILITY_FAILED, {
                "reason": "execution_defensibility_failed",
                "defensibility_score": len(defensibility_report.supporting_evidence) / len(defensibility_report.validation_results) if defensibility_report.validation_results else 0
            }
        
        # Determine approval level based on authority score
        if authority_score.score >= self.minimum_authority_score:
            return DecisionGateResult.APPROVED_SCIENTIFIC, {
                "authority_score": authority_score.score,
                "p_value": authority_score.p_value,
                "sample_size": authority_score.sample_size
            }
        else:
            return DecisionGateResult.APPROVED_PROBATIONARY, {
                "authority_score": authority_score.score,
                "p_value": authority_score.p_value,
                "sample_size": authority_score.sample_size
            }

    def should_block_decision(self, gate_result: DecisionGateResult) -> bool:
        """
        Determine if a decision should be blocked based on gate result
        """
        return gate_result in [
            DecisionGateResult.REJECTED_INSUFFICIENT_EVIDENCE,
            DecisionGateResult.REJECTED_RANDOMNESS_DETECTED,
            DecisionGateResult.REJECTED_DEFENSIBILITY_FAILED,
            DecisionGateResult.REJECTED_STATISTICAL_INVALID
        ]

    def get_approval_level_multiplier(self, gate_result: DecisionGateResult, result_details: Dict[str, Any]) -> float:
        """
        Get capital allocation multiplier based on approval level
        """
        if gate_result == DecisionGateResult.APPROVED_SCIENTIFIC:
            return 1.0  # Full capital allocation
        elif gate_result == DecisionGateResult.APPROVED_PROBATIONARY:
            return 0.1  # Limited capital allocation (10%)
        else:
            return 0.0  # No capital allocation


# Global instance
decision_gate_controller = DecisionGateController()