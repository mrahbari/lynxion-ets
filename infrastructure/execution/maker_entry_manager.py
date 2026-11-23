"""Maker (post-only limit) entries with timeout and market fallback (roadmap E8-2, E16 PASS).

ENTRY_ORDER_MODE=maker: the orchestrator sends the entry as LIMIT POST_ONLY at the best bid (BUY) / best ask
(SELL) with the strategy's SL/TP attached (BingX activates attached SL/TP on fill). This manager then watches
each resting entry:
  FILLED                         -> done
  cancelled/rejected, 0 filled   -> MARKET fallback now (post-only rejected because it would cross)
  open after ENTRY_MAKER_TIMEOUT_S (900) and 0 filled -> cancel, then MARKET fallback
  partially filled at timeout    -> cancel the rest, keep the partial position (attached SL/TP), no fallback
The fallback is skipped when price is already beyond the trade's SL or TP (the setup is void, as in E16).
While an entry rests, the symbol stays in the pending-order tracker so no duplicate entry is placed.
Default ENTRY_ORDER_MODE=market keeps the previous behaviour.
"""
from __future__ import annotations

import dataclasses
import logging
import os
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple

_log = logging.getLogger("MakerEntry")
_log.setLevel(logging.INFO)  # root logger is WARNING; these audit lines must reach the runner log
DONE = {"FILLED"}
DEAD = {"CANCELED", "CANCELLED", "EXPIRED", "REJECTED", "FAILED"}


def maker_mode() -> bool:
    return os.getenv("ENTRY_ORDER_MODE", "market").strip().lower() == "maker"


def timeout_s() -> float:
    return float(os.getenv("ENTRY_MAKER_TIMEOUT_S", "900"))


def hold_after_fill_s() -> float:
    """Keep the symbol held after a fill until reconciliation/positions show it (VST lags; 2026-11-23 OKB double)."""
    return float(os.getenv("ENTRY_MAKER_HOLD_AFTER_FILL_S", "180"))


_exchange = None
_exchange_lock = threading.Lock()


def best_quotes(symbol: str) -> Optional[Tuple[float, float]]:
    """(best bid, best ask) on the execution venue (ccxt, DEFAULT_BROKER), None on any failure."""
    global _exchange
    try:
        import ccxt
        with _exchange_lock:
            if _exchange is None:
                name = (os.getenv("DEFAULT_BROKER") or "bingx").strip().lower()
                ex = getattr(ccxt, name)({"enableRateLimit": True, "options": {"defaultType": "swap"}})
                if os.getenv("BROKER_TESTNET", os.getenv("BINGX_TESTNET", "")).strip().lower() == "true":
                    ex.set_sandbox_mode(True)      # quote the book the order actually goes to (VST)
                ex.load_markets()
                _exchange = ex
        s = str(getattr(symbol, "value", symbol)).upper().replace("-", "")
        base = s[:-4] if s.endswith("USDT") else s
        book = _exchange.fetch_order_book(f"{base}/USDT:USDT", limit=5)
        bid, ask = float(book["bids"][0][0]), float(book["asks"][0][0])
        return (bid, ask) if 0 < bid < ask else None
    except Exception as e:  # noqa: BLE001
        _log.warning("best quotes unavailable for %s: %s", symbol, e)
        return None


def _amount(v) -> Optional[float]:
    v = getattr(v, "amount", v)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


