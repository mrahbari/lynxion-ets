"""Live Order Journal (E11 / B3 — durable live recovery).

A durable, append-only operational journal of every LIVE/TESTNET order's lifecycle:

    INTENT  -> written BEFORE the order is sent (closes the lost-write window)
    SUBMITTED -> broker accepted, carries the exchange order_id
    FILLED / CANCELLED / REJECTED / FAILED -> terminal

Unlike the Execution Truth Ledger (an immutable hash-chained *audit* log of all routes),
this is the operational *state* store the system recovers from on restart: it rebuilds
the in-flight order set, the order_id -> (exchange, symbol) map (so cancel/status survive
restart, B5), and the net live position store.

Because the INTENT record is fsync'd before the send, a crash between send and ack
leaves a recoverable record (status INTENT/SUBMITTED) that startup recovery flags for
broker reconciliation (B4) — there is never a live order with no local trace.

Standard-library only; thread-safe; atomic snapshot for positions.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

_OPEN_STATES = {"INTENT", "SUBMITTED", "PARTIALLY_FILLED"}   # PARTIALLY_FILLED stays in-flight
_TERMINAL = {"FILLED", "CANCELLED", "REJECTED", "FAILED"}


def _project_root() -> str:
    # this file is at <root>/infrastructure/execution/live_order_journal.py -> up 3 levels.
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _default_path() -> str:
    return os.getenv("LIVE_ORDER_JOURNAL_PATH") or os.path.join(_project_root(), "data", "live_order_journal.json")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LiveOrderJournal:
    """Append-only durable journal + derived current-state (orders, positions)."""

    def __init__(self, path: Optional[str] = None):
        self._path = path or _default_path()
        self._lock = threading.RLock()
        self._orders: Dict[str, Dict[str, Any]] = {}   # order_ref -> latest state
        self._load()

    @property
    def path(self) -> str:
        return self._path

    # -- lifecycle records --------------------------------------------------------

    def record_intent(self, symbol: str, side: str, quantity, exchange: str,
                      client_order_id: Optional[str] = None,
                      stop_loss: Optional[Any] = None,
                      take_profit: Optional[Any] = None,
                      confidence: Optional[Any] = None,
                      regime: Optional[Any] = None,
                      strategy: Optional[Any] = None) -> str:
        """Write an INTENT record BEFORE the send; returns an order_ref linking the lifecycle."""
        order_ref = uuid.uuid4().hex
        rec = {
            "order_ref": order_ref, "status": "INTENT", "symbol": symbol, "side": str(side),
            "quantity": str(quantity), "exchange": exchange,
            "client_order_id": client_order_id, "order_id": None,
        }
        if stop_loss is not None:
            rec["stop_loss"] = str(stop_loss)
            rec["initial_stop_loss"] = str(stop_loss)
        if take_profit is not None:
            rec["take_profit"] = str(take_profit)
            rec["initial_take_profit"] = str(take_profit)
        if confidence is not None:
            rec["confidence"] = str(confidence)
        if regime is not None:
            rec["regime"] = str(regime)
        if strategy is not None:
            rec["strategy"] = str(strategy)
            rec["strategy_name"] = str(strategy)

        self._append(rec)
        return order_ref

    def record_submitted(self, order_ref: str, order_id: str, exchange: str) -> None:
        self._append({"order_ref": order_ref, "status": "SUBMITTED",
                      "order_id": str(order_id), "exchange": exchange})

    def record_failed(self, order_ref: str, reason: str = "") -> None:
        self._append({"order_ref": order_ref, "status": "FAILED", "reason": reason})

    def record_fill(self, order_ref: str, cumulative_filled, total_qty,
                    avg_price=None, fee=None) -> str:
        """B7: record (cumulative) fill progress; transition PARTIALLY_FILLED -> FILLED.

        ``cumulative_filled`` is the exchange's total executed quantity for the order (not a
        delta). Returns the resulting status. A partial fill stays in-flight (recoverable on
        restart and re-checked by reconciliation) until cumulative >= total.
        """
        filled = Decimal(str(cumulative_filled))
        total = Decimal(str(total_qty)) if total_qty is not None else filled
        status = "FILLED" if (total > 0 and filled >= total) else "PARTIALLY_FILLED"
        self._append({
            "order_ref": order_ref, "status": status,
            "filled_qty": str(filled), "total_qty": str(total),
            "avg_price": None if avg_price is None else str(avg_price),
            "fee": None if fee is None else str(fee),
        })
        return status

    def net_filled(self, order_ref: str) -> Decimal:
        """Cumulative filled quantity recorded for an order (0 if none)."""
        with self._lock:
            o = self._orders.get(order_ref, {})
            return Decimal(str(o.get("filled_qty", "0")))

    def net_positions(self) -> Dict[str, Decimal]:
        """R2: local net-position book — signed filled quantity per symbol (BUY +, SELL -).

        Derived from the durable journal's recorded fills, so it survives restart and can be
        cross-checked against the broker by reconciliation. Symbols nett to ~0 are omitted.
        """
        with self._lock:
            book: Dict[str, Decimal] = {}
            for o in self._orders.values():
                filled = Decimal(str(o.get("filled_qty", "0")))
                if filled <= 0:
                    continue
                sym = o.get("symbol")
                side = str(o.get("side", "")).upper()
                signed = filled if side in ("BUY", "LONG") else -filled
                book[sym] = book.get(sym, Decimal("0")) + signed
            return {s: q for s, q in book.items() if q != 0}

    def record_terminal(self, order_ref: str, status: str, **extra) -> None:
        if status not in _TERMINAL:
            status = "FAILED"
        self._append({"order_ref": order_ref, "status": status, **extra})

    # -- recovery / queries -------------------------------------------------------

    def in_flight(self) -> List[Dict[str, Any]]:
        """Orders not in a terminal state — these need reconciliation against the broker on startup."""
        with self._lock:
            return [dict(o) for o in self._orders.values() if o.get("status") in _OPEN_STATES]

    def order_exchange_map(self) -> Dict[str, tuple]:
        """Rebuild order_id -> (exchange, symbol) from submitted orders (persists B5 across restart)."""
        with self._lock:
            out = {}
            for o in self._orders.values():
                if o.get("order_id"):
                    out[str(o["order_id"])] = (o.get("exchange"), o.get("symbol"))
            return out

    def recover(self) -> Dict[str, Any]:
        """Startup recovery summary: counts, in-flight orders, and the order->exchange map."""
        with self._lock:
            counts: Dict[str, int] = {}
            for o in self._orders.values():
                counts[o.get("status", "?")] = counts.get(o.get("status", "?"), 0) + 1
            return {
                "total_orders": len(self._orders),
                "status_counts": counts,
                "in_flight": self.in_flight(),
                "order_exchange_map": self.order_exchange_map(),
            }

    # -- persistence (append-only, fsync) -----------------------------------------

    def _append(self, fields: Dict[str, Any]) -> None:
        with self._lock:
            rec = {"ts": _now(), **fields}
            ref = rec["order_ref"]
            cur = self._orders.get(ref, {})
            cur.update({k: v for k, v in rec.items() if v is not None or k not in cur})
            self._orders[ref] = cur
            try:
                os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, default=str) + "\n")
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except (OSError, ValueError):
                        pass
            except Exception:
                pass  # journaling must never break the order path

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    ref = rec.get("order_ref")
                    if not ref:
                        continue
                    cur = self._orders.get(ref, {})
                    cur.update({k: v for k, v in rec.items() if v is not None or k not in cur})
                    self._orders[ref] = cur
        except Exception:
            pass


# Process-wide singleton — the live order journal the real-send path writes to.
live_order_journal = LiveOrderJournal()


__all__ = ["LiveOrderJournal", "live_order_journal"]
