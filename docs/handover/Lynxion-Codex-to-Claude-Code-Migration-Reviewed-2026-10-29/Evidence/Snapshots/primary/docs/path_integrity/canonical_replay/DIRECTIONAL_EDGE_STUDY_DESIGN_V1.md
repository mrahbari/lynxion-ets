# Directional Edge study V1 — outcome-blind boundary inventory

Status: **design / sample feasibility only**. This is a new generation after the immutable closure of the candle-reversal Fusion study in `0986f3e`. No forward return, MFE/MAE, TP/SL, cost, PnL or other outcome has been read. This document is **not** a preregistration and authorizes no outcome calculation.

## Existing directional lineage

| Candidate | Source-backed direction and confidence | Inputs/time/state | Boundary verdict |
|---|---|---|---|
| `TrendMTFWatcher` → `EngineService` | The watcher emits `trend_positive`/`trend_negative` from weighted regression slopes; Engine's existing `trend` branch maps those labels to BUY/SELL, carrying watcher confidence. This is the first observed two-sided BUY/SELL boundary on the qualified candle-only path. | One completed candle's `close` per symbol/event; rolling 5/15/30-sample windows and per-instance history. Despite its name, source uses three windows of the **same input timeframe**, not independently closed HTF candles. No OBI/CVD/BBO. Its former `datetime.now()` values were output/state timestamps, not read by the trend formula. | Selected for a **Level-1 Engine-interpreted direction** feasibility question. Not FusedSignal, ExecutionIntent, trade or live-parity evidence. |
| `AnomalyMLWatcher` → Engine | Watcher emits signed momentum spikes (Engine thresholded BUY/SELL) and positive/negative anomaly labels (Engine contrarian SELL/BUY). Confidence is anomaly/feature-derived. | Flat close/volume and feature history; rolling baseline excludes current feature. Wall-clock observation stamp and global forensic sink remain. No BBO required for its feature input. | Alternative, not selected: combines momentum and contrarian families; would require a larger semantic and time/sink audit. |
| `MarketPulseWatcher` → Engine | Market-pulse positive/negative labels can map to BUY/SELL. | Expects nested candle input whereas inspected monitoring formatter supplies flat OHLCV; hierarchical role is REGIME. | Do not select without proven live input contract. |
| `VolatilityWatcher` → Engine | Volatility high/expansion can map to BUY, low to HOLD; no symmetric SELL interpretation. | Flat OHLC; hierarchical role REGIME. | Not a clean two-sided directional question. |
| `HistoricalCandleWatcherAdapter` → Engine → Fusion | `candle_reversal_*` has no Engine directional branch; corrected routed Fusion remains NEUTRAL in the frozen 1,340-event cohort. | Qualified 1h candle archive. | Closed generation; do not rescue. |
| Order-flow/tick/liquidity watchers | May carry microstructure direction or execution veto in other contexts. | Required historical tick/book/BBO provenance absent from qualified candle archive. | Not historically reproducible here; no proxy inputs. |
| Strategy adapters / `DecisionPipeline` | May emit actionable `ExecutionIntent`. | Point-in-time OBI/CVD/BBO and `SetupEngine` decision clock remain unresolved. | Parked; not necessary for Engine-level Level-1 question. |

The inspected Live factory registers and initialization service constructs TrendMTF for enabled symbols; the monitoring service calls `update_data` and `analyze` with flat close fields. This proves a source-level Live composition path, **not** that historical decisions match Live execution scheduling or that the corresponding Fusion/Strategy branch would accept it. In actual routed processing, `SignalProcessor` passes one interpreted signal to Fusion per invocation, and hierarchical Fusion can require multiple aligned inputs. Engine BUY/SELL must not be relabeled as final Live trading direction.

## Minimal causal seam and preservation

`TrendMTFWatcher` now accepts optional `clock` and `forensic_sink`. With defaults, it uses the same Live `datetime.now()` clock behavior and the same global forensic logger as before; the numerical trend, confidence, thresholds and Engine mapping are unchanged. An explicit ReplayClock stamps the completed-bar close, and a memory sink prevents replay forensic writes. The 5/15/30 windows are the constructor defaults used by the inspected Live factory (it does not pass its separate config-period values); this discrepancy is documented, not changed. The test uses the actual watcher and Engine, fresh per symbol/run, no synthetic decision information.

## Outcome-blind feasibility on qualified frozen BTC/ETH capture

Capture identity and provenance remain in `PRE_INTENT_SIGNAL_STUDY_CLOSURE_V1.md`. Same common 50-bar warmup, 670-bar/symbol evaluation. One watcher update per completed 1h bar, sorted by (close time, symbol); no future bar exposed. Among 1,340 evaluation Engine outputs: **BUY 139, SELL 278, NEUTRAL 923**. Choosing the first directional event per symbol/UTC 4-hour block yields **163** non-overlapping events (BTC 73, ETH 90), on **22/24** distinct UTC days respectively. These are event counts only, not sample power or Edge evidence. A new preregistration must still freeze its own N, horizon, exclusion, statistical and cost contract before any outcome opens. Do not transfer the old study's acceptance decision automatically.

Repeated normalized Engine traces match. Three real-archive cuts (June 8, 18, 28 UTC) match prefix of the full trace. The source has no decision-time wall-clock read after injection; no cross-symbol state is shared in this fixture. Historical watcher cadence differs from the live monitoring loop and is explicitly a once-per-completed-bar research subset. Production persistence and network were not used.

## Open release gates before outcomes

- Freeze and hash `DIRECTIONAL_EDGE_STUDY_V1` preregistration with the Engine-level estimand and an explicit treatment of this bar-close subset versus Live cadence. No post-count threshold, symbol, date, or watcher optimization.
- Verify a normalized decision trace and the exact selected-event set are immutable references; retain the known qualified raw-capture hashes.
- Establish a non-favorable, predeclared cost treatment. Close-to-close forward returns are predictive labels, not executable fills. Any after-cost claim needs an independently justified price/cost model; if unavailable, report predictive evidence only.
- Re-run scoped causal/prefix/regression and persistence checks before outcomes. No Fusion/Strategy/ExecutionIntent parity is claimed by this design.
