# Conditional setup V2 — pre-outcome public candle acquisition specification

**DATA DEFINITION ONLY; freeze/hash/commit before any V2 public acquisition or future-label calculation.** This does not preregister the scientific outcome test, authorize use of V1's opened outcome interval, or modify Lynxion strategy policy. Candidate provenance and old-archive *event counts only* are in `CONDITIONAL_SETUP_EDGE_V2_CANDIDATE_INVENTORY.md`.

## Single source and mechanically selected dates

One source for both symbols: Binance USDⓈ-M Futures **public** `GET https://fapi.binance.com/fapi/v1/klines`, `symbol=BTCUSDT` or `ETHUSDT`, `interval=1h`, `limit=1500`, no credentials, account endpoint, order endpoint or broker SDK. The same source/open-close contract already qualified for the prior candle capture applies: raw row `[0]` is exchange open time in integer milliseconds UTC, `[6]` exchange close time, `[1:6]` OHLCV. Each 1h row is available only at `close_ms + 1 == open_ms + 3,600,000`, never before. Preserve both exchange timestamps and raw response bytes.

The V1 evaluation ended by bar open time at 2026-07-01T00:00 UTC. Select the **first later full UTC evaluation day after a fixed 72-hour warmup**, 2026-07-04. At this specification's 2026-09-26 decision date, the last wholly completed UTC day is 2026-09-25; end evaluation at its next midnight. No inspection of V1 residuals, market behavior, later returns or local outcome files selected these dates.

| Window by exchange bar **open time**, UTC | Exact interval | Purpose |
|---|---|---|
| Acquisition | `[2026-07-01 00:00, 2026-09-26 00:00)`; milliseconds `[1782864000000,1790380800000)` | 2,088 consecutive 1h rows/symbol if complete. |
| Warmup only | `[2026-07-01 00:00, 2026-07-04 00:00)`; 72 bars/symbol | Initializes existing 30-sample trend history and 20-sample structural state with margin. No eligible opportunity or outcome. |
| **Unopened V2 evaluation** | `[2026-07-04 00:00, 2026-09-26 00:00)`; 2,016 bars/symbol | Fixed 84 complete UTC days. Do not extend to improve N/effect. Last events may be censored by a later frozen outcome horizon. |

For each symbol request exactly two pages: page 1 open times `[1782864000000,1788264000000)` (1,500 rows; `endTime=1788263999999`); page 2 `[1788264000000,1790380800000)` (588 rows; `endTime=1790380799999`). UTC page split is 2026-09-01T12:00. No rolling “latest” request, alternate timeframe, resampling, symbol replacement, gap backfill, or source mixing. A source/API anomaly fails qualification until separately recorded; do not silently repair.

## Immutable raw data and provenance

Store each raw HTTP response body once at `data/research/conditional_setup_v2/candle_capture_v1/raw/{SYMBOL}/page-000{1,2}.json`, using exclusive creation/link semantics so reruns cannot overwrite. Record exact URL and parameters, public endpoint/data product, source documentation URL, UTC request/receipt time, HTTP status, raw byte count and SHA-256, row count, first/last exchange open and close milliseconds. Immediately produce a capture manifest containing this specification SHA-256 and commit, source/contract, symbols, 1h timeframe, UTC and millisecond units, all three windows, per-page paths/hashes and acquisition metadata. Raw bodies are immutable; qualification goes in a separately hashed manifest, never by editing the raw capture.

Qualification must establish 2,088 unique monotonic contiguous hourly candles **for each symbol** and exact common UTC overlap; 12-column source rows; `close_ms=open_ms+3,599,999`; finite positive OHLC, low<=open/close<=high, nonnegative finite volume; no duplicate, gap, overlap, partial, malformed or future-incomplete bar. Reject rather than fill. The first 72 bars are warmup, not evaluation; the last bar must have completed by acquisition time. Do not calculate candidate outcomes during capture/qualification. The eventual V2 study must bind exact raw and qualification manifest hashes and pass its separate causal/state/prefix/sample gates before labels open.

If the public source is inaccessible in the current execution environment, record `ENVIRONMENT_BLOCKED_NONCRITICAL` once and preserve this specification. Do not probe DNS repeatedly, use an authenticated API, switch venue, or weaken the fixed interval. No production persistence path may be written.
