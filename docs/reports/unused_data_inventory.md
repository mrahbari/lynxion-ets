# Unused Data Inventory (Phase 13)

**Date:** 2026-06-13. Data infrastructure/data that EXISTS in the repo but is NOT used by the
production trade-decision path. Analysis only.

## 1. Archived derivatives ingestion stack (funding + open interest) — built, tested, UN-WIRED
A complete hexagonal funding/OI ingestion stack lives under `docs/archive/phase6/ingestion/`
(`derivatives_data.py` port, `derivatives_downloader_adapter.py` = ccxt Binance USDⓈ-M futures
`fetch_funding_rate_history`/`fetch_open_interest_history`, `derivatives_store_adapter.py` CSV store,
`ingest_derivatives.py` use case + CLI + runner). Per `docs/archive/phase6/CLEANUP-AND-ADMISSION.md:16`
it was **un-wired from `bootstrap/container.py`** (2 factories removed) because it wasn't used by the
12 production strategies. `grep derivativ bootstrap/container.py` → 0 hits.

**Data it already produced (still on disk):**
| Path | Coverage | Note |
|---|---|---|
| `data/history/raw/funding/` | **24 symbols, ~3 years, 8-hour cadence** (BTC: 3,286 rows, 2023-06→2026-06) | REAL, deep history — completely unused |
| `data/history/raw/open_interest/` | **3 symbols (BTC/ETH/SOL), ~30 days hourly** | data-blocked: Binance OI history endpoint caps ~30d |

The `oi_footprint` strategy built on the OI data was **tested and rejected**:
`data/results_storage/edge_oi_footprint_30d.json` = `DIRECTIONAL_NO_GO`. (Funding data has **never**
been used by any strategy.)

## 2. CoinMarketCap screener — real external feed, fusion-only
`cmc_screener.py` makes a real CMC API call (top-100 listings) and emits market-regime observations to
the event/fusion path. It never reaches a strategy decision and persists nothing. The richest external
data in the system, effectively discarded for trade decisions.

## 3. Inert watcher adapters (instantiated + run, but receive no data)
The watcher feed (`monitoring_analysis_service.py:240-277`, `_format_market_data_for_watcher`) emits
only `open/high/low/close/volume/timestamp/bid/ask`. Watchers that key on other inputs get nothing and
return `None` every cycle:
| Watcher | Needs (never supplied) | Status |
|---|---|---|
| funding_rate | `data['funding_rate']` | inert — no fetch; feed never supplies it |
| orderflow_ws | `data['bids']/['asks']/['trades']` | inert — **no websocket despite the name** |
| liquidity | `data['bids']/['asks']` | inert |
| tick | `data['tick']` | inert **and disabled by default** |
| market_pulse | `data['candle']` | starved (OHLCV-derived but keys on missing `candle`) |
| historical_candle | `data['candle']` | starved |

OHLCV-derived watchers that *do* emit (to fusion only, never to strategies): volatility, trend_mtf,
anomaly_ml (note: anomaly_ml is z-score thresholding, not ML; `model_fitted` never true).

## 4. Live market-data code with no historical store
- Order-book depth fetch (`downloader.py:62`, `rest_client.py:123`) + WS `@depth` — no writer, no files.
- Trade-tape WS `@trade` (`websocket_router.py:100`) — subscribe only, no store.
- These are **forward-recordable** but have **zero backfill/history** today.

## Summary of unused/under-used data
| Asset | Exists as | Used by decisions? | Usable history? |
|---|---|---|---|
| **Funding rates** | archived stack + **3yr on disk** | No | **Yes (deep)** |
| Open interest | archived stack + ~30d on disk | No (oi_footprint tested→failed) | Limited (~30d cap) |
| Market breadth (CMC) | live watcher (real fetch) | No (fusion-only) | No (snapshot only) |
| Order-book depth | fetch/WS code | No | No (snapshot/stream) |
| Trade tape | WS subscribe | No | No (no store) |
| Tick | watcher (disabled) | No | No |

**Most striking:** 3 years of real funding-rate data for 24 symbols sits on disk, fully ingested, and
has never touched a strategy — and a complete ingestion stack to refresh/extend it exists (archived).
The next phase's gap analysis treats this as the lowest-effort, highest-availability lever.
