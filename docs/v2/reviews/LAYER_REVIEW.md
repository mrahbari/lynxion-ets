# Layer-by-layer baseline review (roadmap E15)

Operator request 2026-11-23: review every component one at a time (watchers -> fusion -> engines ->
strategies -> execution/risk) until each does its own job correctly; only then improve quality.
Each section: role, live inputs, logic vs standard definition, correctness (lookahead, units, reachable
outputs), live evidence, verdict. Severity: **P1** = component cannot do its job (fixed in phase 1),
**P2** = quality gap (phase 2), **note** = observation.

---

## E15-W0 — Watcher data feed (`MonitoringAnalysisService`) — 2026-11-23

**Role.** Give every watcher of a symbol the same stream of closed market data, once per bar, from the
market the platform trades, plus the auxiliary inputs each watcher needs (funding, order book, trades).

**How it works (code: `infrastructure/watchers/monitoring_analysis_service.py`).**
- Every cycle (32 symbols in ~0.5 s) `_update_watchers_with_market_data` asks the shared data provider for
  **1m** bars: `period="6h"` at first sight of a symbol, then `"30m"`. `_feed_new_closed_bars` feeds each
  bar once, oldest first, only if `open + 60 s <= now` (forming bar excluded), as `{open..close, volume,
  candle{...}}`.
- First sight: watchers with `HTF_SEED` (TrendMTF) also get higher-timeframe history.
- Funding: BingX public `premiumIndex`, cached 10 min, sent only when the value/period changes.
- Order book: BingX public top-20 depth, every 60 s, only to watchers with `calculate_liquidity_score`.
- Since E14: OBI/CVD snapshot for the confirmation stage (BingX depth + public trades, 60 s).
- Data provider: `EnhancedDataProvider` -> `ConfigurableHistoricalDataProvider`, sources
  `['binance', 'mexc', 'phemex', 'bingx']` (Binance first "to avoid BingX rate limits").

**Live evidence (runner log 2026-11-23, read-only probe of the same provider).**
- 1m bars arrive with 60 s steps, last closed bar 20-80 s old; keys `open high low close volume timestamp`.
- Sources over one runner session: 4,874 fetches served by Binance, 1,362 by BingX.
- Symbols with no Binance perpetual (OKBUSDT, NCSISP5002USDUSDT, NCCO1OILBRENT2USDUSDT, NCCO7241NATGAS2USDUSDT,
  NCCO1OILWTI2USDUSDT) fall back to BingX and repeatedly fail ("No verified perpetual historical data",
  744 / 494 / 452 times; BingX answers "请稍后重试" = retry later).

**Findings.**
| # | Sev | Finding |
|---|---|---|
| W0-1 | P1 | **Wrong market for most symbols.** Watchers (and strategies) read Binance prices while orders execute on BingX (VST). Signals, levels and stops are computed on a different book; on VST the gap is large (VST spread ~27 bp vs ~0.1 bp). The feed should come from the execution venue, Binance only as fallback. |
| W0-2 | P1 | **No data for BingX-only symbols.** OKB and the NC* commodity/index contracts get intermittent or no bars (hundreds of failures per session), yet they are in the approved universe and are traded. Their watchers cannot do their job. |
| W0-3 | P1 | **No trade feed.** `update_data` never receives `trades`, so OrderFlowWS can never emit (see W6). |
| W0-4 | P2 | Bars carry only OHLCV: no quote volume, no taker-buy volume, no trade count, so no watcher can measure flow/participation even though both venues provide it. |
| W0-5 | P2 | Order book only reaches Liquidity-type watchers and is the BingX production book, not VST's. |
| W0-6 | P2 | Data cache key ignores `period` (`data_cache.get(broker, symbol, timeframe)`): a caller asking 6h right after another asked 30m gets 30 bars (reproduced). Harmless in today's call order (6h first; strategies use one period per timeframe), latent otherwise. |
| W0-7 | note | Every runner restart resets watcher history to the 6h seed; ten restarts today. |
| W0-8 | note | NC* contracts (S&P 500, Brent, WTI, natural gas) passed the liquidity rule; they have session hours and no Binance data. Decide in E6 whether they belong in the universe. |

**Verdict.** The feed mechanics (closed bars once, no forming bar, funding de-duplication) are correct. It
does **not** yet do its job fully: wrong venue for most symbols (W0-1), missing data for BingX-only
symbols (W0-2), and no trades (W0-3). Phase-1 fix proposal: make the execution venue (DEFAULT_BROKER)
the primary bar source for watchers and strategies, with Binance as fallback, and either supply public
trades to OrderFlowWS or retire it (decided in W6). To be confirmed with the operator before changing,
because it changes every strategy's input data.
