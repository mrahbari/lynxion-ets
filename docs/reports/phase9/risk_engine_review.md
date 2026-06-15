# Phase 9 — Risk Engine Review

**Areas covered:** 1 Risk management · 2 Position sizing · 3 Exposure controls ·
4 Portfolio limits · 5 Order validation
**Scope:** infrastructure safety only; strategy logic untouched.
**Bottom line:** The system *contains* a correct portfolio risk engine and sizing service, but they
are **disconnected from the live order path**. Live orders are sized with naive arithmetic against a
fabricated balance (and, on missing data, a **random** price) and sent to the broker with only
SL/TP-shape validation that itself **fails open**. Drawdown breaches only alert.

For each Critical/High finding: **Measure → Diagnose → Fix → Re-evaluate**. Fixes touching the
real-funds order path are marked **[GATED]** (Rule 5 — require owner approval; specified, not applied).

---

## Architectural root cause (applies to C1, C4, H2)

The composition root builds a canonical `risk_engine`
(`ConsolidatedRiskEngineAdapter` → `EnterpriseRiskManager`, `bootstrap/container.py:559-562`) and a
`position_sizing_engine` (`bootstrap/container.py:552-557`) with real limits. **Neither is resolved
by the production orchestrator** — `_build_production_orchestrator_factory`
(`bootstrap/container.py:478-489`) injects only `market_data_repo, execution_service,
portfolio_service, optimization_service`. Repo-wide, `resolve("risk_engine")` /
`resolve("position_sizing_engine")` appear **only in tests**. `EnterpriseRiskManager.is_trading_allowed()`
has **zero runtime callers** outside the adapter delegate (`infrastructure/risk/risk_engine_adapter.py:46`).

There are **three competing risk/sizing implementations**, only fragments live:
1. `application/risk_management/enterprise_risk_manager.py` — real governance; **not wired live**.
2. `infrastructure/risk/advanced_risk_management.py` — instantiated per-order at
   `infrastructure/services/broker_execution_service.py:415`; handles only SL/TP, **not** portfolio gates.
3. Orphaned `.pyc`-only modules (no source) under `infrastructure/risk_management/`,
   `infrastructure/risk/`, `infrastructure/position_sizing/` — stale bytecode that could be
   imported accidentally.

---

## AREA 1 — Risk management

### C1 — Portfolio risk gates computed but never enforced before live orders — **Critical**
- **Measure:** `infrastructure/services/broker_execution_service.py:191` `execute_order()` →
  `:316 self.broker.place_order(order)`. Pre-send checks: running flag (`:195`), symbol approval
  (`:202`), duplicate-direction (`:213-251`), SL/TP presence (`:282-286`), SL/TP sanity (`:289`).
  **No** call to `is_trading_allowed()`, `validate_position_entry()`, `get_total_exposure()`, or a
  drawdown gate. `broker_execution_service.py:716-717` documents that risk validation was *removed*.
- **Diagnose:** The admission-control component exists but is never consulted; risk responsibility
  was pushed to "the strategy layer" and then left unimplemented in the order path.
- **Fix [GATED]:** In `execute_order()`, resolve the container `risk_engine` and hard-gate before
  `place_order`: `if not risk_engine.is_trading_allowed(): return Rejected`;
  `if not risk_engine.validate_position_entry(symbol, qty, price): return Rejected`. Register every
  fill back into the engine so exposure/drawdown stay current.
- **Re-evaluate:** With the gate wired and fed by live fills, daily-loss/drawdown/exposure caps
  become enforceable. Residual: requires real account-equity feed (see C4) to be meaningful.

### C2 — Max-drawdown "enforcement" only logs an alert — never halts — **Critical**
- **Measure:** `infrastructure/orchestrators/production_trading_orchestrator.py:154-159` and
  `auto_detection_orchestrator.py:568-573`: on `drawdown < -0.15` / `leverage > 10` it calls
  `logger.warning(...)` + `risk_alert_service.send_alert(...)` and **continues**. No flag set, no
  order path blocked. `_risk_monitoring_loop` is a passive alerter.
- **Diagnose:** Monitoring and enforcement are conflated into a notify-only loop; there is no shared
  "halt" state the order path observes.
- **Fix [GATED]:** Monitoring loop sets a shared `trading_halted` flag (on broker_registry /
  a dedicated safety singleton); `execute_order()` checks it and rejects. Make thresholds
  configurable, not hardcoded `-0.15`/`10.0`.
