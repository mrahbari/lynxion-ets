# Partial Fill Validation (B7)

**Date:** 2026-06-12
**Components:** `infrastructure/execution/live_order_journal.py` (`record_fill`/`net_filled`),
`infrastructure/brokers/adapters/bingx_adapter.py` (`get_order_fill`),
`infrastructure/execution/broker_reconciliation.py` (fill recording in the reconcile loop).
**Status:** ✅ Implemented + unit-tested (3/3). Lifecycle and restart recovery validated
deterministically; reconciliation-driven fill recording validated against a broker fixture.

---

## 1. Partial-fill lifecycle & state transitions
The live order journal tracks cumulative executed quantity per order:
```
INTENT → SUBMITTED → PARTIALLY_FILLED (filled < total, stays in-flight) → FILLED (filled ≥ total, terminal)
```
- `record_fill(order_ref, cumulative_filled, total_qty, avg_price, fee)` sets the status:
  `PARTIALLY_FILLED` while `cumulative_filled < total_qty`, `FILLED` once `>= total_qty`.
- `PARTIALLY_FILLED` is an **open** state — a partially-filled order remains in-flight, so it is
  recovered on restart and re-checked by reconciliation until complete.
- `net_filled(order_ref)` returns the cumulative filled quantity.

## 2. Recovery after restart
A partial fill is persisted (append-only journal). After a simulated restart a fresh journal recovers
the `PARTIALLY_FILLED` status and the cumulative `filled_qty`:
```
status_counts: {"PARTIALLY_FILLED": 1}   ;   net_filled == 0.5 (of 2.0)
in_flight[0].status == "PARTIALLY_FILLED"
```
(`test_b7_partial_fill::test_partial_fill_survives_restart`.)

## 3. Reconciliation interaction
The B4 reconcile loop reads the broker's executed quantity (`get_order_fill` → `executed_qty`) for each
in-flight order and calls `record_fill`:
- partial → recorded `PARTIALLY_FILLED`, order stays in-flight (flagged recoverable);
- subsequent reconcile with full execution → `FILLED`, order resolved.
```
reconcile #1 (executed 0.4/1.0) → recoverable "partially_filled", net_filled == 0.4, still in-flight
reconcile #2 (executed 1.0/1.0) → orders_resolved FILLED, in_flight == []
```
(`test_b7_partial_fill::test_reconciliation_records_partial_then_full`.)

## 4. BingX `get_order_fill`
Added to the adapter: returns `{status, executed_qty, avg_price}` from open orders + order history,
so partial fills are detectable from the exchange.

## 5. Unit evidence
`tests/unit/test_b7_partial_fill.py` (3/3): lifecycle (partial → full), restart recovery of partial
state, reconciliation records partial-then-full.

## 6. Testnet note
On BingX testnet the strategy emits **MARKET** orders, which fill fully and immediately, so a natural
partial fill was not reproduced in the bounded runs (partials are primarily a resting-LIMIT-order
phenomenon). The lifecycle and the reconcile-driven recording are therefore validated
deterministically (unit) and via the broker fixture; the live path will record partials whenever the
exchange reports `executedQty < quantity`. A LIMIT-order fault-injection test on testnet is the
recommended additional confirmation.
