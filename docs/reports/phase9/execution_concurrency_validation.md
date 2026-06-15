# Execution Guard — Concurrency / Race Validation

**Date:** 2026-06-12
**Subject:** Thread-safety of `LIVE_EXECUTION_GUARD` under rapid flag switching, mid-execution kill
switch, and mid-burst circuit-breaker trips.
**Invariant under test:** *No race condition allows a single live (or testnet) order to be sent while
the kill switch is engaged or the circuit breaker is open, and no LIVE send occurs outside the
allowed flag state.*

**Result:** ✅ **PASS** — 0 violations across 2,400 concurrent orders. A real (non-safety) ledger
consistency bug was found during this validation and fixed.

---

## 1. What was hardened first (race-free by construction)

The original integration evaluated the guard and then called `broker.place_order` as two separate
steps — a TOCTOU window in which the kill switch could engage *after* the decision but *before* the
send. That window is now closed:

- **`LiveExecutionGuard.authorize_and_send(broker, settings, order, send_fn)`** performs the decision,
  the Execution-Truth-Ledger write, and the send **atomically under the guard lock**.
- `engage_kill_switch()`, `disengage_kill_switch()`, `is_killed()`, `breaker_blocks()` and
  `record_send_result()` **all acquire the same lock**, so kill-switch and breaker state cannot
  change between the decision and the send in the same locked section.
- Consequence: a LIVE/TESTNET `send_fn` can only *start* if, at that locked instant, the kill switch
  is disengaged and the breaker is closed. A kill engaged or breaker tripped by any other thread is
  serialized — it applies to the next order, never mid-send.

Both real send-points (`MultiBrokerExecutionService.execute_order`,
`BrokerExecutionService.execute_order` single-broker) now route through `authorize_and_send`.

---

## 2. Simulation design

- **8 worker threads × 300 orders = 2,400 orders**, all through the real `authorize_and_send`.
- **Chaos thread** running concurrently:
  - flips `paper_trading`, `bingx_testnet`, `bingx_order_placement_enabled` on the shared settings on
    every iteration (rapid flag switching),
  - flips `LIVE_TRADING` in the environment every iteration,
  - **engages the kill switch mid-execution** (~5% of iterations) and disengages it (~5%),
- **Circuit breaker tripped mid-burst** the realistic way: ~15% of sends are induced to fail, which
  feeds `record_send_result(success=False)` and trips the per-broker breaker OPEN under load.
- Seeded RNG (`Random(1337)`) for reproducibility.
- **Violation probe**: each `send_fn` (which executes only for a real LIVE/TESTNET send) re-checks
  `guard.is_killed()` and `guard.breaker_blocks()` at the moment of send and records a violation if
  either is active. Post-run, every LIVE result is cross-checked against its immutable decision
  record (flags + states) in the ledger.

Every order's decision and outcome is logged to the Execution Truth Ledger
(`docs/reports/phase9/execution_truth_ledger.md`), which is the source of the per-order history below.

---

## 3. Results

```
CONCURRENCY STRESS — 8 workers x 300 orders = 2400 orders
  chaos: kill-switch engaged 85x mid-burst; ~15% sends induced to fail (breaker trips)
  decision routes: {'TESTNET': 247, 'PAPER': 263, 'BLOCKED': 1447, 'LIVE': 443}
  real sends to exchange: 690  (LIVE=443  TESTNET=247)
  ledger records: 3353  (decisions=2400  results=755)
  hash-chain verify: True
  VIOLATIONS — real send while killed/breaker-open : 0
  VIOLATIONS — LIVE send outside allowed flag state : 0
RESULT: PASS
```

- **0** orders were sent to the exchange while the kill switch was engaged or the breaker was open.
- **0** LIVE sends occurred outside the allowed flag state (`LIVE_TRADING=true`, not paper, live
  endpoint, not killed, breaker closed) — verified against each order's immutable decision record.
- The 1,447 `BLOCKED` outcomes are the chaos thread doing its job (kill engaged, breaker open,
  `LIVE_TRADING` off on a live endpoint, or order-placement toggled off) — all correctly refused.
- The audit ledger's hash chain verified intact over all 3,353 records.

### Per-order audit sample (decision history → final resolved state)

Drawn directly from the ledger; each order has one `decision` record (pre-send) and, when applicable,
one `result` record:

```
order 35356570: DECISION route=PAPER  rule=3:paper_trading
                flags(paper=True, testnet=False, live=False) kill=False cb=closed
                FINAL route=PAPER  sent=False order_id=PAPER-BINGX-BTCUSDT-000001 latency=0.0ms success=True
order 8bbab6f1: DECISION route=LIVE   rule=6:live_authorized
                flags(paper=False, testnet=False, live=True) kill=False cb=closed
                FINAL route=LIVE   sent=True  order_id=OID-… latency=…ms success=True
order …       : DECISION route=BLOCKED rule=1:kill_switch (or 2:circuit_breaker / 7:live_blocked_no_optin)
                FINAL (no send)
```

The `rule` field on every decision is the decision trace: it names exactly which precedence rule
resolved the order (`1:kill_switch`, `2:circuit_breaker`, `3:paper_trading`,
`4:order_placement_permission`, `5:testnet_endpoint`, `6:live_authorized`, `7:live_blocked_no_optin`).

---

## 4. Bug found and fixed during validation (ledger accuracy)

The first stress run reported **0** send-while-killed/open violations but **2** "LIVE outside allowed
flags". Investigation showed this was **not** a send leak — it was a *ledger-accuracy* defect:
`evaluate()` read the flags to make the decision, then the ledger snapshot re-read them a few
microseconds later, so under rapid flipping the *recorded* `input_flags` could disagree with the
values the decision was actually made on.

**Fix:** the guard now captures every decision input (`paper_trading`, resolved `testnet`,
`order_placement_enabled`, `LIVE_TRADING`) in a **single atomic read** inside `evaluate()` and attaches
that exact snapshot to the `GuardDecision` (`decision.flags`). `authorize_and_send` records
`decision.flags`, so the ledger now reflects precisely the inputs the decision used. Re-running the
identical stress scenario yields **0 / 0** violations (above). A regression test
(`test_recorded_flags_match_decision`) asserts `ledger.input_flags == decision.flags`.

This is exactly the kind of determinism/reproducibility correctness the current mission calls for: the
audit record is now a faithful, reproducible account of each decision.

---

## 5. Semantics clarification (what "allowed state" means)

- **Kill switch and circuit breaker** are *hard stops*: their state is lock-protected and atomic with
  the send, so an engaged kill / open breaker provably blocks every send that has not already started.
  This is the strong invariant validated above (0 violations).
- **Flags** (`paper_trading`, `testnet`, `LIVE_TRADING`, order-placement) are *point-in-time inputs* to
  each atomic decision. An order authorized under a valid snapshot is correct even if a flag flips
  immediately afterward — the flip governs the *next* order. The ledger records the exact snapshot per
  order, so every decision is auditable and reproducible.

---

## 6. Reproduce

```
.venv/bin/python -m pytest tests/unit/test_execution_truth_ledger.py tests/unit/test_live_execution_guard.py -q
# 19 passed  (includes test_no_send_while_killed_or_breaker_open_under_chaos)
```

**Validation status: PASS.**
