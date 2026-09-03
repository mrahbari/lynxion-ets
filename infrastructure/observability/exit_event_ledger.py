"""Append-only forward exit-event ledger; intentionally not wired to runtime paths."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import threading
from typing import Any, Dict, Iterable


class LedgerValidationError(ValueError):
    pass


EVENT_TYPES = {
    "POSITION_OBSERVED", "MANAGER_EVALUATED", "STOP_REPLACE_REQUESTED",
    "STOP_REPLACE_RESPONDED", "STOP_VISIBILITY_VERIFIED", "STOP_VISIBILITY_FAILED",
    "STATE_COMMITTED", "POSITION_HYDRATED", "EXIT_FILL_OBSERVED",
}
COMMON_REQUIRED = {
    "schema_version", "event_id", "event_type", "event_time_utc", "run_id",
    "evaluation_id", "position_key", "symbol", "side", "quantity", "entry_price",
    "current_price", "price_source", "configured_leverage", "requested_leverage",
    "exchange_leverage", "roe_pct", "peak_price", "peak_roe_pct",
    "manager_state_before", "manager_state_after", "error",
}
EVENT_REQUIRED = {
    "MANAGER_EVALUATED": {"decision"},
    "STOP_REPLACE_REQUESTED": {"requested_stop_price", "attempt"},
    "STOP_REPLACE_RESPONDED": {"causal_event_id", "accepted"},
    "STOP_VISIBILITY_VERIFIED": {"causal_event_id", "visible_stop_price"},
    "STOP_VISIBILITY_FAILED": {"causal_event_id", "mismatch_reason"},
    "STATE_COMMITTED": {"causal_event_id"},
    "POSITION_HYDRATED": {"hydration_source"},
    "EXIT_FILL_OBSERVED": {"fill_price", "fill_quantity", "exit_order_type"},
}
NUMERIC_FIELDS = {
    "quantity", "entry_price", "current_price", "configured_leverage", "requested_leverage",
    "exchange_leverage", "roe_pct", "peak_price", "peak_roe_pct", "requested_stop_price",
    "visible_stop_price", "fill_price", "fill_quantity", "fees", "realized_pnl", "latency_ms",
}
FORBIDDEN_FRAGMENTS = ("api_key", "apikey", "secret", "signature", "request_headers", "account_id")


def _utc_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise LedgerValidationError("event_time_utc must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LedgerValidationError("event_time_utc is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise LedgerValidationError("event_time_utc must be UTC")
    return parsed


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).lower()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


class ExitEventLedger:
    """Validate and append events without importing or calling any execution component."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self._lock = threading.RLock()

    def _path_for(self, event: Dict[str, Any]) -> Path:
        return self.root / f"{_utc_time(event['event_time_utc']).date().isoformat()}.jsonl"

    @staticmethod
    def validate_event(event: Dict[str, Any], known_ids: set[str] | None = None) -> None:
        if not isinstance(event, dict):
            raise LedgerValidationError("event must be an object")
        missing = COMMON_REQUIRED - set(event)
        if missing:
            raise LedgerValidationError(f"missing common fields: {sorted(missing)}")
        event_type = event["event_type"]
        if event_type not in EVENT_TYPES:
            raise LedgerValidationError(f"unknown event_type: {event_type}")
        missing = EVENT_REQUIRED.get(event_type, set()) - set(event)
        if missing:
            raise LedgerValidationError(f"missing {event_type} fields: {sorted(missing)}")
        if event["schema_version"] != 1:
            raise LedgerValidationError("schema_version must be 1")
        for key in ("event_id", "run_id", "evaluation_id", "position_key", "symbol"):
            if not isinstance(event[key], str) or not event[key].strip():
                raise LedgerValidationError(f"{key} must be non-empty")
        if event["side"] not in ("LONG", "SHORT"):
            raise LedgerValidationError("side must be LONG or SHORT")
        _utc_time(event["event_time_utc"])
        for key in NUMERIC_FIELDS & set(event):
            value = event[key]
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise LedgerValidationError(f"{key} must be finite numeric or null")
        for key in _walk_keys(event):
            if any(fragment in key for fragment in FORBIDDEN_FRAGMENTS):
                raise LedgerValidationError(f"forbidden sensitive field: {key}")
        causal = event.get("causal_event_id")
        if causal is not None and (known_ids is None or causal not in known_ids):
            raise LedgerValidationError("causal_event_id does not reference an earlier event")
        if event_type == "STATE_COMMITTED" and event.get("causal_event_type") != "STOP_VISIBILITY_VERIFIED":
            raise LedgerValidationError("STATE_COMMITTED must reference verified visibility")

    @staticmethod
    def _read(path: Path) -> list[Dict[str, Any]]:
        events=[]
        if not path.exists(): return events
        for number,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
            try: event=json.loads(line)
            except json.JSONDecodeError as exc: raise LedgerValidationError(f"invalid JSON at line {number}") from exc
            events.append(event)
        return events

    def append(self, event: Dict[str, Any]) -> Path:
        with self._lock:
            path=self._path_for(event);existing=self._read(path);known={e.get("event_id") for e in existing}
            self.validate_event(event,known)
            if event["event_id"] in known: raise LedgerValidationError("duplicate event_id")
            path.parent.mkdir(parents=True,exist_ok=True)
            rendered=json.dumps(event,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n"
            with path.open("a",encoding="utf-8") as handle:
                handle.write(rendered);handle.flush();os.fsync(handle.fileno())
            return path

    def validate_file(self, path: Path | str) -> Dict[str, Any]:
        path=Path(path);events=self._read(path);known=set();previous=None
        for event in events:
            self.validate_event(event,known)
            if event["event_id"] in known: raise LedgerValidationError("duplicate event_id")
            timestamp=_utc_time(event["event_time_utc"])
            if previous is not None and timestamp<previous: raise LedgerValidationError("event timestamps are out of order")
            previous=timestamp;known.add(event["event_id"])
        raw=path.read_bytes() if path.exists() else b""
        return {"events":len(events),"sha256":hashlib.sha256(raw).hexdigest(),"first_event_id":events[0]["event_id"] if events else None,"last_event_id":events[-1]["event_id"] if events else None}
