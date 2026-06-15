# Phase 3.5 — Coverage Validation: Feature Inventory ↔ Task Graph

**Purpose:** Verify that every feature catalogued in the Phase 1 **Feature Inventory** (§3 of `phase1-codebase-audit-report.md`) has a corresponding migration task in the Phase 3 **Task Graph** (`phase3-task-graph.md`).
**Method:** Each Phase 1 feature is mapped to the Phase 3 epic/task(s) that migrate/consolidate it. Status is **✅ Covered**, **🟡 Partial** (touched indirectly but no dedicated/explicit task), or **❌ Gap** (no task addresses it).
**Result headline:** 22 of 30 features fully covered, 6 partial, **2 gaps**. All gaps and partials are closed by **8 recommended task additions** in the last section.

---

## 1. Coverage Matrix

### A. Data Management

| # | Phase 1 Feature | Primary file(s) | Phase 3 Task(s) | Status |
|---|---|---|---|---|
| F1 | Multi-exchange historical download (Binance/BingX/MEXC/Phemex) | `infrastructure/brokers/adapters/*`, `runner_history_download.py` | E2.T3, E3.T2, E5.T5 (multi_broker) | ✅ |
| F2 | Multi-timeframe resampling (1m→1d) | `infrastructure/data/resample_engine.py`, `runner_multitimeframe_update.py`, `runner_history_download.py` | E2.T3, E3.T2 | ✅ |
| F3 | Gap detection / repair / full resync | `application/data_sync/sync_manager.py`, `runner_resync.py`, `runner_historical_data_sync.py` | E0.T4 (golden), E2.T3, E3.T2 | ✅ |
| F4 | Data caching + multi-source fallback | `infrastructure/data/{data_cache,improved_data_cache,hybrid_data_provider}.py` | E3.T2 | ✅ |
| F5 | **Data-integrity validation** | `utils/data_integrity_checker.py`, `utils/data_integrity_report.py` | E8.T2 (fold utils) only | 🟡 |
| F6 | Approved-symbol filtering/validation | `application/symbol_management/*`, `infrastructure/services/symbol_validation_service.py`, `runner_sync_approved_symbols.py` | E1.T4, E2.T3 | ✅ |

### B. Strategy Research & Validation

| # | Phase 1 Feature | Primary file(s) | Phase 3 Task(s) | Status |
|---|---|---|---|---|
| F7 | Backtesting w/ fees, slippage, market-impact | `infrastructure/backtest/realistic_backtester.py` | E0.T4, E3.T1, E5.T2 | ✅ |
| F8 | Walk-forward optimization + cross-validation | `application/walk_forward/*`, `runner_walkforward.py` | E2.T4, E5.T1 | ✅ |
| F9 | Hyperparameter optimization (hyperopt/Bayesian) | `application/optimization/hyperopt_integration.py`, `infrastructure/optimization/*`, `runner_retune.py` | E2.T4 | ✅ |
| F10 | **Adaptive retuning (schedule + performance)** | `application/services/adaptive_retuning.py` (523 LOC), `application/data_sync/watcher_retune.py` | E2.T4 (runner migrated) only — no dedicated split/consolidation | 🟡 |
| F11 | **Statistical decision-defensibility** | `infrastructure/statistical_validation/decision_defensibility_validator.py` | E5.T5 (named) | ✅ |
| F12 | **Confidence calibration + randomness firewall** | `infrastructure/statistical_validation/{confidence_calibrator,randomness_firewall,statistical_authority_engine}.py` | not named in any task | 🟡 |
| F13 | Portfolio-level + extended-horizon validation | `infrastructure/portfolio/comprehensive_portfolio_backtester.py`, `runner_comprehensive_validation.py`, `runner_extended_horizon_validation.py` | E2.T4, E3.T1 | ✅ |
| F14 | Monte-Carlo risk + capital-shock testing | `infrastructure/risk/{monte_carlo_simulator,capital_shock_tester}.py` | E3.T4 | ✅ |

### C. Signal Generation & Fusion

| # | Phase 1 Feature | Primary file(s) | Phase 3 Task(s) | Status |
|---|---|---|---|---|
| F15 | **Signal engines** (trend, volatility, correlation, orderflow, liquidity, ML, ATR, regime) | `infrastructure/engines/**` incl. `engine_adapters.py` (722 LOC), `dynamic_engine_manager.py` | E2.T6 (singleton retire), E6.T3 (contract) — **no consolidation/split task; `engine_adapters.py` 722 LOC absent from E5.T5 list** | ❌ |
| F16 | Market-opportunity watchers (9 watcher types) | `infrastructure/watchers/**` incl. `market_opportunity_watcher.py` (1778) | E1.T4, E5.T3 | ✅ |
| F17 | Hierarchical / ML / adaptive signal fusion | `infrastructure/fusion/**` incl. `fusion_service.py` (794) | E5.T5 (fusion_service named) | ✅ |
| F18 | Fusion diversity & **explainability / signal lineage** | `shared/signal_correlation_analyzer.py`, `shared/signal_lineage_tracker.py` | not named in any task | 🟡 |
| F19 | Market-regime detection | `infrastructure/market_regime/regime_detector.py` (789) | E2.T6, E5.T5 (named) | ✅ |

