# Lynxion Ground Truth & Engineering Takeover Audit

**Task:** 000
**Audit date:** 2026-08-29
**Branch:** task-00-ground-truth-audit
**Scope:** Read-only code/data/test audit. No production trading logic was changed.

## Executive Summary

The repository has a substantial event-driven trading platform with a guarded execution path, durable journals, strategy adapters, and focused regression coverage. Heartbeat remediation is implemented and its focused tests pass. Current runtime evidence does **not** prove the handover's safety or profitability claims.

Two P0 blockers were verified:

1. Container and guard-fallback risk enforcement instantiate EnterpriseRiskManager() with defaults of $100,000 portfolio and $50,000 per position, not the documented $1,000 / $21 limits.
2. The suite is not green. The paper execution E2E test is blocked by persisted BTC cooldown state, so its result is non-isolated.

The deduplicated trade ledger is severely unprofitable: 1,116 unique completed IDs, -$14,948.79 net PnL, profit factor 0.164, expectancy -$13.40/trade. No promotion, capital increase, or tuning is justified.

## Repository / Git State

**FACT.** Audit started from clean main at 319d9ef870f453387c42e0da3585b2b6481b3e0b; this audit branch was created from it. Historical baseline 75246a1 is an ancestor but not the current experimental state: git diff --stat 75246a1..HEAD reports 58 changed files, 3,285 insertions, and 648 deletions.

## Architecture Map

**FACT.** Intended flow is market observation → SignalProcessor → engine/fusion/strategy → execution service → LiveExecutionGuard → broker. Event subscriptions are in infrastructure/messaging/event_system.py:145-159; market observations enter at lines 168-211. Broker-facing execution is MultiBrokerExecutionService.execute_order (infrastructure/brokers/multi_broker_service.py:424).

**FACT.** Strategy adapters include trend-follow, VWAP reversal, MTF trend, mean reversion, OI footprint, sweep scalper, breakout, liquidity, and reversal implementations under infrastructure/strategies/adapters/.

**UNKNOWN.** No signed-in broker or live WebSocket runtime was invoked; full production composition and broker state remain unproven.

## Runtime / Execution Path

**FACT.** The guard first checks kill switch, circuit breaker, then risk admission, before paper override (shared/live_execution_guard.py:244-277). This means paper execution also depends on global risk state.

**FACT.** Live-order journaling uses an append-only lifecycle and reconstructs latest state by order_ref (infrastructure/execution/live_order_journal.py:48-55, 212-217). Raw JSONL records are not current-order counts.

## Risk Control Verification

| Control | Result | Evidence |
|---|---|---|
| Central live/paper decision gate | FACT: implemented | shared/live_execution_guard.py:244-277 |
| Mandatory finite, side-correct SL | FACT: implemented | infrastructure/risk/risk_enforcement.py:149-203 |
| Normalized, persisted cooldown | FACT: implemented | symbol_cooldown_gate.py:56-59, 95-111, 133-153 |
| Heartbeat fail-close mechanics | FACT: implemented; focused tests pass | event_system.py:161-174 |
| Effective $1,000/$21 caps | **P0 contradicted in current wiring** | Defaults are $100,000/$50,000 at enterprise_risk_manager.py:39-40; container uses defaults at bootstrap/container.py:507; guard fallback does too at live_execution_guard.py:257-262. |
| Single position per symbol | UNKNOWN | Default manager permits 50 concurrent positions (enterprise_risk_manager.py:243-254); no authoritative per-symbol proof found. |
| Mandatory TP/OCO | UNKNOWN | SL admission is explicit; broker-side TP/OCO needs exchange-fixture evidence. |

## Heartbeat Remediation

**FACT.** SignalProcessor.update_market_data_heartbeat initializes state, uppercases/removes hyphens from symbols, and records a supplied timestamp or datetime.now (infrastructure/messaging/event_system.py:161-166). It is called for every routed observation (168-174) and in monitoring ingestion (infrastructure/watchers/monitoring_analysis_service.py:251).

Focused command passed: pytest -q tests/unit/test_heartbeat_guard_remediation.py (part of the 46-test focused safety subset).

## Data / Journals Integrity

### Trade Journal

**FACT.** data/trade_journal.csv contains 1,756 FILLED rows but only 1,116 unique non-empty trade_ids (640 duplicate rows). Metrics use the final occurrence per ID, preserving original order. Time range: 2026-07-08T15:22:25+00:00 to 2026-08-28T18:45:28+00:00.

| Metric | Result |
|---|---:|
| Unique completed trades | 1,116 |
| Net PnL (pnl_usdt) | -$14,948.79 |
| Fees (fees_usdt) | -$558.28 |
| Wins / losses | 359 / 757 |
| Profit factor | 0.164 |
| Expectancy | -$13.40/trade |
| BUY / SELL PnL | -$1,693.21 / -$13,255.59 |
| Missing/invalid initial SL | 742 |
| Missing/invalid initial TP | 742 |

