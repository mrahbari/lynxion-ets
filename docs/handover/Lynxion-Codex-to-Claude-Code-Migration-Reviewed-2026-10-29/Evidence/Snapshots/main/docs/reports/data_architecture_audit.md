# Data Architecture Audit (Phase 13)

**Date:** 2026-06-13. Analysis only — no code/strategy changes. Goal: map every data source in the
repo and establish what the production *trade-decision* path actually consumes.

## Headline
The system has **two disjoint data paths**, and the one that makes buy/sell decisions is **OHLCV-only**:

1. **Observation/selection path:** `watcher.update_data → analyze → MarketObservation → event router →
   Engine → Fusion → FusedSignal` → strategy *selection / execution-intent gating*.
2. **Trade-decision path (OHLCV-only):** OHLCV bar → `strategy.update_with_market_data(bar)` →
   per-symbol `data_buffer` → `strategy.generate_signal(symbol)`.

These never intersect: a strategy's `generate_signal` reads **only** its OHLCV `data_buffer`
(`infrastructure/strategies/strategy_adapters.py:544-563`). No funding/order-flow/breadth/OI/tick value
ever enters a buy/sell decision.

## Active ingestion (what is fetched + stored)
- **OHLCV (spot klines) only**, via ccxt async + direct REST against **binance / bingx / mexc / phemex**:
  `data_downloader_adapter.py:184-189` (`fetch_ohlcv`, hardcoded 1m); `configurable_historical_data_provider.py:400/448/504/550`
  (binance/bingx/mexc/phemex `/klines`); WS klines `websocket_router.py:90-93`.
- Higher TFs (5m/15m/30m/1h) are **resampled from 1m** (`resample_engine.py:39-77`), not fetched.
- Stored by `CandleStore` to `data/history/raw/<tf>/<sym>.csv` (`candle_store.py:12,27`),
  columns `timestamp,open,high,low,close,volume`.

## Code paths that exist but persist nothing (live snapshot/stream only)
| Category | Code | Stored? |
|---|---|---|
| Order-book depth | `downloader.py:62` (`/api/v3/depth`), `rest_client.py:123`, WS `@depth` `websocket_router.py:105` | **No writer; no history** |
| Trade tape | WS `@trade` `websocket_router.py:100` | **No store** |
| Ticker price | `downloader.py:46`, `market_data_feed.py:103` | cached only |

## External non-OHLCV feed that IS real (but unused by decisions)
- **CoinMarketCap screener** (`cmc_screener.py:327`, `/v1/cryptocurrency/listings/latest`, key-gated):
  real top-100 price/volume/market-cap/%-change. Feeds **only the fusion path**, persists nothing,
  and never reaches a strategy decision. (It does not compute dominance/breadth series.)

## What the strategies consume (confirmed)
Pure OHLCV. The strategy `data_buffer` keys are exactly `open/high/low/close/volume/timestamp`
(`scripts/universe_validation.py:43-51`, mirroring the production feed). Every strategy computes its
own EMA/RSI/ATR from that buffer (base helpers `strategy_adapters.py`). No external data.

## Conclusion
The production decision architecture is **strictly OHLCV-only**. Substantial non-OHLCV machinery exists
(watchers, CMC, depth/trade endpoints, an archived derivatives stack) but is either inert, fusion-only,
unstored, or un-wired — see `unused_data_inventory.md`. Whether *adding* non-OHLCV data could create
information beyond OHLCV is assessed in `market_data_gap_analysis.md` / `data_edge_opportunity_matrix.md`
/ `phase13_recommendation.md`. (No profitability is claimed.)
