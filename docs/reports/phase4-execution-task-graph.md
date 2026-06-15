# Phase 4 — FINAL EXECUTION TASK GRAPH

**Repository:** Lynxion ETS
**Status:** Authoritative, execution-ready plan. Supersedes the draft graph in `phase3-task-graph.md` by folding in the 8 gap-closure tasks from `phase3.5-coverage-validation.md`.
**Inputs honored:** Phase 1 Feature Inventory (F1–F30), Phase 2 target structure, Phase 3.5 coverage report (all ❌ gaps + 🟡 partials promoted to explicit tasks).
**Migration pattern:** Strangler — new implementations stood up beside old, traffic redirected, old deleted only after `grep` proves zero importers.

---

## 1. EXECUTION PRINCIPLES

1. **One task = one logical change.** A task touches a single capability/seam and is completable in one coding iteration.
2. **Always-green.** The full unit suite (`pytest -m "not integration"`) and all relevant golden tests must pass before a task is merged. A task that can't keep the system green must be split.
3. **Backward compatibility during transition.** While migrating, the old path keeps working (shim/adapter) until every caller is moved. No caller is left dangling.
4. **No full rewrites.** Large files are split by extraction, never rewritten from scratch. Each extraction preserves observable behavior.
5. **Behavior is pinned before it is moved.** Any consolidation/deletion is gated by a golden/characterization test captured in E0.
6. **No cross-epic coupling in a single task.** A task may *depend on* another epic's completed task, but does not bundle work from two epics.
7. **Strangler redirection, then deletion.** New code is introduced (additive), callers are redirected, and only then is dead code deleted — deletion always in its own task after a zero-importer `grep`.
8. **Every task references real file paths.** No generic tasks. If a task can't name a file, it is invalid.
9. **Settings are injected, never imported.** From E1 onward, no new code may `import Configs`; the global is removed, not extended.
10. **Dependencies point inward.** No task may add an `application→infrastructure`, `infrastructure→application`, `domain→outer`, or `*→bootstrap` import; from E6 this is CI-enforced.

---

## 2. FINAL EPIC STRUCTURE

| Epic | Purpose | Depends on | Risk |
|------|---------|-----------|------|
| **E0 — Safety Net & Tooling** | pytest config, CI, golden/characterization tests so regressions are detectable | — | low |
| **E1 — Settings & `Configs` Cycle Break** | Replace `Configs` singleton with injected typed settings; remove infra↔app cycle | E0 | medium |
| **E2 — Composition Root & Runner Migration** | Single `bootstrap/` wiring; migrate all 13 runners; retire global singletons | E1 | medium–high |
| **E3 — Consolidation Behind Ports** | One port + one canonical adapter per capability (backtest, data, sizing, risk, tracking, logging, **engines, execution, stats, integrity**) | E2 | high |
| **E4 — Domain Model Unification** | Merge entities, delete shadow model, remove pandas from domain, enforce VOs | E2 (parallel-safe) | medium |
| **E5 — Interface Layer & God-Module Splits** | Carve `interface/`; move reporting/dashboard; split files >700 LOC + the two sub-threshold offenders | E3, E4 | high |
| **E6 — Rule Enforcement & Test Pyramid** | import-linter contracts, conformance tests, mypy-strict, unit backfill | E2–E5 | low |
| **E7 — Scale-Readiness (optional)** | DB persistence, distributed bus, REST API, workers — behind existing ports | E3, E6 | medium–high |
| **E8 — Continuous Cleanup & Decommission** | Delete superseded modules, fold `utils/`, refresh docs | the task that supersedes each file | low |

---

## 3. FINAL TASK GRAPH

> Field key — **Type:** refactor / extraction / consolidation / migration / test / deletion. **MUST NOT / MUST preserve** = hard behavioral constraints. **Validation** = exact pass condition.

---

### Epic E0 — Safety Net & Tooling

#### Task ID: E0.T1
- Goal: One-command test execution with central config and markers.
- Problem it solves: P8 — no `pytest.ini`/`pyproject.toml`, no marker discipline.
- Files involved: `pyproject.toml` (new), `tests/conftest.py` (new)
- Feature mapping: enabler for all F1–F30
- Type: test
- Risk level: low
- Dependencies: none
- Implementation constraints:
  - MUST NOT modify any production module.
  - MUST register markers `unit`, `integration`, `e2e`, `contract`.
- Validation method: `pytest --collect-only` succeeds with zero import/collection errors across `tests/**`.

#### Task ID: E0.T2
- Goal: Establish a known-green baseline; mark data-dependent scripts as integration.
- Problem it solves: P8 — integration/verification scripts mixed with unit tests; some fail on missing CSVs.
- Files involved: `tests/final_requirements_verification.py`, `tests/core_component_tests.py`, `tests/wfo_comprehensive_tests.py`, `tests/wfo_complete_pipeline_tests.py`, `tests/wfo_component_tests.py`, `tests/domain/**`, `tests/application/**`, `tests/infrastructure/**`, `tests/optimization/**`
- Feature mapping: enabler
- Type: test
- Risk level: low
- Dependencies: E0.T1
- Implementation constraints:
  - MUST NOT delete any test; only annotate (`@pytest.mark.integration` / `@pytest.mark.skip(reason=...)`).
  - MUST preserve each test's assertions unchanged.
- Validation method: `pytest -m "not integration"` is green; every skip has an explicit reason string.

#### Task ID: E0.T3
- Goal: CI runs the unit suite on every push/PR.
- Problem it solves: P8 — no CI gate.
- Files involved: `.github/workflows/ci.yml` (new), `pyproject.toml`
- Feature mapping: enabler
- Type: test
- Risk level: low
- Dependencies: E0.T1, E0.T2
- Implementation constraints:
  - MUST run `pytest -m "not integration"`.
  - MUST fail the build on any test failure.
