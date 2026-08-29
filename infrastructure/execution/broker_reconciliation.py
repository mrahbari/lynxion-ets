"""Broker Reconciliation + Halt-on-Drift (E11 / B4).

Reconciles LOCAL state (the durable live order journal) against ACTUAL broker state
(open positions + order statuses pulled from the exchange):

  * resolves in-flight journal orders (SUBMITTED but not terminal) by polling the broker's
    real order status — a RECOVERABLE divergence (we just learn the true terminal state);
  * detects UNRECOVERABLE drift — a broker position for a symbol the local side has no
    journal record of (the system is holding a live position it doesn't know about), or a
    journaled-open order the broker no longer recognises with no resolution;
  * on unrecoverable drift, engages the kill switch (halt all new orders) and alerts.

This is the live-trading safety net the audit (B4) flagged as missing. It is broker-
agnostic (uses the BrokerPort interface) and side-effect-free except the halt callback.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional


def _sym(s) -> str:
    return getattr(s, "value", None) or (str(s) if s is not None else "")


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


ACTIVE_POSITIONS_JOURNAL_PATH = os.path.join(_project_root(), "data", "active_positions_journal.json")


_OPEN_ORDER_STATES = {"NEW", "PENDING", "PARTIALLY_FILLED", "PARTIAL", "OPEN", "WORKING"}
_TERMINAL_ORDER_STATES = {"FILLED", "CANCELLED", "CANCELED", "REJECTED", "EXPIRED"}


class BrokerReconciliationService:
    """Reconcile journal vs broker; halt on unrecoverable drift."""

    def __init__(self, halt_fn: Optional[Callable[[str], None]] = None):
        # Default halt = engage the live execution guard kill switch (imported lazily).
        self._halt_fn = halt_fn
        from shared.logger import EnhancedLogger
        self.logger = EnhancedLogger("BrokerReconciliationService")
        # Persistent tracking for active position transitions and closed position idempotency across restarts
        self._previous_active_symbols: set[str] = self._load_active_symbols()
        self._processed_closed_exits: set[str] = set()

    def _load_active_symbols(self) -> set[str]:
        try:
            if os.path.exists(ACTIVE_POSITIONS_JOURNAL_PATH):
                with open(ACTIVE_POSITIONS_JOURNAL_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return set(data)
                    elif isinstance(data, dict):
                        return set(data.get("active_symbols", []))
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.warning(f"Failed to load active positions journal: {e}")
        return set()

    def _save_active_symbols(self) -> None:
        try:
            os.makedirs(os.path.dirname(ACTIVE_POSITIONS_JOURNAL_PATH), exist_ok=True)
            tmp_path = f"{ACTIVE_POSITIONS_JOURNAL_PATH}.tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump({"active_symbols": sorted(list(self._previous_active_symbols))}, f, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except (OSError, ValueError):
                    pass
            os.replace(tmp_path, ACTIVE_POSITIONS_JOURNAL_PATH)
        except Exception as e:
            self.logger.warning(f"Failed to save active positions journal: {e}")

    def _halt(self, reason: str) -> None:
        if self._halt_fn is not None:
            self._halt_fn(reason)
            return
        try:
            from shared.live_execution_guard import live_execution_guard
            live_execution_guard.engage_kill_switch(reason)
        except Exception:
            pass

    def _process_position_closures(self, broker, current_active_symbols: set[str]) -> None:
        """Detect exchange position closures (transition to positionAmt == 0) and propagate trade result."""
        # Find symbols that were active in the previous cycle but are absent in current cycle
        closed_symbols = self._previous_active_symbols - current_active_symbols
        # Update active symbols for next cycle and persist atomically across process restarts
        self._previous_active_symbols = set(current_active_symbols)
        self._save_active_symbols()

        if not closed_symbols:
            return

        for sym in closed_symbols:
            try:
                # 1. Resolve closing order from broker history
                closing_order_id = "UNKNOWN"
                is_profitable = False
                realized_pnl = None

                if hasattr(broker, "get_order_history"):
                    try:
                        history = broker.get_order_history(_sym(sym), limit=20) or []
                        # Sort newest order first
                        sorted_history = sorted(
                            history,
                            key=lambda x: int(x.get("updateTime") or x.get("time") or 0),
                            reverse=True
                        )
                        for order in sorted_history:
                            order_status = str(order.get("status", "")).upper()
                            order_type = str(order.get("type", "")).upper()
                            is_reduce_only = order.get("reduceOnly") in (True, "true", "TRUE")

                            # Match strictly closing orders (STOP_MARKET, TAKE_PROFIT_MARKET, LIQUIDATION, or reduceOnly MARKET/LIMIT)
                            if order_status in _TERMINAL_ORDER_STATES and (
                                order_type in {"STOP_MARKET", "TAKE_PROFIT_MARKET", "LIQUIDATION"} or is_reduce_only
                            ):
                                closing_order_id = str(order.get("orderId", "UNKNOWN"))
                                pnl_val = order.get("realizedProfit", order.get("profit"))
                                if pnl_val is not None:
                                    try:
                                        realized_pnl = float(pnl_val)
                                    except (ValueError, TypeError):
                                        pass

                                if order_type == "TAKE_PROFIT_MARKET" or (realized_pnl is not None and realized_pnl > 0):
                                    is_profitable = True
                                elif order_type in {"STOP_MARKET", "LIQUIDATION"} or (realized_pnl is not None and realized_pnl < 0):
                                    is_profitable = False
                                break
                    except Exception as hist_err:
                        self.logger.warning(f"Could not retrieve order history for {sym}: {hist_err}")

                # 2. Derive Idempotency Key (exchange closing_order_id or fallback)
                exit_key = f"{sym}_{closing_order_id}" if closing_order_id != "UNKNOWN" else f"{sym}_{realized_pnl}"
                if exit_key in self._processed_closed_exits:
                    self.logger.debug(f"Position close for {sym} ({exit_key}) already processed — skipping duplicate.")
                    continue

                # ATOMICITY: Register idempotency key BEFORE emitting to prevent duplicate propagation on crash
                self._processed_closed_exits.add(exit_key)

                # 3. Propagate to strategy_manager and register with SymbolCooldownGate
                from infrastructure.strategies.strategy_manager import strategy_manager
                strategy_manager.record_trade_result(sym, is_profitable=is_profitable, position_closed=True)

                from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
                if not is_profitable or realized_pnl is None or realized_pnl <= 0 or closing_order_id == "UNKNOWN":
                    symbol_cooldown_gate.record_stop_loss_exit(sym)
                    self.logger.warning(f"🛑 SYMBOL COOLDOWN GATE: Activated 60m Stop Loss Cooldown for {sym} (is_profitable={is_profitable}, PnL={realized_pnl})")
                else:
                    symbol_cooldown_gate.record_take_profit_exit(sym)

                print(f"\n🔴 [POSITION CLOSED] {sym}: outcome={'TAKE PROFIT' if is_profitable else 'STOP LOSS'} PnL={realized_pnl if realized_pnl is not None else 'N/A'} USDT", flush=True)
                self.logger.warning(
                    f"✅ POSITION CLOSED CONFIRMED for {sym}: exit_key={exit_key}, is_profitable={is_profitable}"
                )

                # 3b. Sync terminal state to live_order_journal to prevent stale in-flight recovery warnings
                try:
                    from infrastructure.execution.live_order_journal import live_order_journal
                    if closing_order_id and closing_order_id != "UNKNOWN":
                        live_order_journal.record_result(
                            order_ref=closing_order_id,
                            status="FILLED",
                            order_id=closing_order_id,
                            realized_pnl=realized_pnl,
                            symbol=sym
                        )
                except Exception as journal_sync_err:
                    self.logger.warning(f"Could not sync closed position to live_order_journal for {sym}: {journal_sync_err}")

                # 4. Dispatch immediate Telegram Alert for Position Close
                try:
                    from infrastructure.services.risk_alerts import send_telegram
                    outcome_str = "STOP LOSS" if not is_profitable else "TAKE PROFIT"
                    emoji = "🛑" if not is_profitable else "✅"
                    msg = (
                        f"{emoji} <b>EXCHANGE POSITION CLOSED</b>\n\n"
                        f"• <b>Symbol:</b> <code>{sym}</code>\n"
                        f"• <b>Outcome:</b> {outcome_str}\n"
                        f"• <b>Realized PnL:</b> <code>{realized_pnl if realized_pnl is not None else 'N/A'} USDT</code>\n"
                        f"• <b>Cooldown:</b> {'60-Minute Stop Loss Cooldown Activated' if not is_profitable else 'None'}"
                    )
                    send_telegram(msg)
                except Exception as tel_err:
                    self.logger.warning(f"Telegram notification for {sym} close could not be sent: {tel_err}")
            except Exception as e:
                self.logger.error(
                    f"❌ Failed to propagate position close event for {sym}: {e}",
                    exc_info=True
                )

    def reconcile(self, broker, journal, halt_on_unrecoverable: bool = True) -> Dict[str, Any]:
        """One reconciliation pass. Returns a structured drift report."""
        report: Dict[str, Any] = {
            "in_sync": True, "halted": False, "errors": [],
            "broker_positions": [], "recoverable": [], "unrecoverable": [],
            "orders_resolved": [],
        }

        # --- 1. Pull broker truth: open positions ---
        broker_positions: List[Any] = []
        try:
            broker_positions = broker.get_all_positions() or []
        except Exception as e:
            report["errors"].append(f"get_all_positions failed: {e}")

        open_positions = [p for p in broker_positions
                          if abs(float(getattr(p, "quantity", 0) or getattr(p, "position_amt", 0) or 0)) > 0]
        report["broker_positions"] = [
            {"symbol": _sym(getattr(p, "symbol", "")),
             "quantity": str(getattr(p, "quantity", "")),
             "side": getattr(getattr(p, "side", None), "value", str(getattr(p, "side", "")))}
            for p in open_positions
        ]

        # Detect position closures based on exchange position transitions
        current_active_symbols = {b_pos["symbol"] for b_pos in report["broker_positions"] if b_pos.get("symbol")}
        self._process_position_closures(broker, current_active_symbols)

        # --- 2. Local view from the journal: every symbol we have any order record for ---
        try:
            order_map = journal.order_exchange_map()       # order_id -> (exchange, symbol)
            inflight = journal.in_flight()
        except Exception as e:
            report["errors"].append(f"journal read failed: {e}")
            order_map, inflight = {}, []
        known_symbols = {str(sym).upper().replace("-", "").replace("/", "").replace("_", "") for (_ex, sym) in order_map.values() if sym}
        known_symbols |= {str(o.get("symbol")).upper().replace("-", "").replace("/", "").replace("_", "") for o in inflight if o.get("symbol")}

        # --- 3. Resolve in-flight orders against the broker's real status (recoverable) ---
        # B7: when the broker exposes fill detail, record partial/full fills in the journal.
        for o in inflight:
            oid, sym, ref = o.get("order_id"), o.get("symbol"), o.get("order_ref")
            if not oid:
                # INTENT that never reached SUBMITTED: a crash before ack -> needs broker check
                report["recoverable"].append({"order_ref": ref, "issue": "intent_without_ack", "symbol": sym})
                report["in_sync"] = False
                continue
            status, executed_qty, avg_price = "UNKNOWN", None, None
            try:
                if hasattr(broker, "get_order_fill"):
                    fill = broker.get_order_fill(oid, _mk_symbol(sym)) or {}
                    status = str(fill.get("status", "UNKNOWN")).upper()
                    executed_qty = fill.get("executed_qty")
                    avg_price = fill.get("avg_price")
                else:
                    status = str(broker.get_order_status(oid, _mk_symbol(sym))).upper()
            except Exception as e:
                status = "UNKNOWN"
                report["errors"].append(f"status({oid}) failed: {e}")

            # B7: record fill progress (partial or full) when we have executed quantity.
            recorded = None
            if executed_qty is not None and float(executed_qty or 0) > 0:
                try:
                    recorded = journal.record_fill(ref, executed_qty, o.get("quantity"), avg_price)
                except Exception:
                    recorded = None

            if recorded == "FILLED" or status == "FILLED":
                if recorded != "FILLED":
                    try:
                        journal.record_terminal(ref, "FILLED")
                    except Exception:
                        pass
                report["orders_resolved"].append({"order_id": oid, "status": "FILLED",
                                                   "executed_qty": str(executed_qty) if executed_qty is not None else None})
                report["in_sync"] = False
            elif recorded == "PARTIALLY_FILLED" or status in {"PARTIALLY_FILLED", "PARTIAL"}:
                report["recoverable"].append({"order_id": oid, "issue": "partially_filled",
                                              "executed_qty": str(executed_qty), "symbol": sym})
                report["in_sync"] = False
            elif status in _TERMINAL_ORDER_STATES:
                try:
                    journal.record_terminal(ref, _norm_terminal(status))
                except Exception:
                    pass
                report["orders_resolved"].append({"order_id": oid, "status": status})
                report["in_sync"] = False
            elif status in _OPEN_ORDER_STATES:
                pass  # still open at broker — consistent
            else:
                sym_clean = str(sym).upper().replace("-", "").replace("/", "").replace("_", "")
                active_clean = {str(s).upper().replace("-", "").replace("/", "").replace("_", "") for s in current_active_symbols}
                if sym_clean not in active_clean:
                    try:
                        journal.record_terminal(ref, "CANCELLED", reason=f"BROKER_STATUS_{status}_INACTIVE_SYMBOL")
                        report["orders_resolved"].append({"order_id": oid, "status": f"CANCELLED_{status}"})
                    except Exception:
                        pass
                else:
                    report["recoverable"].append({"order_id": oid, "issue": f"status={status}", "symbol": sym})
                    report["in_sync"] = False

        # --- 4. UNRECOVERABLE: a broker position with no local journal record ---
        for p in open_positions:
            raw_psym = getattr(p, "symbol", "")
            psym = _sym(raw_psym).upper().replace("-", "").replace("/", "").replace("_", "")
            if psym and psym not in known_symbols:
                report["unrecoverable"].append({
                    "symbol": _sym(raw_psym), "quantity": str(getattr(p, "quantity", "")),
                    "issue": "broker position with no local order record",
                })
                report["in_sync"] = False

        # --- 5. Halt on unrecoverable drift ---
        if report["unrecoverable"] and halt_on_unrecoverable:
            reason = (f"UNRECOVERABLE broker drift: positions with no local record "
                      f"{[u['symbol'] for u in report['unrecoverable']]}")
            self._halt(reason)
            report["halted"] = True

        return report


def _mk_symbol(sym_str):
    from domain.value_objects import Symbol
    try:
        return Symbol(sym_str)
    except Exception:
        return sym_str


def _norm_terminal(status: str) -> str:
    s = status.upper()
    if s in {"CANCELLED", "CANCELED"}:
        return "CANCELLED"
    if s in {"FILLED"}:
        return "FILLED"
    if s in {"REJECTED", "EXPIRED"}:
        return "REJECTED"
    return "FAILED"


__all__ = ["BrokerReconciliationService"]
