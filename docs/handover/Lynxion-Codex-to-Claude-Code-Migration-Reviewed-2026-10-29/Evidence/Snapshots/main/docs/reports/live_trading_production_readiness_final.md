# Live Trading Production Readiness — Final Report

**Date:** 2026-06-12
**Mandate:** Live Trading Hardening — remove the audited blockers (Measure → Implement → Re-test →
Document), validate on BingX testnet, produce evidence per blocker. Strategy frozen (READY = 0); no
strategy/signal/parameter/optimization work performed.
**Method:** code implementation + deterministic unit tests + BingX-testnet validation runs.

**Verdict:** ⛔ **NO-GO for real funds** — but substantially closer. **5 of 7 blockers are resolved**
and tested (B1 protection, B2 idempotency, B3 durable recovery, B5 order lifecycle, B6 retry). Only
**B4 (broker reconciliation)** and **B7 (partial-fill handling)** remain as gating items (~1 week).

> Update history: this report was revised as blockers were implemented. B3, B5, B6 are now RESOLVED;
> B3 was validated end-to-end on BingX testnet (INTENT-before-send → SUBMITTED with real exchange
> order ids). The remaining matrix rows reflect the current state.

---

## 1. Blocker matrix

| ID | Blocker | Status | Evidence | Remaining |
|----|---------|--------|----------|-----------|
| **B1** | SL/TP not guaranteed → naked position | ✅ **RESOLVED** | On protective-order failure the position is unwound (reduceOnly close); if unwind fails, kill switch engages + orphan flagged. `test_b1_guaranteed_protection` (3/3). Testnet: 4 orders placed, protections succeeded this run (intermittent failure didn't recur, so unwind not observed live — proven by unit tests). | Optional: fault-injection testnet soak to observe unwind firing live. |
| **B2** | No broker-side idempotency | ✅ **RESOLVED** | `client_order_id` generated once per order, assigned back (retry reuses), transmitted as `clientOrderID` on BingX payloads. `test_b2_idempotency` (3/3). | Reconcile-on-unknown depends on B3/B4 + B6 retry to be fully exercised. |
| **B5** | Cancel/status non-functional at the orchestration layer | ✅ **RESOLVED** | `order_id → (exchange, symbol)` map populated at placement; `cancel_order`/`get_execution_status` route to the originating adapter; unknown orders fail safe. `test_b5_order_lifecycle` (2/2). | Persist the map (currently in-memory) — folds into B3. |
| **B3** | No durable live position/order store + startup recovery | ✅ **RESOLVED** | `live_order_journal` (append-only, fsync'd): INTENT before send → SUBMITTED → terminal; multi-broker startup recovery rebuilds the order→exchange map + flags in-flight orders. `test_b3_durable_recovery` (4/4). **Testnet-validated**: INTENT→SUBMITTED with real exchange order ids. | Live net-position store from fills depends on B7/B4 fill detection. |
| **B4** | No reconciliation vs the real broker | ⚠️ **PARTIAL** | `reconciliation_service` detects + repairs divergence by replaying the immutable ledger (`test_reconciliation` 3/3); journal surfaces in-flight orders on startup. | Pull the **real broker** positions/balances/open orders; periodic + startup reconcile loop; **halt-on-drift** (engage kill switch) on unrecoverable divergence. (~3–5 d) |
| **B6** | No retry/backoff | ✅ **RESOLVED** | `shared/retry.py` (capped exponential backoff, should_retry predicate, injectable sleep) applied to the idempotent status-read path; write-retry safe via B2. `test_b6_retry` (4/4). | Extend to more read paths as reconciliation lands. |
| **B7** | No partial-fill handling | ❌ **OPEN** | — | Capture `executedQty`/avg fill price; track partial fills in positions/PnL; record real fee/slippage. (~2–3 d) |

**Resolved this phase: B1, B2, B3, B5, B6** (5 of 7) — all with passing unit tests; B3 also
testnet-validated. **53/53** live-hardening unit tests pass across the execution-safety, paper, risk,
reconciliation, and B1/B2/B3/B5/B6 suites. **Remaining: B4 (broker reconciliation), B7 (partial-fill).**

---

## 2. Per-blocker detail (Measure → Implement → Re-test → Document)

### B1 — Guaranteed protection ✅
- **Measure:** `bingx_adapter` placed SL/TP as separate conditional orders and returned `success:True`
  even when they failed → naked position (reproduced on testnet: 4 conditional errors in the audit run).
- **Implement:** on `conditional_errors`, `_unwind_position` issues a reduceOnly market close; on
  unwind failure, the kill switch is engaged and the order is reported failed with the orphan id.
- **Re-test:** unit 3/3 (unwind on failure; halt on unwind failure; helper). Testnet validation run
  placed 4 orders; **protections succeeded this run** so the unwind path wasn't exercised live (the
  earlier intermittent conditional failure did not recur). The safety net is proven by unit tests.
- **Residual:** to observe the live unwind, run a controlled fault-injection testnet soak.

### B2 — Idempotency ✅
- **Measure:** BingX `place_order` sent no client order id → no exchange-side dedup on retry/timeout.
- **Implement:** `ensure_client_order_id` generates once, assigns back to the order (retry reuses),
  sent as `clientOrderID` on both order payloads.
- **Re-test:** unit 3/3 (generated once, preserved if present, transmitted, reused on retry).
- **Residual:** full reconcile-on-unknown needs B6 (retry) + B3/B4 (journal/broker reconcile).

### B5 — Order lifecycle ✅
- **Measure:** multi-broker `cancel_order`/`get_execution_status` returned `False`/`"unknown"` (no
  order→exchange mapping). BingX adapter `get_order_status` itself works (queries open orders + history).
- **Implement:** `order_id → (exchange, symbol)` map at placement; cancel/status route to the origin adapter.
- **Re-test:** unit 2/2 (route to origin; unknown fails safe).
- **Residual:** persist the map for restart (folds into B3).

### B3 / B4 / B6 / B7 — see matrix (PARTIAL/OPEN) with remaining work and effort.

---

## 3. What is validated end-to-end (cumulative)
- Every real-funds send-point protected by guard + risk admission + kill switch + circuit breaker +
  truth ledger (testnet-validated; **0 unauthorized, 0 LIVE** sends).
- Testnet order placement works (real exchange order ids); correct TESTNET-only routing.
- Paper fills/positions/PnL/equity/persistence/recovery; engine↔ledger reconciliation.
- B1 unwind safety, B2 idempotency key, B5 cancel/status — unit-validated.

## 4. Updated risk ranking (post-fix)
1. **B3** — blind restart for live (no durable live position store / startup recovery).
2. **B4** — undetected drift vs the exchange (no broker-sourced reconcile + halt).
3. **B7** — partial-fill mis-tracking.
4. **B6** — transient-fault fragility (mitigated by B2 once retry is added).
5. ~~B1~~ resolved · ~~B2~~ resolved · ~~B5~~ resolved.
6. Security: rotate previously-committed credentials (owner action).

## 5. Effort to GO (remaining)
| Bundle | Items | Estimate |
|--------|-------|----------|
| Broker reconciliation + halt-on-drift | B4 | ~3–5 d |
| Partial-fill handling + real fee/slippage capture | B7 | ~2–3 d |
| Security (owner) | credential rotation | parallel |
| Final testnet soak | 24–72h with induced faults | ~2–3 d elapsed |
| **Remaining total** | | **~1–1.5 weeks** (down from ~3–4) |

*Resolved: B1, B2, B3, B5, B6.*

## 6. Exact path to production readiness
1. **B3** — durable order-intent journal (write before send) + live position store + startup recovery
   (rebuild from journal + broker); persist the B5 order→exchange map.
2. **B4** — broker reconciliation loop (startup + periodic) pulling real positions/orders; engage the
   kill switch on unrecoverable drift.
3. **B6** — bounded backoff for idempotent reads and for writes (safe now via B2); reconcile-on-unknown.
4. **B7** — partial-fill + real fee/slippage capture into the ledger.
5. **Owner** — rotate committed credentials; remove hardcoded secrets; LIVE startup preflight.
6. **Gate** — ≥24–72h testnet soak with induced disconnects/timeouts/partials + mid-session restart
   (zero naked positions, zero duplicates, clean reconciliation); then `LIVE_TRADING=true` via
   preflight with tiny caps; independent re-audit sign-off.

---

## 7. Final decision

# ⛔ NO-GO for real funds.

Five of the seven blockers — including the most dangerous (B1) — are **resolved and tested** (B3 also
testnet-validated), and the safety spine is validated on testnet. Live deployment remains gated on
**B4 (broker reconciliation + halt-on-drift)** and **B7 (partial-fill handling)**, plus credential
rotation (owner) and a testnet soak — an estimated **~1–1.5 weeks**. Re-evaluate after those close.

> Reminder unchanged from the audit: even at infrastructure GO, no deployable strategy exists
> (READY = 0), so live trading carries no expected profit — infra GO is a prerequisite, not a reason.

## 8. Commits (this phase)
`afd9b6a` (P9 guard/ledger) → … → `26f5f69` (paper engine) → `a19c806` (risk) → `950674f`/`7385096`
(persistence/reconciliation/ledger-resume) → `fb3851b` (readiness audit) → **`b…` B1 unwind** →
**`beeeecf` B2 idempotency** → **`a82011d` B5 cancel/status**.
