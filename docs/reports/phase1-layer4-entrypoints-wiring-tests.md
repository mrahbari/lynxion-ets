# Phase 1 — Layer Report 4: Entry Points, Wiring & Tests

> Detailed exploration report (read-only audit) covering root runners, composition root, cross-cutting concerns, and `tests/`.
> Feeds into `phase1-codebase-audit-report.md`.

---

## 1. ENTRY-POINT INVENTORY (13 runners + 1 container)

| File | LOC | Purpose |
|------|-----|---------|
| `run_trading_system.py` | 1031 | **Primary live orchestrator** — execution, auto-retune + risk monitors, market data streams, background services (threaded) |
| `runner_backtest.py` | 1459 | Multi-strategy backtesting; loads ~10 strategy types from adapters; walk-forward validation |
| `runner_comprehensive_portfolio_backtest.py` | 230 | Portfolio-level backtester; multi-symbol allocation |
| `runner_comprehensive_validation.py` | 451 | End-to-end: backtest → strategy selection → allocation → Monte-Carlo → kill switches |
| `runner_extended_horizon_validation.py` | 393 | Extended-horizon validation; regime/correlation/stress |
| `runner_historical_data_sync.py` | 337 | Sync missing data, repair gaps (file-repository pattern) |
| `runner_history_download.py` | 407 | Download/resample 1m base to multiple timeframes |
| `runner_multitimeframe_update.py` | 332 | Incremental MTF update from 1m base |
| `runner_resync.py` | 481 | Full resync; validation; gap detection/repair (async/context-manager) |
| `runner_retune.py` | 380 | Hyperopt optimization; adaptive performance-based retuning |
| `runner_shadow_deployment.py` | 365 | Shadow/paper trading; KPI monitoring; execution-intent validation |
| `runner_sync_approved_symbols.py` | 160 | Sync approved-symbol list across data/exec/config |
| `runner_walkforward.py` | 307 | WFO pipeline; multi-asset Bayesian hyperopt; cross-validation |

Invocation: `python runner_backtest.py --symbols BTCUSDT ETHUSDT --start ... --end ...`; `python run_trading_system.py` starts the orchestrator.

---

## 2. COMPOSITION ROOT & WIRING

`main_hexagonal_container.py` (343 LOC) is the intended DI root:
- Initializes domain (minimal), application (lazy), infrastructure (FileDataLoader, ResultsTracker, BacktestMetricCalculator, OptimizationRepository, CoinHistoryService, RealisticBacktester, AutoDropEngine), shared (EnhancedLogger), and new-arch components (EngineService, FusionService, StrategyManager + 3 strategies, ConfidenceCalibrator, RegimeDetector, PortfolioRiskManager, ExecutionValidator).
- `_wire_dependencies()` binds ports→adapters; `get_port(name)` / `get_all_ports()` expose them; `_verify_dependencies()` asserts services non-None.

**Critical: runners do NOT use the container.** Each runner manually instantiates adapters inline (e.g. runner_history_download.py:46-49 creates FileRepositoryAdapter + DataDownloaderAdapter + SyncManager). Only tests use the container. → 13 different wiring patterns; behavior drifts per entry point.

**Cross-runner duplication:** Config + symbol-loading block copy-pasted across ~4 runners (~5 lines each). Otherwise wiring is mostly isolated (low duplication, but no central definition).

---

## 3. GLOBAL STATE / SINGLETONS

