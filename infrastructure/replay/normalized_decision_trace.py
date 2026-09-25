"""Read-only, loss-conscious normalization of canonical routed decision events.

Only the random ExecutionIntent UUID is omitted. It is a delivery identity,
not a strategy decision; claim/duplicate behavior needs its own trace gate.
Unknown payload types fail rather than disappearing from the comparison.
"""

from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from math import isfinite


def _value(item):
    if item is None or isinstance(item, (str, bool, int)):
        return item
    if isinstance(item, float):
        if not isfinite(item):
            raise ValueError("nonfinite decision trace value")
        return item
    if isinstance(item, Decimal):
        if not item.is_finite():
            raise ValueError("nonfinite decision trace decimal")
        return str(item)
    if isinstance(item, datetime):
        if item.tzinfo is None:
            raise ValueError("naive decision timestamp")
        return item.isoformat()
    if isinstance(item, Enum):
        return _value(item.value)
    if is_dataclass(item):
        return {
            field.name: _value(getattr(item, field.name))
            for field in fields(item)
            if not (type(item).__name__ == "ExecutionIntent" and field.name == "intent_id")
        }
    if isinstance(item, dict):
        return {str(key): _value(value) for key, value in sorted(item.items(), key=lambda entry: str(entry[0]))}
    if isinstance(item, (list, tuple)):
        return [_value(value) for value in item]
    if isinstance(item, (set, frozenset)):
        return sorted((_value(value) for value in item), key=repr)
    raise TypeError(f"unhandled decision trace value: {type(item).__name__}")


def normalize_event(event):
    """Capture the event and all decision payload fields before subscribers run."""
    return {
        "event_type": event.event_type.value,
        "timestamp": _value(event.timestamp),
        "source": event.source_component,
        "correlation_id": event.correlation_id,
        "data": _value(event.data),
    }
