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
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional


def _sym(s) -> str:
    return getattr(s, "value", None) or (str(s) if s is not None else "")


def _amount(value) -> float:
    """Extract a numeric amount from a Money-like broker/domain value."""
    try:
        return float(getattr(value, "amount", value) or 0)
    except (TypeError, ValueError):
        return 0.0


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


ACTIVE_POSITIONS_JOURNAL_PATH = os.path.join(_project_root(), "data", "active_positions_journal.json")


# Symbols the running reconciler last observed OPEN on the exchange (normalized, in-process only).
# Closures are detected by diffing snapshots, so a stop-out followed by a re-entry on the same
# symbol before the next pass is invisible (A-B-A): the old exit is never processed, its loss
# cooldown never set, no close notification sent. The entry gate asks exit_unreconciled() when
# the broker shows NO position: if the last snapshot still had one, its exit is unprocessed.
_LAST_OBSERVED_OPEN: set[str] = set()
# A closure is booked after this many consecutive absent passes (+1 when the whole snapshot is empty).
CLOSURE_CONFIRM_PASSES = 2
EMPTY_SNAPSHOT_EXTRA_PASSES = 1
ORPHAN_PROTECTION_AGE_S = 120.0


def _norm(symbol) -> str:
    return _sym(symbol).upper().replace("-", "").replace("/", "").replace("_", "")


def exit_unreconciled(symbol) -> bool:
    """True if `symbol` was open at the last reconciliation pass (caller has seen it flat since)."""
    return _norm(symbol) in _LAST_OBSERVED_OPEN


_OPEN_ORDER_STATES = {"NEW", "PENDING", "PARTIALLY_FILLED", "PARTIAL", "OPEN", "WORKING"}
_TERMINAL_ORDER_STATES = {"FILLED", "CANCELLED", "CANCELED", "REJECTED", "EXPIRED"}


