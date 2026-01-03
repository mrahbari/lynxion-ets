"""
Enhanced Logging System for Hierarchical Multi-Watcher Architecture
Implements the required logging standards for the hedge-fund-grade system.
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging
from domain.value_objects import Symbol


class HierarchicalLogger:
    """Enhanced logger that meets the mandatory logging standards"""
    
    def __init__(self, name: str = "HierarchicalTradingSystem"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create a console handler if not already exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_decision(self, symbol: Symbol, 
                    raised_by: str, 
                    regime_state: str, 
                    direction_signals: Dict[str, Any], 
                    execution_signals: Dict[str, Any], 
                    final_decision: str, 
                    reason: str) -> None:
        """
        Log every decision with required information:
        - Symbol
        - Raised By
        - Regime State
        - Direction Signals (accepted / rejected)
        - Execution Signals
        - Final Decision
        - Reason
        """
        message = (
            f"📊 DECISION LOG: {final_decision} | "
            f"Symbol: {symbol.value} | "
            f"Raised By: {raised_by} | "
            f"Regime: {regime_state} | "
            f"Direction: {direction_signals} | "
            f"Execution: {execution_signals} | "
            f"Reason: {reason}"
        )
        
        self.logger.info(message)
        
        # Also log to structured format for analysis
        structured_log = {
            'timestamp': datetime.now().isoformat(),
            'log_type': 'decision_log',
            'symbol': symbol.value,
            'raised_by': raised_by,
            'regime_state': regime_state,
            'direction_signals': direction_signals,
            'execution_signals': execution_signals,
            'final_decision': final_decision,
            'reason': reason
        }
        
        # In a real system, this would go to a structured logging system
        # For now, we'll just log the structured data as JSON string
        self.logger.debug(f"STRUCTURED_LOG: {structured_log}")
    
    def log_watcher_analysis(self, watcher: str, symbol: str, result: str, confidence: float = 0.0, signal_type: str = ""):
        """Log watcher analysis with required format"""
        message = f"[👁️{watcher}] ✅ Observation Generated: {result} | {symbol} | Conf: {confidence:.2%}"
        self.logger.info(message)
        
        structured_log = {
            'timestamp': datetime.now().isoformat(),
            'log_type': 'watcher_analysis',
            'watcher': watcher,
            'symbol': symbol,
            'result': result,
            'confidence': confidence,
            'signal_type': signal_type
        }
        self.logger.debug(f"STRUCTURED_LOG: {structured_log}")
    
    def log_full_flow(self, symbol: str, watcher: str, engine: str, fusion: str, 
                     strategy: str, broker: str, decision: str, confidence: float, reason: str):
        """Log the complete flow from watcher to broker"""
        flow_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        message = (
            f"📊 FULL FLOW: {watcher} → {engine} → {fusion} → {strategy} → {broker} | "
            f"Decision: {decision} | Conf: {confidence:.2%} | "
            f"Reason: {reason} | Flow ID: {flow_id}"
        )
        
        self.logger.info(message)
        
        structured_log = {
            'timestamp': datetime.now().isoformat(),
            'log_type': 'full_flow',
            'flow_id': flow_id,
            'symbol': symbol,
            'watcher': watcher,
            'engine': engine,
            'fusion': fusion,
            'strategy': strategy,
            'broker': broker,
            'decision': decision,
            'confidence': confidence,
            'reason': reason
        }
        self.logger.debug(f"STRUCTURED_LOG: {structured_log}")
    
    def log_background_activity(self, activity_type: str, details: str, **kwargs):
        """Log background activities with additional context"""
        message = f"🔄 BACKGROUND ACTIVITY: {activity_type} | Details: {details}"
        
        # Add any additional context from kwargs
        context_parts = []
        for key, value in kwargs.items():
            if key not in ['activity_type', 'details']:
                context_parts.append(f"{key}={value}")
        
        if context_parts:
            message += f" | {' | '.join(context_parts)}"
        
        self.logger.info(message)
        
        structured_log = {
            'timestamp': datetime.now().isoformat(),
            'log_type': 'background_activity',
            'activity_type': activity_type,
            'details': details,
            **kwargs
        }
        self.logger.debug(f"STRUCTURED_LOG: {structured_log}")
    
    def log_regime_state(self, symbol: Symbol, regime_state: str, confidence: float, reason: str):
        """Log regime state changes"""
        message = f"🏛️ REGIME STATE: {symbol.value} | {regime_state} | Conf: {confidence:.2%} | Reason: {reason}"
        self.logger.info(message)
        
        structured_log = {
            'timestamp': datetime.now().isoformat(),
            'log_type': 'regime_state',
            'symbol': symbol.value,
            'regime_state': regime_state,
            'confidence': confidence,
            'reason': reason
        }
        self.logger.debug(f"STRUCTURED_LOG: {structured_log}")
    
    def log_direction_analysis(self, symbol: Symbol, direction_signals: Dict[str, Any], 
                             final_direction: str, confidence: float, reason: str):
        """Log direction analysis results"""
        message = (
            f"🧭 DIRECTION ANALYSIS: {symbol.value} | "
            f"Final: {final_direction} | Conf: {confidence:.2%} | "
            f"Reason: {reason} | Signals: {direction_signals}"
        )
        self.logger.info(message)
        
        structured_log = {
            'timestamp': datetime.now().isoformat(),
            'log_type': 'direction_analysis',
            'symbol': symbol.value,
            'direction_signals': direction_signals,
            'final_direction': final_direction,
            'confidence': confidence,
            'reason': reason
        }
        self.logger.debug(f"STRUCTURED_LOG: {structured_log}")
    
    def log_execution_decision(self, symbol: Symbol, action: str, confidence: float, 
                             reason: str, execution_signals: Dict[str, Any]):
        """Log execution decisions"""
        message = (
            f"⚡ EXECUTION DECISION: {symbol.value} | "
            f"Action: {action} | Conf: {confidence:.2%} | "
            f"Reason: {reason} | Signals: {execution_signals}"
        )
        self.logger.info(message)
        
        structured_log = {
            'timestamp': datetime.now().isoformat(),
            'log_type': 'execution_decision',
            'symbol': symbol.value,
            'action': action,
            'confidence': confidence,
            'reason': reason,
            'execution_signals': execution_signals
        }
        self.logger.debug(f"STRUCTURED_LOG: {structured_log}")
    
    def log_symbol_state_transition(self, symbol: Symbol, from_state: str, 
                                   to_state: str, reason: str, context: Dict[str, Any]):
        """Log symbol state machine transitions"""
        message = (
            f"🔄 SYMBOL STATE: {symbol.value} | "
            f"{from_state} → {to_state} | Reason: {reason} | Context: {context}"
        )
        self.logger.info(message)
        
        structured_log = {
            'timestamp': datetime.now().isoformat(),
            'log_type': 'symbol_state_transition',
            'symbol': symbol.value,
            'from_state': from_state,
            'to_state': to_state,
            'reason': reason,
            'context': context
        }
        self.logger.debug(f"STRUCTURED_LOG: {structured_log}")
    
    def log_confidence_filtering(self, watcher_name: str, confidence: float, 
                                threshold: float, action: str, symbol: str):
        """Log confidence threshold filtering decisions"""
        message = (
            f"⚖️ CONFIDENCE FILTER: {watcher_name} | "
            f"Conf: {confidence:.2%} | Threshold: {threshold:.2%} | "
            f"Action: {action} | Symbol: {symbol}"
        )
        self.logger.info(message)
        
        structured_log = {
            'timestamp': datetime.now().isoformat(),
            'log_type': 'confidence_filtering',
            'watcher_name': watcher_name,
            'confidence': confidence,
            'threshold': threshold,
            'action': action,
            'symbol': symbol
        }
        self.logger.debug(f"STRUCTURED_LOG: {structured_log}")
    
    def log_conflict_resolution(self, symbol: Symbol, resolution_result: Dict[str, Any]):
        """Log conflict resolution outcomes"""
        message = (
            f"⚖️ CONFLICT RESOLUTION: {symbol.value} | "
            f"Decision: {resolution_result.get('final_decision', 'UNKNOWN')} | "
            f"Conf: {resolution_result.get('confidence', 0):.2%} | "
            f"Reason: {resolution_result.get('reason', 'N/A')}"
        )
        self.logger.info(message)
        
        structured_log = {
            'timestamp': datetime.now().isoformat(),
            'log_type': 'conflict_resolution',
            'symbol': symbol.value,
            'resolution_result': resolution_result
        }
        self.logger.debug(f"STRUCTURED_LOG: {structured_log}")


# Global hierarchical logger instance
hierarchical_logger = HierarchicalLogger()