### D. Position Sizing & Risk

| # | Phase 1 Feature | Primary file(s) | Phase 3 Task(s) | Status |
|---|---|---|---|---|
| F20 | ~8 position-sizing models | `application/position_sizing/*`, `infrastructure/position_sizing/*` | E3.T3 | ✅ |
| F21 | Advanced SL/TP management | `infrastructure/risk/advanced_sltp_manager.py` (1353) | E3.T4, E5.T5 (named) | ✅ |
| F22 | Portfolio risk (drawdown/correlation/exposure/allocation) | `infrastructure/risk_management/portfolio_risk_manager.py`, `infrastructure/risk/advanced_risk_management.py` | E3.T4 | ✅ |
| F23 | Strategy kill-switch | `infrastructure/risk/strategy_kill_switch.py` | E3.T4 | ✅ |
| F24 | Multi-symbol risk routing | `infrastructure/risk/multi_symbol_router.py` | E3.T4 | ✅ |

### E. Execution & Live Trading

| # | Phase 1 Feature | Primary file(s) | Phase 3 Task(s) | Status |
|---|---|---|---|---|
| F25 | Multi-broker routing + availability + rate limiting | `infrastructure/brokers/multi_broker_service.py` (866), `shared/rate_limiter.py` | E1.T4, E2.T6, E5.T5 (named) | ✅ |
| F26 | **Execution algorithms (TWAP / VWAP / smart routing)** | `infrastructure/execution/**`, `infrastructure/execution/adapters/{twap,vwap,smart_router}.py`, `application/execution/*` | not named in any task | ❌ |
| F27 | Live production orchestrator (threaded, auto-retune + risk monitors) | `run_trading_system.py` (1031), `infrastructure/orchestrators/auto_detection_orchestrator.py` (1289) | E2.T5, E5.T4 | ✅ |
| F28 | Shadow / paper-trading deployment + KPI monitoring | `runner_shadow_deployment.py`, `infrastructure/monitoring/shadow_kpi_monitor.py` | E2.T5, E3.T5 | ✅ |
| F29 | Forensic logging / audit trails | `infrastructure/logging/forensic_logger.py` (964) | E3.T6, E5.T5 (named) | ✅ |
| F30 | **Live dashboard adapter** | `infrastructure/adapters/live_dashboard*` | not named (reporting moved in E5.T1 is WFO viz only) | 🟡 |

---

## 2. Summary by Status

| Status | Count | Features |
|--------|-------|----------|
| ✅ Covered | 22 | F1–F4, F6–F9, F11, F13, F14, F16, F17, F19–F25, F27–F29 |
| 🟡 Partial | 6 | F5 (data-integrity), F10 (adaptive retuning), F12 (confidence calibration/randomness firewall), F18 (explainability/lineage), F30 (live dashboard) |
| ❌ Gap | 2 | **F15 (signal engines consolidation/split)**, **F26 (execution algorithms TWAP/VWAP/smart routing)** |

