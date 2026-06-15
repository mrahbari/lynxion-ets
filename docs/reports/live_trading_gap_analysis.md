# Live Trading Gap Analysis

**Date:** 2026-06-12
Companion to `live_trading_readiness_audit.md`. Each gap is risk-ranked and effort-estimated.
Effort is rough engineering time for one developer, excluding strategy work (frozen).

Severity: **Critical** (fund loss / wrong execution possible) · **High** (removes a safety net /
material operational risk) · **Medium** (degradation / latent) · **Low** (hygiene).

---

## Blockers (must be closed before live)

| ID | Gap | Severity | Why it blocks live | Evidence | Effort |
|----|-----|----------|--------------------|----------|--------|
| **B1** | **SL/TP not guaranteed** — placed as separate conditional orders; failure swallowed, main reported as success → **position opened with no stop** | **Critical** | Unbounded loss on a live position with no protective stop | Testnet run: 4 conditional-order errors while mains succeeded (audit §6); `bingx_adapter.py:447-546` | 1–2 d |
| **B2** | **No broker-side idempotency** (`client_order_id` not sent) + errors collapse to `None` | **Critical** | A lost response on a placed order can't be deduped → duplicate/phantom live positions on retry | `bingx_adapter.py:357-363`; `*:382-389/444-451` | 2–3 d |
| **B3** | **No durable live position/order store + no startup recovery** | **Critical** | After crash/restart the system is blind: re-enters held positions, orphans stops | in-memory `PendingOrdersTracker`, `EnterpriseRiskManager.positions`; orchestrators do no startup fetch | 3–5 d |
| **B4** | **No reconciliation vs the real broker** (only engine-vs-ledger today) | **Critical** | Undetected drift between local book and exchange truth (missed fills, liquidations, partials) | `reconciliation_service` reconciles vs ledger, not broker API | 3–5 d |
| **B5** | **Cancel / status non-functional at the orchestration layer** (no `order_id→exchange` map) | **High** | Can't cancel or query an individual live order → no programmatic kill of a specific order | `multi_broker_service` cancel `return False`; `get_execution_status` `"unknown"` | 2–3 d |

## High

| ID | Gap | Severity | Why it matters | Effort |
|----|-----|----------|----------------|--------|
| **B6** | No retry/backoff on broker calls | High | A single transient 5xx/timeout permanently fails the action; with B2 the outcome is silently lost | 1–2 d |
| **B7** | No partial-fill handling | High | Partial fills mis-tracked; position/PnL diverge from exchange | 2–3 d |
| **B8** | Errors not typed (placed vs rejected vs unknown) | High | Caller can't distinguish "rejected" from "maybe placed"; no reconcile-on-unknown | folded into B2 |
| **B9** | Crash lost-write window (place → local record) | High | Live order at exchange with no local record | folded into B3 |

## Medium / Low

| ID | Gap | Severity | Effort |
|----|-----|----------|--------|
| B10 | Binance adapter ignores `testnet`; spot-vs-futures cross-type failover | Medium | 1–2 d |
| B11 | Duplicate-order guard is volatile/racy (in-memory, post-success only) | Medium | folded into B3 |
| B12 | No periodic heartbeat/liveness + halt-on-stale (Phase-9 H9) | Medium | 1–2 d |
| B13 | Committed credentials must be rotated; hardcoded secret defaults removed (Phase-9 C9) | High (security) | owner action |
| B14 | `RotatingFileHandler` rollover flake on WSL mount | Low | 0.5 d |

---

## Risk ranking (most dangerous first)

1. **B1** — live position with no stop (immediate, unbounded loss). *Empirically reproduced on testnet.*
2. **B2/B8/B9** — duplicate/phantom orders and lost-write on timeout/crash.
3. **B3** — blind restart (double exposure, orphaned stops).
4. **B4** — silent divergence from exchange truth.
5. **B5** — cannot cancel/kill an individual live order.
6. **B6/B7** — transient-fault fragility and partial-fill drift.
7. **B10/B11/B12** — venue/instrument and liveness hardening.
8. **B13** — credential hygiene (owner).

---

## Total effort estimate

| Bundle | Items | Estimate |
|--------|-------|----------|
| Execution-correctness core | B1, B2/B8, B5, B6, B7, B10 | ~10–15 days |
| Durable state & recovery | B3/B9/B11 | ~3–5 days |
| Reconciliation & ops | B4, B12 | ~4–6 days |
| Security (owner) | B13 | parallel |
| **Total** | | **~3–4 weeks** focused engineering + a credential rotation |

The strong foundation (guard/risk/kill/breaker/ledger already enforced and testnet-validated) means
this is **incremental hardening of the broker lifecycle**, not a rebuild.
