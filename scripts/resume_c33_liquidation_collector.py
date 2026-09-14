#!/usr/bin/env python3
"""Resume the pinned C-33 collector only after exact source-blob verification."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from requests import RequestException
from websockets.exceptions import ConnectionClosed

try:
    from scripts.collect_c33_liquidation_events import (
        InvalidC33Event,
        activate,
        append_record,
        collect,
        lifecycle_record,
    )
except ModuleNotFoundError:  # Direct ``python scripts/...`` execution.
    from collect_c33_liquidation_events import (
        InvalidC33Event,
        activate,
        append_record,
        collect,
        lifecycle_record,
    )


COLLECTOR_PATH = "scripts/collect_c33_liquidation_events.py"
MAX_RECONNECT_DELAY_SECONDS = 60
MINIMUM_STALE_SESSION_MS = 15 * 60 * 1000


def recover_stale_session(
    output: Path,
    activation_boundary: int,
    expected_session_id: str,
    *,
    now_ms: int | None = None,
    monotonic_ns: int | None = None,
) -> dict[str, object]:
    """Close one externally-proven-dead session without making the missing interval eligible."""

    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    monotonic_ns = time.monotonic_ns() if monotonic_ns is None else int(monotonic_ns)
    if not expected_session_id or not output.exists():
        raise InvalidC33Event("stale-session recovery input is invalid")
    states: dict[str, set[str]] = {}
    latest_ms = 0
    timestamp_fields = {
        "session": "timestamp_ms",
        "heartbeat": "server_time_ms",
        "kline_close": "open_time_ms",
        "liquidation": "trade_time_ms",
    }
    for line in output.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise InvalidC33Event("ledger contains malformed JSON") from error
        record_type = row.get("record_type")
        field = timestamp_fields.get(str(record_type))
        timestamp = row.get(field) if field else None
        if not isinstance(timestamp, int):
            raise InvalidC33Event("ledger timestamp is invalid")
        latest_ms = max(latest_ms, timestamp)
        if record_type == "session":
            session_id, state = row.get("session_id"), row.get("state")
            if not isinstance(session_id, str) or state not in ("STARTED", "ENDED"):
                raise InvalidC33Event("ledger session lifecycle is invalid")
            states.setdefault(session_id, set()).add(state)
    active = sorted(
        session_id
        for session_id, values in states.items()
        if "STARTED" in values and "ENDED" not in values
    )
    if active != [expected_session_id]:
        raise InvalidC33Event("expected session is not the sole active ledger session")
    if now_ms - latest_ms < MINIMUM_STALE_SESSION_MS:
        raise InvalidC33Event("active ledger session is not stale")
    record = lifecycle_record(expected_session_id, "ENDED", now_ms, monotonic_ns)
    if not append_record(output, record, activation_boundary):
        raise InvalidC33Event("stale-session closure was not appended")
    return {
        "candidate": "C-33",
        "status": "STALE_SESSION_CLOSED",
        "session_id": expected_session_id,
        "previous_latest_ms": latest_ms,
        "closed_at_ms": now_ms,
        "missing_interval_policy": "INELIGIBLE_NO_BACKFILL",
    }


def resolve_pinned_commit(
    manifest_path: Path,
    git_output: Callable[[list[str]], str] | None = None,
) -> str:
    if git_output is None:
        def git_output(arguments: list[str]) -> str:
            return subprocess.run(
                ["git", *arguments], check=True, capture_output=True, text=True
            ).stdout.strip()
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidC33Event("activation manifest is unreadable") from error
    pinned = manifest.get("collector_commit")
    if not isinstance(pinned, str) or not pinned:
        raise InvalidC33Event("activation manifest collector commit is invalid")
    current_blob = git_output(["rev-parse", f"HEAD:{COLLECTOR_PATH}"])
    pinned_blob = git_output(["rev-parse", f"{pinned}:{COLLECTOR_PATH}"])
    if not current_blob or current_blob != pinned_blob:
        raise InvalidC33Event("collector source differs from the activation commit")
    return pinned


async def supervise(
    output: Path,
    activation_boundary: int,
    *,
    collect_fn: Callable[[Path, int], object] = collect,
    sleep_fn: Callable[[float], object] = asyncio.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
    max_attempts: int | None = None,
) -> None:
    """Restart clean sessions after transient public-network failures."""
    delay = 1
    attempts = 0
    while max_attempts is None or attempts < max_attempts:
        attempts += 1
        started = monotonic_fn()
        try:
            await collect_fn(output, activation_boundary)  # type: ignore[misc]
        except (OSError, asyncio.TimeoutError, RequestException, ConnectionClosed) as error:
            print(json.dumps({
                "event": "c33_transient_disconnect",
                "attempt": attempts,
                "error_type": type(error).__name__,
                "error": str(error),
            }, sort_keys=True), file=sys.stderr, flush=True)
        if monotonic_fn() - started >= 300:
            delay = 1
        await sleep_fn(delay)  # type: ignore[misc]
        delay = min(delay * 2, MAX_RECONNECT_DELAY_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/research/c33/events.jsonl"))
    parser.add_argument(
        "--activation-manifest", type=Path, default=Path("data/research/c33/activation_manifest.json")
    )
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--recover-stale-session-id")
    parser.add_argument("--confirm-no-process", action="store_true")
    parser.add_argument("--recover-only", action="store_true")
    args = parser.parse_args()
    if args.recover_only:
        if not args.recover_stale_session_id or not args.confirm_no_process:
            raise SystemExit("stale recovery requires exact session id and confirmed no process")
        manifest = json.loads(args.activation_manifest.read_text(encoding="utf-8"))
        result = recover_stale_session(
            args.output,
            int(manifest["activation_boundary"]),
            args.recover_stale_session_id,
        )
        print(json.dumps(result, sort_keys=True))
        return
    if not args.enable_network:
        raise SystemExit("network collection is fail-closed; pass --enable-network explicitly")
    pinned = resolve_pinned_commit(args.activation_manifest)
    manifest = activate(args.activation_manifest, args.output, commit=pinned)
    asyncio.run(supervise(args.output, int(manifest["activation_boundary"])))


if __name__ == "__main__":
    main()
