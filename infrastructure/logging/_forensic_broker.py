"""E5.T5 (infra-only mechanical split): broker-stage forensic logging
(execution + close) extracted from ``ForensicLogger``.

Behavior-preserving mixin — log_broker_execution/log_broker_close moved verbatim
(signatures, ``self`` semantics, log output UNCHANGED) and composed via inheritance.
The broker-only helper ``symbol_from_trade_id`` moves here too (internal-only) and is
re-exported from ``forensic_logger`` to preserve its public import path. Conservative
top-level imports. No layer move, no logic change.
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


def symbol_from_trade_id(trade_id: str) -> str:
    """Extract symbol from trade_id in format SYMBOL_EXCHANGE_TIMESTAMP"""
    # Convert to string in case an integer is passed
    trade_id_str = str(trade_id)
    parts = trade_id_str.split('_')
    if len(parts) >= 2:
        return parts[0]  # Return the symbol part
    # If no underscore is found, return the whole string as symbol
    return trade_id_str


class _ForensicBrokerLoggingMixin:
    """Broker execution + close stage logging."""

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

        # Always log to forensic log regardless of governance decision
        # Governance should only affect execution, not logging for audit purposes
        self._log_structured(log_entry)
        if governance_result["allowed"]:
            self.enhanced_logger.info(f"BROKER EXECUTION: Executed {side} order for {quantity} {str(trade_id).split('_')[0]} at ${price:.2f} (Trade ID: {trade_id})")
        else:
            self.enhanced_logger.warning(f"BROKER EXECUTION BLOCKED: {side} order for {quantity} {str(trade_id).split('_')[0]} at ${price:.2f} (Trade ID: {trade_id}) - governance rejected")

        # Add to historical data tracker
        historical_data_tracker.add_broker_execution(symbol, {
            "trade_id": trade_id,
            "side": side,
            "price": price,
            "slippage": slippage,
            "timestamp": timestamp.isoformat() + "Z",
            "success": True  # This would be updated if execution fails
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

        # Governance controls have been removed for simplicity and reliability
        # Always allow close events to be logged for audit purposes
        governance_result = {
            "allowed": True,  # Always allow close events to be logged
            "classification": "AUDIT_ONLY",  # Removed classification system
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

        # Always log broker close events regardless of governance decision
        # This is already set to always log, but maintaining consistency
        self._log_structured(log_entry)
        self.enhanced_logger.info(f"BROKER CLOSE: Trade {trade_id} closed with PnL ${pnl:.2f} ({roi_pct:.2%} ROI) after {holding_seconds}s")

        # Add to historical data tracker
        historical_data_tracker.add_broker_close(symbol, {
            "trade_id": trade_id,
            "pnl": pnl,
            "roi_pct": roi_pct,
            "exit_reason": exit_reason,
            "timestamp": timestamp.isoformat() + "Z",
            "was_profitable": pnl > 0
        })

        return log_entry
