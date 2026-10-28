# Directional Engine signal study V1 — frozen before outcomes

This is a **new research generation**, not an amendment or rescue of the closed candle-reversal/Fusion study. Freeze this entire artifact and its SHA-256 in a commit **before** computing any future returns or economic outcome. The prior generation remains `PRE_INTENT_STUDY_NOT_IDENTIFIABLE_UNDER_CURRENT_SEMANTICS` and its outcomes will never be opened.

## Question, information set and estimand

Does the BUY/SELL direction from existing `TrendMTFWatcher` → `EngineService.process_observation` show positive side-adjusted 4-completed-hour **close-to-close predictive return** on the frozen BTCUSDT/ETHUSDT 1h archive? The estimand is a Level-1 Engine-interpreted directional proposal, **not** FusedSignal, Strategy, ExecutionIntent, broker fill, portfolio performance or an executable Edge. `TrendMTFWatcher` uses 5/15/30 rolling windows of one 1h close series; no true MTF feed is involved despite its name. Watcher/Engine formulas, defaults, thresholds and confidence are unchanged.

Only source bars fully closed by event time are visible. Fresh watcher state per symbol and run, one `update_data({'close': bar.close})` then `analyze(Symbol(bar.symbol))` and actual `EngineService.process_observation` per completed bar, ordered by `(close_time, symbol)`. ReplayClock is advanced to the bar close; memory forensic sink is injected. No synthetic OBI/CVD/BBO, Strategy or Fusion inputs are used. This once-per-completed-bar research cadence does **not** claim Live wall-time watcher cadence or downstream parity.

## Frozen data and event selection

Use only the qualified public Binance USD-M Futures BTCUSDT/ETHUSDT 1h raw capture in `data/research/pre_intent/candle_capture_v1/capture_manifest.json` (SHA-256 `4832beedbbddb4ea55da8882994cb7497f77298003f09e9642046331e8533ffb`; qualification manifest SHA-256 `2c119868cf0c839ebb934557b1faac8b2771eae722f6cce2c8a8239e2f868775`). Raw BTC SHA-256 `eb0868edc9ff94ce64d898c3a874d18c7979e3ae3d0a683e291b74210ff8c348`; raw ETH SHA-256 `98d4f0c83d29974cb2d220616528d6bd8b998a016867bd37c85a14bd0e7f7190`. `load_frozen_capture` must reject mismatched hashes, gaps, duplicates, invalid OHLCV and timestamp defects. Bars with open times 2026-06-01T00:00 through 2026-06-30T23:00 UTC form the research run. First 50 completed bars per symbol are warmup; evaluation observations have close time **strictly after** 2026-06-03T02:00 UTC through 2026-07-01T00:00 UTC. Bars before June 1 and after July 1 are outside the frozen research sample and cannot supply labels or extra observations.

Retain all BUY, SELL and NEUTRAL Engine counts for audit, but only BUY/SELL are directional candidates. For inference choose **the first chronological directional event per symbol per UTC-aligned 4-hour block** (`floor(unix_seconds / 14400)`). No later event in the same symbol/block may replace it. This rule is fixed without reading future outcomes. Outcome-blind feasibility already observed 1,340 evaluation Engine events: BUY 139, SELL 278, NEUTRAL 923; selected 163 directional events (BTC 73, ETH 90) on 22/24 distinct UTC days. Full normalized trace SHA-256 `e6efa4b9625812dbb864187b6ee87b5e87b939cc1729f040e092fe9b12c25126`; selected-event trace SHA-256 `d5f836229267d36d0f9ec62fa10281877618daf3d0ea939d40f2627688fdb54f`. If these traces change, stop and investigate before outcome computation. Require at least 100 selected events and at least 20 distinct UTC event days for each symbol. Do not alter event selection after seeing labels.

## Outcomes and inference

Primary horizon is exactly four **later completed 1h closes** of the same symbol. Primary label is side-adjusted simple close-to-close return: BUY `(close[T+4]-close[T])/close[T]`, SELL its negative. The 1h later close is a secondary descriptive label only. `T` is the actual closed bar that produced the Engine output. Do not use an event if any required later close lies outside the frozen run; mark it censored, never zero-return. No TP/SL, MFE/MAE, R or executable fill claim: this boundary has no causal entry/exit geometry. Report full/eligible/censored counts and all BUY/SELL/NEUTRAL counts. No change in symbols, horizon, confidence threshold, watcher, date interval or sample minimum after outcome inspection.

One pooled BTC+ETH primary hypothesis: mean 4h side-adjusted return <= 0. Report N, mean, median, standard deviation and a **95% percentile block-bootstrap confidence interval**, 10,000 resamples, fixed seed `20260926`. Resampling unit is a **UTC calendar day across both symbols**; draw the set of distinct eligible event days with replacement, including every selected event from each drawn day, and calculate the pooled event-weighted mean. This handles within-day and cross-symbol co-movement more conservatively than eventwise iid resampling, though it does not eliminate all serial dependence. Report per-symbol and calendar-week descriptive splits, 1h horizon and leave-one-week-out mean as diagnostics only; do not use them as independent positive discovery claims or tune based on them. The primary family has one test. **Predictive support** requires selected/censored sample requirements and the lower 95% bootstrap bound > 0. If the interval includes 0, classify not supported; if sample requirements fail, classify inconclusive/underpowered regardless of point estimate. A negative result is valid. Any failure of causality/determinism/prefix invariance voids interpretation.

## Costs and economic interpretation

The signal is known only after bar completion, so the contemporaneous close is **not** an executable entry fill. This study has no independently justified bid/ask, fee, slippage, funding or execution-time entry/exit data. Therefore the primary outcome is a **gross predictive label only**. No after-cost Edge, expected trading PnL, win rate or Profit Factor claim is authorized from it. Do not insert an arbitrary favorable cost estimate. If predictive support appears, economic Edge remains unresolved and needs a separately preregistered causal execution/cost study; this V1 cannot become one post hoc.

## Pre-outcome hard gates

1. Frozen file hashes and completed-bar provenance pass; no silent cleaning or future bar exposure.
2. Existing Watcher/Engine semantics and per-symbol fresh state are unchanged; no synthetic favorable input reaches this boundary.
3. Event timestamps equal causal bar close; repeated normalized trace and three real-archive prefix cuts (June 8, 18, 28 UTC) pass.
4. Selected-event hash and sample/day feasibility above pass; no outcome has been read before this artifact is hashed and committed.
5. Focused prior regressions pass; protected production persistence hashes unchanged; offline test network is denied and no authenticated broker/order capability used.

Only after all gates pass may this exact study compute the frozen labels. Stop at its scientific checkpoint; do not create V2 from observed outcomes automatically.