- Validation method: CI green on the baseline commit; a deliberately broken test turns CI red.

#### Task ID: E0.T4
- Goal: Golden/characterization tests pinning the canonical backtest + data-sync outputs.
- Problem it solves: Protects E3/E5 consolidations from silent behavior drift.
- Files involved: `infrastructure/backtest/realistic_backtester.py`, `runner_backtest.py`, `infrastructure/data/configurable_historical_data_provider.py`, `application/data_sync/sync_manager.py`; new `tests/e2e/test_backtest_golden.py`, `tests/e2e/test_datasync_golden.py`, `tests/fixtures/golden/*.json`
- Feature mapping: F3, F7, F13 (pins behavior consumed by all consolidations)
- Type: test
- Risk level: medium
- Dependencies: E0.T1
- Implementation constraints:
  - MUST fix RNG seed, freeze timestamps, and stub network so output is deterministic.
  - MUST use a tiny committed dataset (no live API).
- Validation method: golden test produces identical output on two consecutive runs; any output change fails the diff.

---

### Epic E1 — Settings & `Configs` Cycle Break

#### Task ID: E1.T1
- Goal: Typed, frozen, validated settings objects mirroring current config domains.
- Problem it solves: P2 — untyped global `Configs`.
- Files involved: read `application/configs/configs.py`, `application/configs/enhanced_config_loader.py`, `application/configs/schemas/*`, `application/configs/profiles/{dev,staging,live}.py`; write `bootstrap/settings/schema.py`, `bootstrap/settings/profiles/`
- Feature mapping: enabler for all
- Type: extraction
- Risk level: low
- Dependencies: E0.T1
- Implementation constraints:
  - MUST NOT wire anything yet (additive only).
  - MUST preserve every existing config field name + default.
- Validation method: unit test builds each profile; field values equal those returned by current `Configs`.

#### Task ID: E1.T2
- Goal: Single loader producing the schema objects from env + profile.
- Problem it solves: P5 (config duplication) — two loaders + dead `loader.py`.
- Files involved: read `application/configs/enhanced_config_loader.py`, `application/configs/env_loader.py`; write `bootstrap/settings/loaders.py`
- Feature mapping: enabler
- Type: consolidation
- Risk level: low
- Dependencies: E1.T1
- Implementation constraints:
  - MUST reproduce values for dev/staging/live identical to `EnhancedConfigLoader`.
- Validation method: unit test asserts loaded values match a snapshot of current `Configs` per profile.

#### Task ID: E1.T3
- Goal: Make legacy `Configs` delegate to the new loader (compatibility shim).
- Problem it solves: P2 — lets callers migrate without breakage.
- Files involved: `application/configs/configs.py`
- Feature mapping: enabler
- Type: refactor
- Risk level: medium
- Dependencies: E1.T2
- Implementation constraints:
  - MUST NOT change `Configs`' public attribute API.
  - MUST preserve lazy-init semantics during transition.
- Validation method: full unit suite green; a runner prints identical config values before/after.

#### Task ID: E1.T4
- Goal: Remove `from application.configs import Configs` from infrastructure; inject settings via constructors. Batched: (a) `data/`, (b) `brokers/`, (c) `fusion/`+`logging/`+`orchestrators/`+`portfolio/`, (d) `services/`, (e) `watchers/`, (f) `data_sync/`.
- Problem it solves: **P1 (the infra→app cycle)**.
- Files involved: `infrastructure/data/configurable_historical_data_provider.py`, `infrastructure/data/enhanced_data_provider.py`, `infrastructure/data/hybrid_data_provider.py`, `infrastructure/data/wfo_config.py`, `infrastructure/brokers/multi_broker_service.py`, `infrastructure/fusion/fusion_service.py`, `infrastructure/logging/forensic_logger.py`, `infrastructure/orchestrators/auto_detection_orchestrator.py`, `infrastructure/portfolio/comprehensive_portfolio_backtester.py`, `infrastructure/services/symbol_validation_service.py`, `infrastructure/services/symbol_discovery_service.py`, `infrastructure/services/broker_execution_service.py`, `infrastructure/data_sync/data_downloader_adapter.py`, `infrastructure/data_sync/file_repository_adapter.py`, `infrastructure/watchers/**`
- Feature mapping: F1, F2, F4, F6, F16, F17, F25, F27, F29
- Type: migration
- Risk level: medium
- Dependencies: E1.T3, E2.T1 (container passes settings in)
- Implementation constraints:
  - MUST NOT change adapter behavior — only the source of config.
  - MUST migrate in batches with the suite green between batches.
- Validation method: after each batch `grep -rn "from application" infrastructure/` count strictly decreases; golden tests (E0.T4) unchanged.

#### Task ID: E1.T5
- Goal: Remove remaining `Configs` imports from application/shared, including the shared→application back-edge.
- Problem it solves: P1/P2 — last cross-layer config imports.
- Files involved: `shared/event_system.py` (line 12), `application/services/*` (those importing `Configs`), `application/walk_forward/*`
- Feature mapping: F8, F17 (event routing), enabler
- Type: migration
- Risk level: medium
- Dependencies: E1.T4
- Implementation constraints:
  - MUST preserve event-routing behavior in `event_system.py`.
- Validation method: `grep -rn "configs import Configs" application shared infrastructure` returns 0 outside `bootstrap/` and `application/configs/`.

#### Task ID: E1.T6
- Goal: Delete dead/legacy config code now that nothing imports it.
- Problem it solves: P5/P10 — 841-LOC dead `loader.py`, redundant settings.
- Files involved: delete `application/configs/loader.py`, `application/configs/hexagonal_settings.py`; retire `application/configs/configs.py` shim
- Feature mapping: enabler
- Type: deletion
- Risk level: low
- Dependencies: E1.T5
- Implementation constraints:
  - MUST `grep`-confirm zero importers before deleting each file.