**Coverage by epic** (which epics carry the most features):
- E2 (composition root / runner migration) touches the most features — it is the spine; every runner-exposed feature flows through it.
- E3 (consolidation) covers data, sizing, risk, tracking, logging.
- E5 (god-module splits) covers the largest feature-bearing files.
- **E0/E1/E4/E6** are enablers (don't map 1:1 to features but protect/unblock all of them).

---

## 3. Gap & Partial Analysis (what is NOT covered)

### ❌ GAP F15 — Signal engines have no consolidation/split task
The signal **engines** (trend, volatility, correlation, orderflow, liquidity, ML, ATR, regime) are core to the product, yet Phase 3 only *retires the `engine_service` singleton* (E2.T6) and *adds contract tests* (E6.T3). There is **no task to consolidate the engine adapters behind a clean `EnginePort` or to split `engines/adapters/engine_adapters.py` (722 LOC)** — it exceeds the 700-LOC god-module threshold but was omitted from the E5.T5 file list. **Risk if unaddressed:** the engine layer stays a god module and the `dynamic_engine_manager` wiring is never cleaned.

### ❌ GAP F26 — Execution algorithms (TWAP/VWAP/smart routing) untasked
`infrastructure/execution/**` (TWAP, VWAP, smart router, executor) and `application/execution/*` are **not named in any Phase 3 task.** E2.T5 migrates the *live runner* and E5.T5 splits `broker_execution_service.py`, but the execution-algorithm adapters themselves get no port-consolidation or conformance task. **Risk if unaddressed:** execution algos are never placed behind `ExecutionAlgorithmPort`; the `application/execution → infrastructure` violation (Phase 1) persists.

### 🟡 PARTIAL F5 — Data-integrity validation
Only swept up by E8.T2 (folding `utils/` into the new structure). No task verifies the integrity-check *behavior* is preserved or places it behind a port. Currently relegated to "cleanup."

### 🟡 PARTIAL F10 — Adaptive retuning
`adaptive_retuning.py` (523 LOC, flagged a god service in Phase 1) is migrated only as part of the `runner_retune` move (E2.T4). At 523 LOC it falls **below the 700-LOC threshold** that drives E5.T5, so its multi-concern structure (scheduling + performance-checking + retuning) is never split.

### 🟡 PARTIAL F12 — Confidence calibration & randomness firewall
Of the `statistical_validation/` package, only `decision_defensibility_validator.py` is named (E5.T5). `confidence_calibrator.py`, `randomness_firewall.py`, and `statistical_authority_engine.py` have no task — yet the composition root (Phase 2 §0) lists `ConfidenceCalibrator` as a wired component.

### 🟡 PARTIAL F18 — Explainability / signal lineage
`shared/signal_correlation_analyzer.py` and `shared/signal_lineage_tracker.py` (the "explainability" feature) live in `shared/`, which Phase 3 shrinks to dependency-free helpers — but no task explicitly relocates these stateful, domain-aware modules to `infrastructure/`/`application/`.

### 🟡 PARTIAL F30 — Live dashboard adapter
E5.T1 moves only the **WFO matplotlib visualizer** to `interface/reporting/`. The **live dashboard adapter** (`infrastructure/adapters/live_dashboard*`, used by `run_trading_system.py`) is not explicitly relocated to `interface/`.

---

## 4. Recommended Task Additions (close the gaps)

Add these to the Phase 3 Task Graph so coverage reaches 100%.

| New task | Epic | Goal | Input files | Closes | Risk | Validation |
|---|---|---|---|---|---|---|
| **E3.T7 — Consolidate signal engines behind `EnginePort`** | E3 | One engine registry behind `EnginePort`; engines pluggable | `infrastructure/engines/**`, `dynamic_engine_manager.py` | F15 | high | each engine reproduces prior signal on a fixture; contract test passes |
| **E5.T7 — Split `engine_adapters.py` (722 LOC)** | E5 | Bring engine adapters to single-responsibility size | `infrastructure/engines/adapters/engine_adapters.py` | F15 | medium | golden signal output unchanged after split |
| **E3.T8 — Execution algorithms behind `ExecutionAlgorithmPort`** | E3 | TWAP/VWAP/smart routing as adapters behind one port; remove app→infra exec import | `infrastructure/execution/**`, `application/execution/*` | F26 | high | per-algo unit tests; `grep` shows no `application.services.execution_services` import in infra |
| **E3.T9 — Confidence calibration + randomness firewall behind ports** | E3 | Place statistical-validation services behind ports; wire in bootstrap | `infrastructure/statistical_validation/{confidence_calibrator,randomness_firewall,statistical_authority_engine}.py` | F12 | medium | calibration reproduces prior outputs on fixed inputs |
| **E5.T8 — Split `adaptive_retuning.py` (523 LOC)** | E5 | Separate scheduling / performance-check / retuning concerns | `application/services/adaptive_retuning.py` | F10 | medium | retune decisions match prior on fixture history |
| **E3.T10 — Data-integrity validation behind a port** | E3 | Make integrity checks a first-class adapter, not a util | `utils/data_integrity_checker.py`, `utils/data_integrity_report.py` | F5 | low | integrity report matches prior on a corrupted-data fixture |
| **E5.T9 — Relocate explainability/lineage modules** | E5 | Move correlation analyzer + lineage tracker out of `shared/` to proper layer | `shared/signal_correlation_analyzer.py`, `shared/signal_lineage_tracker.py` | F18 | low | lineage output unchanged; `shared/` left dependency-free |
| **E5.T10 — Move live dashboard adapter to `interface/`** | E5 | Dashboard joins reporting in the entry layer | `infrastructure/adapters/live_dashboard*` | F30 | low | dashboard renders from a fixture live state; no infra dependency on it |

---

## 5. Verdict

- **Functional coverage is strong** for the runner-exposed pipeline (data, backtest, WFO, optimization, risk, sizing, live/shadow) — these flow through E2/E3/E5 and are well-tested by the E0 golden gates.
- **Two genuine gaps** (signal engines F15, execution algorithms F26) and **six partials** were found — all caused by either (a) reliance on the 700-LOC god-module threshold that some feature-bearing files miss, or (b) features parked in `shared/`/`utils/` that only the cleanup epic touches.
- **All eight are closed** by the recommended task additions above. With them folded in, **every Phase 1 feature maps to at least one explicit, validated migration task.**

*(Validation/analysis only — no implementation code written. Recommended tasks are proposals to extend the Phase 3 graph, not yet applied to it.)*
