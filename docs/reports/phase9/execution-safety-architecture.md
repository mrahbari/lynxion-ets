# Execution Safety Architecture — LIVE_EXECUTION_GUARD

**Date:** 2026-06-12
**Scope:** Production execution-safety enforcement layer. **No strategy logic changed.**
**Objective:** Eliminate accidental live-trading risk while preserving testnet functionality, by
enforcing the execution-safety flags at a single, unmissable point before any order is sent.

This addresses the Phase-9 finding that the safety flags (`paper_trading`, `*_testnet`,
`*_order_placement_enabled`) and the kill switch / circuit breaker existed but were **not enforced**
in the live order path. `BROKER_TESTNET=false` is a valid, required endpoint selector — the defect
was missing *permission* enforcement, not the flag's existence.

---

## 1. What was built

A single process-wide guard — `shared/live_execution_guard.py` (`LiveExecutionGuard`, exposed as the
`live_execution_guard` singleton) — that answers exactly one question per order:

> *May this order be sent to `<broker>`, and how — blocked, simulated (paper), testnet, or live?*

It is consulted at **every** real-broker send-point, immediately before the order leaves the
execution service for the broker wrapper.

### The decision matrix (single source of truth)

Evaluated in `LiveExecutionGuard.evaluate(broker_name, settings, order)`, first match wins:

| # | Condition | Outcome | Sent to exchange? |
|---|-----------|---------|-------------------|
| 1 | Kill switch **engaged** | `BLOCKED` | No |
| 2 | Circuit breaker **OPEN** for broker | `BLOCKED` | No |
| 3 | `paper_trading == true` | `PAPER` (simulated id) | **No** (override) |
| 4 | `<broker>_order_placement_enabled == false` | `BLOCKED` (no permission) | No |
| 5 | `<broker>_testnet == true` | `TESTNET` | Yes → **testnet** endpoint |
| 6 | live endpoint **and** `LIVE_TRADING=true` | `LIVE` | Yes → **live** endpoint |
| 7 | live endpoint **and** no `LIVE_TRADING` | `BLOCKED` (accidental live prevented) | No |

Key invariants this encodes:

- **`paper_trading` is an absolute override** (rule 3): when on, nothing is ever sent — used for the
  approved "paper trading validation" workflow.
- **`*_testnet` only selects the endpoint** (rules 5–7): testnet routing works *without*
  `LIVE_TRADING` (preserving testnet functionality), and `testnet=false` *alone* never authorizes a
  live send — the explicit `LIVE_TRADING=true` opt-in is the permission gate.
- **Accidental live execution is impossible** without `LIVE_TRADING=true` (rule 7), regardless of how
  the per-broker order-placement defaults are set.
- **Kill switch and circuit breaker are wired into the path** (rules 1–2): both short-circuit to
  `BLOCKED`.
- **Fail-safe defaults**: if settings are unavailable, `paper_trading` resolves to `true` (simulate)
  and order-placement permission resolves to `false` — the guard fails *closed* / to *paper*.

### Runtime kill switch

The guard owns a process-wide runtime kill switch (`engage_kill_switch(reason)` /
`disengage_kill_switch()` / `is_killed()`), default **disengaged**. The orchestrators' risk-monitoring
loops now **engage** it on a critical drawdown/leverage breach (previously alert-only), so a breach
actually halts new sends through the guard.

### Circuit breaker

Per-broker breakers named `order_path:<broker>` are obtained from the existing
`shared/circuit_breaker.py` manager. The execution services call
`record_send_result(broker, success)` after each attempted send; repeated failures trip the breaker
OPEN, which the guard then treats as `BLOCKED` (rule 2) until the breaker's reset timeout elapses.

---

## 2. Before / after flow

### BEFORE — flags defined but unenforced (accidental live possible)

```
orchestrator
  └─ execution_service.execute_order(order)        [BrokerExecutionService]
       ├─ symbol-approved? duplicate? SL/TP shape?  (validation FAILS OPEN on error)
       └─ dispatch:
            ├─ multi:  MultiBrokerExecutionService.execute_order(order)
            │            ├─ route to best_exchange
            │            └─ broker.place_order(order) ───────────────►  EXCHANGE  ⚠️ LIVE
            └─ single: broker.place_order(order) ─────────────────────►  EXCHANGE  ⚠️ LIVE

   paper_trading flag .............. READ INTO CONFIG, NEVER CHECKED  (dead)
   *_testnet ....................... selects endpoint (correct) but ALSO the only thing between
                                     the system and live funds
   *_order_placement_enabled ....... checked only for routing, not as a permission gate
   LIVE_TRADING .................... did not exist
   kill switch ..................... defined (backtest only), NOT in this path
   circuit breaker ................. defined, NOT in this path
   risk breach ..................... ALERT ONLY → keeps trading
```