The missing protection fields are historical data-quality evidence, not proof that present broker protection is absent. They block a retrospective 100%-compliance claim.

### Live Order Journal and Position State

**FACT.** data/live_order_journal.json is JSON Lines, with 4,567 records: INTENT 2,072; FAILED 1,644; SUBMITTED 416; FILLED 368; CANCELLED 67. Raw open-state count is 2,488, but cannot establish current in-flight orders without derived state and a broker query.

**FACT.** data/active_positions_journal.json is {"active_symbols": []}. This is local state, not broker confirmation.

## Strategy Inventory and Performance Attribution

| Strategy | Trades | PnL | Win rate |
|---|---:|---:|---:|
| trend_following | 729 | -$14,763.64 | 31.7% |
| VWAPReversal | 192 | -$152.25 | 28.6% |
| MTFTrend | 61 | -$18.21 | 44.3% |
| SweepScalper | 63 | -$9.24 | 36.5% |
| TrendFollow | 35 | -$9.21 | 17.1% |
| MeanReversion | 23 | +$1.09 | 39.1% |
| OIFootprint | 13 | +$2.67 | 61.5% |

Positive subgroups have inadequate sample sizes. Results are descriptive, not evidence of edge.

## Exit Management Assessment

**FACT.** ActivePositionManager fetches broker positions, derives direction/price, and attempts to attach a 3% SL if no pending stop exists (infrastructure/risk/active_position_manager.py:83-216). Defaults configure 6% ROE breakeven and 10% trailing activation (31-43).

Exit attribution: 389 STOP_MARKET exits lost $8,290.98; 217 TAKE_PROFIT_MARKET exits earned $1,715.41. LIMIT exits are anomalous: 18 records, -$5,246.80 despite 83.3% win rate; review is required.

**UNKNOWN.** No broker proof establishes amendment acceptance, OCO correctness, real fill-price reconciliation, or economic value of BE/trailing.

## Prospective Validation Status

**FACT.** Existing documents name trade #694 as the historical boundary. **UNKNOWN** whether the present CSV can safely reproduce it: duplicate IDs and no immutable cohort field mean a segmentation calculation would be unsafe. Aggregate current results do not support promotion.

## Previous Claim Verification

| Claim | Verdict |
|---|---|
| Heartbeat remediation | FACT: code and focused tests prove unit-level behavior. |
| 446/446 tests passing | FALSE now: pytest -xq produced 126 passed, 1 failed, 1 skipped. |
| $1,000/$21 limits | CONTRADICTED by current default construction. |
| All 1,893 journal orders reconciled | UNVERIFIED: current JSONL has 4,567 lifecycle records; broker query not run. |
| 100% exchange protection | UNKNOWN: local active state is empty; no broker evidence. |
| Profitable prospective cohort | FALSE as a project-level conclusion: aggregate expectancy is deeply negative. |

## Proven Facts

- Guard, risk adapter, cooldown gate, and heartbeat implementation exist and focused safety tests pass.
- The full test baseline is red because persisted cooldown state contaminates an E2E test.
- Current risk-manager defaults contradict the claimed VST caps.
- Deduplicated trade performance is negative and short-side losses dominate.

## Unverified Claims

- Live broker reconciliation and exchange-side SL/TP/OCO coverage.
- Actual production-entrypoint configuration.
- Immutable trade-#694 cohort membership.
- Full path uniqueness and per-symbol position invariant.
- Live WebSocket heartbeat behavior.

## Open Risks and Technical Debt

1. **P0:** effective limits may be $100,000/$50,000, not $1,000/$21.
2. **P0:** tests read live persisted cooldown state.
3. **P1:** duplicate IDs and missing initial protection fields impair analysis.
4. **P1:** no reproducible derived journal-state report.
5. **P1:** anomalous LIMIT exits require record-level review.
6. **P2:** Pydantic v1 APIs emit deprecation warnings under Pydantic v2.

## Ranked Engineering Priorities

1. **P0:** make VST caps explicit in the authoritative guard/composition-root risk instance and add guard-path regression coverage.
2. **P0:** isolate tests from repository runtime journals via injected temporary cooldown state; do not alter live history.
3. **P1:** add a derived latest-state-by-order_ref audit and read-only broker reconciliation report.
4. **P1:** freeze a reproducible cohort ledger before any performance decision.
5. **P1:** perform immutable forensic analysis of LIMIT records and short-side losses.

## Recommended Next Task

**TASK 001 — Fail-closed effective risk-cap wiring and regression coverage.**

Prove and enforce documented VST caps at the LiveExecutionGuard path with tests that reject $21.01 orders and portfolio exposure above $1,000. Acceptance: full suite isolated from persisted journals and green; no alteration to historical journals, prospective boundary, or trading enablement.

## Do Not Do Yet

