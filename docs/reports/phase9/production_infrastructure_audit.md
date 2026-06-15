# Phase 9 — Production Infrastructure Audit

**Date:** 2026-06-12
**Scope:** Production trading *infrastructure* only. No strategy logic, profitability,
or edge research was reviewed or modified (the strategy-validation program is closed; READY = 0).
**Question answered:** *If a profitable strategy were added in the future, would the system be
operationally safe to run with real funds?*

**Verdict (infrastructure only):** ⛔ **PRODUCTION UNSAFE**

---

## 1. Executive summary

The repository contains a competent *library* of safety components — a portfolio risk engine
with exposure/drawdown/daily-loss gates, a position-sizing service, a kill-switch engine, a
circuit-breaker implementation, a forensic logger, an alerting service, and config "safety" flags.

**Almost none of it is wired into the live order path.** The live path
(`run_trading_system.py --mode production` → `interface/cli/trading_system_production.py`
→ `bootstrap/container.py::_build_production_data_and_services` →
`infrastructure/orchestrators/production_trading_orchestrator.py`) constructs a **real**
multi-broker execution service pointed at live exchange endpoints (BingX futures primary), but:

- The composition root builds a canonical `risk_engine` and `position_sizing_engine`
  (`bootstrap/container.py:552-562`) that the production orchestrator **never resolves or calls**
  (verified: resolved only in tests).
- The `kill_switch` and `circuit_breaker` exist but have **zero references** in the
  orchestrator / execution / broker path (verified by repo-wide grep). The kill switch is wired
  only into *offline backtest/validation* use cases.
- The order chokepoint validates only stop-loss/take-profit *shape*, **fails open** on exception,
  and explicitly removed risk validation (`broker_execution_service.py:716-717`).
- There is **no durable persistence** of positions/orders/PnL, **no broker↔local reconciliation**,
  **no startup recovery**, and the broker's `get_order_status` returns a hardcoded `FILLED` fallback.
- Live exchange API keys and a live Telegram bot token are **committed to the repository**
  (tracked `.env.example` + hardcoded Python defaults).
- The live path defaults are **unsafe**: order placement is on by default, the `paper_trading`
  flag is dead code, Binance silently ignores its testnet flag, and there is no startup preflight.

Separately, the currently-wired "production" loop is itself a **placeholder**: it feeds *random*
sample OHLCV through a **stub executor** (`LiveExecutionEngine._execute_trades` is empty) — so the
live data → signal → order → fill → monitor → reconcile chain does not yet exist end-to-end. This
means the path must be *built and re-audited* before it can trade, on top of fixing the gaps below.

**Conclusion:** The infrastructure is not in a state where adding a profitable strategy would be
safe. The gating defect is systemic: safety components are present but disconnected, the order path
is fail-open, and there is no durable state or reconciliation. This is a **PRODUCTION UNSAFE**
verdict from an infrastructure perspective.

---

## 2. Methodology

- Five parallel read-only audits covering the 20 mandated areas, each reading the real
  implementations (not just names) and tracing the **live composition root** to separate
  "what exists" from "what is wired".
- First-hand corroboration by the lead auditor of the highest-impact wiring facts:
  - live broker wiring & absence of dry-run/paper/testnet flag in the production CLI/factory;
  - `kill_switch` / `circuit_breaker` / `risk_engine` / `position_sizing_engine` live-wiring
    (grep across `infrastructure/orchestrators`, `infrastructure/execution`,
    `infrastructure/services`, `infrastructure/brokers`, `interface/cli`,
    `application/use_cases` — confirmed none reach the live order path);
  - presence (not values) of committed secrets in `.env.example` (tracked) and
    `application/configs/schemas/monitoring.py`.
- Severity model: **Critical** (can cause uncontrolled loss / wrong execution / fund exposure),
  **High** (materially raises risk or removes a safety net), **Medium** (operational degradation /
  false assurance), **Low** (hygiene).

Per organisation policy, **no secret values are reproduced** in these reports; secrets are flagged
by variable name and location only and were **not** silently removed from source.

---

## 3. Live-path map (what is actually wired)

```
run_trading_system.py  --mode production
  └─ interface/cli/trading_system_production.py  (no --dry-run/--paper/--testnet flag)
       └─ bootstrap/lifecycle.lifespan()           (no startup safety preflight)
            └─ bootstrap/container.Container
                 └─ _build_production_orchestrator_factory()
                      └─ _build_production_data_and_services()
                           ├─ broker_registry.get_execution_service(use_multi_broker=True,
                           │     primary_broker='bingx')        → REAL live broker adapters
                           ├─ broker_registry.get_historical_data_provider(download_enabled=True)
                           ├─ EqualWeightPortfolioAdapter()
                           └─ AdvancedOptimizationService()
                 └─ ProductionTradingOrchestrator(... 4 deps only ...)
                      ├─ _risk_monitoring_loop()   → ALERT-ONLY (never halts/flattens)
                      ├─ LiveExecutionEngine        → _execute_trades() is a STUB
                      └─ stop_system()              → flips flag; does NOT flatten positions

NOT wired into the above: container risk_engine, position_sizing_engine, kill_switch_factory,
shared/circuit_breaker, enterprise_risk_manager gates, durable persistence, reconciliation.
```

---

## 4. Consolidated findings (all 20 areas)

Counts below are **de-duplicated by theme**; the same defect sometimes surfaces in several
numbered areas (cross-referenced in the per-area reviews).

