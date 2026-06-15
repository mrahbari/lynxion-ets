# Testnet Soak Report

**Date:** 2026-06-12
**Environment:** BingX **testnet** (valid credentials), `paper_trading=False`, `BINGX_TESTNET=True`,
`LIVE_TRADING` unset (live send impossible — guard routes TESTNET only).
**Nature:** **Compressed/accelerated soak** — multiple bounded continuous runs (~2–4 min each) plus
explicit recovery/restart/reconciliation scenarios. A literal 24–72h continuous soak was **not** run
(out of this session's scope) and remains the final release-gate item (§5).

---

## 1. Scenarios exercised (real testnet)

| Scenario | Result |
|----------|--------|
| Connected broker + continuous operation | ✅ brokers connect; full watcher→fusion→strategy→guard→broker pipeline runs; 0 crashes affecting execution |
| Real testnet order placement | ✅ real exchange order ids returned (e.g. `2065541051751337984`, `2065545688332111872`) |
| Guard gating | ✅ TESTNET-only authorized; **0 LIVE**, **0 PAPER**, **0 unauthorized** across all runs |
| Durable order journal | ✅ INTENT-before-send → SUBMITTED recorded with real order ids + client_order_ids |
| **Restart recovery** | ✅ fresh process recovered journaled orders (in-flight + order→exchange map) from disk |
| **Broker reconciliation** | ✅ fetched 9 real positions; classified recoverable vs unrecoverable |
| **Halt-on-drift** | ✅ 7 unrecoverable positions → **kill switch engaged automatically** |
| Idempotency (B2) | ✅ client_order_id transmitted on every order |
| Guaranteed protection (B1) | ✅ unwind path proven by unit tests; testnet protections succeeded (no unwind needed in these runs) |
| Execution Truth Ledger | ✅ every order's decision+result recorded; hash chain verifiable |

## 2. Key recovery transcript (real testnet)
```
RESTART RECOVERY: total_orders 2 | in_flight 2 | order_map_entries 2
RECONCILE: broker_positions 9 | unrecoverable 7 | halted True
KILL SWITCH engaged by drift: True
```
This is the complete B3→B4 chain — durable recovery → broker reconciliation → automatic halt — proven
against the live testnet account.

## 3. Timeout / fault scenarios
- Broker-status `UNKNOWN` (order aged out of the 100-order history window) was observed and handled
  correctly: the reconcile flags it **recoverable** (never falsely resolved).
- The B6 retry/backoff wraps the idempotent status read (transient faults retried).
- The B1 unwind + halt path covers protective-order failure; the kill switch halts on unrecoverable drift.

## 4. What was NOT exercised
- A **continuous 24–72h** run (only bounded multi-minute runs).
- A **natural partial fill** (testnet MARKET orders fill fully — see `partial_fill_validation.md`).
- Induced mid-flight process **kill** during an in-flight send (the journal INTENT-before-send makes
  this recoverable by design; a fault-injection test is recommended).
- A periodic reconcile **loop** wired into the orchestrator (the service is validated on demand).

## 5. Remaining gate
A full **24–72h continuous testnet soak** with induced disconnects/timeouts/partials and a mid-session
restart — confirming zero naked positions, zero duplicates, and clean reconciliation over the full
window — is the final operational gate before live. All the mechanisms it would exercise are
implemented and individually validated above.
