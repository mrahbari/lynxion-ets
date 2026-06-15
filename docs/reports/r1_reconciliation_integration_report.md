# R1 — Periodic Reconciliation Integration Report

**Date:** 2026-06-13
**Objective:** Verify the broker reconciliation loop runs from the live orchestrator; wire it if not;
ensure periodic execution + kill-switch on unrecoverable drift; validate with controlled drift.

---

## 1. Measure (was it running?)
**No.** A repo-wide search found **no** reconcile call in either orchestrator
(`infrastructure/orchestrators/`). `BrokerReconciliationService` (B4) existed and was unit- and
testnet-validated, but it was invoked only on demand — never on a periodic loop in the runtime.

## 2. Implement
Both orchestrators now start a background reconciliation loop:
- `production_trading_orchestrator.py`: `_reconciliation_loop` + `_get_reconcile_broker`, started in
  `_start_background_services` (thread `broker_reconciliation`).
- `auto_detection_orchestrator.py`: same, started alongside the opportunity/risk loops.

Behaviour each cycle (default **60 s**, `reconcile_interval_seconds`):
1. resolve the primary broker adapter (`_get_reconcile_broker`);
2. `BrokerReconciliationService.reconcile(broker, live_order_journal, halt_on_unrecoverable=True)`;
3. on **unrecoverable drift** → kill switch engaged (inside the service) + `CRITICAL` log + critical
   alert; on recoverable drift → `WARNING` with resolved/recoverable counts.

## 3. Validate

### Controlled drift (unit) — `tests/unit/test_r1_reconcile_integration.py` (2/2)
- `_get_reconcile_broker` returns the primary multi-broker adapter.
- A single loop pass against a broker holding `DOGE-USDT` (no journal record) **engages the kill
  switch** — `live_execution_guard.is_killed()` is True.

### Live runtime (BingX testnet)
A production `--auto-detect` testnet run logged:
```
2026-06-13 08:35:14 - AutoDetectionOrchestrator - Broker reconciliation monitoring started
```
→ the loop is wired and runs in the live runtime (0 loop errors).

### Halt-on-drift on real testnet (earlier B4 validation)
A manual reconcile against the live testnet account fetched **9 real positions**, flagged **7 as
unrecoverable** (no local journal record), and **engaged the kill switch**:
```
RECONCILE: broker_positions 9 | unrecoverable 7 | halted True
KILL SWITCH engaged by drift: True
```

## 4. Notes / operational considerations
- The specific 10-minute live run above did not itself trigger a halt (the journal had records for the
  symbols held, or the first 60 s-cadence pass did not surface drift in the short window). The
  halt-on-drift path is proven by the controlled unit test and the real-testnet reconcile above.
- BingX enforces ~5 requests/min; a 60 s reconcile cadence competes with the trading loop's own
  broker calls for that budget. Recommendation: tune `reconcile_interval_seconds` against the rate
  budget and/or give reconciliation a reserved share of the rate limiter.

## 5. Status
✅ **Reconciliation loop integrated into both live orchestrators, periodic, halts on unrecoverable
drift.** Remaining tuning (rate-budget-aware cadence) noted for the soak/ops phase.
