# Pre-intent signal study — frozen design, **not activated**

Frozen before inspecting forward outcomes at repository `3c16b9e`. This is a Level-1 *predictive-signal* question, not a strategy/ExecutionIntent, fill, portfolio, or profitability study. Activation requires the readiness gates in `PRE_INTENT_SIGNAL_READINESS_AND_MICROSTRUCTURE_AUDIT.md`; no outcome calculation is authorized by this document alone.

## Question and object

Does the direction emitted by the existing `HistoricalCandleWatcherAdapter` → `SignalProcessor` → `EngineService` → `FusionService` routed `FusedSignal` predict later completed-candle close-to-close direction more often/strongly than zero, within a strictly candle-only subset? The output is the actual `FusedSignal.dominant_bias`, confidence, symbol and event timestamp, not a strategy entry or mock fused signal. Exclude non-BUY/SELL output from the directional primary estimand; retain HOLD/neutral counts and all exclusions in the audit trail. Do not threshold or optimize confidence; report it descriptively. The pipeline currently fuses one interpreted signal per observation; do not present this as the full live multi-watcher information set.

## Frozen cohort and timing

- Candidate symbols: BTCUSDT and ETHUSDT, 1h completed candles only, UTC. Candidate archived period: common intersection of `data/history/processed/1h/BTC-USDT.csv` and `ETH-USDT.csv`, capped at 2026-07-19 00:00 UTC. **Do not activate** until timestamp unit/meaning, source, continuity and provenance are independently verified; current files merely show a `timestamp` column, with no proven open/close-time contract. No data outside the verified common intersection may be used.
- Historical source enforces valid OHLCV, strictly increasing unique timestamps and contiguous one-hour periods. Any gap, duplicate, nonfinite or invalid bar fails the cohort, never bfill/zero-fill. A bar's OHLC becomes available only after its verified close time. No HTF data are used. Same-time symbols sort by symbol for reproducibility; per-symbol state remains independent.
- Warmup: first 50 completed bars per symbol are discarded from eligible signal observations; all earlier bars may initialize the same watcher state. Do not infer that 50 is optimal. No lookahead normalization or future-derived regime threshold.
- Directional signal at close T is evaluated only against later closes. One observation per symbol per completed bar; duplicate logical events fail closed. Every eligible event is recorded, but for inferential independence retain at most one event per symbol per 4-hour block, selecting the first chronologically; report the full event count too. Do not cherry-pick overlapping signals.

## Outcomes and costs

Primary single horizon: 4 completed 1h bars. Primary outcome: side-adjusted simple close-to-close return, BUY = `(close[T+4]-close[T])/close[T]`, SELL = its negative. One secondary descriptive horizon: 1 completed bar. Events without all future closes are censored, not zero-return. MFE/MAE and TP-before-SL/R are **not** in the primary family: no causal TP/SL geometry exists at this pre-intent boundary. Closing-price returns are predictive labels, not executable fills.

Report gross predictive evidence only. Exact historical spread/fees/slippage/funding are not known at this boundary, so **after-cost edge remains unresolved**. No candle-range spread proxy. If future cost scenarios are proposed, freeze them as a separately versioned protocol before calculating them.

## Inference, multiplicity, decision rule

The one primary null is mean 4h direction-adjusted return <= 0. Report sample count, mean, median, dispersion and a 95% block-bootstrap interval with day-length UTC blocks, fixed seed 20260925 and 10,000 resamples. BTC and ETH form one pooled primary family with per-symbol descriptive splits, not two independent discovery claims. The 1h horizon and confidence stratification are descriptive only. Require at least 100 non-overlapping eligible primary events **and** 20 distinct UTC days per symbol; otherwise `INCONCLUSIVE_UNDERPOWERED`, without replacing symbols/horizons after viewing labels. A positive gross predictive finding requires the lower one-sided-equivalent 95% interval bound > 0 under this frozen procedure; otherwise fail/inconclusive as appropriate. No after-cost/profitability acceptance criterion is defined because executable prices and costs are absent. Robustness: report both symbols, each calendar week, and leave-one-week-out estimates without changing the primary decision. No parameter search, WFO or Hyperopt.

## Hard pre-outcome release gates

Verify archived timestamps are truly causal close-time or open-time plus exactly one hour, source provenance and common continuous coverage; freeze file/config hashes. Show actual normalized `FusedSignal` trace and event-time-only state. Run **historical-data** prefix T versus T+future through the chosen watcher/Engine/Fusion route (warmup, UTC boundary, two symbols) and repeated-run determinism. Confirm no synthetic microstructure reaches this boundary and no production persistence/network capability is exercised. If any gate fails, do not compute outcomes and keep status `PRE_INTENT_EDGE_MEASUREMENT_NOT_READY`.