- **Re-evaluate:** Converts a cosmetic limit into a real circuit breaker (see also C3/H10).

### H2 — Final pre-broker validation **fails open**; skipped on missing price — **High**
- **Measure:** `broker_execution_service.py:641-643`:
  `except Exception: logger.warning("...allowing order to proceed"); return True`. The entire
  SL/TP block is guarded by `if order.price and ...:` (`:551`) with no `else`, so an order with a
  falsy/zero price **skips all validation and returns True**.
- **Diagnose:** Validation was written to "not block trading on errors" — the inverse of a safety gate.
- **Fix [GATED]:** On any validation exception or missing/non-positive price, `return False`
  (fail-closed) and alert.
- **Re-evaluate:** Removes the silent bypass; pairs with H1 (add quantity/notional checks).

### H — Hardcoded `True` "risk compliance" audit flags — **High**
- **Measure:** `broker_execution_service.py:338-342`: `validation_checks = {'margin_availability_check': True,
  'risk_profile_compliance': True, ...}` with comment "Would be checked in real implementation".
- **Diagnose:** Forensic log records checks as passed though none ran — false assurance, corrupt audit trail.
- **Fix [GATED]:** Implement the checks, or emit `"not_implemented"` so the audit trail is truthful.
- **Re-evaluate:** Restores forensic integrity for post-incident analysis.

### M — `validate_position_entry` boundary/NaN gaps (latent, currently unwired) — **Medium**
`application/risk_management/enterprise_risk_manager.py:188,194` use strict `>` (exact cap allowed),
no per-symbol concentration limit, no `isfinite()`/`>0` guard (a `NaN` size passes `NaN > limit == False`).
Fix when wiring C1: add `>=` where appropriate and explicit finite/positive guards.

---

## AREA 2 — Position sizing

### C4 — Naive inline sizing off hardcoded `$10k`; **fabricated/random price** on missing data — **Critical**
- **Measure:**
  - `infrastructure/orchestrators/_auto_detection_execution.py:132-172`: size =
    `account_balance * position_size_pct / current_price`; only a *minimum* floor
    (`:171 if quantity < 0.001: quantity = 0.001`). No maximum, no portfolio cap, no call to the
    container `position_sizing_engine` or `EnterpriseRiskManager.calculate_position_size`.
    `account_balance` defaults to a hardcoded `10000.0` (`:149`) — not real equity.
  - `_auto_detection_execution.py:101-130`: on missing price it fabricates by symbol prefix
    (`BTC→45000`, `ETH→2500`, …) and for unknown symbols `:129-130 current_price =
    random.uniform(0.01, 500.0)`, then uses it for sizing **and** as the order's limit price (`:194`).
- **Diagnose:** Sizing is decoupled from real equity and from any exposure cap; the data-missing
  branch was stubbed with placeholder/random values that leak into live orders.
- **Fix [GATED]:** Source equity from the broker/portfolio service; route sizing through the
  container `position_sizing_engine`; clamp against `risk_engine.get_total_exposure()` remaining
  capacity. **If a real price cannot be obtained, reject the order** — never fabricate/randomize.
- **Re-evaluate:** Eliminates the random-notional hazard and ties size to real capital + exposure.

### H11 — Invalid stop-loss floored to a fabricated 1-unit position — **High**
- **Measure:** `application/position_sizing/enterprise_position_sizing.py:75-77`
  `if risk_per_unit <= 0: return 1.0` (and similar `return 1.0` fallbacks across Kelly/ATR/VolTarget;
  `ProbabilisticPositionSizer:346 risk_per_unit = ... or 0.01`).
- **Diagnose:** Garbage-in (SL == entry) yields a tradable position instead of a rejection; "1 unit"
  of a high-priced asset is a large notional.
- **Fix [GATED]:** Return `0.0` (no trade) on invalid stop distance; caller rejects.
- **Re-evaluate:** Converts a silent fabrication into a clean rejection.

### M — Arbitrary per-price-tier unit caps — **Medium**
`enterprise_position_sizing.py:86-93` `if entry_price > 1000: size = min(size, 10) … else min(size,10000)`
— magic numbers unrelated to equity/exposure. Replace with an equity/exposure-relative cap from the risk engine.

---

## AREA 3 — Exposure controls

