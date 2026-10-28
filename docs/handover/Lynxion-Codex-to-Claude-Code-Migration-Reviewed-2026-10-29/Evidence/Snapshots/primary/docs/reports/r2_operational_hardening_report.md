# R2 — Operational Hardening Report

**Date:** 2026-06-13
**Objective:** Implement and validate startup preflight, local net-position book, order-history
robustness, broker connectivity validation, partial-fill fault injection, and restart/recovery stress.
No strategy logic modified.

---

## 1. Startup preflight checks ✅
`shared/preflight.py::run_preflight(settings, env)` resolves the effective execution mode
(PAPER / TESTNET / LIVE / BLOCKED) from settings + the `LIVE_TRADING` env opt-in (mirrors the guard's
precedence) and returns blocking issues + warnings:
- **LIVE/TESTNET** require non-placeholder API key/secret for the default broker → otherwise *blocking*.
- **LIVE** must be deliberate (`LIVE_TRADING=true`) and emits a real-funds warning.
- live endpoint selected without the opt-in → mode `BLOCKED` (warned: all orders would be guard-blocked).
- kill switch engaged at startup → warned.

Wired into the production CLI (`interface/cli/trading_system_production.py`): prints the preflight,
and **refuses to start (`return 2`) when mode is LIVE and not ok**. Verified live: a testnet run
prints `🔎 Preflight: mode=TESTNET ok=True ...`.
Tests: `test_r2_operational_hardening.py` — PAPER ok, TESTNET ok, TESTNET blocks on placeholder keys,
LIVE ok with opt-in+keys, live-endpoint-without-opt-in → BLOCKED.

## 2. Local net-position book ✅
`live_order_journal.net_positions()` derives a signed net-position book per symbol from journaled
fills (BUY +, SELL −), surviving restart and cross-checkable against the broker by reconciliation.
Test: `1.0 BUY − 0.4 SELL = 0.6` net BTC; `2.0` net ETH.

## 3. Order-history / status robustness ✅ (partial)
`get_order_fill` (B7) reads status + `executed_qty` from open orders **and** the order history; status
that ages out of the window is returned as `UNKNOWN` and treated by reconciliation as **recoverable**
(never falsely resolved). Recommendation (carried): widen the history window / cache fills at
submission so aged orders still resolve.

## 4. Broker connectivity validation ✅
- The execution path only requires connection for **real** sends (LIVE/TESTNET); connect failure is
  logged and the order is rejected (no silent send).
- The reconcile loop runs against the connected primary adapter; connect failures surface as loop
  errors (logged) rather than silent drift.
- The preflight surfaces missing credentials before any connection is attempted.
- Live testnet runs confirm successful broker connect (0 `BROKER NOT CONNECTED` with valid creds).

## 5. Partial-fill fault injection ✅
`test_b7_partial_fill::test_reconciliation_records_partial_then_full` injects a partial fill
(`executed_qty 0.4/1.0`) via a broker fixture → journal records `PARTIALLY_FILLED` (stays in-flight),
then a full fill → `FILLED` (resolved). Lifecycle + restart recovery of partial state validated
(`partial_fill_validation.md`).

## 6. Restart / recovery stress ✅
`test_r2_operational_hardening.py::test_restart_recovery_stress`: 50 orders (mixed BUY/SELL, some
filled) written to the journal, then **5 restart cycles** — each fresh load reproduces identical
`total_orders` (50), `status_counts`, and order→exchange map size. Append-only + last-valid-record
resume (the cross-process-resume fix) make recovery deterministic.

## 7. Status
✅ Preflight, net-position book, partial-fill fault injection, restart-stress, and connectivity
validation implemented and tested. Order-history robustness improved with a documented follow-up
(history-window widening). 9/9 R1+R2 unit tests pass.