- Validation method: suite green; `grep` shows no references; app boots via `bootstrap/settings`.

---

### Epic E2 — Composition Root & Runner Migration

#### Task ID: E2.T1
- Goal: Build the single composition root that constructs adapters, injects settings, exposes wired use cases.
- Problem it solves: P3 — composition root bypassed.
- Files involved: read `main_hexagonal_container.py`, `application/containers/container.py`, `application/factories/trading_factories.py`; write `bootstrap/container.py`, `bootstrap/lifecycle.py`
- Feature mapping: enabler for all runner-exposed features
- Type: extraction
- Risk level: medium
- Dependencies: E1.T2
- Implementation constraints:
  - MUST resolve every domain port without error.
  - MUST own startup/shutdown (no module-level side effects).
- Validation method: smoke test builds container and resolves all ports; teardown releases resources.

#### Task ID: E2.T2
- Goal: Pilot-migrate the most-exercised runner to the container.
- Problem it solves: P3 — proves the strangler pattern end-to-end.
- Files involved: `runner_backtest.py` → `interface/cli/backtest.py` (new), `application/use_cases/run_backtest.py` (new)
- Feature mapping: F7
- Type: migration
- Risk level: medium
- Dependencies: E2.T1, E0.T4
- Implementation constraints:
  - MUST keep `runner_backtest.py` working (delegating) until CLI shell verified.
  - MUST preserve CLI arguments and output format.
- Validation method: golden backtest test (E0.T4) byte-identical via the new path.

#### Task ID: E2.T3
- Goal: Migrate data/sync runners onto the container.
- Problem it solves: P3, copy-paste runner wiring.
- Files involved: `runner_historical_data_sync.py`, `runner_history_download.py`, `runner_multitimeframe_update.py`, `runner_resync.py`, `runner_sync_approved_symbols.py` → `interface/cli/*.py`, `application/use_cases/sync_market_data.py` (new)
- Feature mapping: F1, F2, F3, F6
- Type: migration
- Risk level: medium
- Dependencies: E2.T2
- Implementation constraints:
  - MUST preserve gap-repair output and file layout.
- Validation method: data-sync golden test (E0.T4) identical on fixture dataset.

#### Task ID: E2.T4
- Goal: Migrate validation/optimization runners onto the container.
- Problem it solves: P3.
- Files involved: `runner_comprehensive_portfolio_backtest.py`, `runner_comprehensive_validation.py`, `runner_extended_horizon_validation.py`, `runner_walkforward.py`, `runner_retune.py` → `interface/cli/*.py`, `application/use_cases/run_walkforward.py` (new), `application/use_cases/optimize_strategy.py` (new)
- Feature mapping: F8, F9, F10, F13, F14
- Type: migration
- Risk level: medium
- Dependencies: E2.T2
- Implementation constraints:
  - MUST preserve WFO/optimization numeric outputs within documented tolerance.
- Validation method: pinned WFO/optimization fixture run matches prior within tolerance.

#### Task ID: E2.T5
- Goal: Migrate live + shadow runners with proper lifecycle/shutdown.
- Problem it solves: P3/P4/P9 — threaded live path, no graceful shutdown.
- Files involved: `run_trading_system.py`, `runner_shadow_deployment.py` → `interface/cli/live.py`, `interface/cli/shadow.py`, `application/use_cases/run_live_trading.py` (new), `application/use_cases/run_shadow_deployment.py` (new); uses `infrastructure/execution/live_execution_engine.py`, `infrastructure/execution/live_auto_retune_engine.py`
- Feature mapping: F27, F28
- Type: migration
- Risk level: high
- Dependencies: E2.T2, E2.T3
- Implementation constraints:
  - MUST NOT place real orders in tests (sandbox/paper only).
  - MUST shut down cleanly (close broker registry + pending-orders tracker; no leaked daemon threads).
- Validation method: shadow run completes one full cycle in sandbox; teardown asserts zero live threads remaining.

#### Task ID: E2.T6
- Goal: Convert global singletons to container-scoped instances.
- Problem it solves: **P4** — mutable globals break test isolation.
- Files involved: `infrastructure/strategies/strategy_manager.py`, `infrastructure/services/broker_registry.py`, `infrastructure/shared/pending_orders_tracker.py`, `shared/rate_limiter.py`, `infrastructure/engines/engine_service.py`, `infrastructure/fusion/fusion_service.py`, `infrastructure/market_regime/regime_detector.py`
- Feature mapping: F15, F17, F19, F23, F25
- Type: refactor
- Risk level: high
- Dependencies: E2.T1, plus the runner migrations consuming each singleton
- Implementation constraints:
  - MUST remove module-level instantiation; instances created in `bootstrap/container.py`.
  - MUST preserve single-instance-per-run semantics within a container.
- Validation method: a test builds two containers and asserts independent state; full suite green.

---

### Epic E3 — Consolidation Behind Ports

#### Task ID: E3.T1
- Goal: One backtest engine behind `BacktestEnginePort`; portfolio/comprehensive variants become modes.
- Problem it solves: **P5** — 4–5 backtesters.
- Files involved: keep `infrastructure/backtest/realistic_backtester.py`; reduce/delete `infrastructure/backtest/real_backtest_engine.py`, `infrastructure/backtest/realistic_backtest_engine.py`, `infrastructure/portfolio/comprehensive_portfolio_backtester.py`, `infrastructure/validation/comprehensive_backtest_validator.py`; port `domain/ports/backtest_ports.py`
- Feature mapping: F7, F13
- Type: consolidation
- Risk level: high
- Dependencies: E0.T4, E2.T2
- Implementation constraints:
  - MUST keep golden backtest output byte-identical.
  - MUST NOT change fee/slippage/impact math.
- Validation method: E0.T4 golden identical; portfolio mode matches pinned multi-symbol fixture.

