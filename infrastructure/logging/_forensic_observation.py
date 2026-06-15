"""E5.T5 (infra-only mechanical split): observation-stage forensic logging
(watcher + engine) extracted from ``ForensicLogger``.

Behavior-preserving mixin — methods moved verbatim (signatures, ``self`` semantics,
and log output UNCHANGED) and composed back via inheritance. Imports are the module's
original top-level block (conservative; some unused here) to guarantee name resolution.
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


class _ForensicObservationLoggingMixin:
    """Watcher + engine stage logging (log_watcher_observation, log_engine_interpretation + helpers)."""

    def log_watcher_observation(self,
                               watcher: str,
                               symbol: str,
                               exchange: str,
                               observation_type: str,
                               value: float,
                               confidence: float,
                               market_regime: str = None,
                               historical_accuracy: float = None,
                               timestamp: datetime = None,
                               historical_observations: list = None) -> Dict[str, Any]:
        """Log watcher observation with statistical validation and governance."""
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = datetime.utcnow()

        # Get historical data if not provided
        if historical_observations is None:
            historical_observations = historical_data_tracker.get_watcher_history(symbol, limit=50)

        # Perform statistical validation
        authority_score = None
        randomness_alerts = []
        defensibility_report = None

        if historical_observations:
            authority_score = statistical_authority_engine.calculate_watcher_authority(
                historical_observations,
                {"value": value, "confidence": confidence}
            )

            randomness_alerts = randomness_firewall.check_watcher_randomness(
                {"value": value, "confidence": confidence},
                historical_observations
            )

            defensibility_report = decision_validator.validate_watcher_decision(
                {"value": value, "confidence": confidence},
                historical_observations
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
            "layer": "WATCHER",
            "watcher": watcher,
            "exchange": exchange,
            "symbol": symbol,
            "observation_type": observation_type,
            "value": value,
            "confidence": confidence,
            "timestamp": timestamp.isoformat() + "Z",
            "governance": {
                "allowed": governance_result["allowed"],
                "classification": governance_result["classification"],
                "approval_multiplier": governance_result["approval_multiplier"]
            }
        }

        # Add enhanced fields as per forensic audit requirements
        if market_regime:
            log_entry["market_regime_classification"] = market_regime
        if historical_accuracy is not None:
            log_entry["historical_accuracy_rate"] = historical_accuracy
        log_entry["signal_frequency_deviation"] = self._calculate_frequency_deviation(watcher, symbol)
        log_entry["market_impact_estimation"] = self._estimate_market_impact(observation_type, value)
        log_entry["regime_shift_probability"] = self._calculate_regime_shift_probability(symbol)

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
            self.enhanced_logger.info(f"WATCHER OBSERVATION: {watcher} detected {observation_type} on {symbol} with confidence {confidence:.2%}")
        else:
            self.enhanced_logger.warning(f"WATCHER OBSERVATION BLOCKED: {watcher} detected {observation_type} on {symbol} - governance rejected")

        # Add to historical data tracker
        historical_data_tracker.add_watcher_observation(symbol, {
            "value": value,
            "confidence": confidence,
            "timestamp": timestamp.isoformat() + "Z",
            "was_correct": None  # This would be updated later when outcome is known
        })

        return log_entry

    def _calculate_frequency_deviation(self, watcher_name: str, symbol: str) -> float:
        """Calculate how often this watcher generates signals vs. historical average."""
        # This would interface with historical data to calculate deviation
        # For now, return a placeholder value
        try:
            from infrastructure.statistical_validation.historical_data_tracker import historical_data_tracker
            return historical_data_tracker.get_signal_frequency_deviation(watcher_name, symbol)
        except:
            return 0.0

    def _estimate_market_impact(self, observation_type: str, value: float) -> float:
        """Estimate market impact of acting on this signal."""
        # Placeholder implementation - in reality this would use market microstructure data
        return abs(value) * 0.001  # 0.1% of signal magnitude as estimated impact

    def _calculate_regime_shift_probability(self, symbol: str) -> float:
        """Calculate probability of market regime change in next period."""
        # This would interface with regime detection system
        try:
            from infrastructure.market_regime.regime_detector import regime_detector
            # This is a simplified version - in practice you'd need price data
            return 0.15  # 15% probability as default
        except:
            return 0.10  # 10% probability as fallback

    def log_engine_interpretation(self,
                                 engine: str,
                                 symbol: str,
                                 exchange: str,
                                 input_observation: str,
                                 interpreted_signal: str,
                                 confidence: float,
                                 score: float,
                                 interpretation_delay_ms: int = None,
                                 contextual_factors: dict = None,
                                 internal_metrics: Dict[str, Any] = None,
                                 timestamp: datetime = None,
                                 historical_interpretations: list = None) -> Dict[str, Any]:
        """Log engine interpretation with statistical validation and governance."""
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = datetime.utcnow()

        # Get historical data if not provided
        if historical_interpretations is None:
            historical_interpretations = historical_data_tracker.get_engine_history(symbol, limit=50)

        # Perform statistical validation
        authority_score = None
        randomness_alerts = []
        defensibility_report = None

        if historical_interpretations:
            authority_score = statistical_authority_engine.calculate_engine_authority(
                historical_interpretations,
                {"interpreted_signal": interpreted_signal, "confidence": confidence, "score": score}
            )

            randomness_alerts = randomness_firewall.check_engine_randomness(
                {"interpreted_signal": interpreted_signal, "confidence": confidence, "score": score},
                historical_interpretations
            )

            defensibility_report = decision_validator.validate_engine_decision(
                {"interpreted_signal": interpreted_signal, "confidence": confidence, "score": score},
                historical_interpretations
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
            "layer": "ENGINE",
            "engine": engine,
            "symbol": symbol,
            "exchange": exchange,
            "input_observation": input_observation,
            "interpreted_signal": interpreted_signal,
            "confidence": confidence,
            "score": score,
            "timestamp": timestamp.isoformat() + "Z",
            "governance": {
                "allowed": governance_result["allowed"],
                "classification": governance_result["classification"],
                "approval_multiplier": governance_result["approval_multiplier"]
            }
        }

        # Add enhanced fields as per forensic audit requirements
        if interpretation_delay_ms is not None:
            log_entry["interpretation_delay_ms"] = interpretation_delay_ms
        if contextual_factors:
            log_entry["contextual_market_factors"] = contextual_factors
        log_entry["alternative_interpretation_probabilities"] = self._calculate_alternative_interpretations(input_observation)
        log_entry["interpretation_consistency_score"] = self._calculate_interpretation_consistency(symbol, interpreted_signal)
        log_entry["cross_validation_source"] = self._get_cross_validation_source(symbol)

        # Add internal metrics if provided
        if internal_metrics:
            log_entry["internal_metrics"] = internal_metrics

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
            self.enhanced_logger.info(f"ENGINE INTERPRETATION: {engine} interpreted {input_observation} as {interpreted_signal} on {symbol} with confidence {confidence:.2%}")
        else:
            self.enhanced_logger.warning(f"ENGINE INTERPRETATION BLOCKED: {engine} interpreted {input_observation} as {interpreted_signal} on {symbol} - governance rejected")

        # Add to historical data tracker
        historical_data_tracker.add_engine_interpretation(symbol, {
            "interpreted_signal": interpreted_signal,
            "confidence": confidence,
            "score": score,
            "timestamp": timestamp.isoformat() + "Z",
            "was_correct": None  # This would be updated later when outcome is known
        })

        return log_entry

    def _calculate_alternative_interpretations(self, input_observation: str) -> list:
        """Calculate alternative interpretations and their probabilities."""
        # Placeholder implementation
        return [{"interpretation": "NEUTRAL", "probability": 0.15}, {"interpretation": "BUY", "probability": 0.25}]

    def _calculate_interpretation_consistency(self, symbol: str, interpreted_signal: str) -> float:
        """Calculate how consistent this interpretation is with past similar signals."""
        # This would interface with historical data
        try:
            from infrastructure.statistical_validation.historical_data_tracker import historical_data_tracker
            return historical_data_tracker.get_interpretation_consistency(symbol, interpreted_signal)
        except:
            return 0.65  # Default consistency score

    def _get_cross_validation_source(self, symbol: str) -> str:
        """Get source used for cross-validation."""
        return "TECHNICAL_INDICATORS"
