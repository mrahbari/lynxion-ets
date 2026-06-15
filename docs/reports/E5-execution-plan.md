# E5 — Execution Plan (SPLIT INTO E5-A / E5-B) — design only, NO code

Supersedes the prior over-scoped E5 plan. E4 remains CLOSED/FROZEN (no domain/DTO/ingestion
changes). This plan is split into **E5-A (safe structure splits only)** and **E5-B (deferred
risk-engine splits)**. The two phases are kept strictly separate — not merged.

============================================================
## E5-A — SAFE STRUCTURE SPLITS ONLY
============================================================
Allowed operations: file moves, pure (behavior-identical) extraction, CLI thinning with no
logic change, watcher/orchestrator decomposition **only as pure mechanical extraction**.

**Strict rules (enforced for every E5-A item):** no trading-logic change; no backtest-engine
change; no portfolio-logic change; no broker-logic touch; no DTO-interaction change.

### E5-A scope + verification
| Task | Target | LOC | Importers (update on move) | Op |
|---|---|---|---|---|
| T1 | `application/walk_forward/visualizer.py` → `interface/reporting/walkforward_report.py` | 528 | `application/walk_forward/main_wfo.py` (1) | move |
| T9 | `shared/signal_correlation_analyzer.py`, `shared/signal_lineage_tracker.py` → `infrastructure/monitoring/` | 304/294 | **none found** (pure-analysis; 0 trading keywords) | move |
| T10 | `infrastructure/adapters/live_dashboard.py` → `interface/reporting/live_dashboard.py` | 207 | `production_trading_orchestrator.py` (+1 char test) — **import path only** | move |
| T6 | `interface/cli/*.py` (14 files) | — | leaves → use-cases | thin (extract, no logic change) |
| T3 | `infrastructure/watchers/market_opportunity_watcher.py` | 1778 | `auto_detection_orchestrator.py` (sole) | pure extraction *(conditional)* |
| T4 | `infrastructure/orchestrators/auto_detection_orchestrator.py` | 1289 | `run_auto_detection` (use-case), `trading_system_production` (CLI) | decompose *(conditional, after T3)* |

> **Conditional gate for T3/T4:** allowed in E5-A **only** as behavior-identical mechanical
> extraction (cut method → new module → re-import; call sites unchanged). The moment a clean
> split would require altering detection/trading logic, **that piece drops to E5-B**. No
> exceptions.

### E5-A execution order (safe → risky, dependency-aware)
1. **T1** — move visualizer (1 importer). LOW.
2. **T9** — relocate the two explainability/lineage modules (0 importers, pure analysis). LOW.
3. **T10** — move live dashboard adapter (updates 1 live-orchestrator import line only). LOW.
4. **T6a** — thin the **independent** CLIs (those NOT calling the watcher/orchestrator). LOW–MED, per-file, mechanical.
5. **T3** — `market_opportunity_watcher` pure extraction (sole consumer = orchestrator). MED, conditional gate.
6. **T4** — `auto_detection_orchestrator` decomposition, **after T3**; coordination → `application/pipelines/`, depend on ports. MED, conditional gate.
7. **T6b** — thin the CLI(s) coupled to T4 (`trading_system_production.py`) **after T4**, so they target the stabilized structure (single pass, no rework).

### E5-A dependency graph (this phase only)
```
T1: visualizer            ◄── main_wfo                         (1 edge; isolated)
T9: correlation/lineage   ◄── (none)                           (isolated; possibly dead — verify no dynamic import)
T10: live_dashboard       ◄── production_trading_orchestrator  (import-path only) , (char test)
T6: interface/cli/* (14)  ──► use-cases                        (leaves)
        └─ trading_system_production.py ──► auto_detection_orchestrator   (couples T6b to T4)
T3: market_opportunity_watcher  ◄── auto_detection_orchestrator (sole consumer)
T4: auto_detection_orchestrator ──► market_opportunity_watcher  (so T3 BEFORE T4)
                                ◄── run_auto_detection (use-case), trading_system_production (CLI)
```
**Reading:** T1/T9/T10 are isolated moves (parallelizable, lowest risk). T3→T4 is the only
internal chain (orchestrator consumes watcher). T6 is leaf-level; the one CLI that imports the
orchestrator (`trading_system_production.py`) is sequenced after T4 (= T6b).

### E5-A validation gates (per item)
- `py_compile` + import-graph check (all moved-module importers repointed; no dangling import).
- **Behavior parity** for T3/T4: the extracted modules' public entry points unchanged; a
  diff-of-behavior check (same inputs → same outputs) before landing.
- Standing invariants stay green: `grep "import pandas" domain/`==0, `grep shared.types`==0.
- Per-file PRs; each move/extraction independently revertible.

============================================================
## E5-B — RISK-ENGINE SPLITS (DEFERRED — DO NOT EXECUTE YET)
============================================================
Explicitly **excluded** from E5-A. Each requires golden tests, a per-module rollback strategy,
and an explicit per-file approval gate before any work.

**Excluded modules / work:**
- **T2** `realistic_backtester.py` (2232) — highest fan-in (9 importers); golden-tested.
- `comprehensive_portfolio_backtester.py` (1359) — portfolio logic.
- **All broker adapters** — `binance_adapter`, `bingx_adapter` (820), `mexc_adapter`,
  `phemex_adapter`, `multi_broker_service` (865), `broker_execution_service` (805).
- **T8** `adaptive_retuning.py` (523) + `watcher_retune.py` — **core retune logic**.
- **SLTP / risk engines** — `advanced_sltp_manager.py` (1353), and other risk/trading modules.
- **Remaining T5 god modules** (not in E5-A): `forensic_logger` (967),
  `decision_defensibility_validator` (952), `enhanced_data_provider` (943),
  `strategy_manager` (884), `fusion_service` (809), `regime_detector` (801),
  `sync_market_data` (842), `validate_portfolio` (755), `enhanced_config_loader` (718),
  `probabilistic_position_sizer` (703), `strategy_provider` (703).
- **The deferred E4 broker VO-wiring** (and its prerequisite broker-module splits) —
  belongs to E5-B, gated by E4 contract items D1/D2.

**Obsolete (neither phase):** **E5.T7** — `engine_adapters.py` was deleted in the engine
cleanup. Mark N/A; do not recreate.

### Hard separation
- E5-A introduces **no** logic change and touches **none** of the E5-B modules.
- No DTO interaction is added in E5-A (the deferred broker VO-wiring that introduces DTO
  coupling is entirely within E5-B).
- E5-A and E5-B are not merged and not interleaved.

---
**Design/architecture only — no code, no moves, no commit.** E4 stays closed and frozen.