class BrokerReconciliationService:
    """Reconcile journal vs broker; halt on unrecoverable drift."""

    def __init__(self, halt_fn: Optional[Callable[[str], None]] = None,
                 position_identity_store=None, terminal_observer=None,
                 active_positions_journal_path=None):
        # Default halt = engage the live execution guard kill switch (imported lazily).
        self._halt_fn = halt_fn
        self._position_identity_store = position_identity_store
        self._terminal_observer = terminal_observer
        self._active_positions_journal_path = active_positions_journal_path or ACTIVE_POSITIONS_JOURNAL_PATH
        self._terminal_observation_counts = {"emitted": 0, "excluded": 0, "errors": 0}
        from shared.logger import EnhancedLogger
        self.logger = EnhancedLogger("BrokerReconciliationService")
        # Persistent tracking for active position transitions and closed position idempotency across restarts
        self._previous_active_symbols: set[str] = self._load_active_symbols()
        # Only a fill newer than an observed open position can explain its exit.
        # Symbols restored from the journal have no safe timestamp until seen open.
        self._active_seen_ms: dict[str, int] = {}
        # symbol -> [consecutive absent passes, any of those passes had a non-empty snapshot]
        self._absent_passes: dict[str, list] = {}
        self._processed_closed_exits: set[str] = set()
        self._unknown_exit_sequence = 0

    def _observe_terminal_order(self, symbol: str, order: Dict[str, Any]) -> None:
        """Observe already-selected terminal evidence without changing reconciliation."""
        if self._position_identity_store is None or self._terminal_observer is None:
            return
        try:
            normalized_symbol = _sym(order.get("symbol", "")).upper().replace("-", "").replace("/", "").replace("_", "")
            position_side = str(order.get("positionSide", "")).upper()
            order_id = order.get("orderId")
            if not normalized_symbol or normalized_symbol != _sym(symbol).upper().replace("-", "").replace("/", "").replace("_", ""):
                self._terminal_observation_counts["excluded"] += 1
                return
            if position_side not in {"LONG", "SHORT"} or order_id in (None, "", "UNKNOWN"):
                self._terminal_observation_counts["excluded"] += 1
                return

            identity = self._position_identity_store.resolve_open(normalized_symbol, position_side)
            if identity is None:
                self._terminal_observation_counts["excluded"] += 1
                return

            from infrastructure.observability.terminal_evidence_extractor import extract_terminal_evidence
            evidence = extract_terminal_evidence(order, identity)
            if not evidence.get("eligible"):
                self._terminal_observation_counts["excluded"] += 1
                return

            observed_at = datetime.now(timezone.utc).isoformat()
            evaluation_id = f"terminal:{identity['record_id']}:{order_id}"
            event = {
                "schema_version": 1,
                "event_id": f"{evaluation_id}:exit_fill_observed",
                "event_type": "EXIT_FILL_OBSERVED",
                "event_time_utc": observed_at,
                "run_id": identity["observer_run_id"],
                "evaluation_id": evaluation_id,
                "position_key": identity["position_key"],
                "symbol": normalized_symbol,
                "side": position_side,
                "quantity": identity.get("quantity"),
                "entry_price": identity.get("entry_price"),
                "current_price": None,
                "price_source": None,
                "configured_leverage": None,
                "requested_leverage": None,
                "exchange_leverage": identity.get("exchange_leverage"),
                "roe_pct": None,
                "peak_price": None,
                "peak_roe_pct": None,
                "manager_state_before": "OPEN",
                "manager_state_after": (
                    "TERMINAL_EVIDENCE_COMPLETE" if evidence["terminal_evidence_complete"]
                    else "CLOSURE_OBSERVED"
                ),
                "error": None,
                **{key: evidence.get(key) for key in (
                    "terminal_order_id", "exit_order_type", "fill_price", "fill_quantity",
                    "realized_pnl", "fees", "fill_time_utc", "trigger_price", "trigger_basis",
                    "missing_fields",
                )},
            }
            self._terminal_observer.append(event)

            advanced = dict(identity)
            advanced["lifecycle_state"] = event["manager_state_after"]
            advanced["last_observed_utc"] = observed_at
            advanced["terminal_order_id"] = str(order_id)
            self._position_identity_store.upsert(advanced)
            self._terminal_observation_counts["emitted"] += 1
        except Exception as exc:
            self._terminal_observation_counts["errors"] += 1
            self.logger.warning(f"Terminal evidence observation failed for {symbol}: {exc}")

    def _load_active_symbols(self) -> set[str]:
        try:
            if os.path.exists(self._active_positions_journal_path):
                with open(self._active_positions_journal_path, "r", encoding="utf-8") as f:
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
            os.makedirs(os.path.dirname(self._active_positions_journal_path), exist_ok=True)
            tmp_path = f"{self._active_positions_journal_path}.tmp.{os.getpid()}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump({"active_symbols": sorted(list(self._previous_active_symbols))}, f, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except (OSError, ValueError):
                    pass
            os.replace(tmp_path, self._active_positions_journal_path)
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
        absent = self._previous_active_symbols - current_active_symbols
        # BingX VST intermittently answers the positions endpoint with code 0 and an EMPTY list
        # (2026-11-23: 7 empty replies in ~14 s, then the full 51). One snapshot is not evidence
        # of an exit: book a closure only after CLOSURE_CONFIRM_PASSES consecutive absent passes,
        # one more when every absent pass saw an empty snapshot. Pending symbols stay "open" (entries held, journal kept).
        nonempty = bool(current_active_symbols)
        absent_passes = getattr(self, "_absent_passes", {})
        closed_symbols = set()
        pending = set()
        for sym in absent:
            n, seen_nonempty = absent_passes.get(sym, [0, False])
            n, seen_nonempty = n + 1, seen_nonempty or nonempty
            if n >= CLOSURE_CONFIRM_PASSES + (0 if seen_nonempty else EMPTY_SNAPSHOT_EXTRA_PASSES):
                closed_symbols.add(sym)
            else:
                absent_passes[sym] = [n, seen_nonempty]
                pending.add(sym)
        for sym in list(absent_passes):
            if sym not in pending:
                del absent_passes[sym]
        self._absent_passes = absent_passes
        if pending:
            self.logger.info(f"Position absent from broker snapshot, awaiting confirmation: {sorted(pending)}")
        previously_seen_ms = self._active_seen_ms
        observed_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        self._active_seen_ms = {sym: observed_ms for sym in current_active_symbols}
        self._active_seen_ms.update({sym: previously_seen_ms[sym] for sym in pending if sym in previously_seen_ms})
        # Update active symbols for next cycle and persist atomically across process restarts
        self._previous_active_symbols = set(current_active_symbols) | pending
        self._save_active_symbols()
        _LAST_OBSERVED_OPEN.clear()
        _LAST_OBSERVED_OPEN.update(_norm(x) for x in self._previous_active_symbols)

        if not closed_symbols:
            return

        for sym in closed_symbols:
            try:
                if sym not in previously_seen_ms:
                    # A persisted active symbol was not observed open in this
                    # process.  The first flat snapshot cannot date or identify
                    # its historical exit; do not announce a newly confirmed fill.
                    from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
                    symbol_cooldown_gate.record_unverified_exit(sym)
                    self.logger.warning(
                        f"Previously active {sym} absent from first broker snapshot; "
                        "historical exit remains unverified"
                    )
                    try:
                        from infrastructure.services.risk_alerts import send_telegram
                        send_telegram(
                            f"⚠️ <b>POSITION STATE UNVERIFIED</b>\n\n"
                            f"• <b>Symbol:</b> <code>{sym}</code>\n"
                            "• Previously active, absent from first broker snapshot after restart.\n"
                            "• Historical exit and PnL unknown; safety cooldown active."
                        )
                    except Exception as tel_err:
                        self.logger.warning(f"Telegram notification for {sym} state could not be sent: {tel_err}")
                    continue

                # 1. Resolve closing order from broker history
                closing_order_id = "UNKNOWN"
                is_profitable = None
                realized_pnl = None

                if hasattr(broker, "get_order_history"):
                    try:
                        # BingX returns the oldest orders of the window first: without a start
                        # bound, positions with many stop amendments push the closing fill out
                        # of the page and the exit is reported as UNKNOWN.
                        seen_for_window = previously_seen_ms.get(sym)
                        try:
                            history = broker.get_order_history(
                                _sym(sym), limit=100,
                                start_time=datetime.fromtimestamp(
                                    (seen_for_window - 60_000) / 1000.0, tz=timezone.utc),
                            ) or []
                        except TypeError:
                            history = broker.get_order_history(_sym(sym), limit=20) or []
                        # Sort newest order first
                        sorted_history = sorted(
                            history,
                            key=lambda x: int(x.get("updateTime") or x.get("time") or 0),
                            reverse=True
                        )
                        for order in sorted_history:
                            order_time = order.get("updateTime") or order.get("time")
                            seen_ms = previously_seen_ms.get(sym)
                            try:
                                order_time_ms = int(order_time)
                            except (TypeError, ValueError):
                                continue
                            if seen_ms is None or not seen_ms <= order_time_ms <= observed_ms:
                                continue
                            order_symbol = _sym(order.get("symbol", ""))
                            if order_symbol:
                                normalized_order_symbol = order_symbol.upper().replace("-", "").replace("/", "").replace("_", "")
                                normalized_closed_symbol = _sym(sym).upper().replace("-", "").replace("/", "").replace("_", "")
                                if normalized_order_symbol != normalized_closed_symbol:
                                    continue
                            order_status = str(order.get("status", "")).upper()
                            order_type = str(order.get("type", "")).upper()
                            is_reduce_only = order.get("reduceOnly") in (True, "true", "TRUE")

                            # Match strictly closing orders (STOP_MARKET, TAKE_PROFIT_MARKET, LIQUIDATION, or reduceOnly MARKET/LIMIT)
                            if order_status == "FILLED" and (
                                order_type in {"STOP_MARKET", "TAKE_PROFIT_MARKET", "LIQUIDATION"} or is_reduce_only
                            ):
                                closing_order_id = str(order.get("orderId", "UNKNOWN"))
                                pnl_val = order.get("realizedProfit", order.get("profit"))
                                if pnl_val is not None:
                                    try:
                                        realized_pnl = float(pnl_val)
                                    except (ValueError, TypeError):
                                        pass

                                if realized_pnl is not None:
                                    is_profitable = realized_pnl > 0
                                break
                    except Exception as hist_err:
                        self.logger.warning(f"Could not retrieve order history for {sym}: {hist_err}")

                # 2. Derive Idempotency Key (exchange closing_order_id or fallback)
                if closing_order_id != "UNKNOWN":
                    exit_key = f"{sym}_{closing_order_id}"
                else:
                    # A closed-position transition is emitted once by the active-symbol state
                    # machine.  Do not collapse every evidence-poor closure for this symbol into
                    # the permanent key ``SYMBOL_None``; a later independent closure must still
                    # be processed.
                    self._unknown_exit_sequence += 1
                    exit_key = f"{sym}_UNKNOWN_{self._unknown_exit_sequence}"
                if exit_key in self._processed_closed_exits:
                    self.logger.debug(f"Position close for {sym} ({exit_key}) already processed — skipping duplicate.")
                    continue

                # ATOMICITY: Register idempotency key BEFORE emitting to prevent duplicate propagation on crash
                self._processed_closed_exits.add(exit_key)

                # Optional repository-only observer. The selected order and all
                # operational closure behavior above/below remain unchanged.
                if closing_order_id != "UNKNOWN":
                    self._observe_terminal_order(sym, order)

                # 3. Propagate verified outcomes. UNKNOWN is not a proven loss;
                # apply one conservative safety cooldown without inventing a
                # losing trade or double-counting a rapid-loss circuit breaker.
                from infrastructure.strategies.strategy_manager import strategy_manager
                from infrastructure.risk.symbol_cooldown_gate import symbol_cooldown_gate
                if is_profitable is None:
                    symbol_cooldown_gate.record_unverified_exit(sym)
                    self.logger.warning(f"🛑 SYMBOL COOLDOWN GATE: Safety cooldown for unverified exit on {sym}")
                else:
                    strategy_manager.record_trade_result(sym, is_profitable=is_profitable, position_closed=True)
                    if is_profitable:
                        symbol_cooldown_gate.record_take_profit_exit(sym)

                outcome_label = "UNKNOWN" if is_profitable is None else "PROFITABLE" if is_profitable else "LOSS"
                print(f"\n🔴 [POSITION CLOSED] {sym}: outcome={outcome_label} PnL={realized_pnl if realized_pnl is not None else 'N/A'} USDT", flush=True)
                self.logger.warning(
                    f"✅ POSITION CLOSED CONFIRMED for {sym}: exit_key={exit_key}, "
                    f"outcome={outcome_label}, realized_pnl={realized_pnl}"
                )

                # 3b. Sync terminal state to live_order_journal to prevent stale in-flight recovery warnings
                try:
                    from infrastructure.execution.live_order_journal import live_order_journal
                    if closing_order_id and closing_order_id != "UNKNOWN":
                        order_ref = live_order_journal.order_ref_for_exchange_order(closing_order_id)
                        if order_ref is not None:
                            live_order_journal.record_terminal(
                                order_ref,
                                "FILLED",
                                order_id=closing_order_id,
                                realized_pnl=realized_pnl,
                                symbol=sym,
                            )
                        else:
                            self.logger.warning(
                                f"Could not match closed exchange order {closing_order_id} "
                                f"to one live_order_journal identity for {sym}"
                            )
                except Exception as journal_sync_err:
                    self.logger.warning(f"Could not sync closed position to live_order_journal for {sym}: {journal_sync_err}")

                # 4. Dispatch immediate Telegram Alert for Position Close
                try:
                    from infrastructure.services.risk_alerts import send_telegram
                    # An absent closing order is not evidence of a stop-loss fill.
                    outcome_str = ("UNKNOWN — position gone from the exchange, but no closing SL/TP/market order "
                                   "was found in order history; PnL not booked, check the position on BingX"
                                   if closing_order_id == "UNKNOWN"
                                   else "UNKNOWN — closing order found, realized PnL unavailable" if is_profitable is None
                                   else "PROFITABLE EXIT" if is_profitable else "LOSS")
                    emoji = "⚠️" if is_profitable is None else "✅" if is_profitable else "🛑"
                    cooldown_str = ("Safety cooldown pending exit verification" if is_profitable is None
                                    else "None" if is_profitable else "Loss cooldown active")
                    if closing_order_id == "UNKNOWN":
                        cooldown_str = "60 min safety cooldown on this symbol (no new entry)"
                    msg = (
                        f"{emoji} <b>EXCHANGE POSITION CLOSED</b>\n\n"
                        f"• <b>Symbol:</b> <code>{sym}</code>\n"
                        f"• <b>Outcome:</b> {outcome_str}\n"
                        f"• <b>Realized PnL:</b> <code>{realized_pnl if realized_pnl is not None else 'N/A'} USDT</code>"
                        + (f"\n• <b>Cooldown:</b> {cooldown_str}" if cooldown_str != "None" else "")
                    )
                    send_telegram(msg)
                except Exception as tel_err:
                    self.logger.warning(f"Telegram notification for {sym} close could not be sent: {tel_err}")
            except Exception as e:
                self.logger.error(
                    f"❌ Failed to propagate position close event for {sym}: {e}",
                    exc_info=True
                )

    def inspect(self, broker, journal) -> Dict[str, Any]:
        """Read broker positions and local journal state without writing or halting.

        This is intentionally narrower than ``reconcile``: it does not query order
        status, process position closures, persist snapshots, mutate the journal, or
        engage the kill switch. It is the safe preflight required before any operator
        chooses to run a state-changing reconciliation pass.
        """
        report: Dict[str, Any] = {
            "errors": [],
            "broker_positions": [],
            "journal_symbols": [],
            "journal_net_positions": {},
            "in_flight_orders": [],
            "broker_positions_missing_from_journal": [],
            "protective_orders": [],
            "protection_evidence_status": "UNAVAILABLE",
        }
        try:
            journal.recover()
            report["protective_orders"] = journal.protection_records()
            report["protection_evidence_status"] = "LOCAL_JOURNAL_ONLY"
        except Exception:
            report["errors"].append("journal recovery unavailable; inspection refused")
            return report
        try:
            broker_positions = broker.get_all_positions() or []
        except Exception as exc:
            report["errors"].append(f"get_all_positions failed: {exc}")
            broker_positions = []

        open_positions = [
            position for position in broker_positions
            if abs(float(getattr(position, "quantity", 0) or getattr(position, "position_amt", 0) or 0)) > 0
        ]
        report["broker_positions"] = []
        for position in open_positions:
            quantity = abs(_amount(getattr(position, "quantity", 0) or getattr(position, "position_amt", 0)))
            entry_price = _amount(getattr(position, "entry_price", 0) or getattr(position, "avg_price", 0))
            report["broker_positions"].append({
                "symbol": _sym(getattr(position, "symbol", "")),
                "quantity": str(getattr(position, "quantity", "")),
                "side": getattr(getattr(position, "side", None), "value", str(getattr(position, "side", ""))),
                "entry_notional_usdt": round(quantity * entry_price, 8),
            })
        try:
            order_map = journal.order_exchange_map()
            in_flight = journal.in_flight()
            net_positions = journal.net_positions()
        except Exception as exc:
            report["errors"].append(f"journal read failed: {exc}")
            order_map, in_flight, net_positions = {}, [], {}

        journal_symbols = {
            str(symbol).upper().replace("-", "").replace("/", "").replace("_", "")
            for _exchange, symbol in order_map.values() if symbol
        }
        journal_symbols |= {
            str(symbol).upper().replace("-", "").replace("/", "").replace("_", "")
            for symbol in net_positions if symbol
        }
        journal_symbols |= {
            str(order.get("symbol")).upper().replace("-", "").replace("/", "").replace("_", "")
            for order in in_flight if order.get("symbol")
        }
        report["journal_symbols"] = sorted(journal_symbols)
        report["journal_net_positions"] = {symbol: str(quantity) for symbol, quantity in net_positions.items()}
        report["in_flight_orders"] = in_flight
        report["broker_positions_missing_from_journal"] = [
            position for position in report["broker_positions"]
            if _sym(position["symbol"]).upper().replace("-", "").replace("/", "").replace("_", "") not in journal_symbols
        ]
        return report

    @staticmethod
    def _resolve_orphan_protection(journal, open_positions, report, now: Optional[datetime] = None,
                                   broker: Any = None) -> None:
        """2026-11-25: a stop-UPDATE record left PROTECTION_UNKNOWN after its position closed protects nothing, yet it
        blocked every new order for ~6 h (IMX, SOXL). On a successful (blip-guarded) snapshot, close such records
        when the symbol is flat and the record is older than ORPHAN_PROTECTION_AGE_S. Entry-protection records
        (entry_order_ref set) are left alone: their entry may still fill.
        Same day: an entry INTENT with no exchange order id (send raised, e.g. "TP order failed: network timeout;
        unwound=True") blocked every order. It is closed as FAILED only when the symbol is flat AND the broker
        confirms no pending orders for it (nothing can still fill)."""
        now = now or datetime.now(timezone.utc)
        open_syms = {_norm(getattr(p, "symbol", "")) for p in open_positions}
        try:
            records = journal.in_flight()
        except Exception:
            return
        for rec in records:
            is_orphan_intent = rec.get("status") == "INTENT" and not rec.get("order_id") and broker is not None
            if not is_orphan_intent and (rec.get("status") != "PROTECTION_UNKNOWN" or rec.get("entry_order_ref")):
                continue
            if _norm(rec.get("symbol")) in open_syms:
                continue
            try:
                age = (now - datetime.fromisoformat(str(rec.get("ts")))).total_seconds()
            except Exception:
                continue
            if age < ORPHAN_PROTECTION_AGE_S:
                continue
            if is_orphan_intent:
                try:
                    ev = broker.get_pending_orders_evidence(_mk_symbol(rec.get("symbol")))
                    if ev.get("status") != "OK" or ev.get("orders"):
                        continue
                    journal.record_failed(rec["order_ref"], "no exchange order id; symbol flat and no pending "
                                                            "orders at reconciliation (send failed or unwound)")
                    report.setdefault("orphan_intent_resolved", []).append(rec.get("symbol"))
                except Exception as exc:
                    report["errors"].append(f"orphan intent resolution failed ({type(exc).__name__})")
                continue
            try:
                journal.record_terminal(rec["order_ref"], "CANCELLED",
                                        reason="position flat at reconciliation (orphan stop-update record)")
                report.setdefault("orphan_protection_resolved", []).append(rec.get("symbol"))
            except Exception as exc:
                report["errors"].append(f"orphan protection resolution failed ({type(exc).__name__})")

    def reconcile(self, broker, journal, halt_on_unrecoverable: bool = True) -> Dict[str, Any]:
        """One reconciliation pass. Returns a structured drift report."""
        report: Dict[str, Any] = {
            "in_sync": True, "halted": False, "errors": [],
            "broker_positions": [], "recoverable": [], "unrecoverable": [],
            "orders_resolved": [],
        }
        try:
            journal.recover()
        except Exception:
            report["errors"].append("journal recovery unavailable; reconciliation refused")
            report["in_sync"] = False
            return report

        # --- 1. Pull broker truth: open positions ---
        broker_positions: List[Any] = []
        try:
            broker_positions = broker.get_all_positions()
            if broker_positions is None:
                raise RuntimeError("broker returned no position snapshot")
        except Exception as e:
            report["errors"].append(f"get_all_positions failed: {e}")
            # A failed read is not evidence that a previously open position
            # closed. Keep the prior snapshot and avoid closure side effects.
            report["in_sync"] = False
            return report

        open_positions = [p for p in broker_positions
                          if abs(float(getattr(p, "quantity", 0) or getattr(p, "position_amt", 0) or 0)) > 0]
        report["broker_positions"] = [
            {"symbol": _sym(getattr(p, "symbol", "")),
             "quantity": str(getattr(p, "quantity", "")),
             "side": getattr(getattr(p, "side", None), "value", str(getattr(p, "side", "")))}
            for p in open_positions
        ]
        self._resolve_orphan_protection(journal, open_positions, report, broker=broker)

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
            requested = {kind for field, kind in (("stop_loss", "STOP_MARKET"), ("take_profit", "TAKE_PROFIT_MARKET"))
                         if o.get(field) is not None}
            ids = o.get("protective_order_ids") or {}
            missing = sorted(kind for kind in requested if not isinstance(ids, dict) or not ids.get(kind))
            try:
                reported_quantity = Decimal(str(executed_qty or 0))
                quantity_evidence = not reported_quantity.is_finite() or reported_quantity > 0
            except Exception:
                quantity_evidence = True  # malformed execution data is not proof of no exposure
            if missing and (status in {"FILLED", "PARTIALLY_FILLED", "PARTIAL"} or quantity_evidence):
                report["recoverable"].append({"order_ref": ref, "symbol": sym,
                    "issue": "requested_protection_acknowledgements_missing", "entry_status": status,
                    "missing": missing})
                report["in_sync"] = False
                try:
                    if not any(record.get("status") == "PROTECTION_UNKNOWN"
                               and record.get("entry_order_ref") == ref for record in journal.in_flight()):
                        closing_side = {"BUY": "SELL", "SELL": "BUY"}.get(str(o.get("side", "")).upper(), "UNKNOWN")
                        journal.record_protection_unknown(sym, closing_side, o.get("quantity"),
                                                          o.get("exchange"), entry_order_ref=ref)
                except Exception as persistence_error:
                    report["errors"].append(f"protection uncertainty persistence failed ({type(persistence_error).__name__})")
                    if halt_on_unrecoverable:
                        self._halt("UNVERIFIED_PROTECTION_PERSISTENCE_FAILED")
                        report["halted"] = True
                continue

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
                # A flat position cannot prove cancellation after an unknown or
                # failed order-status query. Preserve identity for reconciliation.
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
