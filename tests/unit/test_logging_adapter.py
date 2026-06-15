"""E4.T4 — unit tests for infrastructure/monitoring/logging_adapter.py.

LoggingAdapter delegates to an EnhancedLogger; tests inject a fake logger (the
documented injection point) so no real log directories/handlers are created.
Pins that each level forwards message + keyword context unchanged, and that an
injected logger is used as-is (no lazy construction). No I/O.
"""

import pytest

from infrastructure.monitoring.logging_adapter import LoggingAdapter


class _FakeLogger:
    def __init__(self):
        self.calls = []

    def info(self, message, **context):
        self.calls.append(("info", message, context))

    def warning(self, message, **context):
        self.calls.append(("warning", message, context))

    def error(self, message, **context):
        self.calls.append(("error", message, context))

    def debug(self, message, **context):
        self.calls.append(("debug", message, context))


@pytest.mark.unit
def test_each_level_forwards_message_and_context():
    fake = _FakeLogger()
    adapter = LoggingAdapter(logger=fake)

    adapter.info("hello", user="u1")
    adapter.warning("careful", code=42)
    adapter.error("boom")
    adapter.debug("trace", step=3)

    assert fake.calls == [
        ("info", "hello", {"user": "u1"}),
        ("warning", "careful", {"code": 42}),
        ("error", "boom", {}),
        ("debug", "trace", {"step": 3}),
    ]


@pytest.mark.unit
def test_injected_logger_is_used_without_lazy_construction():
    fake = _FakeLogger()
    adapter = LoggingAdapter(name="ignored", logger=fake)
    # _delegate() must return the injected logger, never build an EnhancedLogger.
    assert adapter._delegate() is fake