| ID | Theme | Areas | Severity |
|----|-------|-------|----------|
| C1 | No portfolio risk gate on the live order path; `risk_engine` built but never resolved/called | 1,3,4,5,19 | Critical |
| C2 | Risk-limit breaches (drawdown/leverage) only **alert**; never halt or flatten | 1,13 | Critical |
| C3 | No runtime kill switch or circuit breaker on order/data path (decorative / backtest-only) | 14,15 | Critical |
| C4 | Live sizing naive off hardcoded `$10k`, no exposure accumulation; **fabricated/random price** on missing data feeds live orders | 2,3 | Critical |
| C5 | No broker-side idempotency (`client_order_id` never sent) + in-memory-only, racy duplicate guard → duplicate live positions | 5,6 | Critical |
| C6 | Order errors/timeouts collapse to `None` (fail-open; can't distinguish rejected vs unknown) | 5,8 | Critical |
| C7 | No durable state + no startup reconciliation → system starts **blind**, state lost on crash | 9,10 | Critical |
| C8 | No broker↔local reconciliation anywhere; `get_order_status` returns hardcoded `FILLED`; fills logged with fee/slippage = 0 | 6,11 | Critical |
| C9 | Committed live secrets: exchange API keys in **tracked** `.env.example` + Telegram token hardcoded in source defaults | 12,17,18 | Critical |
| C10 | Unsafe live defaults: order placement on by default; `paper_trading` dead code; Binance ignores testnet; no startup preflight | 16,20 | Critical |
| H1 | `Order` entity has no field validation; no qty>0 / notional / leverage cap at the order gate | 5,3 | High |
| H2 | Pre-broker validation **fails open** and is skipped entirely when price is falsy | 5,1 | High |
| H3 | BingX SL/TP placed as separate conditional orders; their failure still reports `success=True` (position opened with no stop) | 6 | High |
| H4 | Binance uses **spot** endpoints while BingX uses **futures**; cross-type "failover" routes wrong instrument | 6 | High |
| H5 | `cancel_order` / `get_execution_status` non-functional in the live multi-broker path | 6 | High |
| H6 | No retry/backoff on any broker API call | 8 | High |
| H7 | No persistence of in-flight / order→exchange mapping | 9 | High |
| H8 | Alerting: notify-only on breach; `run_alert_monitor` fed empty placeholder data; notifier built with empty creds | 13 | High |
| H9 | No heartbeat/liveness; loops swallow exceptions and retry forever; dead daemon threads undetected | 19 | High |
| H10 | Safety config flags (`kill_switch_enabled`, `emergency_stop_enabled`, `circuit_breaker_enabled`) have **no runtime consumer** (false assurance) | 15,16 | High |
| H11 | Invalid stop-loss floored to a fabricated 1-unit position instead of rejecting | 2 | High |
| H12 | `.env` default `ENVIRONMENT=production` with live keys present; no env-only secret invariant | 16,17 | High |
| H13 | Non-atomic CSV write in canonical candle store (corruption on crash) | 10 | High |
| H14 | `sync_logger.py` missing `import os` → sync-path file logging raised `NameError` | 12 | High — **FIXED** |
| M1.. | Medium items (timestamp tz drift, SQLite no-WAL/locking, unbounded in-memory metrics, forensic log no rotation, log size/level config ignored, broker connect failure swallowed, rate-limiter unbounded block, `enabled_brokers` not enforced, no redaction in logs, daily-loss baseline = config constant, correlation/allocation limits are stubs, CMC breaker config with no breaker) | 7,8,10,12,16,19 | Medium |
| L1.. | Low items (CRITICAL log level unused for critical events, `flush_all` foot-gun on shared Redis, fsync-before-replace, no deploy runbook) | 10,12,20 | Low |

**Severity tally (by theme):** Critical = 10, High = 14, Medium ≈ 12, Low ≈ 4.

Detailed evidence (`file:line`), diagnosis, and remediation for each are in:
- `risk_engine_review.md` — areas 1–5 (risk, sizing, exposure, portfolio limits, order validation)
- `broker_reliability_review.md` — areas 6–9 (broker integration, failover, error & restart recovery)
- `operational_readiness_review.md` — areas 10–20 (DB integrity, reconciliation, logging, alerting,
  breakers, kill switches, config/secrets/keys, monitoring, ops readiness)
- `production_release_checklist.md` — Measure→Diagnose→Fix→Re-evaluate gate, what is fixed vs gated, GO/NO-GO

---

## 5. Remediation status & approval gates

Per `CLAUDE.md` Rule 5 and the organisation security policy, the following remediation categories
were **not** auto-applied and require explicit owner action / approval, because they affect the
**real-funds order path** or **production secrets** (which must be *flagged, not silently removed*):

- Rotating/revoking the committed exchange & Telegram credentials and purging git history (C9).
- Any behaviour change to the live order-placement path (C1, C2, C5, C6, C10, H1–H7).
- Building durable persistence + reconciliation (C7, C8, H7).

Applied autonomously in this pass (safe, minimal, verified, non-funds, behaviour-fixing):

- **H14 — `shared/sync_logger.py`**: added missing `import os`. Verified by byte-compile and an
  isolated execution of the file-write branch. This restores data-sync/pipeline observability that
  was silently crashing.

All other Critical/High items are specified with concrete fixes in the per-area reviews and the
release checklist, marked **[GATED]** where they touch funds/secrets.

---

## 6. Final verdict

From an **infrastructure perspective only**, ignoring strategy quality and profitability:

# ⛔ PRODUCTION UNSAFE

The system must not be run against live exchange credentials. The minimum bar to flip this verdict
is enumerated as the **Release Gate** in `production_release_checklist.md`; the non-negotiable
blockers are C1–C10 (no live risk gate, no kill switch/halt, fail-open order path, no idempotency,
no durable state, no reconciliation, committed secrets, unsafe defaults).
