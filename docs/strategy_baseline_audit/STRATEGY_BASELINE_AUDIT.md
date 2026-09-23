# Lynxion strategy baseline audit

## Decision

**Path integrity blocks performance interpretation.** Source inspection identifies ten default strategy *registration names* representing nine classes, plus two source-only adapters. The current backtest strategy provider is not shown to be the same decision path as live with only data source and broker swapped. It first calls each adapter's raw `generate_signal()`, creates a strategy-derived mock fused signal, then calls `evaluate_fused_signal()`. The inspected live/event path feeds watcher/engine output to Fusion and then invokes `evaluate_fused_signal()` through StrategyManager; no equivalent per-adapter raw call was found there. The existing backtest runner also `bfill()`s shifted indicator warmup gaps, which can leak later values backward. No new baseline PnL or edge claim is valid from this audit.

## Required answers

1–3. **Existence/registration/invocation:** Ten default names are in `StrategyManager._register_default_strategies`; nine distinct classes because `crypto_breakout` aliases `breakout`. The map constructs instances when the manager is constructed, with `get_strategy_enabled` hardcoded true. `short_term_reversal` and `donchian_breakout` are implemented but not default-registered. Runtime construction/invocation in an independent live process is UNKNOWN; recent local registration logs are contaminated by F01 tests.
4–8. **Raw signal → Fusion → intent → Risk → simulated execution:** Adapters implement raw `generate_signal()`, but no complete contemporaneous production funnel was available. Live Fusion receives engine signals, not demonstrably each adapter's raw signal. The manager can select one adapter intent after fused evaluation. Source can reach risk/order layers; counts of actual raw signals, Fusion contributions, intents, risk accepts, guard accepts, simulated orders and fills are UNKNOWN, not zero.
9–10. **Effective parameters and precedence:** `EFFECTIVE_CONFIG_AUDIT.csv` separates declared fallback, profile, read-only fresh-loader value and truly running-process value. The latter is UNKNOWN. Known per-strategy design timeframes shadow the global profile timeframe; the strategy enable getter ignores name/env; helper parameter dicts can overwrite top-level settings. Fresh-loaded values do not prove what a running process holds.
11–12. **Parameter provenance:** No current default was tied by this audit to a preregistered empirical validation. Setup ATR/R:R and Fusion/watchers' thresholds are design heuristics or unverified; several helper parameters have UNKNOWN binding/provenance. UNKNOWN provenance alone does not make a parameter bad.
13–14. **Filtering/HOLD:** Candidate loss can occur in Watcher, Engine, Fusion, adapter setup/discipline, manager ranking, cooldown/duplicate prevention, risk or execution guard. No stage-matched ledger quantifies shares; intentional versus accidental selectivity is UNKNOWN.
15–16. **Dead/redundant:** Two adapters are absent from default registration, but not proven globally dead. `breakout`/`crypto_breakout` are exact class aliases. Other pairs share setup types but behavioral redundancy is INSUFFICIENT_DATA.
17–18. **Side and SL/TP:** Code has BUY/SELL setup/intent branches; actual symmetry is UNKNOWN. SL/TP may originate in SetupEngine or base adapter and are sanitized at order construction. No measured trace proves one consistent geometry for every strategy/timeframe.
19–20. **Backtest integrity and untouched performance:** Blocked. No backtest launched, no existing PnL treated as canonical, and all required metrics remain UNKNOWN in `BASELINE_METRICS.csv`.
21–22. **MAE/MFE and dominant bottleneck:** MAE/MFE cannot be attributed. The **confirmed correctness bottleneck** is path integrity; the economic bottleneck (strategy economics vs execution/gating/data) is INSUFFICIENT_EVIDENCE.
23–24. **Parameter sensitivity:** None eligible now; no ranges evaluated or proposed until path, sample and active parameter binding are established.
25. **Do not change yet:** strategies, confidence/Fusion weights, risk/sizing, SL/TP, timeframes, production config, or deployment. No Hyperopt or WFO selection; no sibling behavior transfer.

The compact inventory, effective-config, funnel, metric, diagnostic and later-review artifacts contain the trace and explicit missingness. Correctness observations are not edge evidence. Report → stop → review.

STRATEGY_BASELINE_AUDIT_BLOCKED_PATH_INTEGRITY