class MakerEntryManager:
    def __init__(self, poll_s: float = 15.0, quotes: Callable[[str], Optional[Tuple[float, float]]] = best_quotes,
                 clock: Callable[[], float] = time.time):
        self.poll_s, self.quotes, self.clock = poll_s, quotes, clock
        self._pending: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    # registration ------------------------------------------------------------------------------
    def register(self, service, order, order_id: str) -> None:
        side = getattr(order.side, "name", str(order.side)).upper()
        pos_side = "LONG" if side == "BUY" else "SHORT"
        with self._lock:
            self._pending[str(order_id)] = {"service": service, "order": order, "side": pos_side,
                                            "deadline": self.clock() + timeout_s()}
        try:   # hold the symbol while resting, in the tracker the service's duplicate check reads
            add = getattr(service, "_pending_add", None) or service._add_pending_order
            add(order.symbol, pos_side, str(order_id))
        except Exception:  # noqa: BLE001
            pass
        _log.info("MAKER ENTRY RESTING | %s %s | id=%s price=%s | timeout %.0fs", order.symbol, side, order_id,
                  _amount(order.price), timeout_s())
        self._ensure_thread()

    def _ensure_thread(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run, name="maker-entry", daemon=True)
            self._thread.start()

    def _run(self) -> None:
        while True:
            time.sleep(self.poll_s)
            self.check_all()
            with self._lock:
                if not self._pending:
                    return

    # one pass ----------------------------------------------------------------------------------
    def check_all(self) -> None:
        with self._lock:
            items = list(self._pending.items())
        for oid, p in items:
            try:
                if self._check(oid, p):
                    with self._lock:
                        self._pending.pop(oid, None)
            except Exception as e:  # noqa: BLE001
                _log.warning("maker entry check failed for %s: %s", oid, e)

    @staticmethod
    def _router(service):
        """The multi-broker service that knows order -> exchange (the orchestrator holds a wrapper)."""
        return service if hasattr(service, "_lookup_order") else getattr(service, "broker", service)

    def _fill(self, service, oid: str) -> Dict[str, Any]:
        mb = self._router(service)
        exchange, sym = mb._lookup_order(oid)
        return mb.brokers[exchange].get_order_fill(oid, sym)

    def _cancel(self, service, oid: str) -> bool:
        return bool(self._router(service).cancel_order(oid))

    def _release(self, p: dict, oid: str) -> None:
        try:
            svc = p["service"]
            remove = getattr(svc, "_pending_remove", None) or svc._remove_pending_order
            remove(p["order"].symbol, oid)
        except Exception:  # noqa: BLE001
            pass

    def _check(self, oid: str, p: dict) -> bool:
        svc, order = p["service"], p["order"]
        if "release_at" in p:
            if self.clock() < p["release_at"]:
                return False
            self._release(p, oid)
            return True
        f = self._fill(svc, oid)
        status = str(f.get("status", "UNKNOWN")).upper()
        filled = float(f.get("executed_qty") or 0)
        if status in DONE:
            _log.info("MAKER ENTRY FILLED | %s | id=%s avg=%s", order.symbol, oid, f.get("avg_price"))
            p["release_at"] = self.clock() + hold_after_fill_s()
            return False
        expired = self.clock() >= p["deadline"]
        if status not in DEAD and not expired:
            return False
        if status not in DEAD:
            if not self._cancel(svc, oid):
                _log.warning("MAKER ENTRY CANCEL FAILED | %s | id=%s, retry next pass", order.symbol, oid)
                return False
            f = self._fill(svc, oid)
            filled = float(f.get("executed_qty") or 0)
            if str(f.get("status", "")).upper() in DONE:
                self._release(p, oid)
                return True
        self._release(p, oid)
        if filled > 0:
            _log.warning("MAKER ENTRY PARTIAL | %s | id=%s filled %s of %s; rest cancelled, no fallback",
                         order.symbol, oid, filled, order.quantity)
            return True
        self._fallback(p, oid, "timeout" if expired else status.lower())
        return True

    def _fallback(self, p: dict, oid: str, why: str) -> Optional[str]:
        order, svc = p["order"], p["service"]
        q = self.quotes(order.symbol)
        sl, tp = _amount(order.stop_loss_price), _amount(order.take_profit_price)
        if q is None:
            _log.warning("MAKER FALLBACK SKIPPED | %s | id=%s (%s): no price", order.symbol, oid, why)
            return None
        buy = p["side"] == "LONG"
        px = q[1] if buy else q[0]
        void = (sl is not None and (px <= sl if buy else px >= sl)) or \
               (tp is not None and (px >= tp if buy else px <= tp))
        if void:
            _log.info("MAKER FALLBACK SKIPPED | %s | id=%s (%s): price %s beyond SL %s / TP %s", order.symbol, oid,
                      why, px, sl, tp)
            return None
        from domain.value_objects import Money
        mkt = dataclasses.replace(order, order_type="MARKET", time_in_force="GTC", client_order_id=None,
                                  price=Money(amount=px, currency="USDT"))
        new_id = svc.execute_order(mkt)
        _log.info("MAKER FALLBACK MARKET | %s | id=%s (%s) -> %s at ~%s", order.symbol, oid, why, new_id, px)
        return new_id


maker_entry_manager = MakerEntryManager()
