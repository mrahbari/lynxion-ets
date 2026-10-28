# Live Trading Readiness Audit

**Date:** 2026-06-12
**Scope:** What remains before the system can safely operate with **real funds**. Execution
correctness + operational readiness only. Strategy program is closed (READY = 0); no strategy/signal
/parameter/optimization work performed.
**Method:** end-to-end code trace + a controlled **testnet** validation run with valid BingX
credentials (`paper_trading=False`, `BINGX_TESTNET=True`, `LIVE_TRADING` unset → live send impossible).

**Verdict (summary):** ⛔ **NO-GO for live.** The execution-safety core (guard, risk admission, kill
switch, circuit breaker, truth ledger) is enforced on **every** real-funds send-point and was
validated live-on-testnet. But the broker-integration **lifecycle** (idempotency, status sync,
cancel, partial fills, error typing, SL/TP guarantee), **durable live state**, and **broker
reconciliation** are incomplete. Detailed verdict in `live_trading_go_no_go_decision.md`.

---

## 1. Real-funds execution paths (Task 1 — trace)

The wired production path is `--mode production [--auto-detect]` →
`broker_registry.get_execution_service(use_multi_broker=True, primary_broker='bingx')` →
`BrokerExecutionService(use_multi_broker=True)` → `MultiBrokerExecutionService`.

There are exactly **two** code points where an order can leave for a real exchange:

| # | Path | Location | Used in production |
|---|------|----------|--------------------|
| A | Multi-broker | `infrastructure/brokers/multi_broker_service.py::execute_order` → `broker.place_order` | **Yes** (wired default) |
| B | Single-broker | `infrastructure/services/broker_execution_service.py::execute_order` (single branch) → `self.broker.place_order` | only if `use_multi_broker=False` |

Non-real paths: `infrastructure/execution/execution_adapters.py` uses `MockBrokerAdapter` (no real
funds); `LiveExecutionEngine._execute_trades` is a stub. **Sub-path:** BingX attaches SL/TP as
separate `_place_conditional_order` calls *inside* `place_order` (i.e. downstream of an authorized
main order) — see finding §3.8.

---

## 2. Protection coverage on every real-funds path (Task 2)

Both send-points (A, B) route through `LIVE_EXECUTION_GUARD.authorize_and_send`, which performs the
decision + ledger write + send **atomically under one lock**. Coverage:

| Control | Mechanism | A | B | Evidence |
|---|---|---|---|---|
| **LIVE_EXECUTION_GUARD** | `evaluate()` route decision | ✅ | ✅ | testnet run: 8 TESTNET authorized, **0 LIVE**, 0 PAPER |
| **Risk admission** | rule `2b:risk_engine` (`is_trading_allowed` + `validate_position_entry`, fail-closed) | ✅ | ✅ | `test_risk_enforcement` (6) |
| **Kill switch** | rule `1` (engaged by risk loop on breach) | ✅ | ✅ | concurrency test (85 engagements, 0 leak) |
| **Circuit breaker** | rule `2` (per-broker `order_path:*`, fed by send results) | ✅ | ✅ | `test_live_execution_guard` |
| **Execution Truth Ledger** | decision record BEFORE send + result after; hash-chained | ✅ | ✅ | testnet run: 7 TESTNET result records, unbypassable |

**Finding 2.1 (positive, validated):** every real-funds send-point is protected by all five controls,
and the controls were exercised live-on-testnet. The guard correctly authorized TESTNET, never LIVE
(no `LIVE_TRADING`), and recorded everything in the ledger. **0 unauthorized orders.**

**Finding 2.2 (gap):** BingX SL/TP conditional orders (§3.8) fire downstream of the authorized main
order and are **not individually guarded or ledgered**, and their failure is swallowed.

---

## 3. Broker integration correctness (Task 3)

