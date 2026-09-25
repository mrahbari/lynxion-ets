# Canonical strategy-input provenance gap

Source audit at `a45bf47`; no strategy logic changed and no performance test run.

The closed-bar subset can now feed actual completed bars to existing strategy buffers for **one** symbol and each adapter's exact configured timeframe. This does not prove that every input used to turn a setup into an `ExecutionIntent` existed at decision time.

| Source | Observed dependency | Causal consequence | Status |
|---|---|---|---|
| `BaseStrategyAdapter.ensure_data_buffer` | Default Live resolves a download-capable global historical provider; Replay now binds a fail-closed explicit source | Replay cannot infer unarchived bars; one-symbol completed-bar feed is available, not full archive coverage | PARTIAL |
| `BaseStrategyAdapter.data_buffer` | One list per adapter, not symbol-keyed | Multi-symbol canonical strategy decisions could consume another symbol's history; do not declare multi-symbol research isolation | BLOCKER for multi-symbol |
| `SetupEngine.scan_for_setups` | Uses `datetime.now()` to create setup `ExchangeTimestamp` after five bars | Setup time is not demonstrably event-time causal in a historical run; may affect downstream freshness/decision checks | BLOCKER until reached-path test and clock seam |
| `DecisionPipeline.process_execution_intent` | Missing `obi_ratio`/`cvd` become direction-favoring constants; missing `best_bid`/`best_ask` become ±0.01% of current price | Candle-only data can result in confirmation and optimized price using values not observed by the producer | BLOCKER for after-cost/entry claims using such intents |
| Enabled default setup adapters | Trend, mean reversion, breakout, liquidity, VWAP, MTF, OI, sweep and volatility paths call the shared pipeline | The fallback is not an isolated unused helper; actual strategy eligibility may reach it once setup criteria pass | REACHABLE_BY_SOURCE; fixture has not emitted an intent |

No claim is made that every historical decision took a fallback: the two-bar fixture emitted no intent. No claim is made that complete point-in-time OBI/CVD/quote archives do not exist anywhere; coverage and alignment are unverified. Existing book/taker-flow research files are not automatically a complete, contemporaneous strategy-input feed. We will not fabricate missing values or reinterpret Phase-3A/other frozen research.

The smallest safe next proof is a frozen, non-profit-selected fixture with all required completed timeframe bars and explicitly timestamped microstructure inputs (if available), then a reached-path clock/input trace through actual StrategyManager selection and an intent-level prefix test. If those inputs are unavailable, a narrower pre-intent Engine/Fusion signal question could be defined and preregistered separately; it is **not** evidence for the full strategy/after-cost execution path. Changing or disabling the existing defaults in Live is an economic behavior decision and is not authorized here.
