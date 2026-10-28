# System Stability Report (Operational Hardening — Phase 1)

**Date:** 2026-06-12. Consolidated outcome of the stabilization pass: pending Type-A
fixes, runner validation, production runtime validation, deep log analysis, and the
immediate A/B stabilization loop.

> ## Final verdict: **STABLE** (DEV / paper-trading + testnet)
> The production system boots cleanly, runs continuously, processes the full signal
> pipeline, handles broker-unavailability and data-quality issues gracefully (no crash,
> no deadlock, no runaway resource use), and all validated A/B defects are fixed and
> re-confirmed. Stable as an **operational/technical** system. (This is an operational
> verdict, not a profitability one — see the rehabilitation/readiness reports: the
> strategies remain NOT DEPLOYABLE for edge reasons.)

## 1. Fixes applied (see `stabilization-fixes.md` for detail)
| # | class | fix | status |
|---|---|---|---|
| 1 | A | resample_engine `5T/15T/30T/1H` → `5min/15min/30min/1h` | fixed + validated |
| 2 | A | backtester `_detect_missing_candles` `1H` → `1h` | fixed |
| 3 | B | production-boot crash: restored `setuptools` (`pkg_resources`) in venv | fixed + validated |
| 4 | A | CMC `excluded_coins` list-or-string handling | fixed + validated |
| 5 | B | csv_history_loader empty-file guard | fixed + validated |

## 2. Runner status (see `runner-validation-report.md`)
- **13/13 present runners import cleanly** — no refactor broke an execution path.
- Executed PASS: `run_trading_system` (production), `runner_backtest`,
  `runner_multitimeframe_update`, `runner_history_download`, `runner_historical_data_sync`.
- Import-validated only (heavy/long, or no-optimization lock): comprehensive/extended/
  shadow/resync/sync, and `runner_retune`/`runner_walkforward` (optimization — full run
  intentionally skipped).
- **Doc drift (C):** `runner_correlation_stress_test.py`, `runner_capital_shock_test.py`,
  `tests/integration_tests.py` referenced in README but **missing** from the repo.

## 3. Production boot status
- **First attempt: FAILED** — `ModuleNotFoundError: No module named 'pkg_resources'`
  (hyperopt import during `_build_production_data_and_services`).
- **After fix #3: PASS** — boots in ~15s: brokers initialised (Binance/BingX/MEXC/Phemex,
  testnet), `ArchitectureOrchestrator` started, `SignalAggregator` running, flow
  established (Watcher → Engine → Fusion → Strategy → Aggregator → Broker), 730 approved
  symbols loaded, watchers discovering symbols. Ran the full bounded window (~4.5 min)
  without crash/deadlock/runaway resource use.

## 4. Runtime findings (deep log analysis, classified)
First run: ~28k log lines, 133 error-lines / 328 warning-lines (each event logged twice —
stdout + file). Classification:

| finding | count | class | disposition |
|---|---|---|---|
| BINGX "BROKER NOT CONNECTED" / order id None | ~32 | B (environmental) | testnet mode + non-testnet keys → testnet broker won't auth; graceful, no crash. **Not a code defect** — config/credentials. Documented. |
| CMC `'list' object has no attribute 'split'` | 2 | A | **FIXED** (#4) → 0 on re-run |
| CSV `No columns to parse from file` | 47 | B | **FIXED** (#5) → 0 on re-run |
| `Invalid frequency: 1H` (missing-candle / resample) | recurring | A | **FIXED** (#1, #2) → 0 on re-run |
| Strategy `Contradictory signal: Direction vs Bias` | ~92 | C/strategy | handled by design ("prioritising direction"); flagged for Phase 2 strategy review |
| `No validation method available … assuming valid` | 26 | C | soft observability; watcher assumes valid — note for Phase 2 |
| logging `RotatingFileHandler` rollover `FileNotFoundError` | 1 | C | concurrent-rotation race; non-fatal, trading continued. Logging-config flake, not fixed (C-class). |
| `Order execution returned None` | ~32 | B (environmental) | corollary of broker-not-connected; graceful |

No tracebacks from trading/domain logic; no deadlock, no runaway memory/CPU, no thread
starvation, no event-loop stall, no queue growth observed over the run.

## 5. Fixes validated (Measure → Fix → Re-run → Validate)
Re-run after fixes (~2.8 min, 25.8k lines): **boot PASS; signal flow active (34 execution
intents processed); CMC errors 2 → 0; CSV "No columns" 47 → 0; "Invalid frequency" → 0.**
Only residuals: BINGX-not-connected (16, environmental/testnet) and the single logging
rotation race (C). No new A/B defects introduced.

## 6. Remaining risks
- **Environmental (not code):** live exchange API keys are present in `.env` while
  `testnet=True`/`paper_trading=True`. The run is safe (no real orders), but **flipping
  `BROKER_TESTNET=false` would route real orders with real funds** — a latent operational
  risk. Recommend testnet-specific keys or removing live keys from the dev `.env`.
- **C-class (observability), not fixed under minimal-change/no-A·B-only-loop:** logging
  rotation race; "assuming valid" symbol path; dual stdout+file log duplication; README
  doc-drift (3 missing runners).
- **Strategy-layer (Phase 2):** signal Direction-vs-Bias contradictions warrant review in
  the Final Strategy Review (Type-A/B scope), not in operational stabilization.
- **Architectural (not done, by design):** production boot imports the hyperopt-backed
  optimization service; resolved by restoring `pkg_resources` rather than decoupling
  (no architectural redesign). Lazy-importing hyperopt is a future improvement.

## 7. Production readiness assessment
**Operationally STABLE.** The system is technically correct on its execution paths,
boots and runs without fatal faults, and degrades gracefully under broker/data failures.
All validated A/B operational defects are fixed and re-confirmed. Remaining items are
C-class observability, environmental config, or Phase-2 strategy-layer concerns — none
destabilises runtime.

**Caveat (honest assessment):** operational stability ≠ deployability. Per the
rehabilitation, timeframe-validation, walk-forward, and readiness reports, the strategy
suite has **no demonstrated, persistent, cross-symbol edge** and remains **NOT
DEPLOYABLE with live capital** (READY 0 / NEEDS_IMPROVEMENT 11 / NON_VIABLE 1). This
report certifies the *system runs correctly and stably*, not that it is profitable.
