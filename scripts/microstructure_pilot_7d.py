"""Public, outcome-free BTC/ETH depth integrity capture for a frozen 7-day pilot.

No account credentials, broker dependency, trading route, or derived signal.
The program refuses to run without a pre-recorded activation manifest.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any
from uuid import uuid4

import aiohttp
import websockets


SYMBOLS = ("BTCUSDT", "ETHUSDT")
WS_BASE = "wss://fstream.binance.com/public/ws"
REST_BASE = "https://fapi.binance.com/fapi/v1/depth"
MIN_FREE_BYTES = 10 * 1024**3
CONTRACT = Path(__file__).resolve().parents[1] / "docs/MICROSTRUCTURE_DATA_PILOT_7D_CONTRACT.md"


def number(value: Any, *, positive: bool) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("invalid numeric book field") from exc
    if not result.is_finite() or (result <= 0 if positive else result < 0):
        raise ValueError("invalid numeric book field")
    return result


@dataclass
class Book:
    """Mechanical snapshot+diff state; no predictive features or price outcomes."""

    bids: dict[Decimal, Decimal] = field(default_factory=dict)
    asks: dict[Decimal, Decimal] = field(default_factory=dict)
    last_u: int | None = None
    snapshot_id: int | None = None
    valid: bool = False
    duplicates: int = 0
    out_of_order: int = 0
    gaps: int = 0
    last_event: dict[str, Any] | None = None

    def invalidate(self) -> None:
        self.valid = False
        self.last_u = None
        self.snapshot_id = None
        self.bids.clear()
        self.asks.clear()
        self.last_event = None

    def snapshot(self, data: dict[str, Any]) -> None:
        self.invalidate()
        snapshot_id = int(data["lastUpdateId"])
        if snapshot_id < 0:
            raise ValueError("negative snapshot id")
        bids = self._levels(data["bids"])
        asks = self._levels(data["asks"])
        self._quotes(bids, asks)
        self.bids, self.asks, self.snapshot_id = bids, asks, snapshot_id

    @staticmethod
    def _levels(rows: Any) -> dict[Decimal, Decimal]:
        result: dict[Decimal, Decimal] = {}
        if not isinstance(rows, list):
            raise ValueError("levels must be a list")
        for row in rows:
            if not isinstance(row, list) or len(row) != 2:
                raise ValueError("malformed level")
            price, qty = number(row[0], positive=True), number(row[1], positive=False)
            if qty:
                result[price] = qty
            else:
                result.pop(price, None)
        return result

    @staticmethod
    def _quotes(bids: dict[Decimal, Decimal], asks: dict[Decimal, Decimal]) -> None:
        if not bids or not asks or max(bids) >= min(asks):
            raise ValueError("empty or crossed book")

    def update(self, event: dict[str, Any]) -> str:
        first, last, previous = (int(event[k]) for k in ("U", "u", "pu"))
        if first < 0 or last < first or previous < 0:
            self.invalidate()
            raise ValueError("invalid update identifiers")
        if self.snapshot_id is None:
            return "unbootstrapped"
        if not self.valid:
            if last < self.snapshot_id:
                return "pre_snapshot"
            if not first <= self.snapshot_id <= last:
                self.gaps += 1
                self.invalidate()
                return "gap"
            status = "bridge"
        elif last == self.last_u:
            if event == self.last_event:
                self.duplicates += 1
                return "duplicate"
            self.out_of_order += 1
            self.gaps += 1
            self.invalidate()
            return "conflicting_duplicate"
        elif last < self.last_u:
            self.out_of_order += 1
            self.gaps += 1
            self.invalidate()
            return "out_of_order"
        elif previous != self.last_u:
            self.gaps += 1
            self.invalidate()
            return "gap"
        else:
            status = "applied"

        bids, asks = self.bids.copy(), self.asks.copy()
        try:
            for target, rows in ((bids, event["b"]), (asks, event["a"])):
                if not isinstance(rows, list):
                    raise ValueError("malformed update levels")
                for row in rows:
                    if not isinstance(row, list) or len(row) != 2:
                        raise ValueError("malformed update level")
                    price, qty = number(row[0], positive=True), number(row[1], positive=False)
                    if qty:
                        target[price] = qty
                    else:
                        target.pop(price, None)
            self._quotes(bids, asks)
        except (KeyError, ValueError):
            self.gaps += 1
            self.invalidate()
            return "invalid_book"
        self.bids, self.asks, self.last_u, self.valid = bids, asks, last, True
        self.last_event = event
        return status


class RawCapture:
    """Exclusive gzip chunks; finalized chunks are hashed and never reopened."""

    def __init__(self, root: Path, symbol: str, session: str):
        self.root, self.symbol, self.session = root, symbol, session
        self.root.mkdir(parents=True, exist_ok=True)
        self.index = 0
        self.handle = None
        self.path: Path | None = None
        self.count = 0
        self.files: list[dict[str, Any]] = []
        self.bounds: dict[str, list[int]] = {}

    def _open(self) -> None:
        self.index += 1
        self.path = self.root / f"{self.symbol}-{self.session}-{self.index:04d}.jsonl.gz"
        self.handle = gzip.open(self.path, "xb", compresslevel=6)
        self.count = 0
        self.bounds = {}

    def append(self, kind: str, payload: bytes | None, **fields: Any) -> tuple[int, int]:
        if self.handle is None:
            self._open()
        wall_ns, mono_ns = time.time_ns(), time.monotonic_ns()
        record = {"kind": kind, "symbol": self.symbol, "session": self.session,
                  "receipt_utc_ns": wall_ns, "receipt_monotonic_ns": mono_ns,
                  "payload_b64": base64.b64encode(payload).decode("ascii") if payload is not None else None,
                  **fields}
        self.handle.write((json.dumps(record, separators=(",", ":")) + "\n").encode())
        self.count += 1
        for key, value in (("receipt_utc_ns", wall_ns), ("receipt_monotonic_ns", mono_ns)):
            bounds = self.bounds.setdefault(key, [value, value])
            bounds[0], bounds[1] = min(bounds[0], value), max(bounds[1], value)
        if payload is not None:
            try:
                source = json.loads(payload)
                for key in ("E", "T", "U", "u", "pu", "lastUpdateId"):
                    if key in source:
                        value = int(source[key])
                        bounds = self.bounds.setdefault(key, [value, value])
                        bounds[0], bounds[1] = min(bounds[0], value), max(bounds[1], value)
            except (ValueError, TypeError, AttributeError):
                pass  # Raw bytes remain preserved; schema failure is handled by caller.
        if self.count >= 9000:  # At most ~15 minutes at ten updates/second.
            self.finalize_chunk()
        return wall_ns, mono_ns

    def finalize_chunk(self) -> None:
        if self.handle is None:
            return
        self.handle.close()
        assert self.path is not None
        fd = os.open(self.path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        digest = hashlib.sha256()
        with self.path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        self.files.append({"path": str(self.path), "sha256": digest.hexdigest(),
                           "bytes": self.path.stat().st_size, "records": self.count,
                           "bounds": self.bounds})
        self.handle = None

    def close(self) -> list[dict[str, Any]]:
        self.finalize_chunk()
        return self.files


def save_manifest(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    with temporary.open("x") as output:
        json.dump(state, output, indent=2, sort_keys=True)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


async def capture_symbol(symbol: str, root: Path, stop_ns: int, manifest: dict[str, Any]) -> None:
    attempts = 0
    while time.time_ns() < stop_ns:
        if shutil.disk_usage(root).free < MIN_FREE_BYTES:
            manifest["failures"].append({"symbol": symbol, "reason": "disk_reserve", "utc_ns": time.time_ns()})
            break
        session_id = uuid4().hex
        raw = RawCapture(root / "raw" / symbol, symbol, session_id)
        book = Book()
        epoch: dict[str, Any] = {"symbol": symbol, "session": session_id,
                                  "start_utc_ns": time.time_ns(), "events": 0,
                                  "snapshots": 0, "applied": 0, "gaps": [], "errors": [],
                                  "status": "RUNNING"}
        manifest["sessions"].append(epoch)
        save_manifest(root / "capture_manifest.json", manifest)
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as http:
                uri = f"{WS_BASE}/{symbol.lower()}@depth@100ms"
                async with websockets.connect(uri, open_timeout=10, close_timeout=3,
                                              max_size=4 * 1024 * 1024, max_queue=4096) as ws:
                    async def get_snapshot() -> tuple[bytes, dict[str, Any], int, int]:
                        req_ns = time.time_ns()
                        async with http.get(REST_BASE, params={"symbol": symbol, "limit": 1000}) as response:
                            response.raise_for_status()
                            payload = await response.read()
                        received_ns = time.time_ns()
                        return payload, json.loads(payload), req_ns, received_ns

                    snapshot_task = asyncio.create_task(get_snapshot())
                    buffered: list[dict[str, Any]] = []
                    bootstrapped = False
                    previous_clock_offset_ns: int | None = None
                    while time.time_ns() < stop_ns:
                        timeout = min(15.0, max(.1, (stop_ns - time.time_ns()) / 1e9))
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=timeout)
                        except asyncio.TimeoutError:
                            if time.time_ns() >= stop_ns:
                                break
                            raise RuntimeError("stale_depth_stream")
                        payload = message.encode() if isinstance(message, str) else message
                        receipt_ns, receipt_mono_ns = raw.append("depth", payload)
                        epoch["events"] += 1
                        offset_ns = receipt_ns - receipt_mono_ns
                        if previous_clock_offset_ns is not None and abs(offset_ns - previous_clock_offset_ns) > 1_000_000_000:
                            raise RuntimeError("local_clock_jump")
                        previous_clock_offset_ns = offset_ns
                        if epoch["events"] % 1000 == 0 and shutil.disk_usage(root).free < MIN_FREE_BYTES:
                            raise RuntimeError("disk_reserve")
                        if len(raw.files) != len(epoch.get("files", [])):
                            epoch["files"] = raw.files.copy()
                            save_manifest(root / "capture_manifest.json", manifest)
                        event = json.loads(payload)
                        if event.get("e") != "depthUpdate" or event.get("s") != symbol:
                            raise ValueError("unexpected depth event")
                        for field in ("E", "T"):
                            source_ms = int(event[field])
                            if source_ms < 0 or source_ms > receipt_ns // 1_000_000 + 5000:
                                raise ValueError(f"invalid_or_future_exchange_{field}")
                        if not bootstrapped:
                            buffered.append(event)
                            if not snapshot_task.done():
                                continue
                            snap_raw, snapshot, request_ns, receive_ns = snapshot_task.result()
                            raw.append("snapshot", snap_raw, request_utc_ns=request_ns,
                                       response_utc_ns=receive_ns)
                            epoch["snapshots"] += 1
                            book.snapshot(snapshot)
                            bootstrapped = True
                            pending, buffered = buffered, []
                        else:
                            pending = [event]
                        for item in pending:
                            status = book.update(item)
                            if status in ("bridge", "applied"):
                                epoch["applied"] += 1
                                epoch.setdefault("valid_start_utc_ns", time.time_ns())
                                epoch["last_valid_event_utc_ns"] = time.time_ns()
                            elif status in ("gap", "out_of_order", "conflicting_duplicate", "invalid_book"):
                                epoch["gaps"].append({"utc_ns": time.time_ns(), "status": status,
                                                       "U": item.get("U"), "u": item.get("u"),
                                                       "pu": item.get("pu")})
                                raise RuntimeError(f"rebootstrap:{status}")
                    if not snapshot_task.done():
                        snapshot_task.cancel()
        except Exception as exc:
            epoch["errors"].append({"utc_ns": time.time_ns(), "error": type(exc).__name__,
                                    "detail": str(exc)[:200]})
            raw.append("collector_error", None, error=type(exc).__name__, detail=str(exc)[:200])
        finally:
            epoch["stop_utc_ns"] = time.time_ns()
            epoch["book_valid_at_stop"] = book.valid
            epoch["duplicates"] = book.duplicates
            epoch["out_of_order"] = book.out_of_order
            epoch["files"] = raw.close()
            epoch["status"] = "CLOSED"
            save_manifest(root / "capture_manifest.json", manifest)
        attempts += 1
        if time.time_ns() < stop_ns:
            await asyncio.sleep(min(30, 2**min(attempts, 4)))


async def run(activation_path: Path) -> None:
    activation = json.loads(activation_path.read_text())
    if activation["symbols"] != list(SYMBOLS):
        raise ValueError("activation symbols mismatch")
    if activation["contract_sha256"] != hashlib.sha256(CONTRACT.read_bytes()).hexdigest():
        raise ValueError("frozen contract hash mismatch")
    start_ns = int(activation["start_utc_ns"])
    stop_ns = int(activation["stop_utc_ns"])
    if stop_ns - start_ns != 7 * 86400 * 10**9 or start_ns % (86400 * 10**9):
        raise ValueError("activation must span seven complete UTC days")
    if time.time_ns() >= stop_ns:
        raise ValueError("pilot boundary already elapsed")
    root = Path(activation["output_root"]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock_handle = (root / "pilot.lock").open("a+")
    fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if shutil.disk_usage(root).free < MIN_FREE_BYTES:
        raise RuntimeError("insufficient disk reserve")
    manifest_path = root / "capture_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest["activation"] != activation or "completed_utc_ns" in manifest:
            raise ValueError("activation mismatch or already completed")
        for session in manifest["sessions"]:
            if session.get("status") == "RUNNING":
                session["status"] = "INTERRUPTED_UNOBSERVED_GAP"
                session["interruption_detected_utc_ns"] = time.time_ns()
            for item in session.get("files", []):
                source = Path(item["path"])
                if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != item["sha256"]:
                    raise ValueError("finalized raw hash mismatch on restart")
        listed = {item["path"] for session in manifest["sessions"] for item in session.get("files", [])}
        orphans = sorted(str(path) for path in (root / "raw").rglob("*.jsonl.gz") if str(path) not in listed)
        manifest["failures"].append({"reason": "collector_restart", "utc_ns": time.time_ns(),
                                     "unfinalized_raw_chunks": orphans})
    else:
        manifest = {"activation": activation, "sessions": [], "failures": [],
                    "created_utc_ns": time.time_ns()}
    save_manifest(manifest_path, manifest)
    while time.time_ns() < start_ns:
        await asyncio.sleep(min(30, (start_ns - time.time_ns()) / 1e9))
    await asyncio.gather(*(capture_symbol(symbol, root, stop_ns, manifest) for symbol in SYMBOLS))
    manifest["completed_utc_ns"] = time.time_ns()
    save_manifest(manifest_path, manifest)
    lock_handle.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activation", required=True, type=Path)
    asyncio.run(run(parser.parse_args().activation))
