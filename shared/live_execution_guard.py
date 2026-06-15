"""LIVE_EXECUTION_GUARD — the single, unified execution-safety enforcement point.

Phase-9 execution-safety layer. This guard sits in front of EVERY real-broker
order send (the "execution service -> broker wrapper" boundary) and decides, for
each order, whether it may be sent and *how*:

    BLOCKED  -> do not send; reject the order
    PAPER    -> do not send; return a simulated order id (paper-trading override)
    TESTNET  -> send to the broker's TESTNET endpoint (endpoint already selected
                by the adapter's testnet config); preserves testnet functionality
    LIVE     -> send to the broker's LIVE endpoint (real funds)

Design goals (Phase-9 mission):
  * One decision function, one source of truth — no scattered ad-hoc flag checks.
  * ``paper_trading`` is an absolute override: when on, nothing is ever sent.
  * ``*_testnet`` ONLY selects the endpoint — it does NOT, by itself, grant
    permission to trade live. Live sends require an explicit ``LIVE_TRADING=true``.
  * Accidental live execution is impossible without that explicit opt-in.
  * The runtime kill switch and per-broker circuit breaker are wired *into* this
    path: if either is tripped, no order is sent.

Import-time dependencies are restricted to the standard library so this module is
trivially unit-testable in isolation (the circuit-breaker integration is imported
lazily inside methods).
"""

from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Tuple

_log = logging.getLogger("LiveExecutionGuard")

_TRUTHY = {"1", "true", "yes", "on", "y", "t"}
_KNOWN_BROKERS = ("bingx", "binance", "mexc", "phemex")


class ExecutionMode(str, Enum):
    """The decision outcome for a single order."""
    BLOCKED = "blocked"   # do not send; reject
    PAPER = "paper"       # do not send; simulate (paper_trading override)
    TESTNET = "testnet"   # send to the testnet endpoint
    LIVE = "live"         # send to the live endpoint (real funds)


@dataclass(frozen=True)
class GuardDecision:
    """Immutable result of a guard evaluation."""
    mode: ExecutionMode
    reason: str
    broker: str
    testnet: bool
    live_trading_flag: bool
    rule: str = ""  # which precedence rule decided (decision-trace marker)
    # Exact input-flag values the decision was computed from (single atomic read),
    # so the Execution Truth Ledger records what was actually decided on — not a re-read.
    flags: Dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        """True when the order may proceed (either as a real send or a simulation)."""
        return self.mode is not ExecutionMode.BLOCKED

    @property
    def simulate(self) -> bool:
        """True when the order must be simulated and NOT sent to any exchange."""
        return self.mode is ExecutionMode.PAPER

    @property
    def is_live_send(self) -> bool:
        """True only when this would hit a live (real-funds) endpoint."""
        return self.mode is ExecutionMode.LIVE

    @property
    def is_real_send(self) -> bool:
        """True when this would contact an exchange (LIVE or TESTNET) — i.e. needs a connection."""
        return self.mode in (ExecutionMode.LIVE, ExecutionMode.TESTNET)


def _is_truthy(value: Optional[str]) -> bool:
    return str(value).strip().lower() in _TRUTHY if value is not None else False