### AFTER — single guard enforced before every send

```
orchestrator
  │   risk-monitoring loop ── critical breach ──► live_execution_guard.engage_kill_switch(reason)
  └─ execution_service.execute_order(order)        [BrokerExecutionService]
       ├─ symbol-approved? duplicate? SL/TP shape?
       └─ dispatch:
            ├─ multi:  MultiBrokerExecutionService.execute_order(order)
            │            ├─ route to best_exchange
            │            ├─ ╔══════════════════════════════════════════════╗
            │            │  ║  LIVE_EXECUTION_GUARD.evaluate(best_exchange) ║
            │            │  ╚══════════════════════════════════════════════╝
            │            │        ├─ BLOCKED  → return None  (no send) 🛑
            │            │        ├─ PAPER    → return PAPER-… id (no send) 🧪
            │            │        └─ TESTNET/LIVE → authorize
            │            └─ broker.place_order(order) ──► EXCHANGE (testnet|live)
            │               record_send_result(best_exchange, ok)  → feeds circuit breaker
            └─ single: ╔════════════════════════════════════════════════╗
                       ║  LIVE_EXECUTION_GUARD.evaluate(self.broker_type)║
                       ╚════════════════════════════════════════════════╝
                            ├─ BLOCKED → return None 🛑
                            ├─ PAPER   → return PAPER-… id 🧪
                            └─ TESTNET/LIVE → broker.place_order(order) ──► EXCHANGE
                               record_send_result(...)  → feeds circuit breaker

   paper_trading ............ ENFORCED (rule 3 — absolute override, simulate)
   *_testnet ................ ONLY selects endpoint (rules 5–7); cannot authorize live alone
   *_order_placement_enabled  ENFORCED as permission gate (rule 4)
   LIVE_TRADING ............. required for any live send (rules 6–7); default off
   kill switch .............. wired in (rule 1) + engaged by risk breaches
   circuit breaker .......... wired in (rule 2) + fed by send results
```

There is exactly **one** decision function (`evaluate`) and it is invoked at the only two code points
where a real order can leave for an exchange.

---

## 3. Enforcement points (where the guard is invoked)

| Send-point | File | Position | Broker known as |
|------------|------|----------|-----------------|
| Multi-broker (wired production default) | `infrastructure/brokers/multi_broker_service.py` | in `execute_order`, immediately before `broker.place_order` (was ~:426) | `best_exchange` (post-routing) |
| Single-broker | `infrastructure/services/broker_execution_service.py` | in `execute_order` single-broker branch, before `self.broker.place_order` (was ~:316) | `self.broker_type` |

The multi-broker branch of `BrokerExecutionService.execute_order` delegates to
`MultiBrokerExecutionService.execute_order`, which is itself guarded — so it is not double-evaluated.

Kill-switch engagement wired into:
- `infrastructure/orchestrators/production_trading_orchestrator.py` `_risk_monitoring_loop`
- `infrastructure/orchestrators/auto_detection_orchestrator.py` risk-monitoring loop

---

## 4. Unsafe bypass paths — analysis & disposition

The objective requires eliminating paths by which an order could reach a **real** exchange without
passing the guard. Every order-emitting path was traced:

