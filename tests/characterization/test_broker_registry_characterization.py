"""Characterization: broker_registry singleton semantics (E2.T5.0).

Pins the CURRENT behavior that E2.T5 must preserve:

* ``BrokerRegistry`` is a process-wide singleton (one instance per run).
* ``get_execution_service`` de-duplicates: the same configuration constructs the
  underlying execution service exactly once (no duplicate broker construction).

No real broker is constructed — ``create_execution_service`` is stubbed.
"""

import pytest

from infrastructure.services.broker_registry import BrokerRegistry, broker_registry
import infrastructure.services.broker_execution_service as bes


@pytest.mark.unit
def test_broker_registry_is_singleton():
    a = BrokerRegistry()
    b = BrokerRegistry()
    assert a is b
    assert a is broker_registry


@pytest.mark.integration
def test_execution_service_is_not_duplicated(monkeypatch):
    """Same config -> one construction; cached instance returned thereafter."""
    calls = {"count": 0}

    class _StubExecutionService:
        def __init__(self, primary_broker):
            self.primary_broker = primary_broker

    def _fake_create_execution_service(settings=None, broker_type=None, use_multi_broker=True,
                                       primary_broker=None):
        calls["count"] += 1
        return _StubExecutionService(primary_broker)

    monkeypatch.setattr(bes, "create_execution_service", _fake_create_execution_service)

    # Settings are injected by the composition root (E1.T4); the registry forwards
    # the object opaquely, so a sentinel is sufficient for this caching test.
    settings = object()

    # Isolate from any state accumulated elsewhere in the session.
    broker_registry.clear_registry()
    try:
        first = broker_registry.get_execution_service(settings=settings, use_multi_broker=True,
                                                       primary_broker="bingx")
        second = broker_registry.get_execution_service(settings=settings, use_multi_broker=True,
                                                        primary_broker="bingx")

        assert first is second
        assert calls["count"] == 1  # constructed exactly once for this config

        # A different configuration constructs a separate instance.
        other = broker_registry.get_execution_service(settings=settings, use_multi_broker=False,
                                                       primary_broker="binance")
        assert other is not first
        assert calls["count"] == 2
    finally:
        broker_registry.clear_registry()