| Singleton | Location | Risk |
|-----------|----------|------|
| **Configs** | application/configs/configs.py (`__new__`, _initialized flag) | HIGH — mutable class state, not thread-safe, implicit lazy init, race on init check |
| **strategy_manager** | infrastructure/strategies/strategy_manager.py | HIGH — mutable, mutated during container init |
| **broker_registry** | infrastructure/services/broker_registry.py (`__new__`) | HIGH — stores broker connections; only cleared by run_trading_system shutdown |
| **PendingOrdersTracker** | infrastructure/shared/pending_orders_tracker.py (`__new__`) | HIGH — live order state, not reset between runs/tests |
| **event_bus** | shared/event_bus.py (global, daemon thread) | MEDIUM — async ordering not guaranteed; no error propagation |
| **logger** | shared/logger.py | MEDIUM — rotating handler can fail silently |
| **engine_service / fusion_service / regime_detector** | infrastructure/* | MEDIUM — module-level globals |
| **RateLimiter** | shared/rate_limiter.py (`__new__`) | MEDIUM — shared across runners, state not reset |
| **error_service** | shared/exceptions.py | MEDIUM — unclear usage |

Risks: implicit Configs init, no test isolation, no graceful shutdown outside run_trading_system.

---

## 4. CROSS-CUTTING CONCERNS

- **Logging:** decentralized — each module does `EnhancedLogger("Name")`. Consistent class, ad-hoc instantiation. `logs/system.log` hardcoded; rotating handler (1MB, 5 backups).
- **Error handling:** try/except wrapper around `main()` in most runners; no recovery strategy; exceptions printed + logged; event-bus swallows callback exceptions.
- **Configuration:** Configs singleton + `.env` (dotenv). Lazy-initialized on first access; not explicitly initialized in most runners. Some paths hardcoded (data/cache, data/results.db).
- **Event bus:** queue-based, in-memory, daemon thread; minimal adoption — runners orchestrate via raw threads, not events.

---

## 5. TESTS (64 files)

| Directory | Count | Type |
|-----------|-------|------|
| tests/ (root) | 42 | Mixed unit/integration/verification |
| tests/domain/ | 1 | Entity tests |
| tests/infrastructure/ | 8 | Adapter/broker/strategy tests |
| tests/application/ | 2 | Service tests |
| tests/optimization/ | 3 | Hyperopt/import tests |

**Largest:** final_requirements_verification.py (879, 13 TestCase classes, end-to-end verification not pytest), core_component_tests.py (734, unit), wfo_comprehensive_tests.py / wfo_complete_pipeline_tests.py / wfo_component_tests.py (large integration).

**Framework:** `unittest` (42 files). **No `pytest.ini`/`pyproject.toml` pytest config, no conftest, no CI.** Tests depend on CSV data files (fail silently if missing). Minimal mocking — they integrate real Backtester/FileRepository/Hyperopt.

**Coverage:**
- Tested: domain entities, infra adapters, backtest logic, WFO orchestration, strategy adapters, broker integration.
- **Untested (unit level):** infrastructure engines, fusion, market_regime, risk management (sltp/adaptive/portfolio), position sizing, advanced strategy selector/signal processor, live execution engines, watchers (incl. 1778-LOC watcher), shared components (logger/event_bus/rate_limiter/auto_drop_engine), adaptive_retuning.
- Estimate: ~40% touched via integration tests; ~60% unit-untested.

---

## 6. EXECUTION FLOW NOTES

- Backtest: `main() → load_sample_strategy() → RealisticBacktester.run() → MetricCalculator → ResultsTracker`.
- Data sync: `main() → FileRepositoryAdapter + DataDownloaderAdapter → SyncManager.run_sync_cycle()`.
- Live: `run_trading_system.py → ProductionTradingOrchestrator.initialize_system() → LiveExecutionEngine + RiskAlertService + AutoRetuneOptimizer → daemon monitor threads`.
- No strict port enforcement at runtime; runners pass concrete adapters directly. Execution is thread-based, not event-driven; daemon threads lack graceful shutdown guarantees.

---

## KEY FINDINGS

1. MainHexagonalContainer is aspirational — unused by production runners.
2. 10+ mutable global singletons; broken test isolation; no graceful shutdown.
3. Wiring is manual, not DI-driven; repeated per runner.
4. Cross-cutting concerns partially implemented and ad-hoc (logging per-module, event bus unused, implicit Configs init).
5. Test suite is integration-heavy verification scripts, ~60% infra unit-untested, no CI/pytest config.
6. Live execution is thread-based, not event-driven.