| # | Path | Reaches real funds? | Status |
|---|------|--------------------|--------|
| B1 | `BrokerExecutionService.execute_order` → single-broker `self.broker.place_order` | **Yes** | ✅ **GUARDED** (single-broker branch) |
| B2 | `BrokerExecutionService.execute_order` → multi → `MultiBrokerExecutionService.execute_order` → `broker.place_order` | **Yes** | ✅ **GUARDED** (multi send-point) |
| B3 | Direct `MultiBrokerExecutionService.execute_order(order)` (used as an `ExecutionPort`) | **Yes** | ✅ **GUARDED** (same multi send-point) |
| B4 | `infrastructure/execution/advanced_execution_service.py` (TWAP/iceberg) → `self.execution_port.execute_order` | Yes, *if wired* | ✅ Covered — delegates to the guarded `execute_order`; not in the production composition root |
| B5 | `infrastructure/orchestrators/_auto_detection_execution.py:248` `self.execution_service.execute_order(order)` | **Yes** | ✅ Covered — funnels through the guarded `execute_order` |
| B6 | `infrastructure/execution/execution_adapters.py` (`DirectExecutionAdapter`/TWAP) `broker.place_order` ×4 | **No** — uses `MockBrokerAdapter` | ➖ Not a live path; not wired into production. Left unchanged (no real funds). |
| B7 | `infrastructure/execution/live_execution_engine.py` `_execute_trades` | No — empty stub today | ➖ Stub; when implemented it must route through the guarded `execute_order` (noted in release checklist) |
| B8 | Broker adapter `place_order` / BingX `_place_conditional_order` (SL/TP) called directly | Yes, but only *after* a guard-authorized main order | ➖ Conditional SL/TP orders are downstream of an authorized entry; they do not constitute an independent accidental-live entry path |

**Removed / neutralized accidental-live bypasses:** B1, B2, B3 (and therefore B4, B5 which feed them).
These are the only paths in the wired production composition that could send a real order; all now
pass the single guard, and none can produce a live send without an explicit `LIVE_TRADING=true`.

**Explicitly out of scope (not live):** B6 (mock broker), B7 (unimplemented stub), B8 (downstream of
an authorized order). B7's future implementation is flagged in `production_release_checklist.md` to
route through `execute_order`.

---

## 5. Operating modes (operator reference)

| Goal | `paper_trading` | `*_order_placement_enabled` | `*_testnet` | `LIVE_TRADING` | Result |
|------|-----------------|-----------------------------|-------------|----------------|--------|
| Paper / dry-run validation | `true` | any | any | any | Simulated `PAPER-…` ids, nothing sent |
| Testnet integration | `false` | `true` | `true` | unset | Real orders to **testnet** endpoint |
| Live trading (deliberate) | `false` | `true` | `false` | **`true`** | Real orders to **live** endpoint |
| Misconfig safety net | `false` | `true` | `false` | unset | **BLOCKED** — accidental live prevented |
| Emergency halt | any | any | any | any | **BLOCKED** while kill switch engaged |

`LIVE_TRADING` is read from the environment on every evaluation, so it can be revoked without a
restart. It is intentionally **not** a config-schema field (kept as an explicit, separate env opt-in).

---

## 6. Verification

- `tests/unit/test_live_execution_guard.py` — 11 cases covering the full matrix, kill-switch
  precedence, testnet-≠-permission, fail-safe defaults, simulated-id format, and circuit-breaker
  blocking. **Result: 11/11 passed** (`.venv/bin/python -m pytest`).
- All edited modules byte-compile; `shared.live_execution_guard`,
  `infrastructure.brokers.multi_broker_service`, and
  `infrastructure.services.broker_execution_service` import cleanly.
- The guard module is standard-library-only at import time (circuit-breaker imported lazily), so it
  is independently testable and adds no heavy import-time coupling.

### Recommended follow-ups (not required for accidental-live safety; see release checklist)
- Add a **startup preflight** that logs the resolved mode per broker and refuses to start in
  LIVE/PRODUCTION when keys/flags are inconsistent.
- Surface `live_execution_guard.status()` on the dashboard/monitoring for live visibility of mode,
  kill-switch state, and breaker states.
- Route the future `LiveExecutionEngine._execute_trades` implementation through the guarded
  `execute_order` (B7).

---

## 7. Files changed

| File | Change |
|------|--------|
| `shared/live_execution_guard.py` | **New** — the unified guard (decision matrix, runtime kill switch, circuit-breaker integration, simulated ids, status). |
| `infrastructure/brokers/multi_broker_service.py` | Guard enforced before `broker.place_order`; `record_send_result` on success/failure. |
| `infrastructure/services/broker_execution_service.py` | Guard enforced in the single-broker send branch; `record_send_result` on result. |
| `infrastructure/orchestrators/production_trading_orchestrator.py` | Critical risk breach now **engages** the guard kill switch (was alert-only). |
| `infrastructure/orchestrators/auto_detection_orchestrator.py` | Same kill-switch engagement on critical breach. |
| `tests/unit/test_live_execution_guard.py` | **New** — 11-case regression suite for the guard. |

No strategy modules were modified.
