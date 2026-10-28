# Strategy-path diagnostics

## Canonical path observed in source

`ArchitectureOrchestrator` subscribes event handlers and starts `SignalAggregator`. `SignalProcessor` handles market observation → `EngineService.process_observation` → `FusionService.fuse_signals([signal])`. A fused event is handed to the aggregator; `StrategyManager.evaluate_fused_signal` loops all registered adapters, each evaluates the same fused signal, then ranks emitted intents and returns only the top intent. The event processor constructs an order; risk/guard and broker behavior are downstream. Separate auto-detection execution code constructs an order as an alternate path. Registration, invocation, intent, guard acceptance, and fill are different states; source reachability does not prove a run occurred.

The default manager map has ten names, but only nine distinct classes: `crypto_breakout` aliases `BreakoutStrategyAdapter`. `short_term_reversal` and `donchian_breakout` exist in source/design-timeframe map but not that default registration map. The `enable_strategy` dynamic map is not evidence of current enablement; its additional names are not default registrations. `StrategyConfig.get_strategy_enabled` returns True regardless of the strategy name, so a per-strategy enabled/disabled claim based solely on environment variable names would be wrong.

## Blocking backtest/live differences

1. `BacktestStrategyProvider.load_sample_strategy` (adapter branch) feeds each bar to an adapter and calls its `generate_signal()` before forming a mock `FusedSignal` and calling `evaluate_fused_signal()`. The inspected live event/aggregator route calls `evaluate_fused_signal()` on a watcher/engine-fused signal; it does not call each adapter's `generate_signal()` there. The signal populations, Fusion inputs, confidence provenance and HOLD counts are therefore not demonstrably equivalent.
2. `application/use_cases/run_backtest.py:436` uses `ffill().bfill()` after shifted indicator construction. Backfilling early warmup gaps can carry later computed indicators backward into earlier bars. This is a lookahead-integrity blocker for that runner. It was documented, not changed.
3. The provider constructs mock fused direction/regime from its strategy signal, including a strategy-name regime fallback. Live Fusion derives these from watcher/engine observations. That changes downstream eligibility and attribution.
4. The backtest adapter and backtester simulate orders/fills through their own path; the live event path includes aggregator ranking, market-data heartbeat, risk enforcement/guard and broker-specific handling. Equivalence apart from DataSource/Broker substitution is not established.

Consequently **no new performance baseline was run or interpreted**. Historical trade journal or prior backtest outputs are not substitutes for this canonical-path audit. This is `BASELINE_BLOCKED_PATH_INTEGRITY`, not a verdict that any strategy loses or wins.

## Funnel, selectivity, and overlap

The code contains a best-effort `SignalCensusJournal` for adapter intent accept/reject events, but its default file `data/signal_census.jsonl` was absent during this audit. It does not by itself count observations, adapter raw signals, Fusion inputs, guard decisions and fills on a common cohort. The latest `logs/system.log` registration and sizing messages coincide with F01 test execution and are not independent evidence of a running production strategy. No complete stage-matched funnel was found. The CSV marks measured counts UNKNOWN, not zero.

Selectivity can arise in Watcher/Engine, Fusion, per-adapter setup and discipline checks, strategy ranking, cooldown/duplicate protection, risk and execution guards. Without stage-matched counters, intentional selectivity cannot be separated from accidental suppression. The manager chooses one intent from multiple adapters; it does not combine their raw `generate_signal()` outputs in live Fusion. Thus “Fusion contribution per strategy” is not currently evidenced.

Source-level overlap: `breakout` and `crypto_breakout` are the same class (REDUNDANT implementation, potentially independent instance state); `trend_following`/`mtf_trend` both filter NGTREND_FOLLOW; `mean_reversion`/`vwap_reversal` both filter NGMR_REVERSION; `liquidity`/`sweep_scalper` both filter NGLS_SWEEP. The latter pairs remain INSUFFICIENT_DATA for behavioral redundancy because timeframe/config/regime gates differ and no aligned decisions were measured.

## Entry, side, and exits

`SetupEngine` has BUY/SELL branches for sweep, reversal, trend and breakout families. Adapters map BUY to LONG intent and SELL to SHORT. This supports code-level directional paths, not equivalent long/short results or exposure. Setup SL has structural/ATR/default-distance elements and TP can be extended to meet minimum R:R. The strategy/base adapter may instead construct risk parameters and `SignalProcessor` sanitizes prices before order construction. No single entry/exit geometry across all adapters is established without an actual intent trace. F01 separately showed dynamic sizing when explicitly selected; its fixed-mode wiring and 0.001 floor caveats can affect any later baseline, but were not re-tested here.

MAE/MFE, giveback, stop-vs-target exit rates, execution costs and profit attribution are UNKNOWN under this audit's path-integrity gate. Do not diagnose entry versus exit economics from unavailable comparable trades.
