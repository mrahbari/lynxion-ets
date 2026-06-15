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

from shared.logger import EnhancedLogger
from infrastructure.statistical_validation.statistical_authority_engine import statistical_authority_engine, StatisticalAuthorityScore
from infrastructure.statistical_validation.randomness_exposure_firewall import randomness_firewall, RandomnessExposureAlert
from infrastructure.statistical_validation.decision_defensibility_validator import decision_validator, DecisionDefensibilityReport
from infrastructure.statistical_validation.historical_data_tracker import historical_data_tracker
from infrastructure.logging._forensic_observation import _ForensicObservationLoggingMixin
from infrastructure.logging._forensic_decision import _ForensicDecisionLoggingMixin
from infrastructure.logging._forensic_broker import _ForensicBrokerLoggingMixin, symbol_from_trade_id


class ForensicLogger(_ForensicObservationLoggingMixin, _ForensicDecisionLoggingMixin, _ForensicBrokerLoggingMixin):
    """Enhanced forensic-grade structured logging system with statistical validation capabilities."""

    def __init__(self, log_file: str = None, enabled: bool = True, monitoring_config=None):
        """Initialize the enhanced forensic logger with statistical validation capabilities."""
        # Anchor to <project-root>/logs (not cwd-relative) so logs persist in
        # ./logs regardless of where the process runs from.
        if log_file is None:
            from shared.log_paths import log_path
            log_file = log_path("forensic.log")
        # Monitoring config is injected via constructor by the composition root.
        # When absent (unwired/test path) forensic_logging_enabled falls back to
        # True — the settings-schema default — so this module no longer imports
        # bootstrap.settings.loaders (E1).
        self.enabled = enabled and (monitoring_config.forensic_logging_enabled if monitoring_config and hasattr(monitoring_config, 'forensic_logging_enabled') else True)

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
        # default=str so numpy bools/floats in a decision payload never crash a
        # backtest mid-run ("Object of type bool is not JSON serializable").
        self.logger.info(json.dumps(log_entry, default=str))

    def _generate_trade_id(self, symbol: str, exchange: str = "BINANCE") -> str:
        """Generate a unique trade identifier."""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        return f"{symbol}_{exchange}_{timestamp}"


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

        return json.dumps(log_entry, default=str)


# Global forensic logger instance
forensic_logger = ForensicLogger()