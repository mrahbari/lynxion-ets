"""Disconnected, restart-safe position identity snapshot for forward evidence."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import threading
from typing import Any, Dict


class PositionIdentityError(ValueError):
    pass


REQUIRED_FIELDS = {
    "schema_version", "record_id", "position_key", "symbol", "side", "entry_price",
    "quantity", "exchange_leverage", "first_observed_utc", "last_observed_utc",
    "observer_run_id", "exchange_position_id", "exchange_order_id", "lifecycle_state",
}
LIFECYCLE_ORDER = {"OPEN": 0, "CLOSURE_OBSERVED": 1, "TERMINAL_EVIDENCE_COMPLETE": 2}
IMMUTABLE_FIELDS = {
    "schema_version", "record_id", "position_key", "symbol", "side", "entry_price",
    "exchange_leverage", "first_observed_utc", "observer_run_id", "exchange_position_id",
}
FORBIDDEN_FRAGMENTS = ("api_key", "apikey", "secret", "signature", "request_headers", "account_id")


def _utc_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise PositionIdentityError("timestamp must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PositionIdentityError("timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise PositionIdentityError("timestamp must be UTC")
    return parsed


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key).lower()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def deterministic_record_id(position_key: str, observer_run_id: str, first_observed_utc: str) -> str:
    raw = f"{position_key}\x1f{observer_run_id}\x1f{first_observed_utc}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class PositionIdentitySnapshot:
    """Validate and atomically persist identities without importing runtime components."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self._lock = threading.RLock()

    @staticmethod
    def validate_record(record: Dict[str, Any]) -> None:
        if not isinstance(record, dict):
            raise PositionIdentityError("record must be an object")
        missing = REQUIRED_FIELDS - set(record)
        if missing:
            raise PositionIdentityError(f"missing fields: {sorted(missing)}")
        if record["schema_version"] != 1:
            raise PositionIdentityError("schema_version must be 1")
        for key in ("record_id", "position_key", "symbol", "observer_run_id"):
            if not isinstance(record[key], str) or not record[key].strip():
                raise PositionIdentityError(f"{key} must be non-empty")
        if record["side"] not in ("LONG", "SHORT"):
            raise PositionIdentityError("side must be LONG or SHORT")
        if record["symbol"] != record["symbol"].upper() or any(
            separator in record["symbol"] for separator in "-/_ "
        ):
            raise PositionIdentityError("symbol must be normalized")
        for key in ("entry_price", "quantity", "exchange_leverage"):
            value = record[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise PositionIdentityError(f"{key} must be positive finite numeric")
        first = _utc_time(record["first_observed_utc"])
        last = _utc_time(record["last_observed_utc"])
        if last < first:
            raise PositionIdentityError("last_observed_utc precedes first_observed_utc")
        if record["lifecycle_state"] not in LIFECYCLE_ORDER:
            raise PositionIdentityError("invalid lifecycle_state")
        expected_id = deterministic_record_id(
            record["position_key"], record["observer_run_id"], record["first_observed_utc"]
        )
        if record["record_id"] != expected_id:
            raise PositionIdentityError("record_id is not deterministic")
        for key in _walk_keys(record):
            if any(fragment in key for fragment in FORBIDDEN_FRAGMENTS):
                raise PositionIdentityError(f"forbidden sensitive field: {key}")

    def _read(self) -> Dict[str, Dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PositionIdentityError("snapshot is corrupt") from exc
        if not isinstance(payload, dict) or payload.get("schema_version") != 1 or not isinstance(payload.get("records"), dict):
            raise PositionIdentityError("snapshot envelope is invalid")
        records = payload["records"]
        for record_id, record in records.items():
            self.validate_record(record)
            if record_id != record["record_id"]:
                raise PositionIdentityError("snapshot key does not match record_id")
        return records

    def upsert(self, record: Dict[str, Any]) -> Path:
        self.validate_record(record)
        with self._lock:
            records = self._read()
            existing = records.get(record["record_id"])
            if existing is not None:
                changed = [key for key in IMMUTABLE_FIELDS if existing[key] != record[key]]
                if changed:
                    raise PositionIdentityError(f"immutable identity fields changed: {sorted(changed)}")
                if LIFECYCLE_ORDER[record["lifecycle_state"]] < LIFECYCLE_ORDER[existing["lifecycle_state"]]:
                    raise PositionIdentityError("lifecycle regression")
                if _utc_time(record["last_observed_utc"]) < _utc_time(existing["last_observed_utc"]):
                    raise PositionIdentityError("last observation regressed")
            records[record["record_id"]] = dict(record)
            payload = {"schema_version": 1, "records": records}
            rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(f"{self.path.name}.tmp.{os.getpid()}")
            with temporary.open("w", encoding="utf-8") as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            return self.path

    def resolve_open(self, symbol: str, side: str) -> Dict[str, Any] | None:
        matches = [
            record for record in self._read().values()
            if record["symbol"] == symbol and record["side"] == side
            and record["lifecycle_state"] == "OPEN"
        ]
        if len(matches) > 1:
            raise PositionIdentityError("ambiguous open position identity")
        return dict(matches[0]) if matches else None

    def validate_file(self) -> Dict[str, Any]:
        records = self._read()
        raw = self.path.read_bytes() if self.path.exists() else b""
        return {"records": len(records), "sha256": hashlib.sha256(raw).hexdigest()}
