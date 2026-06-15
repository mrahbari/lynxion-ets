# Live Trading — GO / NO-GO Decision

**Date:** 2026-06-12
**Decision scope:** infrastructure readiness to operate with **real funds**. Strategy is out of scope
and closed (READY = 0 — note: even with perfect infrastructure there is no deployable edge, so live
trading is not *commercially* justified today regardless; this decision is purely about whether the
*plumbing* is safe).

---

# ⛔ NO-GO for live trading

The execution-safety foundation is strong and was validated live-on-testnet, but the broker-integration
lifecycle, durable live state, and broker reconciliation are incomplete. Going live now risks naked
positions, duplicate/phantom orders, and undetected drift.

---

## What is GO-ready (validated)
- **Every real-funds send-point is protected** by the LIVE_EXECUTION_GUARD, risk admission (fail-closed),
  kill switch, circuit breaker, and the Execution Truth Ledger — confirmed by code trace and a testnet run.
- **Correct gating proven on testnet:** 4 real testnet orders placed (real exchange ids); **0 LIVE**
  authorizations (no `LIVE_TRADING`), **0 paper**, **0 unauthorized**, all ledgered.
- Paper trading is complete (fills/positions/PnL/equity/persistence/recovery/reconciliation).

## Remaining blockers (must close — see gap analysis for evidence/effort)
| # | Blocker | Severity |
|---|---------|----------|
| B1 | SL/TP not guaranteed → position with no stop (**reproduced on testnet**) | Critical |
| B2 | No `client_order_id` idempotency + untyped `None` errors → duplicate/phantom on retry | Critical |
| B3 | No durable live position/order store + no startup recovery → blind restart | Critical |
| B4 | No reconciliation vs the real broker → undetected drift | Critical |
| B5 | Cancel/status non-functional at the orchestration layer | High |
| B6/B7 | No retry/backoff; no partial-fill handling | High |

## Risk ranking (most dangerous first)
1. B1 naked position (immediate, unbounded loss)
2. B2 duplicate/phantom orders & lost-write on timeout/crash
3. B3 blind restart (double exposure / orphaned stops)
4. B4 silent divergence from exchange truth
5. B5 cannot kill an individual live order
6. B6/B7 transient-fault fragility & partial-fill drift
7. Security: rotate committed credentials (owner)

## Implementation effort estimate
- Execution-correctness core (B1, B2, B5, B6, B7, Binance/instrument): **~10–15 days**
- Durable state & recovery (B3): **~3–5 days**
- Reconciliation & ops (B4, heartbeat): **~4–6 days**
- Security (owner, parallel): credential rotation
- **Total: ~3–4 weeks** focused engineering. This is incremental hardening, not a rebuild — the
  guard/risk/kill/breaker/ledger spine is done.

## Exact path to production readiness (ordered)
1. **A1 — guarantee the stop** (unwind/halt if SL fails; ledger conditional orders). *Highest risk, smallest effort.*
2. **A2 — idempotency + typed results + reconcile-on-unknown** (`client_order_id`, Placed/Rejected/Unknown).
3. **A3 — durable order/position journal + startup recovery** (transactional store; rebuild + reconcile before new entries).
4. **A4 — broker reconciliation loop + halt-on-drift** (pull broker truth; kill switch on divergence).
5. **A5 — order→exchange map → working cancel/status + operator flat-all.**
6. **A6 — retry/backoff + partial-fill + real fee/slippage capture.**
7. **Section C (owner)** — rotate credentials; remove hardcoded secrets; LIVE startup preflight.
8. **Section D gate** — ≥24–72h testnet soak with induced disconnects/timeouts/partials + mid-session
   restart (zero naked positions, zero duplicates, clean reconciliation); then enable `LIVE_TRADING`
   via preflight with tiny caps for the first window; independent sign-off.

## Bottom line
The system is **safe to run in paper and testnet today** and the safety spine that makes live trading
*possible* is built and proven. It is **not yet safe for real funds**: close blockers B1–B7 (≈3–4
weeks) and pass a testnet soak. Separately, since no deployable strategy exists (READY = 0), live
deployment carries **no expected profit** even once the infrastructure is GO — infrastructure GO is a
prerequisite, not a reason, to trade live.

**Decision: NO-GO. Re-evaluate after Section A + the testnet soak.**