#### Task ID: E3.T2
- Goal: One data provider + one cache behind `DataProviderPort`/`DataCachePort`; fold `data_sync/` into `data/`+`persistence/`.
- Problem it solves: **P5** — 5–6 providers, 2 caches.
- Files involved: consolidate `infrastructure/data/enhanced_data_provider.py`, `configurable_historical_data_provider.py`, `csv_history_loader.py`, `hybrid_data_provider.py`, `market_data_loader.py`, `coin_history_service.py`, `data_cache.py`, `improved_data_cache.py`, `infrastructure/data_sync/*`; ports `domain/ports/data.py`
- Feature mapping: F1, F2, F3, F4
- Type: consolidation
- Risk level: high
- Dependencies: E0.T4, E2.T3
- Implementation constraints:
  - MUST preserve multi-source fallback order and cache TTL behavior.
- Validation method: data-sync golden identical; cache hit/miss unit-tested.

#### Task ID: E3.T3
- Goal: One position-sizing adapter behind `PositionSizingPort`; algorithms pluggable.
- Problem it solves: **P5** — sizing in 4 places.
- Files involved: consolidate `application/position_sizing/enterprise_position_sizing.py`, `application/services/position_sizing_service.py`, `infrastructure/position_sizing/probabilistic_position_sizer.py`, `infrastructure/position_sizing/advanced_position_sizing.py`
- Feature mapping: F20
- Type: consolidation
- Risk level: medium
- Dependencies: E2.T1
- Implementation constraints:
  - MUST reproduce each algorithm's size output for fixed inputs.
- Validation method: per-algorithm unit tests reproduce current outputs.

#### Task ID: E3.T4
- Goal: One risk module behind `RiskManagementPort`/`RiskGovernorPort`; separate SL/TP from portfolio risk.
- Problem it solves: **P5** — parallel `risk/` + `risk_management/`.
- Files involved: `infrastructure/risk/advanced_risk_management.py`, `infrastructure/risk/advanced_sltp_manager.py`, `infrastructure/risk/adaptive_risk_manager.py`, `infrastructure/risk/strategy_kill_switch.py`, `infrastructure/risk/monte_carlo_simulator.py`, `infrastructure/risk/capital_shock_tester.py`, `infrastructure/risk/multi_symbol_router.py`, `infrastructure/risk_management/portfolio_risk_manager.py`, `application/risk_management/enterprise_risk_manager.py`
- Feature mapping: F14, F21, F22, F23, F24
- Type: consolidation
- Risk level: high
- Dependencies: E2.T1
- Implementation constraints:
  - MUST preserve kill-switch / drawdown / exposure decisions exactly.
- Validation method: risk-decision unit tests reproduce prior decisions on fixed scenarios.

#### Task ID: E3.T5
- Goal: One tracking adapter behind `TrackingPort`.
- Problem it solves: **P5** — tracking fragmented across 3 dirs.
- Files involved: `infrastructure/tracking/trade_tracker.py`, `infrastructure/results_tracking/results_tracker.py`, `infrastructure/monitoring/shadow_kpi_monitor.py`
- Feature mapping: F28
- Type: consolidation
- Risk level: medium
- Dependencies: E2.T1
- Implementation constraints:
  - MUST preserve tracked-metric values + persistence format.
- Validation method: tracked metrics for a fixture run match prior tracker output.

#### Task ID: E3.T6
- Goal: One logger behind `LoggingPort` + one event bus behind `MessagingPort`.
- Problem it solves: **P5** — duplicate loggers, 3 event systems.
- Files involved: `shared/logger.py`, `utils/logger.py`, `shared/event_system.py`, `shared/event_bus.py`, `shared/hexagonal_utils.py` → `infrastructure/monitoring/` (logging) + `infrastructure/messaging/` (bus)
- Feature mapping: F29 (logging), F16/F17 (event routing)
- Type: consolidation
- Risk level: medium
- Dependencies: E1.T5
- Implementation constraints:
  - MUST preserve log format; MUST surface callback exceptions (no silent swallowing).
- Validation method: log-format snapshot unchanged; pub/sub unit test delivers events and propagates a raised callback error.

#### Task ID: E3.T7  *(gap-closure: F15)*
- Goal: Consolidate signal engines behind `EnginePort` via one registry; engines pluggable.
- Problem it solves: **Gap F15** — engines had no consolidation task.
- Files involved: `infrastructure/engines/engine_service.py`, `infrastructure/engines/dynamic_engine_manager.py`, `infrastructure/engines/base_engine_adapter.py`, `infrastructure/engines/adapters/{trend_engine,volatility_engine,correlation_engine,orderflow_engine,liquidity_engine,ml_weight_engine,atr_risk_engines,regime_engine,registry}.py`; port `domain/ports/engine.py`
- Feature mapping: F15
- Type: consolidation
- Risk level: high
- Dependencies: E2.T6 (engine_service singleton retired)
- Implementation constraints:
  - MUST reproduce each engine's signal output on a recorded fixture.
  - MUST NOT alter engine scoring formulas.
- Validation method: per-engine golden signal output unchanged; `EnginePort` contract test passes for each engine.

#### Task ID: E3.T8  *(gap-closure: F26)*
- Goal: Place execution algorithms behind `ExecutionAlgorithmPort`/`ExecutionPort`; remove app→infra execution import.
- Problem it solves: **Gap F26** — execution algos untasked; `application/execution → infrastructure` violation.
- Files involved: `infrastructure/execution/advanced_execution_service.py`, `infrastructure/execution/execution_adapters.py`, `infrastructure/execution/adapters/{twap,vwap,smart_router,executor}.py`, `application/execution/advanced_execution_algorithms.py`, `application/execution/advanced_execution_engine.py`; ports `domain/ports/execution.py`
- Feature mapping: F26
- Type: consolidation
- Risk level: high
- Dependencies: E2.T1; coordinate with E1.T4 (advanced_execution_service de-Configs)
- Implementation constraints:
  - MUST preserve TWAP/VWAP slicing schedules + smart-routing decisions.
  - MUST remove `infrastructure/execution/advanced_execution_service.py:11 from application.services.execution_services`.
