# Live Trading Release Checklist

**Date:** 2026-06-12
Gate to flip the live verdict to GO. Every Section-A item must be ☑ and a sustained testnet soak must
pass. Legend: ☑ done · ☐ open · **[OWNER]** = human action (secrets/funds).

---

## Section 0 — Already done (validated foundation)
- ☑ LIVE_EXECUTION_GUARD enforced on every real-funds send-point (testnet-validated; 0 unauthorized/LIVE).
- ☑ Risk admission gate on every order path (fail-closed) + exposure feedback.
- ☑ Kill switch + circuit breaker wired and race-free.
- ☑ Execution Truth Ledger (hash-chained, written-before-send, resume-hardened).
- ☑ Paper fills / positions / PnL / equity / persistence / restart recovery.
- ☑ Engine-vs-ledger reconciliation (detect + repair).
- ☑ Testnet order placement validated (real exchange ids; correct TESTNET-only gating).

## Section A — Hard blockers (all required for GO)

### A1 Guaranteed protective stop (B1) — Critical
- ☐ Treat SL/TP attach failure as critical: atomically unwind the just-opened position or halt+alert;
  never report `success` when the stop did not attach.
- ☐ Ledger each SL/TP conditional order (decision + result), not just the main order.
- ☐ Testnet proof: induce SL failure → position is unwound/halted, never left naked.

### A2 Idempotency + typed results + reconcile-on-unknown (B2/B8/B9) — Critical
- ☐ Generate + transmit a deterministic `client_order_id` on every adapter `place_order`.
- ☐ Return a typed result (Placed / Rejected / Unknown-needs-reconcile) instead of `None`.
- ☐ On Unknown (timeout/network), query the exchange by `client_order_id` before any resubmit.
- ☐ Testnet proof: kill the process between send and ack → on restart the order is reconciled, not duplicated.

### A3 Durable live state + startup recovery (B3/B11) — Critical
- ☐ Persist open positions and an order journal (intent → submitted → ack, with `client_order_id` +
  exchange) to a transactional store (SQLite WAL / Postgres) on every transition.
- ☐ On startup, load local state and fetch live positions + open orders from the broker; rebuild and
  reconcile **before** enabling new entries.
- ☐ Make duplicate-prevention authoritative against the persisted+reconciled order ledger; fail closed
  when position state can't be verified.
- ☐ Testnet proof: restart mid-session → positions/orders recovered; no duplicate entry.

### A4 Broker reconciliation + halt-on-drift (B4) — Critical
- ☐ Periodic + startup reconcile: pull broker positions/balances/open orders, diff vs local ledger.
- ☐ On drift beyond tolerance: engage the kill switch + alert (halt new orders).
- ☐ Testnet proof: induce drift (manual testnet order) → detected, trading halted, alert raised.

### A5 Working cancel / status at the orchestration layer (B5) — High
- ☐ Persist `order_id → (exchange, symbol)` at placement; implement real cancel + status via the
  originating adapter (BingX `get_order_status` already works per-adapter).
- ☐ Operator flat-all / cancel-all entry point wired to the kill switch.
- ☐ Testnet proof: cancel a resting testnet order programmatically; query its real status.

### A6 Transient-fault & partial-fill handling (B6/B7) — High
- ☐ Bounded exponential backoff on idempotent reads, and on writes only when paired with `client_order_id`.
- ☐ Capture `executedQty`/avg fill price; track partial fills; record real fee/slippage (not 0.0).
- ☐ Testnet proof: a partial fill is tracked correctly in positions/PnL.

## Section B — Pre-live hardening (strongly recommended)
- ☐ Binance testnet wiring + forbid spot↔futures cross-type failover (B10).
- ☐ Heartbeat/liveness + watchdog halt-on-stale; restart dead daemon threads (B12).
- ☐ Capture real fee/slippage from broker fill responses into the ledger/forensic record.
- ☐ Fix `RotatingFileHandler` rollover on the deployment FS (B14).

## Section C — Security & ops (OWNER)
- ☐ **[OWNER]** Rotate/revoke previously-committed exchange + Telegram credentials; purge git history.
- ☐ **[OWNER]** Remove hardcoded secret defaults from source; secrets env-only.
- ☐ **[OWNER]** Startup preflight that refuses to start LIVE with inconsistent config (already specified Phase-9).
- ☐ Documented deploy runbook + explicit, logged environment selection.

## Section D — Go-live gate (after A–C)
- ☐ Sustained **testnet soak** (≥ 24–72h) with: forced disconnects, induced timeouts, partial fills,
  and a mid-session restart — zero naked positions, zero duplicates, clean reconciliation.
- ☐ `LIVE_TRADING=true` enabled only via the preflight, with tiny position caps for the first live window.
- ☐ Independent re-audit of this checklist signed off.

---

**Current gate status:** Section 0 ✅ · Section A **0/6 closed** · ⇒ **NO-GO.**
