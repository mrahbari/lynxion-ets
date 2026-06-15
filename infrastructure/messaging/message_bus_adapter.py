"""Consolidated event-bus adapter (E3.T6).

A single adapter behind :class:`domain.ports.messaging_ports.MessagingPort` that
replaces the three fragmented event systems (``shared.event_bus.EventBus``,
``infrastructure.messaging.event_system.EventRouter``, ``shared.hexagonal_utils.HexagonalEventBus``)
with one pub/sub bus.

The three legacy buses dispatched on a background thread and **silently
swallowed** callback exceptions (``print(...)`` and continue). Per the E3.T6
constraint, this consolidated bus dispatches synchronously and **propagates
callback exceptions to the publisher** — no silent swallowing — so failures are
surfaced rather than lost on a daemon thread. Subscription semantics (multiple
ordered subscribers per topic, idempotent-safe unsubscribe) match the legacy
buses. The legacy modules remain importable as deprecated shims; physical removal
is deferred to E8.
"""
from typing import Any, Callable, Dict, List

from domain.ports.messaging_ports import MessagingPort


class MessageBusAdapter(MessagingPort):
    """Single, container-managed synchronous event bus.

    Constructed with no side effects (no threads started at import or
    construction), so each container holds its own bus instance.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable[[Any], None]) -> None:
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
            except ValueError:
                pass  # Callback was not subscribed.

    def publish(self, event_type: str, data: Any) -> None:
        # Iterate over a snapshot so a callback may (un)subscribe during dispatch.
        # Exceptions propagate to the caller — callback errors are NOT swallowed.
        for callback in list(self._subscribers.get(event_type, [])):
            callback(data)