- Validation method: per-algorithm unit tests reproduce slice schedules; `grep -rn "from application" infrastructure/execution/` returns 0.

#### Task ID: E3.T9  *(gap-closure: F12)*
- Goal: Place statistical-validation services behind ports; wire in bootstrap.
- Problem it solves: **Partial F12** — confidence calibrator/randomness firewall untasked.
- Files involved: `infrastructure/statistical_validation/confidence_calibrator.py`, `infrastructure/statistical_validation/randomness_exposure_firewall.py`, `infrastructure/statistical_validation/statistical_authority_engine.py`, `infrastructure/statistical_validation/historical_data_tracker.py`, `infrastructure/statistical_validation/decision_defensibility_validator.py`
- Feature mapping: F11, F12
- Type: consolidation
- Risk level: medium
- Dependencies: E2.T1
- Implementation constraints:
  - MUST reproduce calibration + firewall outputs on fixed inputs.
- Validation method: calibration/firewall unit tests reproduce prior outputs; components resolvable from `bootstrap/container.py`.

#### Task ID: E3.T10  *(gap-closure: F5)*
- Goal: Make data-integrity validation a first-class adapter behind a `DataIntegrityPort`.
- Problem it solves: **Partial F5** — integrity only swept by cleanup.
- Files involved: `utils/data_integrity_checker.py`, `utils/data_integrity_report.py` → `infrastructure/data/integrity/` (new); port `domain/ports/data.py` (extend)
- Feature mapping: F5
- Type: migration
- Risk level: low
- Dependencies: E2.T1
- Implementation constraints:
  - MUST preserve integrity-report fields and pass/fail thresholds.
- Validation method: integrity report on a corrupted-data fixture matches prior output exactly.

---

### Epic E4 — Domain Model Unification

#### Task ID: E4.T1
- Goal: Merge the two entity sets into one canonical model.
- Problem it solves: **P6** — duplicated entities.
- Files involved: `domain/entities/trading_entities.py`, `domain/entities/signal_entities.py`, `domain/entities/__init__.py` → canonical `domain/entities/{signal,order,position,market_data,account}.py`
- Feature mapping: all (model underpins every feature)
- Type: consolidation
- Risk level: medium
- Dependencies: none (coordinate import updates with E2/E3)
- Implementation constraints:
  - MUST preserve each entity's fields + validation invariants.
  - MUST update importers mechanically (no behavior change).
- Validation method: entity-invariant unit tests pass; suite green after import rewrite.

#### Task ID: E4.T2
- Goal: Delete the shadow model and dedupe enums to a single home.
- Problem it solves: **P6** — `shared/types.py` shadow model, triplicated enums.
- Files involved: delete `shared/types.py`; canonicalize `domain/enums/*` (`SignalType`, `OrderSide`, `PositionSide`)
- Feature mapping: all
- Type: deletion
- Risk level: medium
- Dependencies: E4.T1
- Implementation constraints:
  - MUST repoint every `shared.types` importer to `domain`.
- Validation method: `grep -rn "shared.types\|from shared import types"` returns 0; suite green.

#### Task ID: E4.T3
- Goal: Remove pandas from domain contracts.
- Problem it solves: domain-purity violation (Phase 1).
- Files involved: `domain/engines/engine_interface.py` (line 8), `domain/ports/optimization_ports.py` (line 5)
- Feature mapping: F8, F9, F15
- Type: refactor
- Risk level: medium
- Dependencies: E4.T1
- Implementation constraints:
  - MUST move pandas-typed signatures to infrastructure/application DTOs; domain speaks entities/VOs.
- Validation method: `grep -rn "import pandas" domain/` returns 0; mypy-strict passes on `domain/`.

#### Task ID: E4.T4
- Goal: Enforce value objects at adapter/use-case boundaries.
- Problem it solves: P6 — raw `str`/`float` leaking inward.
- Files involved: data/broker/execution adapters (boundary points), `application/dto/` (new)
- Feature mapping: all
- Type: refactor
- Risk level: medium
- Dependencies: E4.T1, E4.T2
- Implementation constraints:
  - MUST construct `Symbol`/`Money`/`Percentage` at edges; interiors typed.
- Validation method: mypy-strict on `domain/`+`application/`; boundary test rejects invalid raw inputs.

---

### Epic E5 — Interface Layer & God-Module Splits

#### Task ID: E5.T1
- Goal: Move the WFO matplotlib visualizer out of application into the entry layer.
- Problem it solves: **P9** — plotting in application.
- Files involved: `application/walk_forward/visualizer.py` → `interface/reporting/walkforward_report.py`
- Feature mapping: F8
- Type: migration
- Risk level: low
- Dependencies: E2.T4
- Implementation constraints:
  - MUST render the same report from a fixture WFO result.
- Validation method: report renders from fixture; no matplotlib import remains under `application/`.

#### Task ID: E5.T2
- Goal: Split `realistic_backtester.py` (2232 LOC) into execution-sim / fees-slippage / position-mgmt / result-tracking, pushing pure math to `domain/services`.
- Problem it solves: **P7** — largest god module.
- Files involved: `infrastructure/backtest/realistic_backtester.py` → focused modules under `infrastructure/backtest/` + `domain/services/`
- Feature mapping: F7
- Type: extraction
- Risk level: high
- Dependencies: E3.T1
- Implementation constraints:
  - MUST keep golden backtest output byte-identical after each extraction.
- Validation method: E0.T4 golden unchanged after every split commit.

