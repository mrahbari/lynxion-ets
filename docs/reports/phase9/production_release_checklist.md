# Phase 9 — Production Release Checklist (Infrastructure Gate)

**Date:** 2026-06-12
**Purpose:** The concrete, verifiable gate that must be **fully green** before the system may be run
against live exchange credentials with a (future) profitable strategy. This is an *infrastructure*
gate only — strategy quality/profitability is out of scope (program closed, READY = 0).

**Current gate status:** ⛔ **NO-GO** — 10 Critical blockers open, 14 High open.

Legend: ☐ open · ☑ done · **[GATED]** = touches real-funds path or production secrets → requires
explicit owner approval (Rule 5 / org policy); specified here, not auto-applied.

---

## Section A — HARD BLOCKERS (all must be ☑ for GO)

### A1. Credentials (do first — independent of code)
- ☐ **[GATED]** Rotate/revoke **all** committed credentials: BingX, Binance, MEXC, Phemex API
  keys/secrets (+ BingX passphrase), CMC key, **Telegram bot token**. *(C9 — flagged, not removed
  per org policy; rotation is owner action.)*
- ☐ Replace every value in `.env.example` with placeholders (`BINGX_API_KEY=your_key_here`).
- ☐ Remove hardcoded secret defaults from source: `application/configs/schemas/monitoring.py:19-21`,
  `application/configs/_config_extractors.py:288-290`, `application/configs/profiles/{dev,staging,live}.py`.
- ☐ Purge the secrets from git history (filter-repo/BFG) and force-rotate anything ever pushed.
- ☐ Add a lint/test that fails on any non-empty literal default for a secret-named field.

### A2. Make accidental live trading impossible (safe defaults + preflight)
- ☐ **[GATED]** `BINGX_ORDER_PLACEMENT_ENABLED` (and peers) default **False**; explicit env opt-in. *(C10a)*
- ☐ **[GATED]** Enforce `paper_trading`/`dry_run` as a hard gate in `place_order` (simulate + synthetic
  id; never call broker). *(C10b)*
- ☐ **[GATED]** Thread `testnet` into the Binance adapter/`RestClient`; select testnet URL or fail
  fast. *(C10c)*
- ☐ **[GATED]** Startup preflight in `bootstrap/lifecycle`/composition root: if
  `environment ∈ {LIVE,PRODUCTION}`, **abort loudly** unless {keys present & non-placeholder,
  testnet consistent with intent, `paper_trading` explicitly False, order placement explicitly
  enabled, all safety flags backed by a bound enforcer}. *(C10/H10/A1)*
- ☐ Default working `.env`/`.env.example` to `dev`; require explicit, logged opt-in for production. *(H12)*

### A3. Live risk gate on the order path (wire the engine that already exists)
- ☐ **[GATED]** In `BrokerExecutionService.execute_order()`, **before** `place_order`, hard-gate on
  the container `risk_engine`: `is_trading_allowed()` + `validate_position_entry(symbol, qty, price)`;
  reject on failure. *(C1)*
- ☐ **[GATED]** Add fail-closed order checks: `isfinite(quantity) and quantity > 0`, min/max notional
  (`qty*price <= max_position_exposure`), max leverage. *(C-exposure / H1)*
- ☐ **[GATED]** Make `_validate_order_parameters_before_broker` **fail closed** (reject on exception
  and on missing/non-positive price). *(H2)*
- ☐ **[GATED]** Add `Order.__post_init__` invariants (qty>0, price>0 when present, side/type enums). *(H1)*
- ☐ **[GATED]** Route live sizing through `position_sizing_engine` against **real account equity**;
  clamp to remaining exposure; **reject (never fabricate/randomize price)** on missing data. *(C4)*
- ☐ **[GATED]** Position sizers return `0.0` (no trade) on invalid stop distance. *(H11)*

### A4. Halt / kill switch / circuit breakers (enforcement, not alerts)
- ☐ **[GATED]** Drawdown/leverage breaches set a shared `trading_halted` flag that `execute_order`
  checks and rejects on (configurable thresholds). *(C2)*
- ☐ **[GATED]** Inject a runtime kill switch + operator-triggerable **flat-all/halt** entry point
  into the orchestrator and order path. *(C3 — depends on A6 working cancel)*
- ☐ **[GATED]** Wrap broker `place_order/cancel_order/get_position` and data fetches with
  `shared/circuit_breaker`; on OPEN, block orders + alert. *(C3)*
- ☐ **[GATED]** Add a **data-staleness** breaker (none exists). *(C3)*
- ☐ Wire `safety.py` flags (`kill_switch_enabled`/`emergency_stop_enabled`/`circuit_breaker_enabled`)
  to real enforcement, or remove them. *(H10)*

### A5. Idempotency + error handling (no phantom/duplicate positions)
- ☐ **[GATED]** Generate + transmit a deterministic `client_order_id` on every adapter. *(C5)*
- ☐ **[GATED]** Return a **typed** order result (Placed/Rejected/Unknown-needs-reconcile); on Unknown,
  query the exchange by `client_order_id` before any resubmit. *(C6)*
