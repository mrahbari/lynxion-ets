"""Consolidated logging adapter (E3.T6).

A single adapter behind :class:`domain.ports.logging_ports.LoggingPort` that
exposes one logger for the system. Log format is preserved **byte-for-byte** by
delegating to the canonical ``shared.logger.EnhancedLogger`` — the rich
structured logger already used across the application. The other historical
loggers (``shared.sync_logger.SyncLogger``, ``shared.hexagonal_utils`` logger helpers)
remain importable as deprecated shims; physical removal is deferred to E8.

The underlying logger is built lazily on first use, so importing this module has
no side effects (no log directories/handlers are created at import time) and each
container holds its own adapter.
"""
from domain.ports.logging_ports import LoggingPort


class LoggingAdapter(LoggingPort):
    """Single, container-managed logger.

    Delegates to ``EnhancedLogger`` without altering its message construction or
    output format. An existing logger may be injected; otherwise one is created
    lazily for ``name``.
    """

    def __init__(self, name: str = "HedgeFund", logger=None):
        self._name = name
        self._logger = logger

    def _delegate(self):
        if self._logger is None:
            from shared.logger import EnhancedLogger
            self._logger = EnhancedLogger(self._name)
        return self._logger

    def info(self, message: str, **context) -> None:
        self._delegate().info(message, **context)

    def warning(self, message: str, **context) -> None:
        self._delegate().warning(message, **context)

    def error(self, message: str, **context) -> None:
        self._delegate().error(message, **context)

    def debug(self, message: str, **context) -> None:
        self._delegate().debug(message, **context)
