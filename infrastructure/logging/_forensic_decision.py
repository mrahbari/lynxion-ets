"""E5.T5 (infra-only mechanical split): decision-stage forensic logging
(fusion + strategy) extracted from ``ForensicLogger``.

Behavior-preserving mixin — methods moved verbatim (signatures, ``self`` semantics,
log output UNCHANGED) and composed via inheritance. Conservative top-level imports.
No layer move, no logic change.
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from uuid import uuid4

from shared.logger import EnhancedLogger
from infrastructure.statistical_validation.statistical_authority_engine import statistical_authority_engine, StatisticalAuthorityScore
from infrastructure.statistical_validation.randomness_exposure_firewall import randomness_firewall, RandomnessExposureAlert
from infrastructure.statistical_validation.decision_defensibility_validator import decision_validator, DecisionDefensibilityReport
from infrastructure.statistical_validation.historical_data_tracker import historical_data_tracker


class _ForensicDecisionLoggingMixin:
    """Fusion + strategy stage logging (log_fusion_result, log_strategy_decision)."""

    def log_fusion_result(self,
                         symbol: str,
                         exchange: str,
                         regime: str,
                         fused_direction: str,
                         confidence: float,
                         contributors: Dict[str, float],
                         signal_correlation_matrix: dict = None,
                         regime_prediction_accuracy: float = None,
                         fusion_conflict_severity: float = None,
                         weight_adjustment_reasoning: str = None,
                         alternative_fusion_outcomes: list = None,
                         decision_reason: str = None,
                         rejected_engines: list = None,
                         timestamp: datetime = None,
                         historical_fusions: list = None) -> Dict[str, Any]:
        """Log fusion result with statistical validation and governance."""
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = datetime.utcnow()

        # Get historical data if not provided
        if historical_fusions is None:
            historical_fusions = historical_data_tracker.get_fusion_history(symbol, limit=50)

        # Perform statistical validation
        authority_score = None
        randomness_alerts = []
        defensibility_report = None

        if historical_fusions:
            authority_score = statistical_authority_engine.calculate_fusion_authority(
                historical_fusions,
                {"fused_direction": fused_direction, "confidence": confidence, "contributors": contributors}
            )

            randomness_alerts = randomness_firewall.check_fusion_randomness(
                {"fused_direction": fused_direction, "confidence": confidence, "contributors": contributors},
                historical_fusions
            )

            defensibility_report = decision_validator.validate_fusion_decision(
                {"fused_direction": fused_direction, "confidence": confidence, "contributors": contributors},
                historical_fusions
            )

        # Governance controls have been removed for simplicity and reliability
        # Always allow logging for audit purposes
        governance_result = {
            "allowed": True,
            "classification": "AUDIT_ONLY",  # Removed classification system
            "approval_multiplier": 1.0,
            "gate_result": "LOGGING_ALWAYS_ALLOWED",
            "result_details": {"reason": "governance_removed_for_simplicity"}
        }

        log_entry = {
            "trace_id": str(uuid4()),
            "layer": "FUSION",
            "symbol": symbol,
            "exchange": exchange,
            "regime": regime,
            "fused_direction": fused_direction,
            "confidence": confidence,
            "contributors": contributors,
            "timestamp": timestamp.isoformat() + "Z",
            "governance": {
                "allowed": governance_result["allowed"],
                "classification": governance_result["classification"],
                "approval_multiplier": governance_result["approval_multiplier"]
            }
        }

        # Add enhanced fields as per forensic audit requirements
        if signal_correlation_matrix:
            log_entry["signal_correlation_matrix"] = signal_correlation_matrix
        if regime_prediction_accuracy is not None:
            log_entry["regime_prediction_accuracy"] = regime_prediction_accuracy
        if fusion_conflict_severity is not None:
            log_entry["fusion_conflict_severity"] = fusion_conflict_severity
        if weight_adjustment_reasoning:
            log_entry["weight_adjustment_reasoning"] = weight_adjustment_reasoning
        if alternative_fusion_outcomes:
            log_entry["alternative_fusion_outcomes"] = alternative_fusion_outcomes

        # Add optional fields if provided
        if decision_reason:
            log_entry["decision_reason"] = decision_reason
        if rejected_engines:
            log_entry["rejected_engines"] = rejected_engines

        # Add statistical validation results if available
        if authority_score:
            log_entry["statistical_authority"] = {
                "score": authority_score.score,
                "p_value": authority_score.p_value,
                "confidence_interval": authority_score.confidence_interval,
                "sample_size": authority_score.sample_size,
                "statistical_test": authority_score.statistical_test,
                "validation_status": authority_score.validation_status
            }

        if randomness_alerts:
            log_entry["randomness_exposure_alerts"] = [
                {
                    "risk_type": alert.risk_type,
                    "severity": alert.severity,
                    "metric_value": alert.metric_value,
                    "threshold": alert.threshold,
                    "mitigation_action": alert.mitigation_action
                } for alert in randomness_alerts
            ]

        if defensibility_report:
            log_entry["defensibility_validation"] = {
                "is_defensible": defensibility_report.is_defensible,
                "validation_results": defensibility_report.validation_results,
                "supporting_evidence_count": len(defensibility_report.supporting_evidence),
                "decision_id": defensibility_report.decision_id
            }

        # Always log to forensic log regardless of governance decision
        # Governance should only affect execution, not logging for audit purposes
        self._log_structured(log_entry)
        if governance_result["allowed"]:
            self.enhanced_logger.info(f"FUSION RESULT: Combined signals for {symbol} resulted in {fused_direction} with confidence {confidence:.2%}")
        else:
            self.enhanced_logger.warning(f"FUSION RESULT BLOCKED: Combined signals for {symbol} resulted in {fused_direction} - governance rejected")

        # Add to historical data tracker
        historical_data_tracker.add_fusion_result(symbol, {
            "fused_direction": fused_direction,
            "confidence": confidence,
            "contributors": contributors,
            "timestamp": timestamp.isoformat() + "Z",
            "was_correct": None  # This would be updated later when outcome is known
        })

        return log_entry

    def log_strategy_decision(self,
                             strategy: str,
                             symbol: str,
                             exchange: str,
                             decision: str,
                             confidence: float,
                             trade_id: str,
                             strategy_selection_reasoning: str = None,
                             historical_performance_match: float = None,
                             risk_adjusted_confidence: float = None,
                             strategy_diversification_impact: float = None,
                             opportunity_cost_analysis: dict = None,
                             decision_reasons: Dict[str, Any] = None,
                             fusion_outputs_used: Dict[str, Any] = None,
                             timestamp: datetime = None,
                             historical_decisions: list = None) -> Dict[str, Any]:
        """Log strategy decision with statistical validation and governance."""
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = datetime.utcnow()

        # Get historical data if not provided
        if historical_decisions is None:
            historical_decisions = historical_data_tracker.get_strategy_history(symbol, limit=50)

        # Perform statistical validation
        authority_score = None
        randomness_alerts = []
        defensibility_report = None

        if historical_decisions:
            authority_score = statistical_authority_engine.calculate_strategy_authority(
                historical_decisions,
                {"strategy": strategy, "decision": decision, "confidence": confidence}
            )

            randomness_alerts = randomness_firewall.check_strategy_randomness(
                {"strategy": strategy, "decision": decision, "confidence": confidence},
                historical_decisions
            )

            defensibility_report = decision_validator.validate_strategy_decision(
                {"strategy": strategy, "decision": decision, "confidence": confidence},
                historical_decisions
            )

        # Governance controls have been removed for simplicity and reliability
        # Always allow logging for audit purposes
        governance_result = {
            "allowed": True,
            "classification": "AUDIT_ONLY",  # Removed classification system
            "approval_multiplier": 1.0,
            "gate_result": "LOGGING_ALWAYS_ALLOWED",
            "result_details": {"reason": "governance_removed_for_simplicity"}
        }

        log_entry = {
            "trace_id": str(uuid4()),
            "layer": "STRATEGY",
            "strategy": strategy,
            "symbol": symbol,
            "exchange": exchange,
            "decision": decision,
            "confidence": confidence,
            "trade_id": trade_id,
            "timestamp": timestamp.isoformat() + "Z",
            "governance": {
                "allowed": governance_result["allowed"],
                "classification": governance_result["classification"],
                "approval_multiplier": governance_result["approval_multiplier"]
            }
        }

        # Add enhanced fields as per forensic audit requirements
        if strategy_selection_reasoning:
            log_entry["strategy_selection_reasoning"] = strategy_selection_reasoning
        if historical_performance_match is not None:
            log_entry["historical_performance_match"] = historical_performance_match
        if risk_adjusted_confidence is not None:
            log_entry["risk_adjusted_confidence"] = risk_adjusted_confidence
        if strategy_diversification_impact is not None:
            log_entry["strategy_diversification_impact"] = strategy_diversification_impact
        if opportunity_cost_analysis:
            log_entry["opportunity_cost_analysis"] = opportunity_cost_analysis

        # Add optional fields if provided
        if decision_reasons:
            log_entry["decision_reasons"] = decision_reasons
        if fusion_outputs_used:
            log_entry["fusion_outputs_used"] = fusion_outputs_used

        # Add statistical validation results if available
        if authority_score:
            log_entry["statistical_authority"] = {
                "score": authority_score.score,
                "p_value": authority_score.p_value,
                "confidence_interval": authority_score.confidence_interval,
                "sample_size": authority_score.sample_size,
                "statistical_test": authority_score.statistical_test,
                "validation_status": authority_score.validation_status
            }

        if randomness_alerts:
            log_entry["randomness_exposure_alerts"] = [
                {
                    "risk_type": alert.risk_type,
                    "severity": alert.severity,
                    "metric_value": alert.metric_value,
                    "threshold": alert.threshold,
                    "mitigation_action": alert.mitigation_action
                } for alert in randomness_alerts
            ]

        if defensibility_report:
            log_entry["defensibility_validation"] = {
                "is_defensible": defensibility_report.is_defensible,
                "validation_results": defensibility_report.validation_results,
                "supporting_evidence_count": len(defensibility_report.supporting_evidence),
                "decision_id": defensibility_report.decision_id
            }

        # Always log to forensic log regardless of governance decision
        # Governance should only affect execution, not logging for audit purposes
        self._log_structured(log_entry)
        if governance_result["allowed"]:
            self.enhanced_logger.info(f"STRATEGY DECISION: {strategy} decided {decision} for {symbol} (Trade ID: {trade_id}) with confidence {confidence:.2%}")
        else:
            self.enhanced_logger.warning(f"STRATEGY DECISION BLOCKED: {strategy} decided {decision} for {symbol} (Trade ID: {trade_id}) - governance rejected")

        # Add to historical data tracker
        historical_data_tracker.add_strategy_decision(symbol, {
            "strategy": strategy,
            "decision": decision,
            "confidence": confidence,
            "raw_confidence": decision_reasons.get("fused_signal_confidence") if decision_reasons else confidence,
            "trade_id": trade_id,
            "timestamp": timestamp.isoformat() + "Z",
            "was_profitable": None  # This would be updated later when trade closes
        })

        return log_entry