#### Task ID: E5.T3
- Goal: Split `market_opportunity_watcher.py` (1778 LOC) into orchestration / discovery / detection / event-routing / init.
- Problem it solves: **P7** — watcher god module.
- Files involved: `infrastructure/watchers/market_opportunity_watcher.py` → focused watcher modules + `application/pipelines/`
- Feature mapping: F16
- Type: extraction
- Risk level: high
- Dependencies: E1.T4, E2.T1
- Implementation constraints:
  - MUST emit identical opportunities for a recorded market fixture.
- Validation method: watcher fixture replay yields identical opportunity set.

#### Task ID: E5.T4
- Goal: Split `auto_detection_orchestrator.py` (1289 LOC); move coordination into `application/pipelines/`, depend on ports not concrete infra.
- Problem it solves: **P7** — orchestrator god module + tight coupling.
- Files involved: `infrastructure/orchestrators/auto_detection_orchestrator.py` → `application/pipelines/detection_pipeline.py` + thinned infra
- Feature mapping: F27
- Type: extraction
- Risk level: high
- Dependencies: E5.T3, E2.T6
- Implementation constraints:
  - MUST produce identical execution intents for a fixture observation stream.
- Validation method: fixture observation stream yields identical intents.

#### Task ID: E5.T5
- Goal: Split remaining >700-LOC god modules (one file per PR).
- Problem it solves: **P7**.
- Files involved: `infrastructure/risk/advanced_sltp_manager.py`, `infrastructure/logging/forensic_logger.py`, `infrastructure/statistical_validation/decision_defensibility_validator.py`, `infrastructure/data/enhanced_data_provider.py`, `infrastructure/strategies/strategy_manager.py`, `infrastructure/brokers/multi_broker_service.py`, `infrastructure/services/broker_execution_service.py`, `infrastructure/fusion/fusion_service.py`, `infrastructure/market_regime/regime_detector.py`
- Feature mapping: F11, F17, F19, F21, F25, F29
- Type: extraction
- Risk level: medium
- Dependencies: relevant E3 consolidations
- Implementation constraints:
  - MUST split by extraction only; one file per commit; behavior preserved.
- Validation method: per-module unit tests + relevant golden test green after each split.

#### Task ID: E5.T6
- Goal: Thin all CLI shells to parse→bootstrap→use-case→render.
- Problem it solves: **P9** — business logic in entry points.
- Files involved: all `interface/cli/*.py` produced in E2
- Feature mapping: all runner-exposed (F1–F3, F6–F10, F13, F14, F27, F28)
- Type: refactor
- Risk level: low
- Dependencies: E2.T2–E2.T5
- Implementation constraints:
  - MUST contain no domain/infra logic in CLI modules.
- Validation method: import-contract review confirms each CLI imports only `bootstrap` + use cases.

#### Task ID: E5.T7  *(gap-closure: F15)*
- Goal: Split `engine_adapters.py` (722 LOC) into single-responsibility modules.
- Problem it solves: **Gap F15** — file above threshold, omitted from original E5.T5 list.
- Files involved: `infrastructure/engines/adapters/engine_adapters.py` (and the duplicate `infrastructure/engines/engine_adapters.py`)
- Feature mapping: F15
- Type: extraction
- Risk level: medium
- Dependencies: E3.T7
- Implementation constraints:
  - MUST preserve signal output (golden from E3.T7).
- Validation method: per-engine golden signal output unchanged after split.

#### Task ID: E5.T8  *(gap-closure: F10)*
- Goal: Split `adaptive_retuning.py` (523 LOC) into scheduling / performance-check / retuning concerns.
- Problem it solves: **Partial F10** — sub-700-LOC god service missed by threshold.
- Files involved: `application/services/adaptive_retuning.py`, `application/data_sync/watcher_retune.py`
- Feature mapping: F10
- Type: extraction
- Risk level: medium
- Dependencies: E2.T4
- Implementation constraints:
  - MUST reproduce retune trigger decisions on fixture performance history.
- Validation method: retune-decision unit test matches prior on fixture history.

#### Task ID: E5.T9  *(gap-closure: F18)*
- Goal: Relocate explainability/lineage modules out of `shared/` to the correct layer.
- Problem it solves: **Partial F18** — stateful, domain-aware modules left in `shared/`.
- Files involved: `shared/signal_correlation_analyzer.py`, `shared/signal_lineage_tracker.py` → `infrastructure/monitoring/` or `application/pipelines/`
- Feature mapping: F18
- Type: migration
- Risk level: low
- Dependencies: E3.T6
- Implementation constraints:
  - MUST preserve lineage/correlation output; MUST leave `shared/` dependency-free.
- Validation method: lineage output unchanged on fixture; `shared/` imports nothing from other layers.

#### Task ID: E5.T10  *(gap-closure: F30)*
- Goal: Move the live dashboard adapter into the entry/presentation layer.
- Problem it solves: **Partial F30** — dashboard not relocated.
- Files involved: `infrastructure/adapters/live_dashboard.py` → `interface/reporting/live_dashboard.py`
- Feature mapping: F30
- Type: migration
- Risk level: low
- Dependencies: E2.T5
- Implementation constraints:
  - MUST render from a fixture live-state snapshot; no application/infra dependency on the dashboard.
- Validation method: dashboard renders fixture state; `grep` shows no inward dependency on it.

---

### Epic E6 — Rule Enforcement & Test Pyramid

#### Task ID: E6.T1
- Goal: Encode dependency rules R1–R6 as import-linter contracts in CI.
- Problem it solves: P1/P10 — prevent architectural regression.
- Files involved: `pyproject.toml`, `.github/workflows/ci.yml`
- Feature mapping: enabler
- Type: test
- Risk level: low
- Dependencies: E2–E5 substantially complete
- Implementation constraints:
  - MUST encode: domain pure; application→domain only; infra→domain only; only interface imports bootstrap.
- Validation method: `lint-imports` passes; an injected bad import fails CI.