- Do not deploy or enable real-money trading.
- Do not raise leverage, limits, capital, or frequency.
- Do not tune against trade #695 onward or reset its boundary.
- Do not rewrite/delete/deduplicate historical journals in place.
- Do not add ML, Kelly sizing, exchanges, or new strategy features.
- Do not claim reconciliation/OCO coverage without broker evidence.

## Follow-up Task Ledger

### TASK 001 — Fail-closed VST execution caps

**Result: completed.** Commit `e959324` introduced the single
`build_vst_risk_enforcement` factory used by both container wiring and the guard fallback.
It sets a $1,000 portfolio cap and a strict $21 per-order cap; over-limit orders are
rejected rather than silently resized. The paper E2E fixture now uses a compliant order,
includes a valid stop loss, and snapshots/restores cooldown state in memory without
changing the persisted runtime journal.

**Validation:** 31 focused tests passed. A subsequent full run reached 606 passed and 1
skipped; its only two failures are local settings-snapshot mismatches limited to MEXC key
fields, outside this task's scope.

### TASK 002 — Derived live-order journal state

**Result: completed.** Commit `127b3da` adds `scripts/audit_live_order_journal.py`, a
read-only JSONL report with a no-write regression test. Against the current journal it
reports 2,075 unique orders, 0 in flight, 416 mapped exchange order IDs, and local net
positions of BTCUSDT 0.6263 and DOGEUSDT 86.0. The local net positions conflict with the
empty active-position snapshot and require a read-only broker reconciliation before any
state repair.

### TASK 003 — Reproducible trade-journal cohort analysis

**Result: completed.** Commit `bcdbf4f` adds `scripts/audit_trade_journal.py`, which
deduplicates by final trade ID, applies an explicit inclusive exit-timestamp boundary, and
never changes the source CSV. For the documented 2026-08-13T13:31:42+00:00 boundary, the
actual dataset has 419 completed unique trades, -$253.1793 PnL, 0.2074 profit factor, and
-$0.6042 expectancy. The previous 92/100 cohort claim is therefore false for the current
data snapshot.

**Forensic extension (uncommitted at this entry):** The same report now attributes cohort
PnL by side, exit reason, and strategy. MARKET exits account for -$253.8165, BUY trades
for -$218.5403, and SELL trades for -$34.6390; take-profit exits contribute +$58.1593.
This is a diagnosis signal, not authorization to tune or disable a strategy.

### TASK 004 — Local position-state drift visibility

**Result: completed.** Commit `3dbda3f` extends the read-only live-order journal report
to compare derived local net positions against `active_positions_journal.json`. Current
evidence: the snapshot has no active symbols while the journal derives BTCUSDT and DOGEUSDT.
No state was repaired or broker endpoint called.

### Regression status after Tasks 001–004

The full local test run completed with 611 passed, 2 failed, and 1 skipped. The two failures
are settings-loader golden-snapshot differences limited to local MEXC credential fields.
Changing a credential-bearing baseline or its loading semantics is security-sensitive and
requires an operator decision; it was intentionally left out of these tasks.

### TASK 005 — VST broker-state verification

**Result: partially completed, read-only verification plus local snapshot recovery.** Commit
`8e29f9f` introduced `BrokerReconciliationService.inspect`, which cannot write state or halt
trading. A read-only BingX VST query found active broker positions while the persisted active
snapshot was empty. The standard existing reconciliation was then run against VST only; it
updated the local active snapshot to 22 symbols, did not alter exchange orders, and did not
engage the kill switch. One `ONDOUSDT` intent remains recoverable because it has no broker
acknowledgement/order ID; it was not fabricated into a terminal state.

At verification time total VST entry notional was $419.8565, within the $1,000 portfolio cap.
One existing position had $24.334 entry notional, above the new $21 hard per-order cap. The
cap prevents new violations; reducing or closing the pre-existing position would affect the
prospective execution record and requires an explicit operator decision.

**Protective-order evidence:** A read-only VST open-orders query found 22 open positions,
22 `STOP_MARKET` orders, and 22 `TAKE_PROFIT_MARKET` orders. Each open position matched one
SL and one TP after normalized symbol comparison. Commit `9ef59e0` adds the reusable
`scripts/audit_vst_protection.py` report; it refuses to run unless BingX VST/testnet is
enabled. No exchange order was created, amended, cancelled, or closed during this audit.

### Current test baseline

After all completed tasks, `pytest -q` reports 615 passed and 1 skipped. The only skip is
the optional import-layering test, because `import-linter` is not installed.

## Reproducible Commands

    git status --short --branch
    git log --oneline --decorate -10
    pytest -xq
    pytest -q tests/unit/test_heartbeat_guard_remediation.py tests/unit/test_risk_enforcement.py tests/unit/test_symbol_cooldown_gate.py tests/unit/test_b4_broker_reconciliation.py tests/unit/test_live_execution_guard.py

Data metrics came from a read-only standard-library csv/json inspection, deduplicating the trade CSV by final trade_id record.
