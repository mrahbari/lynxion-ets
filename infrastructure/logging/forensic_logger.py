"""
Forensic-grade structured logging system for the crypto trading architecture.
Enables complete decision traceability across:
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


class ForensicLogger:
    """Forensic-grade structured logging system for complete trade traceability."""

    def __init__(self, log_file: str = "logs/forensic.log", enabled: bool = True):
        """Initialize the forensic logger with structured logging capabilities."""
        # Check if forensic logging is enabled via environment variable or parameter
        self.enabled = enabled and os.getenv('FORENSIC_LOGGING_ENABLED', 'true').lower() == 'true'

        if not self.enabled:
            # If disabled, just return early without setting up loggers
            self.logger = None
            self.enhanced_logger = EnhancedLogger("Forensic")
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
        self.logger = logging.getLogger("ForensicLogger")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.file_handler)

        # Enhanced logger for human-readable logs
        self.enhanced_logger = EnhancedLogger("Forensic")
        
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
                               timestamp: datetime = None) -> Dict[str, Any]:
        """Log watcher observation with structured format."""
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = datetime.utcnow()

        log_entry = {
            "layer": "WATCHER",
            "watcher": watcher,
            "exchange": exchange,
            "symbol": symbol,
            "observation_type": observation_type,
            "value": value,
            "confidence": confidence,
            "timestamp": timestamp.isoformat() + "Z"
        }

        self._log_structured(log_entry)
        self.enhanced_logger.info(f"WATCHER OBSERVATION: {watcher} detected {observation_type} on {symbol} with confidence {confidence:.2%}")

        return log_entry
        
    def log_engine_interpretation(self,
                                 engine: str,
                                 symbol: str,
                                 exchange: str,
                                 input_observation: str,
                                 interpreted_signal: str,
                                 confidence: float,
                                 score: float,
                                 internal_metrics: Dict[str, Any] = None,
                                 timestamp: datetime = None) -> Dict[str, Any]:
        """Log engine interpretation with structured format."""
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = datetime.utcnow()

        log_entry = {
            "layer": "ENGINE",
            "engine": engine,
            "symbol": symbol,
            "exchange": exchange,
            "input_observation": input_observation,
            "interpreted_signal": interpreted_signal,
            "confidence": confidence,
            "score": score,
            "timestamp": timestamp.isoformat() + "Z"
        }

        # Add internal metrics if provided
        if internal_metrics:
            log_entry["internal_metrics"] = internal_metrics

        self._log_structured(log_entry)
        self.enhanced_logger.info(f"ENGINE INTERPRETATION: {engine} interpreted {input_observation} as {interpreted_signal} on {symbol} with confidence {confidence:.2%}")

        return log_entry
        
    def log_fusion_result(self,
                         symbol: str,
                         exchange: str,
                         regime: str,
                         fused_direction: str,
                         confidence: float,
                         contributors: Dict[str, float],
                         decision_reason: str = None,
                         rejected_engines: list = None,
                         timestamp: datetime = None) -> Dict[str, Any]:
        """Log fusion result with structured format."""
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = datetime.utcnow()

        log_entry = {
            "layer": "FUSION",
            "symbol": symbol,
            "exchange": exchange,
            "regime": regime,
            "fused_direction": fused_direction,
            "confidence": confidence,
            "contributors": contributors,
            "timestamp": timestamp.isoformat() + "Z"
        }

        # Add optional fields if provided
        if decision_reason:
            log_entry["decision_reason"] = decision_reason
        if rejected_engines:
            log_entry["rejected_engines"] = rejected_engines

        self._log_structured(log_entry)
        self.enhanced_logger.info(f"FUSION RESULT: Combined signals for {symbol} resulted in {fused_direction} with confidence {confidence:.2%}")

        return log_entry
        
    def log_strategy_decision(self,
                             strategy: str,
                             symbol: str,
                             exchange: str,
                             decision: str,
                             confidence: float,
                             trade_id: str,
                             decision_reasons: Dict[str, Any] = None,
                             fusion_outputs_used: Dict[str, Any] = None,
                             timestamp: datetime = None) -> Dict[str, Any]:
        """Log strategy decision with structured format."""
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = datetime.utcnow()

        log_entry = {
            "layer": "STRATEGY",
            "strategy": strategy,
            "symbol": symbol,
            "exchange": exchange,
            "decision": decision,
            "confidence": confidence,
            "trade_id": trade_id,
            "timestamp": timestamp.isoformat() + "Z"
        }

        # Add optional fields if provided
        if decision_reasons:
            log_entry["decision_reasons"] = decision_reasons
        if fusion_outputs_used:
            log_entry["fusion_outputs_used"] = fusion_outputs_used

        self._log_structured(log_entry)
        self.enhanced_logger.info(f"STRATEGY DECISION: {strategy} decided {decision} for {symbol} (Trade ID: {trade_id}) with confidence {confidence:.2%}")

        return log_entry
        
    def log_broker_execution(self,
                            trade_id: str,
                            exchange: str,
                            side: str,
                            price: float,
                            sl: float,
                            tp: float,
                            quantity: float,
                            fee: float = 0.0,
                            slippage: float = 0.0,
                            validation_checks: Dict[str, Any] = None,
                            order_status_lifecycle: list = None,
                            timestamp: datetime = None) -> Dict[str, Any]:
        """Log broker execution with structured format."""
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = datetime.utcnow()

        log_entry = {
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
            "timestamp": timestamp.isoformat() + "Z"
        }

        # Add optional fields if provided
        if validation_checks:
            log_entry["validation_checks"] = validation_checks
        if order_status_lifecycle:
            log_entry["order_status_lifecycle"] = order_status_lifecycle

        self._log_structured(log_entry)
        self.enhanced_logger.info(f"BROKER EXECUTION: Executed {side} order for {quantity} {trade_id.split('_')[0]} at ${price:.2f} (Trade ID: {trade_id})")

        return log_entry
        
    def log_broker_close(self,
                        trade_id: str,
                        pnl: float,
                        roi_pct: float,
                        exit_reason: str,
                        holding_seconds: int,
                        timestamp: datetime = None) -> Dict[str, Any]:
        """Log broker close with structured format."""
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = datetime.utcnow()

        log_entry = {
            "layer": "BROKER_CLOSE",
            "trade_id": trade_id,
            "pnl": pnl,
            "roi_pct": roi_pct,
            "exit_reason": exit_reason,
            "holding_seconds": holding_seconds,
            "timestamp": timestamp.isoformat() + "Z"
        }

        self._log_structured(log_entry)
        self.enhanced_logger.info(f"BROKER CLOSE: Trade {trade_id} closed with PnL ${pnl:.2f} ({roi_pct:.2%} ROI) after {holding_seconds}s")

        return log_entry


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