#### Task ID: E6.T2
- Goal: Local layering contract test mirroring CI.
- Problem it solves: fast local feedback.
- Files involved: `tests/contract/test_layering.py` (new)
- Feature mapping: enabler
- Type: test
- Risk level: low
- Dependencies: E6.T1
- Implementation constraints:
  - MUST fail on any layering violation.
- Validation method: passes clean tree; fails an injected violation.

#### Task ID: E6.T3
- Goal: Adapter↔port conformance tests for every canonical adapter.
- Problem it solves: P5 — guarantee adapters satisfy ports.
- Files involved: `domain/ports/**`, canonical adapters from E3; new `tests/contract/test_*_adapters.py`
- Feature mapping: F1–F30 (each adapter-backed feature)
- Type: test
- Risk level: low
- Dependencies: E3
- Implementation constraints:
  - MUST run the same suite against each implementation of a port.
- Validation method: every canonical adapter passes its port's shared test suite.

#### Task ID: E6.T4
- Goal: mypy-strict on domain + application in CI.
- Problem it solves: keep inner layers pure/typed.
- Files involved: `domain/**`, `application/**`, `pyproject.toml`
- Feature mapping: enabler
- Type: test
- Risk level: low
- Dependencies: E4
- Implementation constraints:
  - MUST be clean on `domain/` and `application/`.
- Validation method: `mypy` exits 0 for those packages in CI.

#### Task ID: E6.T5
- Goal: Backfill unit tests for previously-untested infra (engines, fusion, risk, sizing, watchers, execution, shared).
- Problem it solves: **P8** — ~60% infra unit-untested.
- Files involved: consolidated adapters from E3/E5; new `tests/unit/**`, `tests/integration/**`
- Feature mapping: F11, F12, F14–F26, F29
- Type: test
- Risk level: low
- Dependencies: E3, E5
- Implementation constraints:
  - MUST use port fakes for unit tests (no I/O).
- Validation method: coverage on `domain/`+`application/` ≥ agreed threshold; CI enforces.

---

### Epic E7 — Scale-Readiness (optional)

#### Task ID: E7.T1
- Goal: DB-backed persistence adapter behind the persistence port.
- Files involved: `infrastructure/persistence/` (file adapter from E3.T2) + new DB adapter
- Feature mapping: F1–F4 (storage)
- Type: migration
- Risk level: medium
- Dependencies: E3.T2, E6.T3
- Implementation constraints: MUST pass the same persistence contract test as the file adapter.
- Validation method: contract test green for both adapters; golden data path unchanged.

#### Task ID: E7.T2
- Goal: Distributed event bus (Redis/Kafka) behind `MessagingPort`.
- Files involved: `infrastructure/messaging/` (in-proc bus from E3.T6) + new adapter
- Feature mapping: F16, F17, F27
- Type: migration
- Risk level: medium
- Dependencies: E3.T6, E6.T3
- Implementation constraints: MUST pass the pub/sub contract test against the broker.
- Validation method: contract test green; e2e pipeline unaffected.

#### Task ID: E7.T3
- Goal: Optional FastAPI surface exposing use cases.
- Files involved: `application/use_cases/**`, `bootstrap/container.py` → new `interface/api/`
- Feature mapping: all use-case-exposed
- Type: migration
- Risk level: medium
- Dependencies: E2, E6
- Implementation constraints: MUST contain no business logic in routers (call use cases only).
- Validation method: API integration tests return expected DTOs.

#### Task ID: E7.T4
- Goal: Run watchers/engines as separate workers.
- Files involved: `application/pipelines/**`, messaging adapter → new worker entry points under `interface/`
- Feature mapping: F15, F16
- Type: migration
- Risk level: high
- Dependencies: E5.T3, E5.T4, E7.T2
- Implementation constraints: MUST yield identical intents in-proc vs distributed (fixture replay).
- Validation method: fixture replay identical across both modes.

---

### Epic E8 — Continuous Cleanup & Decommission

#### Task ID: E8.T1
- Goal: Delete superseded modules once `grep` proves zero importers.
- Files involved: files marked superseded by E1/E2/E3/E4 (e.g. losing backtesters/providers/sizers/loggers)
- Feature mapping: enabler
- Type: deletion
- Risk level: low
- Dependencies: the task superseding each file
- Implementation constraints: MUST confirm zero importers before each delete.
- Validation method: suite green after each deletion; `grep` confirms no references.

#### Task ID: E8.T2
- Goal: Fold `utils/` into the new structure; relocate `profitability_enhancer`; drop duplicate logger.
- Files involved: `utils/profitability_enhancer.py`, `utils/config_helper.py`, `utils/symbol_validator.py`, `utils/logger.py`, `utils/data_integrity_*.py` (latter handled by E3.T10)
- Feature mapping: F5, F6
- Type: migration
- Risk level: low
- Dependencies: E3.T6, E3.T10, E4
- Implementation constraints: MUST repoint importers; `utils/` removed when empty.
- Validation method: suite green; `utils/` no longer referenced.

#### Task ID: E8.T3
- Goal: Refresh docs/onboarding to the new structure.
- Files involved: `README.md`, `docs/**`, this graph
- Feature mapping: enabler
- Type: documentation
- Risk level: low
- Dependencies: E6
- Implementation constraints: MUST reflect final folder layout + how to run tests/backtest.
- Validation method: a new contributor runs tests + a backtest using only the README.

---

## 4. GAP CLOSURE SECTION

Every ❌ gap and 🟡 partial from Phase 3.5 is now assigned to at least one explicit task:

| Phase 3.5 item | Status before | Resolving task(s) | Status now |
|---|---|---|---|
| **F15 — Signal engines (consolidation/split)** | ❌ Gap | **E3.T7** (consolidate behind `EnginePort`) + **E5.T7** (split `engine_adapters.py` 722 LOC) | ✅ Resolved |
| **F26 — Execution algorithms (TWAP/VWAP/smart routing)** | ❌ Gap | **E3.T8** (behind `ExecutionAlgorithmPort`; removes app→infra import) | ✅ Resolved |
| **F5 — Data-integrity validation** | 🟡 Partial | **E3.T10** (first-class adapter behind `DataIntegrityPort`) + E8.T2 | ✅ Resolved |
| **F10 — Adaptive retuning** | 🟡 Partial | **E5.T8** (split scheduling/perf-check/retuning) + E2.T4 (migration) | ✅ Resolved |
| **F12 — Confidence calibration + randomness firewall** | 🟡 Partial | **E3.T9** (`confidence_calibrator.py`, `randomness_exposure_firewall.py`, `statistical_authority_engine.py` behind ports) | ✅ Resolved |
| **F18 — Explainability / signal lineage** | 🟡 Partial | **E5.T9** (relocate `signal_correlation_analyzer.py`, `signal_lineage_tracker.py`) | ✅ Resolved |
| **F30 — Live dashboard adapter** | 🟡 Partial | **E5.T10** (move `infrastructure/adapters/live_dashboard.py` → `interface/reporting/`) | ✅ Resolved |
| F11 — Statistical decision-defensibility | ✅ (kept) | E3.T9, E5.T5 | ✅ |

**Coverage assertion:** all 30 Phase 1 features (F1–F30) now map to ≥1 task. No gap remains unassigned. (Cross-check of the §3 feature-mapping fields covers F1–F30 with no omissions.)

---

## 5. EXECUTION ORDER (STRICT)

Execute strictly in this order. Do not start a stage until the prior stage's tasks are merged and green. Tasks on the same line are independent and may run in parallel.

**Stage 0 — Safety setup (must precede everything):**
`E0.T1 → E0.T2 → E0.T3`; `E0.T4` (after E0.T1).

**Stage 1 — Lowest-risk refactors (additive, no behavior change):**
`E1.T1 → E1.T2 → E1.T3`. In parallel: `E4.T1 → E4.T2` (model merge is additive + mechanical).

**Stage 2 — Core architecture breaking changes:**
`E2.T1` → then `E1.T4` (needs container for settings injection) → `E1.T5 → E1.T6`.
Then `E2.T2` (pilot) → `E2.T3`, `E2.T4` (parallel) → `E2.T5` → `E2.T6`.
Then `E4.T3 → E4.T4`.

**Stage 3 — Consolidation (one capability at a time, golden-gated):**
`E3.T1`, `E3.T2`, `E3.T3`, `E3.T4`, `E3.T5`, `E3.T6`, `E3.T7`, `E3.T8`, `E3.T9`, `E3.T10` — orderable by risk: do low/medium first (E3.T3, E3.T5, E3.T6, E3.T9, E3.T10), then high (E3.T1, E3.T2, E3.T4, E3.T7, E3.T8).
Then god-module splits depending on consolidations: `E5.T1`, `E5.T2`, `E5.T3 → E5.T4`, `E5.T5`, `E5.T6`, `E5.T7`, `E5.T8`, `E5.T9`, `E5.T10`.

**Stage 4 — Enforcement (lock in the structure):**
`E6.T1 → E6.T2`, `E6.T3`, `E6.T4`, `E6.T5`.

**Stage 5 — Deletion / cleanup:**
`E8.T1`, `E8.T2`, `E8.T3` (each after its superseding task).

**Stage 6 — Scale-readiness (optional, only when needed):**
`E7.T1`, `E7.T2`, `E7.T3`, `E7.T4`.

---

## 6. RISK MAP — Top 5 Highest-Risk Tasks

| Rank | Task | Why risky | Mitigation |
|------|------|-----------|------------|
| 1 | **E3.T1 — One backtest engine** | `realistic_backtester.py` is 2232 LOC and is the source of truth for all research results; consolidating 4–5 engines risks silent numeric drift in fees/slippage/impact. | Gate on E0.T4 golden (byte-identical); consolidate behind the port *before* splitting (E5.T2); one variant folded in per commit; keep losing engines until golden passes, delete in E8.T1. |
| 2 | **E2.T5 — Live + shadow runner migration** | Live trading path with threads + real broker connections; wrong shutdown leaks orders/threads or places real trades. | Sandbox/paper only in tests; assert zero live threads on teardown; close broker registry + pending-orders tracker; migrate shadow before live; never run against prod keys. |
| 3 | **E2.T6 — Retire global singletons** | `broker_registry`/`PendingOrdersTracker`/`strategy_manager` hold live state; hidden coupling means subtle behavior changes when scoping them. | Two-container isolation test; migrate one singleton per commit; keep a temporary module-level accessor delegating to the container until all callers move. |
| 4 | **E3.T4 — One risk module** | Correctness-critical: kill-switch/drawdown/exposure decisions protect capital; a regression can permit unsafe trades. | Characterization tests on fixed scenarios reproducing prior decisions exactly; separate SL/TP from portfolio risk in distinct commits; require risk-decision parity before deleting old modules. |
| 5 | **E3.T8 — Execution algorithms behind port** (tie: **E5.T3 watcher split**) | E3.T8: TWAP/VWAP slicing + smart-routing affect real fills and removes a live app→infra import. E5.T3: 1778-LOC watcher drives opportunity detection; extraction can change emitted signals. | E3.T8: pin slice schedules + routing decisions in unit tests; remove the app import in its own commit verified by `grep`. E5.T3: fixture replay must yield identical opportunity set after each extraction; de-Configs (E1.T4) first. |

**Cross-cutting mitigation:** every high-risk task is (a) preceded by a behavior-pinning test, (b) executed as additive-then-redirect-then-delete (strangler), and (c) reversible via VCS since deletion is always a separate, late task.

---

*Execution plan only — no code written. This graph is the authoritative input for Phase 4 implementation; each task is sized for a single coding iteration and tied to real file paths.*