### C — No notional / leverage / margin / quantity cap before sending an order — **Critical** (part of C1)
- **Measure:** `_validate_order_parameters_before_broker` (`broker_execution_service.py:547-643`)
  validates only SL/TP direction & distance ratios. **No** `order.quantity` check
  (NaN/zero/negative/max), no notional cap, no leverage limit; the "margin availability" check is the
  hardcoded `True` above. `infrastructure/brokers/multi_broker_service.py:633-717` mirrors this.
- **Diagnose:** No fat-finger / max-notional guard at the single chokepoint to the exchange.
- **Fix [GATED]:** Add fail-closed `isfinite(quantity) and quantity > 0`, min/max notional
  (`quantity * price <= max_position_exposure`), and a max-leverage check in
  `_validate_order_parameters_before_broker`.
- **Re-evaluate:** Bounds the worst-case order independent of upstream sizing bugs.

### H — Live exposure never accumulated; each order sized in isolation — **High**
- **Measure:** sizing uses a flat `account_balance` and never consults aggregate open exposure;
  `EnterpriseRiskManager.get_total_exposure()` (`enterprise_risk_manager.py:381-385`) is only
  reachable through the unwired adapter. Orchestrators hold only a `RiskAlertService`, no risk manager.
- **Diagnose:** N concurrent symbols each size to "x% of balance" with no portfolio ceiling.
- **Fix [GATED]:** Maintain authoritative live exposure (from broker positions or the wired risk
  engine); gate each new order against remaining portfolio capacity.
- **Re-evaluate:** Caps total book size by symbol count; depends on reconciliation (C8) for truth.

---

## AREA 4 — Portfolio limits

### C — `max_portfolio_exposure` / `max_position_exposure` unenforced in live trading — **Critical** (part of C1)
- **Measure:** limits live only in `EnterpriseRiskManager` (`enterprise_risk_manager.py:37-42`,
  enforced in `validate_position_entry:188-195` / `calculate_position_size:166-178`), which the
  production path never calls. The exposing adapter (`risk_engine_adapter.py:43-53`) is built
  (`container.py:562`) but unused.
- **Fix [GATED]:** Wire the container `risk_engine` into `execute_order()` (see C1); feed fills back.
- **Re-evaluate:** Makes the headline `$100k`/`$50k` caps real.

### M — `PortfolioRiskController` correlation/allocation limits are stubs — **Medium**
`infrastructure/risk/strategy_kill_switch.py:454-464`: `_assess_diversification_risk` and
`_assess_allocation_risk` both `return False`; `max_strategy_correlation` / `max_strategy_allocation`
are stored but never evaluated. Implement or remove so they aren't mistaken for active controls.

### M — Daily/drawdown baseline = config constant, not equity — **Medium**
`enterprise_risk_manager.py:110 self.starting_equity = self.max_portfolio_exposure`; daily-loss %
(`:359`) and drawdown measured against the exposure constant, not real equity. Initialize
`starting_equity` from real account equity at session start; reset per trading day.

---

## AREA 5 — Order validation

### C5 / C6 — see `broker_reliability_review.md` (idempotency, fail-open error handling).

### H1 — `Order` entity performs zero field validation — **High**
- **Measure:** `domain/entities/order.py:31-60` — no `__post_init__`; `quantity`, `price`, SL/TP
  accepted unchecked. Sibling `ExecutionIntent.__post_init__` *does* validate (`:26-28`), making the
  omission conspicuous. The only quantity guard is `str(round(float(order.quantity), 6))`
  (`bingx_adapter.py:361`), which happily formats `0`/negative.
- **Diagnose:** No domain-level invariant; malformed orders are valid objects that reach the broker.
- **Fix [GATED]:** Add `__post_init__` to `Order`: `quantity > 0`, `price.amount > 0` when present,
  side/type in allowed enums.
- **Re-evaluate:** Establishes a fail-fast invariant complementing the gate checks (C/H above).

### Positive — symbol whitelist enforced
`multi_broker_service.py:326-330`, `broker_execution_service.py:201-205` consistently reject symbols
not in `symbol_validator.get_approved_symbols()`. Keep.

---

## Priority order (highest leverage first)
1. **C1/C4** — wire the existing `risk_engine` + `position_sizing_engine` into `execute_order()` as
   **fail-closed** gates fed by real equity and live fills; reject orders without a real price.
2. **C2/H10** — make drawdown/leverage breaches **halt** (shared halt flag), not just alert.
3. **H2/H1/C(exposure)** — fail-closed validation + `Order` invariants + quantity/notional/leverage caps.
4. Mediums — boundary/NaN guards, real equity baseline, remove magic-number caps, implement or drop
   correlation/allocation limits.
