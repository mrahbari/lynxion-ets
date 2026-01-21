"""
Enhanced Forensic-grade structured logging system with statistical validation for the crypto trading architecture.
Enables complete decision traceability with statistical defensibility across:
Watcher → Engine → Fusion → Strategy → Broker → Trade Close
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from uuid import uuid4
import os

from shared.logger import EnhancedLogger
from infrastructure.statistical_validation.statistical_authority_engine import statistical_authority_engine, StatisticalAuthorityScore
from infrastructure.statistical_validation.randomness_exposure_firewall import randomness_firewall, RandomnessExposureAlert
from infrastructure.statistical_validation.decision_defensibility_validator import decision_validator, DecisionDefensibilityReport
from infrastructure.statistical_validation.historical_data_tracker import historical_data_tracker
# Import governance components separately to avoid circular imports
from infrastructure.governance.decision_gate_controller import decision_gate_controller
from infrastructure.governance.trade_classifier import trade_classifier, TradeClassification
from infrastructure.governance.forensic_attribution_model import forensic_attribution_model


class ForensicLogger:
    """Enhanced forensic-grade structured logging system with statistical validation capabilities."""

    def __init__(self, log_file: str = "logs/forensic.log", enabled: bool = True):
        """Initialize the enhanced forensic logger with statistical validation capabilities."""
        # Check if forensic logging is enabled via environment variable or parameter
        self.enabled = enabled and os.getenv('FORENSIC_LOGGING_ENABLED', 'true').lower() == 'true'

        if not self.enabled:
            # If disabled, just return early without setting up loggers
            self.logger = None
            self.enhanced_logger = EnhancedLogger("EnhancedForensic")
            return

        # Ensure logs directory exists
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create file handler for forensic logs
        self.file_handler = logging.FileHandler(log_file)
        self.file_handler.setLevel(logging.INFO)

        # Use JSON formatter for structured logging
        formatter = JsonFormatter()
        self.file_handler.setFormatter(formatter)

        # Create logger
        self.logger = logging.getLogger("EnhancedForensicLogger")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.file_handler)

        # Enhanced logger for human-readable logs
        self.enhanced_logger = EnhancedLogger("EnhancedForensic")

    def _log_structured(self, log_entry: Dict[str, Any]):
        """Log a structured entry to the forensic log file."""
        if not self.enabled:
            return
        self.logger.info(json.dumps(log_entry))

    def _generate_trade_id(self, symbol: str, exchange: str = "BINANCE") -> str:
        """Generate a unique trade identifier."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        return f"{symbol}_{exchange}_{timestamp}"

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

        # Apply governance controls
        gate_result, result_details = decision_gate_controller.evaluate_watcher_decision(
            {"value": value, "confidence": confidence}, symbol
        )

        should_block = decision_gate_controller.should_block_decision(gate_result)
        approval_multiplier = decision_gate_controller.get_approval_level_multiplier(
            gate_result, result_details
        )

        # Classify the decision
        from infrastructure.governance.decision_gate_controller import DecisionGateResult
        if gate_result == DecisionGateResult.APPROVED_SCIENTIFIC:
            classification = TradeClassification.SCIENTIFIC
        elif gate_result == DecisionGateResult.APPROVED_PROBATIONARY:
            classification = TradeClassification.PROBATIONARY
        else:
            classification = TradeClassification.RANDOM

        governance_result = {
            "allowed": not should_block,
            "classification": classification.value,
            "approval_multiplier": approval_multiplier,
            "gate_result": gate_result,
            "result_details": result_details
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

        # Only log if governance allows it
        if governance_result["allowed"]:
            self._log_structured(log_entry)
            self.enhanced_logger.info(f"WATCHER OBSERVATION: {watcher} detected {observation_type} on {symbol} with confidence {confidence:.2%}")
        else:
            self.enhanced_logger.warning(f"WATCHER OBSERVATION BLOCKED: {watcher} detected {observation_type} on {symbol} - governance rejected")

        # Add to historical data tracker regardless of governance decision
        # This allows for learning and improvement of governance rules
        historical_data_tracker.add_watcher_observation(symbol, {
            "value": value,
            "confidence": confidence,
            "timestamp": timestamp.isoformat() + "Z",
            "was_correct": None,  # This would be updated later when outcome is known
            "governance_classification": governance_result["classification"]
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

        # Apply governance controls
        gate_result, result_details = decision_gate_controller.evaluate_engine_decision(
            {"interpreted_signal": interpreted_signal, "confidence": confidence, "score": score}, symbol
        )

        should_block = decision_gate_controller.should_block_decision(gate_result)
        approval_multiplier = decision_gate_controller.get_approval_level_multiplier(
            gate_result, result_details
        )

        # Classify the decision
        from infrastructure.governance.decision_gate_controller import DecisionGateResult
        if gate_result == DecisionGateResult.APPROVED_SCIENTIFIC:
            classification = TradeClassification.SCIENTIFIC
        elif gate_result == DecisionGateResult.APPROVED_PROBATIONARY:
            classification = TradeClassification.PROBATIONARY
        else:
            classification = TradeClassification.RANDOM

        governance_result = {
            "allowed": not should_block,
            "classification": classification.value,
            "approval_multiplier": approval_multiplier,
            "gate_result": gate_result,
            "result_details": result_details
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

        # Only log if governance allows it
        if governance_result["allowed"]:
            self._log_structured(log_entry)
            self.enhanced_logger.info(f"ENGINE INTERPRETATION: {engine} interpreted {input_observation} as {interpreted_signal} on {symbol} with confidence {confidence:.2%}")
        else:
            self.enhanced_logger.warning(f"ENGINE INTERPRETATION BLOCKED: {engine} interpreted {input_observation} as {interpreted_signal} on {symbol} - governance rejected")

        # Add to historical data tracker regardless of governance decision
        # This allows for learning and improvement of governance rules
        historical_data_tracker.add_engine_interpretation(symbol, {
            "interpreted_signal": interpreted_signal,
            "confidence": confidence,
            "score": score,
            "timestamp": timestamp.isoformat() + "Z",
            "was_correct": None,  # This would be updated later when outcome is known
            "governance_classification": governance_result["classification"]
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

        # Apply governance controls
        gate_result, result_details = decision_gate_controller.evaluate_fusion_decision(
            {"fused_direction": fused_direction, "confidence": confidence, "contributors": contributors}, symbol
        )

        should_block = decision_gate_controller.should_block_decision(gate_result)
        approval_multiplier = decision_gate_controller.get_approval_level_multiplier(
            gate_result, result_details
        )

        # Classify the decision
        from infrastructure.governance.decision_gate_controller import DecisionGateResult
        if gate_result == DecisionGateResult.APPROVED_SCIENTIFIC:
            classification = TradeClassification.SCIENTIFIC
        elif gate_result == DecisionGateResult.APPROVED_PROBATIONARY:
            classification = TradeClassification.PROBATIONARY
        else:
            classification = TradeClassification.RANDOM

        governance_result = {
            "allowed": not should_block,
            "classification": classification.value,
            "approval_multiplier": approval_multiplier,
            "gate_result": gate_result,
            "result_details": result_details
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

        # Only log if governance allows it
        if governance_result["allowed"]:
            self._log_structured(log_entry)
            self.enhanced_logger.info(f"FUSION RESULT: Combined signals for {symbol} resulted in {fused_direction} with confidence {confidence:.2%}")
        else:
            self.enhanced_logger.warning(f"FUSION RESULT BLOCKED: Combined signals for {symbol} resulted in {fused_direction} - governance rejected")

        # Add to historical data tracker regardless of governance decision
        # This allows for learning and improvement of governance rules
        historical_data_tracker.add_fusion_result(symbol, {
            "fused_direction": fused_direction,
            "confidence": confidence,
            "contributors": contributors,
            "timestamp": timestamp.isoformat() + "Z",
            "was_correct": None,  # This would be updated later when outcome is known
            "governance_classification": governance_result["classification"]
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

        # Apply governance controls
        gate_result, result_details = decision_gate_controller.evaluate_strategy_decision(
            {"strategy": strategy, "decision": decision, "confidence": confidence}, symbol
        )

        should_block = decision_gate_controller.should_block_decision(gate_result)
        approval_multiplier = decision_gate_controller.get_approval_level_multiplier(
            gate_result, result_details
        )

        # Classify the decision
        from infrastructure.governance.decision_gate_controller import DecisionGateResult
        if gate_result == DecisionGateResult.APPROVED_SCIENTIFIC:
            classification = TradeClassification.SCIENTIFIC
        elif gate_result == DecisionGateResult.APPROVED_PROBATIONARY:
            classification = TradeClassification.PROBATIONARY
        else:
            classification = TradeClassification.RANDOM

        governance_result = {
            "allowed": not should_block,
            "classification": classification.value,
            "approval_multiplier": approval_multiplier,
            "gate_result": gate_result,
            "result_details": result_details
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

        # Only log if governance allows it
        if governance_result["allowed"]:
            self._log_structured(log_entry)
            self.enhanced_logger.info(f"STRATEGY DECISION: {strategy} decided {decision} for {symbol} (Trade ID: {trade_id}) with confidence {confidence:.2%}")
        else:
            self.enhanced_logger.warning(f"STRATEGY DECISION BLOCKED: {strategy} decided {decision} for {symbol} (Trade ID: {trade_id}) - governance rejected")

        # Add to historical data tracker regardless of governance decision
        # This allows for learning and improvement of governance rules
        historical_data_tracker.add_strategy_decision(symbol, {
            "strategy": strategy,
            "decision": decision,
            "confidence": confidence,
            "trade_id": trade_id,
            "timestamp": timestamp.isoformat() + "Z",
            "was_profitable": None,  # This would be updated later when trade closes
            "governance_classification": governance_result["classification"]
        })

        return log_entry

    def log_broker_execution(self,
                            trade_id: str,
                            exchange: str,
                            side: str,
                            price: float,
                            sl: float,
                            tp: float,
                            quantity: float,
                            execution_quality_score: float = None,
                            market_microstructure_conditions: dict = None,
                            alternative_execution_methods_evaluated: list = None,
                            latency_to_exchange_ms: int = None,
                            fill_probability_estimate: float = None,
                            fee: float = 0.0,
                            slippage: float = 0.0,
                            validation_checks: Dict[str, Any] = None,
                            order_status_lifecycle: list = None,
                            timestamp: datetime = None,
                            historical_executions: list = None) -> Dict[str, Any]:
        """Log broker execution with statistical validation and governance."""
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = datetime.utcnow()

        # Get historical data if not provided
        symbol = symbol_from_trade_id(trade_id)
        if historical_executions is None:
            historical_executions = historical_data_tracker.get_broker_history(symbol, limit=50)

        # Perform statistical validation
        authority_score = None
        randomness_alerts = []
        defensibility_report = None

        if historical_executions:
            authority_score = statistical_authority_engine.calculate_broker_authority(
                historical_executions,
                {"slippage": slippage, "side": side, "price": price}
            )

            randomness_alerts = randomness_firewall.check_broker_randomness(
                {"slippage": slippage, "side": side, "price": price},
                historical_executions
            )

            defensibility_report = decision_validator.validate_broker_decision(
                {"slippage": slippage, "side": side, "price": price},
                historical_executions
            )

        # Apply governance controls
        gate_result, result_details = decision_gate_controller.evaluate_broker_decision(
            {"slippage": slippage, "side": side, "price": price, "quantity": quantity}, symbol
        )

        should_block = decision_gate_controller.should_block_decision(gate_result)
        approval_multiplier = decision_gate_controller.get_approval_level_multiplier(
            gate_result, result_details
        )

        # Classify the decision
        from infrastructure.governance.decision_gate_controller import DecisionGateResult
        if gate_result == DecisionGateResult.APPROVED_SCIENTIFIC:
            classification = TradeClassification.SCIENTIFIC
        elif gate_result == DecisionGateResult.APPROVED_PROBATIONARY:
            classification = TradeClassification.PROBATIONARY
        else:
            classification = TradeClassification.RANDOM

        governance_result = {
            "allowed": not should_block,
            "classification": classification.value,
            "approval_multiplier": approval_multiplier,
            "gate_result": gate_result,
            "result_details": result_details
        }

        log_entry = {
            "trace_id": str(uuid4()),
            "layer": "BROKER",
            "trade_id": trade_id,
            "exchange": exchange,
            "side": side,
            "price": price,
            "sl": sl,
            "tp": tp,
            "quantity": quantity,
            "fee": fee,
            "slippage": slippage,
            "timestamp": timestamp.isoformat() + "Z",
            "governance": {
                "allowed": governance_result["allowed"],
                "classification": governance_result["classification"],
                "approval_multiplier": governance_result["approval_multiplier"]
            }
        }

        # Add enhanced fields as per forensic audit requirements
        if execution_quality_score is not None:
            log_entry["execution_quality_score"] = execution_quality_score
        if market_microstructure_conditions:
            log_entry["market_microstructure_conditions"] = market_microstructure_conditions
        if alternative_execution_methods_evaluated:
            log_entry["alternative_execution_methods_evaluated"] = alternative_execution_methods_evaluated
        if latency_to_exchange_ms is not None:
            log_entry["latency_to_exchange_ms"] = latency_to_exchange_ms
        if fill_probability_estimate is not None:
            log_entry["fill_probability_estimate"] = fill_probability_estimate

        # Add optional fields if provided
        if validation_checks:
            log_entry["validation_checks"] = validation_checks
        if order_status_lifecycle:
            log_entry["order_status_lifecycle"] = order_status_lifecycle

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

        # Only log if governance allows it
        if governance_result["allowed"]:
            self._log_structured(log_entry)
            self.enhanced_logger.info(f"BROKER EXECUTION: Executed {side} order for {quantity} {trade_id.split('_')[0]} at ${price:.2f} (Trade ID: {trade_id})")
        else:
            self.enhanced_logger.warning(f"BROKER EXECUTION BLOCKED: {side} order for {quantity} {trade_id.split('_')[0]} at ${price:.2f} (Trade ID: {trade_id}) - governance rejected")

        # Add to historical data tracker regardless of governance decision
        # This allows for learning and improvement of governance rules
        historical_data_tracker.add_broker_execution(symbol, {
            "trade_id": trade_id,
            "side": side,
            "price": price,
            "slippage": slippage,
            "timestamp": timestamp.isoformat() + "Z",
            "success": True,  # This would be updated if execution fails
            "governance_classification": governance_result["classification"]
        })

        return log_entry

    def log_broker_close(self,
                        trade_id: str,
                        pnl: float,
                        roi_pct: float,
                        exit_reason: str,
                        holding_seconds: int,
                        exit_strategy_effectiveness: float = None,
                        post_exit_market_behavior: dict = None,
                        opportunity_cost_of_exit_timing: float = None,
                        drawdown_recovery_efficiency: float = None,
                        portfolio_impact_assessment: dict = None,
                        timestamp: datetime = None,
                        historical_closures: list = None) -> Dict[str, Any]:
        """Log broker close with statistical validation."""
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = datetime.utcnow()

        # Get historical data if not provided
        symbol = symbol_from_trade_id(trade_id)
        if historical_closures is None:
            historical_closures = historical_data_tracker.get_broker_close_history(symbol, limit=50)

        # Perform statistical validation
        authority_score = None
        randomness_alerts = []
        defensibility_report = None

        if historical_closures:
            authority_score = statistical_authority_engine.calculate_broker_close_authority(
                historical_closures,
                {"pnl": pnl, "roi_pct": roi_pct, "exit_reason": exit_reason}
            )

            randomness_alerts = randomness_firewall.check_broker_close_randomness(
                {"pnl": pnl, "roi_pct": roi_pct, "exit_reason": exit_reason},
                historical_closures
            )

            defensibility_report = decision_validator.validate_broker_close_decision(
                {"pnl": pnl, "roi_pct": roi_pct, "exit_reason": exit_reason},
                historical_closures
            )

        # Apply governance controls
        # Note: For broker close, we still want to log the close event for record keeping,
        # but we can still apply governance for analysis purposes
        governance_result = {
            "allowed": True,  # Always allow close events to be logged
            "classification": "POST_TRADE_ANALYSIS",  # Special classification for post-trade analysis
            "approval_multiplier": 1.0
        }

        log_entry = {
            "trace_id": str(uuid4()),
            "layer": "BROKER_CLOSE",
            "trade_id": trade_id,
            "pnl": pnl,
            "roi_pct": roi_pct,
            "exit_reason": exit_reason,
            "holding_seconds": holding_seconds,
            "timestamp": timestamp.isoformat() + "Z",
            "governance": {
                "allowed": governance_result["allowed"],
                "classification": governance_result["classification"],
                "approval_multiplier": governance_result["approval_multiplier"]
            }
        }

        # Add enhanced fields as per forensic audit requirements
        if exit_strategy_effectiveness is not None:
            log_entry["exit_strategy_effectiveness"] = exit_strategy_effectiveness
        if post_exit_market_behavior:
            log_entry["post_exit_market_behavior"] = post_exit_market_behavior
        if opportunity_cost_of_exit_timing is not None:
            log_entry["opportunity_cost_of_exit_timing"] = opportunity_cost_of_exit_timing
        if drawdown_recovery_efficiency is not None:
            log_entry["drawdown_recovery_efficiency"] = drawdown_recovery_efficiency
        if portfolio_impact_assessment:
            log_entry["portfolio_impact_assessment"] = portfolio_impact_assessment

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

        self._log_structured(log_entry)
        self.enhanced_logger.info(f"BROKER CLOSE: Trade {trade_id} closed with PnL ${pnl:.2f} ({roi_pct:.2%} ROI) after {holding_seconds}s")

        # Add to historical data tracker
        historical_data_tracker.add_broker_close(symbol, {
            "trade_id": trade_id,
            "pnl": pnl,
            "roi_pct": roi_pct,
            "exit_reason": exit_reason,
            "timestamp": timestamp.isoformat() + "Z",
            "was_profitable": pnl > 0,
            "governance_classification": governance_result["classification"]
        })

        return log_entry


def symbol_from_trade_id(trade_id: str) -> str:
    """Extract symbol from trade_id in format SYMBOL_EXCHANGE_TIMESTAMP"""
    parts = trade_id.split('_')
    if len(parts) >= 2:
        return parts[0]  # Return the symbol part
    return "UNKNOWN"


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + "Z",
            'level': record.levelname,
            'message': record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, 'structured_data'):
            log_entry.update(record.structured_data)

        return json.dumps(log_entry)


# Global forensic logger instance
forensic_logger = ForensicLogger(enabled=os.getenv('FORENSIC_LOGGING_ENABLED', 'true').lower() == 'true')