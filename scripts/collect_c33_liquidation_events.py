#!/usr/bin/env python3
"""Append-only C-33 liquidation/liveness collector; no broker or order imports."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import math
import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import requests
import websockets


BOUNDARY = 1788678803
SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT")
STREAM_URL = "wss://fstream.binance.com/market/stream?streams="
SERVER_TIME_URL = "https://fapi.binance.com/fapi/v1/time"


class InvalidC33Event(ValueError):
    """A fail-closed C-33 event rejection."""


def _positive(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise InvalidC33Event(f"{field} must be numeric") from error
    if not math.isfinite(result) or result <= 0:
        raise InvalidC33Event(f"{field} must be finite and positive")
    return result


def _integer(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise InvalidC33Event(f"{field} must be an integer") from error


def _raw_fields(raw: bytes) -> dict[str, str]:
    return {
        "raw_base64": base64.b64encode(raw).decode("ascii"),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
    }


def parse_stream_message(raw: bytes, *, receipt_monotonic_ns: int, session_id: str) -> dict[str, Any] | None:
    if receipt_monotonic_ns <= 0 or not session_id:
        raise InvalidC33Event("receipt and session identity are required")
    try:
        envelope = json.loads(raw)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InvalidC33Event("stream message is not valid JSON") from error
    if not isinstance(envelope, dict):
        raise InvalidC33Event("stream message must be an object")
    payload = envelope.get("data", envelope)
    if not isinstance(payload, dict):
        raise InvalidC33Event("stream payload must be an object")
    event_type = payload.get("e")

    common = {"session_id": session_id, "receipt_monotonic_ns": receipt_monotonic_ns, **_raw_fields(raw)}
    if event_type == "forceOrder":
        order = payload.get("o")
        if not isinstance(order, dict):
            raise InvalidC33Event("liquidation order is missing")
        symbol, pair = order.get("s"), payload.get("ps")
        side = order.get("S")
        trade_time = _integer(order.get("T"), "trade time")
        event_time = _integer(payload.get("E"), "event time")
        quantity = _positive(order.get("z"), "filled quantity")
        average_price = _positive(order.get("ap"), "average price")
        if payload.get("st") != 1:
            raise InvalidC33Event("event is not USD-M")
        if symbol not in SYMBOLS or pair != symbol:
            raise InvalidC33Event("symbol or pair is outside frozen universe")
        if side not in ("BUY", "SELL") or order.get("X") != "FILLED":
            raise InvalidC33Event("side or fill status is invalid")
        if trade_time // 1000 <= BOUNDARY or event_time < trade_time:
            raise InvalidC33Event("event is pre-boundary or causally invalid")
        key = f"liquidation:1:{symbol}:{side}:{trade_time}:{order.get('z')}:{order.get('ap')}"
        return {
            "record_type": "liquidation",
            "key": key,
            "event_time_ms": event_time,
            "trade_time_ms": trade_time,
            "symbol": symbol,
            "side": side,
            "filled_quantity": quantity,
            "average_price": average_price,
            "observed_notional": quantity * average_price,
            "snapshot_censored": True,
            **common,
        }

    if event_type == "kline":
        kline = payload.get("k")
        if not isinstance(kline, dict):
            raise InvalidC33Event("kline payload is missing")
        if not kline.get("x"):
            return None
        symbol = kline.get("s") or payload.get("s")
        open_time = _integer(kline.get("t"), "kline open time")
        close_time = _integer(kline.get("T"), "kline close time")
        if symbol not in SYMBOLS or kline.get("i") != "1m":
            raise InvalidC33Event("kline is outside frozen universe or interval")
        if open_time // 1000 <= BOUNDARY or open_time % 60_000 or close_time - open_time != 59_999:
            raise InvalidC33Event("kline boundary is invalid")
        open_price = _positive(kline.get("o"), "open")
        high_price = _positive(kline.get("h"), "high")
        low_price = _positive(kline.get("l"), "low")
        close_price = _positive(kline.get("c"), "close")
        if high_price < max(open_price, close_price) or low_price > min(open_price, close_price):
            raise InvalidC33Event("kline OHLC is inconsistent")
        return {
            "record_type": "kline_close",
            "key": f"kline:{symbol}:{open_time}",
            "event_time_ms": _integer(payload.get("E"), "event time"),
            "symbol": symbol,
            "open_time_ms": open_time,
            "close_time_ms": close_time,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            **common,
        }
    raise InvalidC33Event("unexpected stream event type")


def parse_heartbeat(raw: bytes, *, receipt_monotonic_ns: int, session_id: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InvalidC33Event("heartbeat is not valid JSON") from error
    if not isinstance(payload, dict):
        raise InvalidC33Event("heartbeat must be an object")
    server_time = _integer(payload.get("serverTime"), "server time")
    if server_time // 1000 <= BOUNDARY:
        raise InvalidC33Event("heartbeat is pre-boundary")
    minute = server_time // 60_000 * 60_000
    return {
        "record_type": "heartbeat",
        "key": f"heartbeat:{session_id}:{minute}",
        "session_id": session_id,
        "server_time_ms": server_time,
        "minute_ms": minute,
        "receipt_monotonic_ns": receipt_monotonic_ns,
        **_raw_fields(raw),
    }


def lifecycle_record(session_id: str, state: str, timestamp_ms: int, monotonic_ns: int) -> dict[str, Any]:
    if state not in ("STARTED", "ENDED") or timestamp_ms // 1000 <= BOUNDARY or monotonic_ns <= 0:
        raise InvalidC33Event("invalid lifecycle record")
    return {
        "record_type": "session",
        "key": f"session:{session_id}:{state}",
        "session_id": session_id,
        "state": state,
        "timestamp_ms": timestamp_ms,
        "receipt_monotonic_ns": monotonic_ns,
    }


def _validate_record_boundary(record: dict[str, Any]) -> None:
    field_by_type = {
        "liquidation": "trade_time_ms",
        "kline_close": "open_time_ms",
        "heartbeat": "server_time_ms",
        "session": "timestamp_ms",
    }
    field = field_by_type.get(record.get("record_type"))
    if field is None or _integer(record.get(field), field) // 1000 <= BOUNDARY:
        raise InvalidC33Event("record is unknown or pre-boundary")


def append_record(path: Path, record: dict[str, Any]) -> bool:
    key = str(record.get("key", ""))
    if not key:
        raise InvalidC33Event("record key is required")
    _validate_record_boundary(record)
    keys: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                existing = json.loads(line)
            except json.JSONDecodeError as error:
                raise InvalidC33Event("ledger contains malformed JSON") from error
            if not isinstance(existing, dict):
                raise InvalidC33Event("ledger contains a non-object record")
            _validate_record_boundary(existing)
            existing_key = str(existing.get("key", ""))
            if not existing_key or existing_key in keys:
                raise InvalidC33Event("ledger contains invalid or duplicate key")
            keys.add(existing_key)
    if key in keys:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    return True


def fetch_heartbeat(get: Callable[..., Any] = requests.get) -> bytes:
    response = get(SERVER_TIME_URL, timeout=10)
    response.raise_for_status()
    return bytes(response.content)


async def collect(output: Path) -> None:
    session_id = str(uuid.uuid4())
    append_record(output, lifecycle_record(session_id, "STARTED", int(time.time() * 1000), time.monotonic_ns()))
    streams = ["!forceOrder@arr", *(f"{symbol.lower()}@kline_1m" for symbol in SYMBOLS)]
    uri = STREAM_URL + "/".join(streams)
    try:
        async with websockets.connect(uri, ping_interval=60, ping_timeout=10, max_size=2**20) as socket:
            last_heartbeat_minute = None
            while True:
                raw_message = await asyncio.wait_for(socket.recv(), timeout=70)
                raw = raw_message.encode() if isinstance(raw_message, str) else bytes(raw_message)
                record = parse_stream_message(raw, receipt_monotonic_ns=time.monotonic_ns(), session_id=session_id)
                if record is not None:
                    append_record(output, record)
                current_minute = int(time.time()) // 60
                if current_minute != last_heartbeat_minute:
                    heartbeat_raw = await asyncio.to_thread(fetch_heartbeat)
                    heartbeat = parse_heartbeat(
                        heartbeat_raw, receipt_monotonic_ns=time.monotonic_ns(), session_id=session_id
                    )
                    append_record(output, heartbeat)
                    last_heartbeat_minute = current_minute
    finally:
        append_record(output, lifecycle_record(session_id, "ENDED", int(time.time() * 1000), time.monotonic_ns()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/research/c33/events.jsonl"))
    parser.add_argument("--enable-network", action="store_true")
    args = parser.parse_args()
    if not args.enable_network:
        raise SystemExit("network collection is fail-closed; pass --enable-network explicitly")
    asyncio.run(collect(args.output))


if __name__ == "__main__":
    main()
