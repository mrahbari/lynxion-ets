# Stabilization Fixes (Operational Hardening — Phase 1)

**Date:** 2026-06-12. Type-A (implementation/runtime/data-flow) and B-class operational
defects fixed during operational stabilization. **No** strategy hypotheses, trading
logic, thresholds, parameters, or risk model were changed. Each fix is minimal and
correctness-restoring.

| # | issue | class | root cause | fix | files | expected impact |
|---|---|---|---|---|---|---|
| 1 | `resample_engine` raises `ValueError: Invalid frequency` on every higher-TF resample | A (runtime/deprecated) | pandas ≥2.2 removed legacy offset aliases `5T/15T/30T/1H`; code still used them | `tf_map` → `5min/15min/30min/1h` | `infrastructure/data/resample_engine.py` | multi-timeframe resampling works again (verified via `runner_multitimeframe_update`: Successful 1 / Failed 0) |
| 2 | `_detect_missing_candles` silently dead (always excepts → returns `[]`) | A (runtime/deprecated) | default `expected_frequency='1H'` rejected by pandas ≥2.2 | `'1H'` → `'1h'` | `infrastructure/backtest/realistic_backtester.py` | data-gap detection executes instead of being swallowed; removes recurring `Could not detect missing candles: Invalid frequency: 1H` warning |
| 3 | **Production boot crash** at startup | B (missing dependency / runtime) | `_build_production_data_and_services` imports `AdvancedOptimizationService` → `from hyperopt …` → hyperopt `atpe` imports `pkg_resources`; `setuptools` absent in the py3.12 venv → `ModuleNotFoundError: No module named 'pkg_resources'` | restored `setuptools` in the **local** `.venv` (provides `pkg_resources`); no global install, no code change | `.venv` (env only) | production boots and runs end-to-end (brokers init, orchestrator starts, signal flow established) |
| 4 | `MarketOpportunityWatcher`/symbol discovery: `Error fetching from CMC API: 'list' object has no attribute 'split'` | A (data-flow / type) | `cmc_excluded_coins` may be configured as a **list**, but code unconditionally called `.split(',')` (assumed string) | accept list-or-string before iterating | `infrastructure/services/symbol_discovery_service.py` | CMC symbol-discovery source no longer errors out; removes the 2× per-cycle warning |
| 5 | 47× `Could not update existing file for <SYMBOL>, overwriting: No columns to parse from file` | B (data-flow / observability) | an existing but **empty/0-byte** CSV makes `pd.read_csv` raise `EmptyDataError`; caught, warned, overwritten | guard `file_path.exists() and file_path.stat().st_size > 0` → empty files treated as new (written directly) | `infrastructure/data/csv_history_loader.py` | eliminates the repeated warning + redundant read attempt on empty files; cleaner data-update path |

## Notes
- Fixes #1, #2, #4, #5 are code; #3 is a venv dependency restoration (local, not global).
- Strategy-fidelity Type-A defects from earlier phases (liquidity missing-`type` directional
  bug; vwap_reversal slope/session data-flow bugs; scalping volume-units) were already
  applied and committed in prior work — they are **not** re-listed here as they predate
  this stabilization phase.
- The hyperopt/`pkg_resources` coupling at production boot is environmentally resolved
  (#3). A deeper decoupling (lazy hyperopt import so production never imports the
  optimization subsystem) is noted as an architectural improvement but was **not** done
  here — it is a multi-file refactor of the optimization subsystem and "no architectural
  redesign" applies; the minimal dependency-restoration fix is sufficient for stability.

## Out-of-scope deprecated-alias usages (NOT changed — not on the production path)
`freq='H'` remains in `infrastructure/optimization/{auto_retune_hyperopt,run_hyperopt*}.py`
(Hyperopt modules — forbidden territory, not run) and in synthetic-data fallbacks of
`comprehensive_portfolio_backtester.py` / `live_dashboard.py`. These would raise on
pandas ≥2.2 **if executed**, but are not exercised by the production runtime path; flagged
for a future minimal sweep, not changed under the minimal-change rule.