| # | Item | Status | Detail |
|---|------|--------|--------|
| 3.1 | **client_order_id idempotency** | ❌ **MISSING** | BingX `place_order` payload (`bingx_adapter.py:357-363`) sends no client order id; no broker-side dedup on retry/timeout |
| 3.2 | Duplicate-order protection | ⚠️ **WEAK** | `PendingOrdersTracker` in-memory, set only after success, racy, lost on restart |
| 3.3 | Order status synchronization | ⚠️ **PARTIAL** | BingX adapter `get_order_status` is real (queries open orders + history); **but** the multi-broker layer has no `order_id→exchange` map → `get_execution_status` returns `"unknown"`; Binance adapter returns hardcoded `FILLED` |
| 3.4 | Cancel / replace | ❌ **NON-FUNCTIONAL** | `multi_broker_service` cancel returns `False` ("without knowing original exchange"); no replace flow |
| 3.5 | Retry / backoff | ❌ **MISSING** | no retry/backoff anywhere in broker calls (grep clean) |
| 3.6 | Partial-fill handling | ❌ **MISSING** | fills assumed full; no `executedQty`/partial reconciliation in the execution flow |
| 3.7 | Network-failure handling | ❌ **UNSAFE** | errors collapse to `None`; "placed-but-response-lost" indistinguishable from "rejected"; no reconcile-on-unknown |
| 3.8 | Exchange-rejection handling | ⚠️ **WEAK** | rejections swallowed to `None`; no typed result; **SL/TP attach failure reported as success** → position opened with **no stop** (empirically: 4 conditional errors on testnet) |
| 3.9 | Binance spot vs BingX futures | ⚠️ **MEDIUM** | cross-instrument failover risk (Phase-9 H4); Binance ignores `testnet` |

---

## 4. Persistence & recovery (Task 4)

| Item | Status | Detail |
|------|--------|--------|
| Open positions (paper) | ✅ | `PaperTradingEngine` atomic JSON persistence + restart recovery (validated) |
| Open positions (**live**) | ❌ | no durable live position store (`EnterpriseRiskManager.positions` in-memory) |
| Open orders | ❌ | `PendingOrdersTracker` in-memory, not persisted |
| Restart recovery (paper) | ✅ | engine reloads + reconciles vs ledger |
| Restart recovery (**live**) | ❌ | orchestrators do no startup position/order fetch or rebuild |
| Crash recovery | ❌ | place→record lost-write window; in-flight live order can exist at the exchange with no local record |
| State consistency | ⚠️ | ETL is durable + hash-chained (resume hardened); live position store is not reconciled against the broker |

---

## 5. Reconciliation (Task 5)

| Item | Status | Detail |
|------|--------|--------|
| Local vs broker state | ❌ for live | `reconciliation_service` compares the live engine vs the immutable **ledger** (paper). It does **not** yet pull the real broker's `get_all_positions`/balances/open orders |
| Divergence detection | ✅ framework | per-symbol + realized-PnL diff; extends to broker by replaying broker fills |
| Divergence repair | ✅ framework | `repair()` rebuilds the live store from the source of truth (ledger today; broker for live) |
| Reconciliation safety | ⚠️ | repair is safe (rebuild from source of truth) but there is no periodic broker reconcile + **halt-on-drift** loop yet |

---

## 6. Controlled testnet validation results (Task 6)

Bounded run (~3m44s), valid BingX creds, testnet routing:

- Brokers connected; **GUARD authorized TESTNET: 8** (4 unique orders); **LIVE: 0**; **PAPER: 0**.
- **ORDER PLACED SUCCESSFULLY ON BINGX: 8** → **4 unique real exchange order ids** (e.g.
  `2065529962644901888`). **0 placement failures.**
- **GUARD blocked: 0** unauthorized; ETL recorded 7 TESTNET result records.
- ⚠️ **4 SL/TP conditional-order errors** — main orders succeeded while their stop/TP conditional
  orders failed ⇒ **testnet positions opened without protective stops** (confirms finding 3.8).
- 1 benign `RotatingFileHandler` rollover traceback (WSL-mount flake; does not affect execution/ledger).
- Observation (out of scope, strategy frozen): an `ArchitectureOrchestrator` "Signal contradiction:
  Bias=SELL vs Order=BUY" warning — a fusion/strategy-layer inconsistency, noted only.

**Conclusion:** the real-send path *works and is correctly gated* (orders reach BingX testnet only as
TESTNET, never LIVE; all recorded). The **post-placement lifecycle** is where live readiness fails
(stops not guaranteed; status/cancel/partial-fill/idempotency/reconciliation incomplete).

---

## 7. What's solid vs what's missing

**Solid (validated):** single-chokepoint guard; risk admission on every path (fail-closed); kill
switch + circuit breaker wired and race-free; immutable hash-chained truth ledger written before send;
paper fills/positions/PnL/equity/persistence/recovery; testnet order placement + correct gating;
zero unauthorized/live sends.

**Missing for live:** broker-side idempotency; typed order results + reconcile-on-unknown; guaranteed
SL/TP (or unwind); working cancel/status at the orchestration layer; retry/backoff; partial-fill
handling; durable live position/order store + startup recovery; broker reconciliation + halt-on-drift;
credential rotation (owner).

See `live_trading_gap_analysis.md` (risk + effort), `live_trading_release_checklist.md` (actions),
and `live_trading_go_no_go_decision.md` (verdict + path).