class LiveExecutionGuard:
    """Process-wide execution-safety guard (single instance — see module global).

    The guard is intentionally free of trading-domain logic: it answers exactly one
    question — "is this order allowed to be sent, and how?" — from configuration,
    the ``LIVE_TRADING`` environment opt-in, the runtime kill switch, and the
    per-broker circuit breaker.
    """

    _LIVE_TRADING_ENV = "LIVE_TRADING"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # Runtime kill switch — defaults DISENGAGED, but any engage() blocks all sends.
        self._killed = False
        self._kill_reason: Optional[str] = None
        self._killed_at: Optional[str] = None
        self._sim_counter = 0
        # Optional callable returning a JSON-able snapshot of risk-engine state for the
        # Execution Truth Ledger. Defaults to None -> recorded as "not wired" (honest:
        # the portfolio risk engine is not currently on the order path).
        self._risk_state_provider = None
        # Optional callable(order) -> fill-summary dict, invoked for PAPER decisions to
        # simulate a fill (positions/PnL/equity). Defaults to None -> a synthetic id only.
        self._paper_fill_handler = None
        # Optional callable(order) -> (allowed: bool, reason: str). Enforces the portfolio
        # risk engine on EVERY order path (paper and live). Defaults to None -> no risk gate.
        self._risk_enforcer = None

    def set_risk_enforcer(self, enforcer) -> None:
        """Register a callable(order)->(allowed, reason) that enforces portfolio risk admission."""
        self._risk_enforcer = enforcer

    def set_risk_state_provider(self, provider) -> None:
        """Register a zero-arg callable returning a JSON-able risk-engine state snapshot."""
        self._risk_state_provider = provider

    def set_paper_fill_handler(self, handler) -> None:
        """Register a callable(order)->dict that simulates a PAPER fill (paper-trading engine)."""
        self._paper_fill_handler = handler

    # -- live-trading opt-in -------------------------------------------------------

    def live_trading_enabled(self) -> bool:
        """Explicit, environment-driven opt-in for LIVE (real-funds) sends.

        Read fresh from the environment each call so an operator can revoke it
        without a process restart. Defaults to False (safe).
        """
        return _is_truthy(os.getenv(self._LIVE_TRADING_ENV))

    # -- runtime kill switch -------------------------------------------------------

    def engage_kill_switch(self, reason: str) -> None:
        """Engage the kill switch — every subsequent order is BLOCKED until disengaged."""
        with self._lock:
            already = self._killed
            self._killed = True
            self._kill_reason = reason
            self._killed_at = datetime.now(timezone.utc).isoformat()
        if not already:
            _log.critical("LIVE_EXECUTION_GUARD kill switch ENGAGED: %s", reason)

    def disengage_kill_switch(self) -> None:
        """Disengage the kill switch (operator action)."""
        with self._lock:
            self._killed = False
            self._kill_reason = None
            self._killed_at = None
        _log.warning("LIVE_EXECUTION_GUARD kill switch DISENGAGED")

    def is_killed(self) -> bool:
        with self._lock:
            return self._killed

    # -- circuit breaker (lazy, per-broker) ----------------------------------------

    def _breaker(self, broker: str):
        """Get/create the per-broker order-path circuit breaker from the shared manager."""
        from shared.circuit_breaker import CircuitBreaker, circuit_breaker_manager
        name = f"order_path:{broker}"
        cb = circuit_breaker_manager.get_circuit_breaker(name)
        if cb is None:
            cb = CircuitBreaker(name=name, failure_threshold=5, timeout=60)
            circuit_breaker_manager.register_circuit_breaker(cb)
        return cb

    def breaker_blocks(self, broker: str) -> Tuple[bool, str]:
        """Return (blocked, reason). Blocked iff the breaker is OPEN and not yet eligible to reset.

        Breaker state is read under the guard lock so it cannot change between this
        check and a send authorized in the same locked section (see authorize_and_send).
        """
        with self._lock:
            try:
                status = self._breaker(broker).get_status()
            except Exception:  # pragma: no cover - breaker must never break the guard
                return (False, "")
            if status.get("state") == "open" and not status.get("should_reset"):
                return (True, f"circuit breaker OPEN for {broker} (failures={status.get('failure_count')})")
            return (False, "")

    def record_send_result(self, broker: str, success: bool) -> None:
        """Feed the per-broker breaker after an attempted send (success closes, failure trips).

        Mutates breaker state under the guard lock so breaker reads/writes are serialized
        with decisions — no decision can observe a half-updated breaker.
        """
        with self._lock:
            try:
                cb = self._breaker(broker)
                if success:
                    cb._on_success()
                else:
                    cb._on_failure()
            except Exception:  # pragma: no cover
                pass

    # -- the single decision -------------------------------------------------------

    def evaluate(self, broker_name: str, settings: Any = None, order: Any = None) -> GuardDecision:
        """Decide whether/how an order to ``broker_name`` may be sent.

        Precedence (first match wins):
          1. kill switch engaged              -> BLOCKED
          2. circuit breaker OPEN             -> BLOCKED
          3. paper_trading enabled            -> PAPER (simulate; never sent)
          4. order placement not enabled      -> BLOCKED (no permission for this broker)
          5. testnet endpoint                 -> TESTNET (allowed; no LIVE_TRADING needed)
          6. live endpoint + LIVE_TRADING=true-> LIVE
          7. live endpoint + no LIVE_TRADING  -> BLOCKED (accidental live prevented)
        """
        broker = (broker_name or "").lower()
        # Single atomic read of every decision input, so the decision and the ledger
        # record reflect exactly the same values even under rapid concurrent flag changes.
        cfg = self._broker_cfg(settings)
        paper = self._resolve_paper_trading(settings)
        placement = self._resolve_order_placement_enabled(settings, broker)
        testnet = self._resolve_testnet(settings, broker)
        global_testnet = bool(getattr(cfg, "testnet", True)) if cfg is not None else True
        live_flag = self.live_trading_enabled()
        snapshot = {
            "paper_trading": paper,
            "testnet_resolved": testnet,
            "global_testnet": global_testnet,
            "order_placement_enabled": placement,
            "live_trading_env": live_flag,
        }

        def decision(mode: ExecutionMode, reason: str, rule: str) -> GuardDecision:
            return GuardDecision(mode=mode, reason=reason, broker=broker,
                                 testnet=testnet, live_trading_flag=live_flag, rule=rule,
                                 flags=dict(snapshot))

        # 1. Kill switch
        with self._lock:
            if self._killed:
                return decision(ExecutionMode.BLOCKED,
                                f"kill switch engaged: {self._kill_reason}", "1:kill_switch")

        # 2. Circuit breaker
        blocked, reason = self.breaker_blocks(broker)
        if blocked:
            return decision(ExecutionMode.BLOCKED, reason, "2:circuit_breaker")

        # 2b. Portfolio risk admission — enforced on EVERY order path (paper and live).
        # A risk-rejected order is blocked outright (it is not even paper-simulated).
        if self._risk_enforcer is not None and order is not None:
            try:
                allowed, risk_reason = self._risk_enforcer(order)
            except Exception as e:
                allowed, risk_reason = False, f"risk enforcer error: {e}"  # fail closed
            if not allowed:
                return decision(ExecutionMode.BLOCKED, risk_reason, "2b:risk_engine")

        # 3. Paper-trading override — strongest "never send" signal.
        if paper:
            return decision(ExecutionMode.PAPER,
                            "paper_trading enabled — order simulated, not sent", "3:paper_trading")

        # 4. Order-placement permission for this broker.
        if not placement:
            return decision(ExecutionMode.BLOCKED,
                            f"order placement not enabled for '{broker}' "
                            f"(set {broker.upper()}_ORDER_PLACEMENT_ENABLED=true to allow)",
                            "4:order_placement_permission")

        # 5. Testnet endpoint — real order send, but no real funds. No LIVE_TRADING needed.
        if testnet:
            return decision(ExecutionMode.TESTNET, f"sending to {broker} TESTNET endpoint", "5:testnet_endpoint")

        # 6/7. Live endpoint — requires the explicit opt-in.
        if live_flag:
            return decision(ExecutionMode.LIVE, "LIVE trading authorized (LIVE_TRADING=true)", "6:live_authorized")
        return decision(ExecutionMode.BLOCKED,
                        "live endpoint requires explicit LIVE_TRADING=true — "
                        "accidental live execution prevented", "7:live_blocked_no_optin")

    # -- simulated order ids -------------------------------------------------------

    def simulated_order_id(self, order: Any = None, broker: str = "sim") -> str:
        """Deterministic-ish synthetic id for PAPER orders (clearly marked, never a real id)."""
        with self._lock:
            self._sim_counter += 1
            n = self._sim_counter
        symbol = ""
        try:
            sym = getattr(order, "symbol", None)
            symbol = getattr(sym, "value", None) or (str(sym) if sym is not None else "")
        except Exception:
            symbol = ""
        symbol = (symbol or "NA").replace("/", "").replace(" ", "")
        return f"PAPER-{(broker or 'sim').upper()}-{symbol}-{n:06d}"

    # -- atomic authorize + send (race-free) + Execution Truth Ledger -------------

    @staticmethod
    def _order_symbol(order: Any) -> str:
        try:
            sym = getattr(order, "symbol", None)
            return getattr(sym, "value", None) or (str(sym) if sym is not None else "")
        except Exception:
            return ""

    def flags_snapshot(self, settings: Any, broker: str) -> Dict[str, Any]:
        """Immutable snapshot of the input flags that drive the decision."""
        cfg = self._broker_cfg(settings)
        return {
            "paper_trading": self._resolve_paper_trading(settings),
            "testnet_resolved": self._resolve_testnet(settings, broker),
            "global_testnet": bool(getattr(cfg, "testnet", True)) if cfg is not None else True,
            "order_placement_enabled": self._resolve_order_placement_enabled(settings, broker),
            "live_trading_env": self.live_trading_enabled(),
        }

    def states_snapshot(self, broker: str) -> Dict[str, Any]:
        """Snapshot of the runtime safety states (kill switch, breaker, risk engine)."""
        with self._lock:
            kill = {"engaged": self._killed, "reason": self._kill_reason, "since": self._killed_at}
        try:
            breaker = self._breaker(broker).get_status()
        except Exception:
            breaker = {"state": "unavailable"}
        risk: Dict[str, Any] = {"status": "not_wired_into_order_path"}
        if self._risk_state_provider is not None:
            try:
                risk = dict(self._risk_state_provider())
            except Exception as e:  # pragma: no cover
                risk = {"status": "provider_error", "error": str(e)}
        return {"kill_switch": kill, "circuit_breaker": breaker, "risk_engine": risk}

    def authorize_and_send(self, broker_name: str, settings: Any, order: Any, send_fn,
                           ledger: Any = None):
        """Atomically decide and (if permitted) send, writing the Execution Truth Ledger.

        The whole decision + ledger write + send happens under the guard lock, so an
        ``engage_kill_switch`` (or breaker trip) cannot interleave between the decision
        and the send — no live/testnet send can *start* once the kill switch is engaged.
        The ETL ``decision`` record is written BEFORE ``send_fn`` is ever called and
        cannot be bypassed (this is the only authorized send path).

        Returns ``(GuardDecision, order_id_or_None)``. ``send_fn`` is a zero-arg callable
        performing the real ``broker.place_order``; exceptions propagate after being
        recorded.
        """
        if ledger is None:
            from shared.execution_truth_ledger import execution_truth_ledger as ledger
        broker = (broker_name or "").lower()
        symbol = self._order_symbol(order)

        with self._lock:
            decision = self.evaluate(broker_name, settings, order)
            order_ref = ledger.new_order_ref()
            # --- PRE-SEND record: written BEFORE any send attempt, cannot be bypassed ---
            ledger.append("decision", {
                "order_ref": order_ref,
                "symbol": symbol,
                "broker": broker,
                "route": decision.mode.value.upper(),
                "decision_trace": {"rule": decision.rule, "reason": decision.reason},
                "input_flags": decision.flags,  # exact values the decision used (atomic)
                **self.states_snapshot(broker),
            })

            if not decision.allowed:
                return decision, None

            if decision.simulate:
                # Paper fill simulation (positions/PnL/equity) if a handler is registered;
                # otherwise a bare synthetic id. Runs under the guard lock with the decision.
                paper_fill = None
                if self._paper_fill_handler is not None:
                    try:
                        paper_fill = self._paper_fill_handler(order)
                    except Exception as e:  # a fill-sim error must not break the safety path
                        paper_fill = {"filled": False, "error": str(e)}
                sim_id = (paper_fill or {}).get("order_id") or self.simulated_order_id(order, broker)
                ledger.append("result", {
                    "order_ref": order_ref, "symbol": symbol, "broker": broker, "route": "PAPER",
                    "order_id": sim_id, "broker_response": None, "sent_to_exchange": False,
                    "execution_latency_ms": 0.0, "success": True, "paper_fill": paper_fill,
                })
                return decision, sim_id

            # LIVE / TESTNET — real send, performed under the lock for race-freedom.
            t0 = time.perf_counter()
            try:
                order_id = send_fn()
            except Exception as e:
                latency = round((time.perf_counter() - t0) * 1000.0, 3)
                self.record_send_result(broker, success=False)
                ledger.append("result", {
                    "order_ref": order_ref, "symbol": symbol, "broker": broker,
                    "route": decision.mode.value.upper(), "order_id": None,
                    "broker_response": f"EXCEPTION: {e}", "sent_to_exchange": True,
                    "execution_latency_ms": latency, "success": False,
                })
                raise
            latency = round((time.perf_counter() - t0) * 1000.0, 3)
            self.record_send_result(broker, success=bool(order_id))
            ledger.append("result", {
                "order_ref": order_ref, "symbol": symbol, "broker": broker,
                "route": decision.mode.value.upper(), "order_id": order_id,
                "broker_response": str(order_id) if order_id else None, "sent_to_exchange": True,
                "execution_latency_ms": latency, "success": bool(order_id),
            })
            return decision, order_id

    # -- status (monitoring) -------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        with self._lock:
            base = {
                "kill_switch_engaged": self._killed,
                "kill_reason": self._kill_reason,
                "killed_at": self._killed_at,
                "live_trading_enabled": self.live_trading_enabled(),
            }
        try:
            from shared.circuit_breaker import circuit_breaker_manager
            base["circuit_breakers"] = {
                n: s for n, s in circuit_breaker_manager.get_all_statuses().items()
                if n.startswith("order_path:")
            }
        except Exception:
            base["circuit_breakers"] = {}
        return base

    # -- config resolution (defensive) ---------------------------------------------

    @staticmethod
    def _broker_cfg(settings: Any):
        return getattr(settings, "broker", None) if settings is not None else None

    def _resolve_paper_trading(self, settings: Any) -> bool:
        """``paper_trading`` defaults to True (safe) when settings are unavailable."""
        cfg = self._broker_cfg(settings)
        if cfg is None:
            return True
        return bool(getattr(cfg, "paper_trading", True))

    def _resolve_testnet(self, settings: Any, broker: str) -> bool:
        """Per-broker testnet flag, falling back to the global ``testnet`` (default True)."""
        cfg = self._broker_cfg(settings)
        if cfg is None:
            return True
        global_testnet = bool(getattr(cfg, "testnet", True))
        if broker in _KNOWN_BROKERS:
            return bool(getattr(cfg, f"{broker}_testnet", global_testnet))
        return global_testnet

    def _resolve_order_placement_enabled(self, settings: Any, broker: str) -> bool:
        """Per-broker order-placement permission (defaults False — safe)."""
        cfg = self._broker_cfg(settings)
        if cfg is None:
            return False
        if broker in _KNOWN_BROKERS:
            return bool(getattr(cfg, f"{broker}_order_placement_enabled", False))
        # Unknown broker name: fall back to whether ANY broker is enabled is unsafe;
        # require an explicit per-broker flag, so default to blocked.
        return False


# Process-wide singleton — the one guard every send path consults.
live_execution_guard = LiveExecutionGuard()


__all__ = ["LiveExecutionGuard", "GuardDecision", "ExecutionMode", "live_execution_guard"]