- ☐ **[GATED]** Bounded exponential backoff for idempotent reads / idempotent writes only. *(H6)*
- ☐ **[GATED]** Back duplicate prevention with broker-side idempotency + reconciliation; fail
  **closed** when position state can't be verified. *(C5b)*

### A6. Durable state + reconciliation (no blind starts)
- ☐ **[GATED]** Persist positions/orders/fills + `order_id→(exchange,symbol)` to a transactional
  store (SQLite WAL / Postgres) on every transition. *(C7/H7)*
- ☐ **[GATED]** Startup reconciliation: fetch live positions + open orders per broker, rebuild state,
  adopt/reconcile stops **before** enabling new entries. *(C7)*
- ☐ **[GATED]** Periodic broker↔local reconciliation loop; **halt + alert** on drift beyond tolerance. *(C8)*
- ☐ **[GATED]** Replace fabricated `FILLED` status with the real terminal status + filled qty. *(C8b)*
- ☐ **[GATED]** Capture real fill price/fee/slippage from the broker response and persist those. *(C8 / fills)*
- ☐ **[GATED]** Implement working `cancel_order`/`get_execution_status` against the originating
  exchange. *(H5)*

### A7. Execution correctness
- ☐ **[GATED]** Never report order `success` unless the protective stop attached; otherwise unwind or
  halt. *(H3)*
- ☐ **[GATED]** Forbid cross-instrument-type failover (Binance spot vs BingX futures); make adapters
  instrument-type-aware or restrict to one venue/type. *(H4)*
- ☐ Replace the random-sample fetcher + stub `_execute_trades` with the real data→order chain, then
  **re-run this entire audit** on the real path. *(H — monitoring)*

---

## Section B — STRONGLY RECOMMENDED (should be ☑ for GO)

- ☐ Heartbeat per loop/thread + watchdog that alerts/halts on staleness; restart/fail-loud on dead
  daemon threads. *(H9)*
- ☐ Alerting: wire `run_alert_monitor` to real data (or delete); inject notifier credentials from
  settings; escalate on send failure. *(H8)*
- ☐ Graceful shutdown that snapshots state and cancels/records working orders. *(restart M)*
- ☑ **Fix `shared/sync_logger.py` missing `import os`.** *(H14 — DONE; verified byte-compile +
  isolated write test.)*
- ☐ Atomic candle-store write (temp + `os.replace` + fsync). *(H13 — safe; deferred only for test-run)*
- ☐ SQLite WAL + busy timeout + per-thread connections; unique natural keys + `ON CONFLICT`. *(DB M)*
- ☐ Standardize all trade/order/fill timestamps on `datetime.now(timezone.utc)`. *(DB M)*
- ☐ Secret-redaction log filter; default prod log level INFO; honor configured log size/level/rotation. *(M)*
- ☐ Forensic log rotation **with deliberate high retention** (audit trail). *(M)*
- ☐ Metrics ring-buffer + exporter (Prometheus/StatsD). *(M)*
- ☐ Health-checked broker failover; rate-limiter max-wait timeout; startup broker-connect readiness
  check; enforce `enabled_brokers` at routing. *(M)*

---

## Section C — HYGIENE (track; not gating)
- ☐ Remove/guard `flush_all` on the shared Redis client. *(L)*
- ☐ `fsync` before `os.replace` in sync repo writers. *(L)*
- ☐ Emit risk breaches / breaker trips at `error`/`critical`. *(L)*
- ☐ Delete orphaned `.pyc`-only risk/sizing modules (no source) to prevent accidental import. *(noted)*
- ☐ Implement or remove `PortfolioRiskController` correlation/allocation stubs. *(M)*
- ☐ Deploy/release runbook; explicit + logged environment selection. *(L)*

---

## Re-evaluation procedure (per the Measure→Diagnose→Fix→Re-evaluate mandate)
For each item moved to ☑:
1. **Measure** — cite the `file:line` and the before-state evidence (captured in the area reviews).
2. **Diagnose** — confirm the root cause is addressed, not just the symptom.
3. **Fix** — minimal change; for `[GATED]` items, owner approval recorded.
4. **Re-evaluate** — run the (now-runnable) test suite + a **testnet** dry-run end-to-end:
   place → (induced) timeout → reconcile → halt → flat-all, verifying no phantom/duplicate position,
   no fabricated FILLED, no fail-open, and a working kill path. Only then flip the item green.

---

## GO / NO-GO

| Gate | Required | Status |
|------|----------|--------|
| Section A (Hard blockers) | 100% ☑ | **0 of 10 critical themes resolved** |
| Section B (Recommended) | ≥ 90% ☑ | 1 of 11 (H14) |
| Testnet end-to-end dry-run passed | Yes | Not started (path is stub/sample) |
| Independent re-audit of the *real* order path | Yes | Pending (path not yet real) |

# DECISION: ⛔ NO-GO — PRODUCTION UNSAFE (infrastructure)

The system must not run against live credentials until Section A is fully green and a testnet
end-to-end dry-run + re-audit pass. The fastest risk-reduction sequence is **A1 (rotate secrets) →
A2 (safe defaults + preflight, makes accidental live trading impossible) → A3/A4 (risk gate + halt) →
A5/A6 (idempotency + durable state + reconciliation) → A7 (execution correctness) → testnet dry-run →
re-audit.**
