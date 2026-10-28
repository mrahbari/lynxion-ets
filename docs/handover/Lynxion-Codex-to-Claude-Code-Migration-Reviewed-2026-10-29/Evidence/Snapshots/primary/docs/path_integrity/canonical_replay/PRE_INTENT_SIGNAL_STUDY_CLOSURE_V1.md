# Frozen pre-intent signal study — immutable closure

**Final status: `PRE_INTENT_STUDY_NOT_IDENTIFIABLE_UNDER_CURRENT_SEMANTICS`.** This is a measurement-identifiability result, not `NO_EDGE`, `EDGE_REJECTED`, negative expectancy, or strategy failure. This generation is closed; do not modify its definition or calculate its forward outcomes.

## Frozen identities

- Original preregistration: `PRE_INTENT_SIGNAL_STUDY_PREREGISTRATION.md`, SHA-256 `454485ff11fad12a9ad355517d3c1461b1df1676e182937c6c2d7e02d10a8cac`.
- Data-only addendum, frozen before acquisition: `DATA_ONLY_PREREGISTRATION_ADDENDUM_V1.md`, SHA-256 `b17e50a75591b26d08f435d460e9a9a8ca928ef0aab633b73de2ba495416bae5`, commit `5dd7906`.
- Qualified public BTCUSDT/ETHUSDT Binance USD-M Futures 1h capture: `data/research/pre_intent/candle_capture_v1/capture_manifest.json`, SHA-256 `4832beedbbddb4ea55da8882994cb7497f77298003f09e9642046331e8533ffb`; qualification manifest SHA-256 `2c119868cf0c839ebb934557b1faac8b2771eae722f6cce2c8a8239e2f868775`. Raw BTC SHA-256 `eb0868edc9ff94ce64d898c3a874d18c7979e3ae3d0a683e291b74210ff8c348`; raw ETH SHA-256 `98d4f0c83d29974cb2d220616528d6bd8b998a016867bd37c85a14bd0e7f7190`.

## Pre-outcome evidence and reason for closure

The accepted dataset has causal exchange open/close timestamps, common 50-candle warmup and 670-candle evaluation windows per symbol, and no detected gaps, duplicates or malformed OHLCV. Following the narrow mechanical Replay watcher-identity correction in `fbb5a34`, repeated normalized closed-candle → Watcher → Engine → Fusion runs were identical. Real-archive prefix invariance passed at UTC cut points 2026-06-08, 06-18 and 06-28 within this pre-intent boundary. No Strategy/ExecutionIntent or full Live watcher parity is claimed.

The frozen evaluation produced **1,340 total Fusion outputs: BUY 0, SELL 0, NEUTRAL 1,340**. The preregistered directional estimand requires at least 100 non-overlapping eligible primary events and 20 distinct UTC days per symbol. It has zero directional events. `HistoricalCandleWatcherAdapter` emits `candle_reversal_*` analytical observations; the active Engine has no specified directional mapping for these types and returns NEUTRAL. Correct watcher identity selects hierarchical Fusion, while the current routed processor gives it one signal per event and its existing direction resolver requires at least two aligned observations. The repository does not establish one unique intended BUY/SELL reinterpretation. See `PRE_INTENT_ZERO_DIRECTION_SEMANTIC_LINEAGE.md`.

**No future returns, MFE/MAE, TP/SL outcomes, PnL, expectancy, win rate, Profit Factor, cost-adjusted results, bootstrap statistics or economic labels were inspected or calculated for this study.** The zero count was measured solely from causal decision outputs. No thresholds, dates, symbols, watcher/Engine/Fusion semantics or sample minima were changed to manufacture events. The next directional study must be a separately preregistered generation selected outcome-blind.
