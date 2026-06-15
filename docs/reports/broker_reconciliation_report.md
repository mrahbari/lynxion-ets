# Broker Reconciliation Report (B4)

**Date:** 2026-06-12
**Component:** `infrastructure/execution/broker_reconciliation.py` (`BrokerReconciliationService`)
**Status:** ✅ Implemented + unit-tested (4/4) + **validated end-to-end on BingX testnet**, including
automatic halt-on-drift.

---

## 1. What it does
Reconciles LOCAL state (the durable live order journal, B3) against ACTUAL broker state pulled from
the exchange:
- **Order resolution (recoverable):** for each in-flight journal order (SUBMITTED / PARTIALLY_FILLED),
  poll the broker's real status / fill (`get_order_fill` → status + `executed_qty`) and record the
  outcome in the journal (FILLED / PARTIALLY_FILLED / terminal).
- **Position drift (unrecoverable):** any open broker position for a symbol with **no local journal
  record** means the system is holding a position it doesn't know about.
- **Halt-on-drift:** on unrecoverable drift, engage the LIVE_EXECUTION_GUARD kill switch (halt all new
  orders) and report.

It is broker-agnostic (uses `BrokerPort`: `get_all_positions`, `get_order_status`/`get_order_fill`).

## 2. Drift classification
| Class | Condition | Action |
|-------|-----------|--------|
| In-sync | broker orders/positions match local journal | none |
| Recoverable | in-flight order resolved by broker status (filled/partial/cancelled); intent-without-ack | update journal; flag |
| **Unrecoverable** | broker position with no local order record | **engage kill switch (halt) + alert** |

## 3. Testnet validation (real BingX testnet)
Run against the live testnet account after journaled orders:
```
RESTART RECOVERY: total_orders 2 | in_flight 2 | order_map_entries 2
RECONCILE: broker_positions 9 | unrecoverable 7 | halted True
KILL SWITCH engaged by drift: True
kill reason: UNRECOVERABLE broker drift: positions with no local record
             ['SUIUSDT','ATOMUSDT','BCHUSDT','HYPEUSDT','XLMUSDT','SOLUSDT','SOLUSDT']
```
- Fetched **9 real positions** from the testnet account.
- Correctly flagged **7 as unrecoverable** (leftover positions from earlier runs not in the fresh
  journal) and **automatically engaged the kill switch** — exactly the intended safety behaviour.

## 4. Robustness fix surfaced by testnet
The first live run hit `get_all_positions failed: Invalid symbol format: NCCOGOLD2USDUSDT` — one
exotic testnet symbol threw on the domain `Symbol` validator and **disabled position-drift detection
for the whole account**. Fixed: `get_all_positions` now skips an unparseable position (logged) and
returns the rest. Re-run returned 9 positions, 0 errors.

## 5. Unit evidence
`tests/unit/test_b4_broker_reconciliation.py` (4/4): no-drift; recoverable in-flight resolution;
unrecoverable → halt; default halt engages the guard kill switch.

## 6. Residual / remaining
- **Periodic reconcile loop** is not yet wired into the live orchestrator (the service is validated
  and called on demand / startup). Production needs it on a timer (startup + every N seconds). ~1–2 d.
- Order status sometimes returns `UNKNOWN` on testnet when an order has aged out of the 100-order
  history window — widen the history query / cache fills at submission. (Recoverable; flagged, never
  falsely resolved.)
- A locally-maintained authoritative net-position book (updated from fills) would complement
  broker-sourced reconciliation; today the broker is the source of truth via this service.
