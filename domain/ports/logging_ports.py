"""Logging port for the consolidated logger (E3.T6).

Logging was duplicated across ``shared/logger.py`` (``EnhancedLogger`` — the rich
structured app logger), ``utils/logger.py`` (``SyncLogger`` — JSON sync logger),
and ``shared/hexagonal_utils.py`` (``create_hexagonal_logger``). This single port
exposes the canonical structured-logging surface so callers depend on one
contract; a single adapter
(:class:`infrastructure.monitoring.logging_adapter.LoggingAdapter`) implements it
over the canonical ``EnhancedLogger``, preserving its log format exactly (F29).
"""
from abc import abstractmethod
from typing import Protocol


class LoggingPort(Protocol):
    """Canonical structured-logging contract (E3.T6).

    Mirrors ``EnhancedLogger``'s message surface: a message plus optional
    keyword context that is rendered into the log line unchanged.
    """

    @abstractmethod
    def info(self, message: str, **context) -> None:
        """Log an info message with optional keyword context."""
        pass

    @abstractmethod
    def warning(self, message: str, **context) -> None:
        """Log a warning message with optional keyword context."""
        pass

    @abstractmethod
    def error(self, message: str, **context) -> None:
        """Log an error message with optional keyword context."""
        pass

    @abstractmethod
    def debug(self, message: str, **context) -> None:
        """Log a debug message with optional keyword context."""
        pass
