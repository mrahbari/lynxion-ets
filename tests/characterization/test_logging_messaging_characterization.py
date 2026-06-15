"""Characterization: consolidated logger + event bus (E3.T6).

Pins the E3.T6 consolidation behind ``LoggingPort`` + ``MessagingPort``:

* the single logging adapter preserves the canonical ``EnhancedLogger`` log
  format byte-for-byte (message + ``" | k=v"`` context rendering), and
* the single event bus delivers events to subscribers AND propagates a raised
  callback error instead of silently swallowing it (the legacy buses printed and
  continued).
"""

import logging
import logging.handlers

import pytest

from infrastructure.messaging.message_bus_adapter import MessageBusAdapter


# --- Logging: format snapshot must equal the canonical EnhancedLogger ---------

# Canonical file format string (shared.logger.create_logger).
_CANONICAL_FILE_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"


@pytest.mark.unit
def test_logging_file_format_string_unchanged():
    """The canonical formatter string is pinned; the adapter must not change it."""
    # The live logger uses exactly this format string (see shared.logger.create_logger).
    from shared.logger import create_logger

    fmt = logging.Formatter(_CANONICAL_FILE_FORMAT)
    record = logging.LogRecord(
        name="HedgeFund", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello world", args=(), exc_info=None,
    )
    rendered = fmt.format(record)
    # asctime is run-dependent; pin the stable " - LEVEL - name - message" tail.
    assert rendered.endswith(" - INFO - HedgeFund - hello world")

    # And confirm a freshly created canonical logger still carries this exact format.
    canonical = create_logger("E3T6FormatProbe")
    file_formats = [
        h.formatter._fmt for h in canonical.handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
    ]
    assert _CANONICAL_FILE_FORMAT in file_formats


@pytest.mark.unit
def test_logging_adapter_preserves_message_construction():
    """Adapter renders ``message | k=v`` exactly like EnhancedLogger."""
    from infrastructure.monitoring.logging_adapter import LoggingAdapter

    captured = []

    class _CaptureLogger:
        """Stand-in matching EnhancedLogger's message-building contract."""

        def _build(self, message, **context):
            if context:
                context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
                return f"{message} | {context_str}"
            return message

        def info(self, message, **context):
            captured.append(("info", self._build(message, **context)))

        def warning(self, message, **context):
            captured.append(("warning", self._build(message, **context)))

        def error(self, message, **context):
            captured.append(("error", self._build(message, **context)))

        def debug(self, message, **context):
            captured.append(("debug", self._build(message, **context)))

    adapter = LoggingAdapter(logger=_CaptureLogger())
    adapter.info("signal generated", symbol="BTCUSDT", confidence=0.9)
    adapter.error("boom")

    assert captured == [
        ("info", "signal generated | symbol=BTCUSDT | confidence=0.9"),
        ("error", "boom"),
    ]


@pytest.mark.unit
def test_real_enhanced_logger_message_format_matches_adapter():
    """End-to-end: the real EnhancedLogger emits the pinned record message."""
    from shared.logger import EnhancedLogger
    from infrastructure.monitoring.logging_adapter import LoggingAdapter

    enhanced = EnhancedLogger("E3T6Char")
    records = []
    handler = logging.Handler()
    handler.emit = records.append  # capture LogRecords directly
    enhanced.logger.addHandler(handler)
    try:
        LoggingAdapter(logger=enhanced).info("hello", symbol="BTCUSDT")
    finally:
        enhanced.logger.removeHandler(handler)

    assert [r.getMessage() for r in records] == ["hello | symbol=BTCUSDT"]


# --- Messaging: delivery + callback-error propagation -------------------------

@pytest.mark.unit
def test_bus_delivers_events_to_subscribers():
    bus = MessageBusAdapter()
    received = []

    bus.subscribe("tick", lambda data: received.append(("a", data)))
    bus.subscribe("tick", lambda data: received.append(("b", data)))
    bus.subscribe("other", lambda data: received.append(("c", data)))

    bus.publish("tick", 42)

    # Both "tick" subscribers fire in subscription order; "other" does not.
    assert received == [("a", 42), ("b", 42)]


@pytest.mark.unit
def test_bus_propagates_callback_exception():
    """No silent swallowing: a raised callback error reaches the publisher."""
    bus = MessageBusAdapter()

    def boom(_data):
        raise RuntimeError("callback failed")

    bus.subscribe("tick", boom)

    with pytest.raises(RuntimeError, match="callback failed"):
        bus.publish("tick", {"x": 1})


@pytest.mark.unit
def test_bus_unsubscribe_stops_delivery():
    bus = MessageBusAdapter()
    received = []
    cb = lambda data: received.append(data)

    bus.subscribe("tick", cb)
    bus.unsubscribe("tick", cb)
    bus.unsubscribe("tick", cb)  # idempotent / no error
    bus.publish("tick", 1)

    assert received == []


# --- Container wiring: one logger + one bus resolvable behind the ports -------

@pytest.mark.unit
def test_container_resolves_single_logger_and_bus():
    from bootstrap.settings.loaders import load_settings
    from bootstrap.container import Container
    from infrastructure.monitoring.logging_adapter import LoggingAdapter

    container = Container(load_settings())
    log = container.resolve("logging")
    bus = container.resolve("message_bus")

    assert isinstance(log, LoggingAdapter)
    assert isinstance(bus, MessageBusAdapter)
    # Cached: same instances on re-resolve.
    assert container.resolve("logging") is log
    assert container.resolve("message_bus") is bus
