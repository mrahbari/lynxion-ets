"""Execution Truth Ledger (ETL) — immutable, append-only per-order audit trail.

Every order that reaches the execution-safety boundary writes a record here *before*
any send is attempted, and a second linked record with the broker response/latency
after. The ledger is the single source of truth for "what did the system decide, in
what state, and what actually happened" for each order.

Guarantees:
  * **Append-only** — records are only ever appended; nothing is updated or deleted.
  * **Tamper-evident** — each record carries a SHA-256 hash chaining it to the
    previous record (``prev_hash`` + canonical JSON), so any after-the-fact edit
    breaks the chain and is detectable via :func:`verify`.
  * **Written before send** — the guard writes the ``decision`` record (with the full
    flag snapshot, decision trace and runtime states) strictly before invoking the
    broker send. Because the only code that sends orders does so through the guard's
    atomic ``authorize_and_send``, this record cannot be bypassed.
  * **Durable** — each append is flushed and fsync'd.

Storage is newline-delimited JSON (``logs/execution_truth_ledger.jsonl`` by default).
Import-time dependencies are standard-library only, so the ledger is independently
testable and adds no heavy coupling to the execution path.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_GENESIS = "0" * 64


def _project_root() -> str:
    # shared/execution_truth_ledger.py -> project root is two levels up.
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _default_path() -> str:
    env = os.getenv("EXECUTION_TRUTH_LEDGER_PATH")
    if env:
        return env
    return os.path.join(_project_root(), "logs", "execution_truth_ledger.jsonl")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


class ExecutionTruthLedger:
    """Append-only, hash-chained JSONL audit ledger (thread-safe)."""

    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path or _default_path()
        self._lock = threading.Lock()
        self._seq = 0
        self._last_hash = _GENESIS
        self._init_from_existing()

    @property
    def path(self) -> str:
        return self._path

    def _init_from_existing(self) -> None:
        """Resume the seq counter and hash chain from the last VALID record in the file.

        Robust to a corrupt/partial tail (e.g. from a killed process): we scan all lines
        and resume from the last parseable record carrying both ``seq`` and ``hash``,
        rather than resetting to genesis on a single bad line (which would duplicate seqs
        and break the chain for subsequent appends).
        """
        if not os.path.exists(self._path):
            return
        last_seq, last_hash = 0, _GENESIS
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue  # skip a corrupt/partial line; keep the last good one
                    if "seq" in rec and "hash" in rec:
                        last_seq, last_hash = int(rec["seq"]), rec["hash"]
        except Exception:
            pass
        self._seq, self._last_hash = last_seq, last_hash

    def append(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Append one immutable, hash-chained record and return it (with seq/hash)."""
        with self._lock:
            self._seq += 1
            body = {
                "seq": self._seq,
                "ts": _utc_now_iso(),
                "event": event,
                "prev_hash": self._last_hash,
                **payload,
            }
            body["hash"] = hashlib.sha256(
                (self._last_hash + _canonical(body)).encode("utf-8")
            ).hexdigest()
            self._write_line(body)
            self._last_hash = body["hash"]
            return body

    def _write_line(self, record: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        line = json.dumps(record, default=str) + "\n"
        # Open per-append in append mode so a crash can never truncate prior records,
        # and fsync so the record is durable BEFORE the caller proceeds to send.
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            try:
                os.fsync(f.fileno())
            except (OSError, ValueError):
                pass  # fsync unsupported on some mounts; the append itself still landed

    def new_order_ref(self) -> str:
        """Opaque id linking an order's decision record to its later result record."""
        return uuid.uuid4().hex

    def verify(self) -> Dict[str, Any]:
        """Re-read the ledger and verify the hash chain is intact (tamper detection)."""
        ok, count, broken_at = True, 0, None
        prev = _GENESIS
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    count += 1
                    stored = rec.get("hash")
                    recomputed = hashlib.sha256(
                        (prev + _canonical({k: v for k, v in rec.items() if k != "hash"})).encode("utf-8")
                    ).hexdigest()
                    if rec.get("prev_hash") != prev or stored != recomputed:
                        ok = False
                        broken_at = rec.get("seq")
                        break
                    prev = stored
        except FileNotFoundError:
            return {"ok": True, "records": 0, "broken_at": None}
        return {"ok": ok, "records": count, "broken_at": broken_at}

    def read_all(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        out.append(json.loads(line))
        except FileNotFoundError:
            pass
        return out


# Process-wide singleton — the canonical ledger the execution path writes to.
execution_truth_ledger = ExecutionTruthLedger()


__all__ = ["ExecutionTruthLedger", "execution_truth_ledger"]
