# Phase 9 — Broker Reliability Review

**Areas covered:** 6 Broker integration · 7 Broker failover handling · 8 Error recovery ·
9 Process restart recovery (with order-validation cross-refs to area 5)
**Scope:** infrastructure safety only; strategy logic untouched.

**Live path:** `--mode production` → `bootstrap/container.py::_build_production_data_and_services`
(`:442-476`) → `broker_registry.get_execution_service(use_multi_broker=True, primary_broker='bingx')`
→ `BrokerExecutionService(use_multi_broker=True)` → `MultiBrokerExecutionService`, which builds
**real** REST adapters (BingX/Binance/MEXC/Phemex) that HMAC-sign and POST to **live** exchange
endpoints (live profile sets all `*_testnet=False`). **This is a real live-trading path.**

Caveat: the *currently-wired* sample loop reaches the real broker only via the auto-detect path;
`LiveExecutionEngine._execute_trades` (`infrastructure/execution/live_execution_engine.py:138-154`)
is an empty stub and `BrokerAPIService.place_order` (`:220-226`) returns a fake order id. The chain
must be made real **and** the gaps below fixed before any live run.

Fixes touching the real-funds path are **[GATED]** (Rule 5 — specified, not applied).

---

## AREA 6 — Broker integration

### C5 — `client_order_id` never sent → no broker-side idempotency — **Critical**
- **Measure:** `Order.client_order_id` exists (`domain/entities/order.py:47`) but is never placed in
  any payload: BingX (`bingx_adapter.py:357-363, 454-460`) and Binance
  (`binance_adapter.py:89-97` → `RestClient.place_order`) send no `clientOrderId`/`newClientOrderId`.
- **Diagnose:** Exchange-side idempotency — the standard defense against duplicate orders on
  retry/timeout — is absent. If a POST succeeds but the response is lost, a resubmit creates a
  **second live position** with no way to dedupe.
- **Fix [GATED]:** Generate a deterministic `client_order_id` per order and transmit it on every
  adapter; on uncertain responses reconcile by it before any resubmit.
- **Re-evaluate:** Enables safe retries (H6) and reconciliation (C8).

### C5b — Duplicate prevention in-memory only, racy, lost on restart — **Critical** (with C7)
- **Measure:** `infrastructure/shared/pending_orders_tracker.py:19-115` — process-singleton dict
  keyed by symbol+side; populated only *after* a successful order id
  (`multi_broker_service.py:434-436`); auto-purged after 30 min (`pending_orders_tracker.py:90`).
  The check (`:351`) → place (`:426`) window is not atomic. On Binance `get_position` always returns
  `[]` (`binance_adapter.py:182-195`), so the position-based duplicate guard is blind there.
- **Diagnose:** The only duplicate guard is volatile, coarse (symbol+side), racy, and fails open on
  broker error (`broker_execution_service.py:217-220` proceeds when `get_position` throws).
- **Fix [GATED]:** Back duplicate prevention with broker-side `client_order_id` + a startup reconcile
  (C7/9.1); fail **closed** when position state can't be verified.
- **Re-evaluate:** Removes the restart-double-entry and race windows.

### H3 — BingX SL/TP placed as separate conditional orders; failure reported as success — **High**
- **Measure:** `bingx_adapter.py:447-546` — for MARKET orders the main order is placed first, then
  SL and TP via separate `_place_conditional_order` calls; on their failure it still returns
  `{'success': True, 'order_id': main_order_id, 'conditional_orders_errors': [...]}` (`:534-546`),
  and the wrapper only logs a warning (`:104-106`).
- **Diagnose:** A live position can open with **no stop attached** while the system believes the
  order fully succeeded — unbounded-loss exposure.
- **Fix [GATED]:** Treat SL-attach failure as critical: atomically close the just-opened position or
  escalate/halt; never report success when the protective stop did not attach.
- **Re-evaluate:** Guarantees every live position carries its stop, or is unwound.

### H4 — Binance spot vs BingX futures; cross-type "failover" — **High**
- **Measure:** `binance_adapter.py:182-187` ("spot doesn't have positions" → `[]`), `:202` hits
  `api.binance.com/api/v3` (spot); BingX uses `/openApi/swap/v2` futures with `positionSide`
  (`bingx_adapter.py:471,614,813`). `multi_broker_service.py:54` can switch an order between them.
- **Diagnose:** A futures-intended position (leverage, `positionSide`, conditional SL/TP) routed to
  Binance spot executes with wrong semantics; Binance `get_position` is always blind.
- **Fix [GATED]:** Restrict live trading to one venue/instrument type, or make adapters
  instrument-type-aware and **forbid** cross-type failover.
- **Re-evaluate:** Eliminates silently-wrong execution across venues.

### H5 — `cancel_order` / `get_execution_status` non-functional in the live path — **High**
- **Measure:** `multi_broker_service.py:842-867`:
  `"Cannot cancel order ... without knowing original exchange"; return False` and
  `return "unknown"`. Single-broker path uses a placeholder `Symbol("BTCUSDT")`
  (`broker_execution_service.py:730,745`).
- **Diagnose:** In the wired config (`use_multi_broker=True`) there is **no working way to cancel an
  order or query status** — no order→exchange mapping is stored. This cripples any kill-switch /
  manual-intervention path.
- **Fix [GATED]:** Persist `order_id → (exchange, symbol)` at placement; implement real cancel/status
  against the originating exchange.
- **Re-evaluate:** Restores operator control and a working kill path (ties to area 15).

---

## AREA 7 — Broker failover handling

