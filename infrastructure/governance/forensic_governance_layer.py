"""
Comprehensive Forensic Governance Layer for Enterprise Hedge Fund Trading System
Implements complete decision governance from watcher to broker close
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from infrastructure.governance.decision_gate_controller import (
    decision_gate_controller, DecisionGateResult
)
from infrastructure.governance.trade_classifier import (
    trade_classifier, TradeClassification
)
from infrastructure.governance.forensic_attribution_model import (
    forensic_attribution_model
)
from infrastructure.statistical_validation.statistical_authority_engine import (
    statistical_authority_engine
)
from infrastructure.statistical_validation.randomness_exposure_firewall import (
    randomness_firewall
)
from infrastructure.statistical_validation.decision_defensibility_validator import (
    decision_validator
)
from infrastructure.statistical_validation.historical_data_tracker import (
    historical_data_tracker
)


class ForensicGovernanceLayer:
    """
    Main governance layer that orchestrates forensic controls across all system components
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def govern_watcher_observation(self, 
                                 watcher_data: Dict[str, Any], 
                                 symbol: str, 
                                 exchange: str) -> Dict[str, Any]:
        """
        Govern watcher observation decision
        """
        # Evaluate through decision gate
        gate_result, result_details = decision_gate_controller.evaluate_watcher_decision(
            watcher_data, symbol
        )
        
        # Determine if decision should be blocked
        should_block = decision_gate_controller.should_block_decision(gate_result)
        
        # Get approval level multiplier
        approval_multiplier = decision_gate_controller.get_approval_level_multiplier(
            gate_result, result_details
        )
        
        # Classify the decision
        classification = self._classify_decision_from_gate_result(gate_result, result_details)
        
        # Log the governance decision
        governance_log = {
            "layer": "WATCHER",
            "symbol": symbol,
            "exchange": exchange,
            "gate_result": gate_result.value,
            "should_block": should_block,
            "approval_multiplier": approval_multiplier,
            "classification": classification.value,
            "result_details": result_details,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.logger.info(f"Watcher governance: {gate_result.value} for {symbol}")
        
        return {
            "allowed": not should_block,
            "classification": classification.value,
            "approval_multiplier": approval_multiplier,
            "governance_log": governance_log,
            "gate_result": gate_result,
            "result_details": result_details
        }
    
    def govern_engine_interpretation(self, 
                                   engine_data: Dict[str, Any], 
                                   symbol: str, 
                                   exchange: str) -> Dict[str, Any]:
        """
        Govern engine interpretation decision
        """
        # Evaluate through decision gate
        gate_result, result_details = decision_gate_controller.evaluate_engine_decision(
            engine_data, symbol
        )
        
        # Determine if decision should be blocked
        should_block = decision_gate_controller.should_block_decision(gate_result)
        
        # Get approval level multiplier
        approval_multiplier = decision_gate_controller.get_approval_level_multiplier(
            gate_result, result_details
        )
        
        # Classify the decision
        classification = self._classify_decision_from_gate_result(gate_result, result_details)
        
        # Log the governance decision
        governance_log = {
            "layer": "ENGINE",
            "symbol": symbol,
            "exchange": exchange,
            "gate_result": gate_result.value,
            "should_block": should_block,
            "approval_multiplier": approval_multiplier,
            "classification": classification.value,
            "result_details": result_details,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.logger.info(f"Engine governance: {gate_result.value} for {symbol}")
        
        return {
            "allowed": not should_block,
            "classification": classification.value,
            "approval_multiplier": approval_multiplier,
            "governance_log": governance_log,
            "gate_result": gate_result,
            "result_details": result_details
        }
    
    def govern_fusion_decision(self, 
                             fusion_data: Dict[str, Any], 
                             symbol: str, 
                             exchange: str) -> Dict[str, Any]:
        """
        Govern fusion decision
        """
        # Evaluate through decision gate
        gate_result, result_details = decision_gate_controller.evaluate_fusion_decision(
            fusion_data, symbol
        )
        
        # Determine if decision should be blocked
        should_block = decision_gate_controller.should_block_decision(gate_result)
        
        # Get approval level multiplier
        approval_multiplier = decision_gate_controller.get_approval_level_multiplier(
            gate_result, result_details
        )
        
        # Classify the decision
        classification = self._classify_decision_from_gate_result(gate_result, result_details)
        
        # Log the governance decision
        governance_log = {
            "layer": "FUSION",
            "symbol": symbol,
            "exchange": exchange,
            "gate_result": gate_result.value,
            "should_block": should_block,
            "approval_multiplier": approval_multiplier,
            "classification": classification.value,
            "result_details": result_details,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.logger.info(f"Fusion governance: {gate_result.value} for {symbol}")
        
        return {
            "allowed": not should_block,
            "classification": classification.value,
            "approval_multiplier": approval_multiplier,
            "governance_log": governance_log,
            "gate_result": gate_result,
            "result_details": result_details
        }
    
    def govern_strategy_decision(self, 
                               strategy_data: Dict[str, Any], 
                               symbol: str, 
                               exchange: str) -> Dict[str, Any]:
        """
        Govern strategy decision
        """
        # Evaluate through decision gate
        gate_result, result_details = decision_gate_controller.evaluate_strategy_decision(
            strategy_data, symbol
        )
        
        # Determine if decision should be blocked
        should_block = decision_gate_controller.should_block_decision(gate_result)
        
        # Get approval level multiplier
        approval_multiplier = decision_gate_controller.get_approval_level_multiplier(
            gate_result, result_details
        )
        
        # Classify the decision
        classification = self._classify_decision_from_gate_result(gate_result, result_details)
        
        # Log the governance decision
        governance_log = {
            "layer": "STRATEGY",
            "symbol": symbol,
            "exchange": exchange,
            "gate_result": gate_result.value,
            "should_block": should_block,
            "approval_multiplier": approval_multiplier,
            "classification": classification.value,
            "result_details": result_details,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.logger.info(f"Strategy governance: {gate_result.value} for { symbol}")
        
        return {
            "allowed": not should_block,
            "classification": classification.value,
            "approval_multiplier": approval_multiplier,
            "governance_log": governance_log,
            "gate_result": gate_result,
            "result_details": result_details
        }
    
    def govern_broker_execution(self, 
                              broker_data: Dict[str, Any], 
                              symbol: str, 
                              exchange: str) -> Dict[str, Any]:
        """
        Govern broker execution decision
        """
        # Evaluate through decision gate
        gate_result, result_details = decision_gate_controller.evaluate_broker_decision(
            broker_data, symbol
        )
        
        # Determine if decision should be blocked
        should_block = decision_gate_controller.should_block_decision(gate_result)
        
        # Get approval level multiplier
        approval_multiplier = decision_gate_controller.get_approval_level_multiplier(
            gate_result, result_details
        )
        
        # Classify the decision
        classification = self._classify_decision_from_gate_result(gate_result, result_details)
        
        # Log the governance decision
        governance_log = {
            "layer": "BROKER",
            "symbol": symbol,
            "exchange": exchange,
            "gate_result": gate_result.value,
            "should_block": should_block,
            "approval_multiplier": approval_multiplier,
            "classification": classification.value,
            "result_details": result_details,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.logger.info(f"Broker governance: {gate_result.value} for {symbol}")
        
        return {
            "allowed": not should_block,
            "classification": classification.value,
            "approval_multiplier": approval_multiplier,
            "governance_log": governance_log,
            "gate_result": gate_result,
            "result_details": result_details
        }
    
    def _classify_decision_from_gate_result(self, gate_result: DecisionGateResult, 
                                          result_details: Dict[str, Any]) -> TradeClassification:
        """
        Convert gate result to trade classification
        """
        if gate_result == DecisionGateResult.APPROVED_SCIENTIFIC:
            return TradeClassification.SCIENTIFIC
        elif gate_result == DecisionGateResult.APPROVED_PROBATIONARY:
            return TradeClassification.PROBATIONARY
        else:
            return TradeClassification.RANDOM
    
    def perform_forensic_analysis_on_trade(self, 
                                         trade_data: Dict[str, Any], 
                                         pnl: float) -> Dict[str, Any]:
        """
        Perform comprehensive forensic analysis on a completed trade
        """
        # Perform attribution analysis
        attribution = forensic_attribution_model.attribute_loss(trade_data, pnl)
        
        # Calculate regret metrics
        regret_metrics = forensic_attribution_model.calculate_regret_metrics(trade_data, pnl)
        
        # Perform counterfactual analysis
        counterfactual_analysis = forensic_attribution_model.calculate_counterfactual_analysis(
            trade_data, pnl
        )
        
        # Compile forensic report
        forensic_report = {
            "trade_id": trade_data.get("trade_id"),
            "symbol": trade_data.get("symbol"),
            "pnl": pnl,
            "attribution": attribution,
            "regret_metrics": regret_metrics,
            "counterfactual_analysis": counterfactual_analysis,
            "analysis_timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.logger.info(f"Forensic analysis completed for trade {trade_data.get('trade_id')}")
        
        return forensic_report
    
    def enforce_decision_governance(self, 
                                  layer: str, 
                                  decision_data: Dict[str, Any], 
                                  symbol: str, 
                                  exchange: str) -> Dict[str, Any]:
        """
        Generic method to enforce decision governance across any layer
        """
        if layer.upper() == "WATCHER":
            return self.govern_watcher_observation(decision_data, symbol, exchange)
        elif layer.upper() == "ENGINE":
            return self.govern_engine_interpretation(decision_data, symbol, exchange)
        elif layer.upper() == "FUSION":
            return self.govern_fusion_decision(decision_data, symbol, exchange)
        elif layer.upper() == "STRATEGY":
            return self.govern_strategy_decision(decision_data, symbol, exchange)
        elif layer.upper() == "BROKER":
            return self.govern_broker_execution(decision_data, symbol, exchange)
        else:
            raise ValueError(f"Unknown layer: {layer}")


# Global instance
forensic_governance_layer = ForensicGovernanceLayer()