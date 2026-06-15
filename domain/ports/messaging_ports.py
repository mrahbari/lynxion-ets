"""Messaging port for the consolidated event bus (E3.T6).

Event routing was fragmented across three systems (**P5**):

* ``shared/event_bus.py`` — ``EventBus`` (string topics, background thread),
* ``infrastructure/messaging/event_system.py`` — ``EventRouter`` (typed ``SignalEvent`` routing,
  background thread), and
* ``shared/hexagonal_utils.py`` — ``HexagonalEventBus`` (string topics,
  background thread).

All three **silently swallowed** callback exceptions (printing and continuing).
This single port exposes one pub/sub contract (F16/F17); the consolidated adapter
(:class:`infrastructure.messaging.message_bus_adapter.MessageBusAdapter`)
implements it and — per the E3.T6 constraint — **surfaces callback exceptions
instead of swallowing them**.
"""
from abc import abstractmethod
from typing import Protocol, Callable, Any


class MessagingPort(Protocol):
    """Canonical publish/subscribe contract (E3.T6)."""

    @abstractmethod
    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Register ``callback`` to receive ``event_type`` payloads."""
        pass

    @abstractmethod
    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        """Remove ``callback`` from ``event_type`` (no-op if not subscribed)."""
        pass

    @abstractmethod
    def publish(self, event_type: str, data: Any) -> None:
        """Deliver ``data`` to every subscriber of ``event_type``.

        Callback exceptions propagate to the publisher (no silent swallowing).
        """
        pass
