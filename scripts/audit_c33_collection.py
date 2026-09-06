#!/usr/bin/env python3
"""Read-only integrity and completed-bucket audit for the prospective C-33 cohort."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from scripts.collect_c33_liquidation_events import BOUNDARY, SYMBOLS
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from collect_c33_liquidation_events import BOUNDARY, SYMBOLS


FIVE_MINUTES_MS = 300_000
ONE_MINUTE_MS = 60_000
TIMESTAMP_FIELD = {
    "session": "timestamp_ms",
    "heartbeat": "server_time_ms",
    "kline_close": "open_time_ms",
    "liquidation": "trade_time_ms",
}


class InvalidC33Ledger(ValueError):
    """The active C-33 cohort cannot be trusted."""


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidC33Ledger(f"cannot read valid JSON from {path}") from error
    if not isinstance(value, dict):
        raise InvalidC33Ledger(f"{path} must contain an object")
    return value


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise InvalidC33Ledger(f"cannot read {path}") from error
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise InvalidC33Ledger(f"malformed JSON on line {number}") from error
        if not isinstance(row, dict):
            raise InvalidC33Ledger(f"line {number} is not an object")
        rows.append(row)
    return rows


def _verify_raw(row: dict[str, Any]) -> None:
    if row["record_type"] == "session":
        return
    try:
        raw = base64.b64decode(row["raw_base64"], validate=True)
    except (KeyError, ValueError) as error:
        raise InvalidC33Ledger("record raw bytes are missing or invalid") from error
    if hashlib.sha256(raw).hexdigest() != row.get("raw_sha256"):
        raise InvalidC33Ledger("record raw SHA-256 mismatch")


def audit(manifest_path: Path, events_path: Path | None = None) -> dict[str, Any]:
    manifest = _load_object(manifest_path)
    required = {
        "candidate": "C-33",
        "protocol": "edge-candidate-register-v32",
        "candidate_boundary": BOUNDARY,
        "historical_import_allowed": False,
    }
    if any(manifest.get(key) != value for key, value in required.items()):
        raise InvalidC33Ledger("activation manifest violates the frozen C-33 contract")
    activation = manifest.get("activation_boundary")
    if not isinstance(activation, int) or activation <= BOUNDARY:
        raise InvalidC33Ledger("activation boundary is invalid")
    configured_output = Path(str(manifest.get("output", "")))
    if events_path is None:
        events_path = configured_output
    elif str(events_path) != str(configured_output):
        raise InvalidC33Ledger("event path differs from the activation manifest")

    rows = _load_rows(events_path)
    keys: set[str] = set()
    sessions: dict[str, dict[str, int | None]] = {}
    heartbeats: set[tuple[str, int]] = set()
    klines: set[tuple[str, str, int]] = set()
    liquidations: list[dict[str, Any]] = []
    latest_ms = 0
    completion_watermark_ms = 0
    counts: Counter[str] = Counter()

    for row in rows:
        record_type = row.get("record_type")
        if record_type not in TIMESTAMP_FIELD:
            raise InvalidC33Ledger("unknown record type")
        key = row.get("key")
        if not isinstance(key, str) or not key or key in keys:
            raise InvalidC33Ledger("missing or duplicate record key")
        keys.add(key)
        session_id = row.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise InvalidC33Ledger("record session identity is missing")
        field = TIMESTAMP_FIELD[record_type]
        timestamp = row.get(field)
        if not isinstance(timestamp, int) or timestamp // 1000 <= activation:
            raise InvalidC33Ledger("record is at or before the activation boundary")
        latest_ms = max(latest_ms, timestamp)
        if record_type == "kline_close" and isinstance(row.get("close_time_ms"), int):
            completion_watermark_ms = max(completion_watermark_ms, row["close_time_ms"] + 1)
        elif record_type == "heartbeat":
            completion_watermark_ms = max(completion_watermark_ms, timestamp)
        counts[record_type] += 1
        _verify_raw(row)

        if record_type == "session":
            state = row.get("state")
            if state not in ("STARTED", "ENDED"):
                raise InvalidC33Ledger("invalid session lifecycle state")
            lifecycle = sessions.setdefault(session_id, {"start": None, "end": None})
            target = "start" if state == "STARTED" else "end"
            if lifecycle[target] is not None:
                raise InvalidC33Ledger("duplicate session lifecycle state")
            lifecycle[target] = timestamp
        elif record_type == "heartbeat":
            minute = row.get("minute_ms")
            if not isinstance(minute, int) or minute != timestamp // ONE_MINUTE_MS * ONE_MINUTE_MS:
                raise InvalidC33Ledger("heartbeat minute is invalid")
            heartbeats.add((session_id, minute))
        elif record_type == "kline_close":
            symbol, open_ms = row.get("symbol"), row.get("open_time_ms")
            if symbol not in SYMBOLS or open_ms % ONE_MINUTE_MS:
                raise InvalidC33Ledger("kline universe or timestamp is invalid")
            klines.add((session_id, symbol, open_ms))
        else:
            if row.get("symbol") not in SYMBOLS or row.get("side") not in ("BUY", "SELL"):
                raise InvalidC33Ledger("liquidation universe or side is invalid")
            liquidations.append(row)

    if not sessions or any(value["start"] is None for value in sessions.values()):
        raise InvalidC33Ledger("session STARTED lifecycle is missing")
    for lifecycle in sessions.values():
        if lifecycle["end"] is not None and lifecycle["end"] < lifecycle["start"]:
            raise InvalidC33Ledger("session lifecycle is out of order")

    bucket_starts: set[int] = set()
    for _, minute in heartbeats:
        bucket_starts.add(minute // FIVE_MINUTES_MS * FIVE_MINUTES_MS)
    for _, _, minute in klines:
        bucket_starts.add(minute // FIVE_MINUTES_MS * FIVE_MINUTES_MS)

    eligible: list[int] = []
    missing_reasons: Counter[str] = Counter()
    bucket_session: dict[int, str] = {}
    for start in sorted(bucket_starts):
        end = start + FIVE_MINUTES_MS
        if end > completion_watermark_ms:
            continue
        qualifying = []
        for session_id, lifecycle in sessions.items():
            session_start = int(lifecycle["start"])
            session_end = lifecycle["end"]
            if session_start <= start and (session_end is None or int(session_end) >= end):
                qualifying.append(session_id)
        if len(qualifying) != 1:
            missing_reasons["uninterrupted_session"] += 1
            continue
        session_id = qualifying[0]
        minutes = range(start, end, ONE_MINUTE_MS)
        if any((session_id, minute) not in heartbeats for minute in minutes):
            missing_reasons["heartbeat"] += 1
            continue
        if any((session_id, symbol, minute) not in klines for minute in minutes for symbol in SYMBOLS):
            missing_reasons["kline"] += 1
            continue
        eligible.append(start)
        bucket_session[start] = session_id

    aggregates: dict[tuple[int, str, str], dict[str, float | int]] = defaultdict(
        lambda: {"observed_count": 0, "observed_notional": 0.0}
    )
    eligible_set = set(eligible)
    for row in liquidations:
        bucket = row["trade_time_ms"] // FIVE_MINUTES_MS * FIVE_MINUTES_MS
        if bucket not in eligible_set or row["session_id"] != bucket_session[bucket]:
            continue
        target = aggregates[(bucket, row["symbol"], row["side"])]
        target["observed_count"] += 1
        target["observed_notional"] += float(row["observed_notional"])

    liquidation_totals = [
        {"bucket_start_ms": bucket, "symbol": symbol, "side": side, **values}
        for (bucket, symbol, side), values in sorted(aggregates.items())
    ]
    active_sessions = sum(value["end"] is None for value in sessions.values())
    return {
        "candidate": "C-33",
        "verdict": "COLLECTING",
        "activation_boundary": activation,
        "record_counts": dict(sorted(counts.items())),
        "session_count": len(sessions),
        "active_session_count": active_sessions,
        "latest_record_ms": latest_ms,
        "eligible_completed_bucket_count": len(eligible),
        "ineligible_completed_bucket_reasons": dict(sorted(missing_reasons.items())),
        "eligible_bucket_starts_ms": eligible,
        "eligible_liquidation_totals": liquidation_totals,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation-manifest", type=Path, default=Path("data/research/c33/activation_manifest.json"))
    parser.add_argument("--events", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.activation_manifest, args.events), sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