### M — "Failover" is symbol-availability routing, not health/error failover — **Medium**
`multi_broker_service.py:318-451` chooses an exchange by `_find_best_exchange_for_symbol`; on
`place_order` failure (`:426-447`) it logs and `return None` — it does **not** try the next exchange.
The "multi-broker" naming overstates resilience. Fix: add explicit health-checked failover on
transient errors, subject to the instrument-type constraint (H4).

### M — order-placement-enabled flag pins broker, skips availability recheck — **Medium**
`multi_broker_service.py:360-385`: if `bingx_order_placement_enabled` is set, `best_exchange='bingx'`
unconditionally, then `:390 if best_exchange in self.brokers` proceeds without re-validating that the
symbol exists on the pinned broker. Fix: re-validate symbol availability on the forced broker.

---

## AREA 8 — Error recovery

### C6 — All order errors collapse to `None`; rejected vs unknown indistinguishable — **Critical**
- **Measure:** `broker_execution_service.py:382-389` and `multi_broker_service.py:444-451` both
  `except Exception: ... return None` ("Return None ... to prevent system crashes"). Duplicate
  prevention, validation failure, not-connected, and genuine API errors **all return `None`**.
- **Diagnose:** On a network timeout the order may or may not have reached the exchange, yet the
  system treats `None` as "cleanly rejected" — no reconcile, no alert, no retry. Classic source of
  phantom/duplicate live positions; callers also get no signal to halt.
- **Fix [GATED]:** Return a **typed result** (Placed / Rejected / Unknown-needs-reconcile). On
  Unknown, query the exchange by `client_order_id` (C5) before any further action.
- **Re-evaluate:** Makes uncertainty explicit and recoverable instead of silently lost.

### H6 — No retry/backoff on any broker API call — **High**
- **Measure:** `bingx_adapter.py:242-313` `_make_request` makes one attempt and `raise`s; the Binance
  `RestClient` returns `None` on first failure. No `tenacity`/backoff/`max_attempts` anywhere in
  broker/execution code.
- **Diagnose:** A single transient 5xx/timeout permanently fails the action; with C6 the outcome is
  silently dropped.
- **Fix [GATED]:** Bounded exponential backoff for idempotent reads, and for writes **only** when
  paired with `client_order_id` idempotency (C5).
- **Re-evaluate:** Survives transient faults without risking duplicates.

### M — Rate limiter can block the trading thread indefinitely — **Medium**
`shared/rate_limiter.py:60-68` `while not self.acquire(...): time.sleep(0.1)` with no timeout; BingX
limit is 5 req/min (`:94`) and every request waits (`bingx_adapter.py:237-240`). Under burst load,
time-sensitive exits/stops can stall unboundedly. Fix: add a max-wait with a raised/alerted timeout.

### M — Broker connect failure swallowed at init; service appears "ready" while disconnected — **Medium**
`broker_execution_service.py:114-125` logs and "Don't raise"; `bingx_adapter.connect()` (`:50-58`)
returns `False` on exception. The orchestrator initializes "successfully" with a broker that never
connected; orders then fail the `connected` guard (`:298-301`) and return `None` (C6). Fix: a startup
readiness check that fails loudly if the primary broker cannot authenticate/connect.

---

## AREA 9 — Process restart recovery

### C7 — No state reconciliation on startup — the system starts **blind** — **Critical**
- **Measure:** `production_trading_orchestrator.py:83-93` (`initialize_system`) and the auto-detect
  equivalent only start threads and set `is_running=True`. **Neither queries `get_all_positions()`,
  open orders, or pending orders at startup.** `PendingOrdersTracker` is in-memory and starts empty.
- **Diagnose:** After any restart/crash/redeploy, the system has no knowledge of open positions,
  working stops/TPs, or in-flight orders. It will open **duplicate** same-direction positions (empty
  guard) and never manage pre-existing positions/stops.
- **Fix [GATED]:** On startup, fetch live positions + open orders per broker, rebuild internal state,
  adopt/reconcile existing stops **before** enabling new entries.
- **Re-evaluate:** Eliminates blind-start double-exposure and orphaned stops (depends on C5/C8).

### H7 — No persistence of in-flight / order→exchange state — **High**
- **Measure:** pending orders live only in class-level dicts (`pending_orders_tracker.py:27-28`); no
  order→exchange map is stored (root of H5); nothing is written durably at placement time.
- **Diagnose:** A crash between "exchange accepted" and "response processed" leaves an untracked live
  order; with C5 missing it can't be matched even after fetching positions.
- **Fix [GATED]:** Persist an order journal (intent → submitted → ack, with `client_order_id` and
  exchange) to durable storage; replay/reconcile on startup.
- **Re-evaluate:** Closes the lost-write window (ties to C8 / DB integrity).

### M — Shutdown does not flush/cancel/snapshot; daemon threads die abruptly — **Medium**
`production_trading_orchestrator.py:276-284` `stop_system` only sets `is_running=False`. No draining,
no cancel of working orders, no state snapshot. Fix: graceful shutdown that snapshots state and
optionally cancels/records working orders.

---

## Priority order (highest leverage first)
1. **C5** broker-side idempotency (`client_order_id`) — prerequisite for safe retries & reconcile.
2. **C6** typed order results + reconcile-on-unknown; fail-closed (with H2 from risk review).
3. **C7/H7** startup reconciliation + durable order journal.
4. **H3** never report success without an attached stop; **H5** working cancel/status; **H4**
   forbid cross-instrument failover.
5. **H6** retry/backoff; mediums (health-checked failover, rate-limit timeout, connect readiness).
