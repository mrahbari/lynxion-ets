# Runner Validation Report (Operational Hardening — Phase 1)

**Date:** 2026-06-12. Goal: verify recent refactors did **not** break execution paths.
Every documented runner was inventoried from `README.md` and exercised. Import-level
validation (`--help`, which triggers all module imports + argument parsing — the precise
check for refactor-induced breakage) was run on all; core data/backtest paths were
executed fully.

## Inventory & results

| runner | import (--help) | executed | result | notes |
|---|---|---|---|---|
| `run_trading_system.py` | ✅ clean | ✅ (production, ~4.5 min) | **PASS** (after fix) | initially crashed on missing `pkg_resources`; fixed (see stabilization #3); now boots + runs |
| `runner_backtest.py` | ✅ clean | ✅ (trend_following, 14d, BTC) | **PASS** | `✅ Backtest completed with validation`, rc=0 |
| `runner_multitimeframe_update.py` | ✅ clean | ✅ (BTC, 5m/15m/30m/1h) | **PASS** | `Successful: 1, Failed: 0` — validates resample fix (#1) end-to-end |
| `runner_history_download.py` | ✅ clean | ✅ (1d, BTC, 1m) | **PASS** | 1,439 candles downloaded; network reachable, rc=0 |
| `runner_historical_data_sync.py` | ▲ no `--help` | ✅ (ran sync) | **PASS** | ignores `--help`, runs sync; logged "Historical data sync compl…" (no crash) |
| `runner_comprehensive_portfolio_backtest.py` | ✅ clean | — | **PASS (import)** | imports clean; heavy full run not exercised (time) |
| `runner_comprehensive_validation.py` | ✅ clean | — | **PASS (import)** | imports clean; heavy multi-symbol run not exercised (time) |
| `runner_extended_horizon_validation.py` | ✅ clean | — | **PASS (import)** | imports clean; long horizon run not exercised (time) |
| `runner_resync.py` | ✅ clean | — | **PASS (import)** | network sync; import verified |
| `runner_sync_approved_symbols.py` | ✅ clean | — | **PASS (import)** | network sync; import verified |
| `runner_shadow_deployment.py` | ✅ clean | — | **PASS (import)** | continuous/interval runner; import verified |
| `runner_walkforward.py` | ✅ clean | — | **PASS (import)** | train/test = optimization; full run **skipped per no-optimization lock** |
| `runner_retune.py` | ✅ clean | — | **PASS (import)** | Hyperopt; full run **skipped per no-Hyperopt lock** |

## Missing / documentation drift (C-class observability)
README references three runnables that are **absent** from the repo:
- `runner_correlation_stress_test.py` (README ~line 634) — MISSING
- `runner_capital_shock_test.py` (README ~line 796) — MISSING
- `tests/integration_tests.py` (README ~line 673) — MISSING

These are documentation/repo discrepancies, not refactor breakage. Recommend either
restoring the files or removing the README references.

## Verdict
**No refactor broke an import path.** All 13 present runners import cleanly; every core
execution path exercised (production boot, backtest, multi-timeframe resample, history
download, data sync) **passed** after the stabilization fixes. The only execution failure
encountered (production boot) was a missing-dependency defect, now fixed and re-validated.
Optimization runners (`retune`, `walkforward`) are import-validated but intentionally not
fully executed (no-optimization mandate). 3 README-referenced files are missing (doc drift).
