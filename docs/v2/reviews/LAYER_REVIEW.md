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
| W0-1 | note (was P1) | **Watchers read Binance, orders go to BingX — measured, negligible.**  Watchers (and strategies) read Binance prices while orders execute on BingX (VST). Signals, levels and stops are computed on a different book; on VST the gap is large (VST spread ~27 bp vs ~0.1 bp). The feed should come from the execution venue, Binance only as fallback. |
| W0-2 | P2 (was P1) | **Gappy data for BingX-only symbols.** OKB and the NC* commodity/index contracts get intermittent or no bars (hundreds of failures per session), yet they are in the approved universe and are traded. Their watchers cannot do their job. |
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

**Follow-up measurement (same day, before any change).** Last 120 closed 1m bars, median |close difference|:
BingX prod vs Binance 0.2-3.3 bp, VST vs Binance 0.4-3.9 bp (BTC, ETH, SOL, DOT, XRP, ENA, NEAR, HYPE);
1m return correlation Binance/VST 0.46-0.99 (VST adds noise on thin names). Against ~120 bp median stops
this is negligible, so W0-1 is downgraded to a note and **no source switch is made** (it would change every
strategy's input for no measurable gain). BingX-only symbols: one session had 111-128 successful BingX
fetches vs 226-372 failed or skipped (BingX "retry later" plus the provider's 300 s failure cache); the
30-bar request window backfills missed bars, so their watchers lag by up to ~5 min rather than starve:
W0-2 downgraded to P2. Revised verdict: the feed does its job for all live watchers except OrderFlowWS
(W0-3, decided in W6).

---

## E15-W1 — Volatility watcher (`infrastructure/watchers/adapters/volatility.py`) — 2026-11-23

**Role.** Regime, not direction: is the market in volatility expansion, compression or normal right now.
(Fusion's classifier maps it to `WatcherRole.REGIME`; the Engine reads it as non-directional.)

**Logic.** On each closed 1m bar: realized vol of the last 60 one-minute log returns divided by the std of
all returns kept (up to 1,440 = 24 h; at least 240 = 4 h before any output). Ratio >= 1.5 -> expansion,
<= 0.67 -> compression, else normal. Standard definition: realized-volatility ratio (short window vs
baseline); this is a correct, conventional form. No lookahead (closed bars only).

**Live evidence (all runner logs 2026-11-23).** Outputs: normal 8,866 / compression 3,132 / expansion
1,348 (66 / 23 / 10 %). All three states are produced; warm-up met at first sight (6 h seed = 360 bars).
Unit test exists (`tests/unit/test_watcher_logic_review.py::test_volatility_regime_compares_last_hour_with_baseline`).

**Findings.**
| # | Sev | Finding |
|---|---|---|
| W1-1 | P2 | Baseline includes the last hour itself, which pulls the ratio towards 1 (standard: baseline excludes the short window, or EWMA). |
| W1-2 | P2 | No intraday seasonality: a quiet hour is compared with a 24 h baseline that contains the US session, so compression is over-reported in quiet hours (23 % compression vs 10 % expansion). Standard fix: compare with the same hour of previous days. |
| W1-3 | P2 | Confidence (0.3 normal; 0.6-0.9 otherwise) is a fixed mapping of the ratio, not a calibrated probability. |
| W1-4 | P2 | ~110 lines of unreachable legacy code after `return` (old score, regime, ATR); ATR is computed every bar and never used. Cleanup in E10. |
| W1-5 | note | Observation timestamp is `datetime.now()`, not the bar's close time. |
| W1-6 | note | Its value to trades is a separate question: as a regime filter on E9 trades it separated nothing (E12). How Fusion/Engine/strategies consume it is reviewed in F1/G1. |

**Verdict: does its job** (phase 1 OK, no P1). Phase-2 list: W1-1..W1-4.

---

## E15-W2 — TrendMTF watcher (`infrastructure/watchers/adapters/trend_mtf.py`) — 2026-11-23

**Role.** Directional context: is there a trend aligned across 15m, 1h and 4h (positive / negative /
neutral). The Engine maps `trend_positive` to BUY and `trend_negative` to SELL.

**Inputs and mechanics (OK).** Closed 1m bars are downsampled into closed 15m/1h/4h bars; at first sight
the higher timeframes are seeded with real closed bars (15m 2d, 1h 3d, 4h 15d) and 1m bars of seeded
buckets are skipped. Buckets align to UTC like Binance candles; gaps close the bucket with its last close;
partial higher-TF bars are never used. No lookahead.

**Logic defect (P1, fixed).** Each timeframe's trend was the t-statistic of a regression of log price on
time over 20 bars, called significant at |t| >= 2. That statistic is invalid on prices (spurious
regression): on a simulated **random walk it exceeds 2 in 72 % of windows** instead of ~5 %. So "trend"
mostly labelled noise (live today: 30 % positive, 2 % negative). Standard definition: a trend is a drift
whose mean return is significant against bar noise, t = mean(r) / (sd(r)/sqrt(n)) (6 % on a random walk).
- Fix: `_drift_t` replaces `_trend_t` in MTF mode. The joint threshold is calibrated on the null only (no
  outcome data): with nested 15m/1h/4h windows, |t| >= 1.0 on all three fires on 5.0 % of random walks
  (2.0 would fire on 0.1 %). `MTF_T_MIN = 1.0`.
- Effect on 2025-26 Binance history (10 symbols, 4h steps): old rule 6.0 % positive / 7.1 % negative;
  new rule 1.6 % / 2.0 % — i.e. aligned trends occur about as often as in a random walk at these
  horizons. Expect far fewer trend observations live (from ~32 % to a few %).
- Tests: random-walk false-positive rate of `_drift_t` (< 10 %) and of the joint rule (2-9 %).
  Legacy mode (frozen research feeds) unchanged.

**Other findings.**
| # | Sev | Finding |
|---|---|---|
| W2-1 | P1 | Spurious-regression trend statistic (fixed above). |
| W2-2 | P2 | Confidence (0.55 + 0.05 x (t - threshold)) is a mapping, not a calibrated probability. |
| W2-3 | P2 | ~150 lines of legacy-mode code still loaded in live (needed only by frozen research studies). |
| W2-4 | note | Live effect of fewer BUY/SELL trend signals on strategy triggering is checked in G1 (Engine). |

**Verdict: does its job after the fix** (deployed with the next runner restart).

---

## E15-W3 — FundingRate watcher (`infrastructure/watchers/adapters/funding_rate.py`) — 2026-11-23

**Role.** Positioning / crowding context: funding normal, positive (longs pay), negative (shorts pay),
or extreme. Fusion classifies it as REGIME.

**Inputs.** BingX public `premiumIndex` `lastFundingRate` (the rate for the running period), fetched at
most every 10 min, delivered only when the value or period changes.

**Logic.** Current rate vs fixed thresholds: |rate| > 0.05 % -> positive/negative, > 0.10 % -> extreme
(5x and 10x the 0.01 % base rate). Conventional.

**Live evidence.** All 14,280 observations today were `funding_rate_normal`. A same-day cross-section of
the 77 approved symbols (8 h-normalised) shows why: median 0.007 %, 95th percentile 0.010 %, none above
0.05 %, 18 negative. So "normal" is the correct answer in this calm market, not a defect.

**Findings.**
| # | Sev | Finding |
|---|---|---|
| W3-1 | P1 | **Units bug (fixed).** BingX contracts settle every 4 h or 8 h (1 h also exists); the per-period rate was compared with per-8 h thresholds, so a 4 h contract needed twice the real crowding to register. The feed now passes `fundingIntervalHours` and the watcher normalises to 8 h (metadata: `rate_basis`, `funding_interval_hours`); feeds without the interval are unchanged. Test added. |
| W3-2 | P2 | History is appended only when the value changes, so "average funding" is an average of changes, not of time. |
| W3-3 | P2 | Confidence is a fixed table (0.3 / 0.65 / 0.8), not calibrated. |
| W3-4 | note | E12: on the strategies' trades, entries on the side that pays funding (crowded) were slightly worse (-0.05 R, t -2.3) at a 0.01 % threshold — the only watcher state with a consistent sign. Use as a veto is a phase-2 candidate. |

**Verdict: does its job after the units fix** (deployed with the next runner restart).

---

## E15-W4 — MarketPulse watcher (`infrastructure/watchers/adapters/market_pulse.py`) — 2026-11-23

**Role.** Short-term momentum context on 1m bars: is the last few minutes' move a real push up/down, or
exhausted (overbought/oversold), or nothing. Engine maps `*bullish*` -> BUY, `*bearish*` -> SELL,
`caution/neutral/...` -> NEUTRAL; Fusion classifies it as REGIME.

**Former logic.** A 16-label decision tree on the last 15 1m candles: "MACD" from 5/10 EMAs above 5 bp
plus any positive raw-price slope -> `bullish_strong`; 15-bar simple RSI at 65/35; Bollinger position;
volume spike; fixed slope/momentum cut-offs. None of these thresholds was scaled to the symbol's
volatility.

**Defect (P1, fixed).** On simulated random walks (8 bp/min) the old tree labelled **33 %** of minutes
`bullish_strong`/`bearish_strong` (live today: 45 % of 15,250 outputs), i.e. the "strong" labels were
mostly noise and fed the Engine as BUY/SELL signals.

**Fix (standard definitions).** Momentum z-score: sum of the last 15 one-minute log returns divided by
(1m volatility of the last 60 returns x sqrt(15)); |z| >= 2 -> strong (two-sided ~5 % on a random walk).
Wilder RSI(14): a strong up-move with RSI >= 70 -> `bullish_overbought_caution`, a strong down-move with
RSI <= 30 -> `bearish_oversold_caution`; otherwise `neutral_low_momentum`. Labels kept so Engine/Fusion read
them unchanged; warm-up 61 closes (the 6 h seed covers it). Random-walk check: 94.5 % neutral, 4.4 %
caution, 1.0 % strong. Tests: random walk < 10 % non-neutral; a +/-3 % 15-minute move is flagged by side.
The old tree is kept as `_analyze_impl_legacy` until the E10 cleanup.

**Other findings.**
| # | Sev | Finding |
|---|---|---|
| W4-1 | P1 | Noise-level "strong" labels (fixed above). |
| W4-2 | P2 | Volume no longer used (OHLCV volume without taker split says little); revisit if the feed gains taker volume (W0-4). |
| W4-3 | P2 | Confidence fixed (0.3 / 0.5 / 0.7), not calibrated. |
| W4-4 | note | Expect far fewer BUY/SELL pulse signals live; effect on strategy triggering checked in G1. |

**Verdict: does its job after the fix** (deployed with the next runner restart).

---

## E15-W5 — Liquidity watcher (`infrastructure/watchers/adapters/liquidity.py`) — 2026-11-23

**Role.** Execution context: is the order book of this symbol liquid enough right now (spread, depth).
Not directional.

**Inputs.** BingX production top-20 order book every 60 s (W0). **Logic.** spread = (ask - bid)/bid;
depth = top-5 bid+ask notional, scored log1p(depth/10,000)/5 capped at 1; score = 0.4 x (1 - 100 x spread)
+ 0.6 x depth; < 0.3 low, > 0.7 high. Arithmetic checked; correct.

**Live evidence.** high 12,560 / normal 2,826 / none yet 3,708 (before the first book). "normal" only on
the thinner books (OKB, XAUT, BNB, HYPE, PIEVERSE, CRO ...); "low" never — the universe is already
liquid (E6: >= 5 M USDT median daily volume).

**Findings.**
| # | Sev | Finding |
|---|---|---|
| W5-1 | P2 | Depth is scored on an absolute dollar scale that saturates around 1.5 M of top-5 depth; the standard question is depth relative to the intended order (our orders ~200 USDT: every listed book absorbs them). A slippage-for-order-size estimate would make it informative. |
| W5-2 | P2 | Production book, not VST's (W0-5). |
| W5-3 | note | Fusion's classifier gives it `WatcherRole.DIRECTION` (should be execution/regime) -> F1. Engine maps `liquidity_normal` (value 0) to HOLD and `high` to NEUTRAL -> G1. |

**Verdict: does its job** (correct measurement; low information inside an already-liquid universe). No P1.

---

## E15-W6 — OrderFlowWS watcher (`infrastructure/watchers/adapters/orderflow_ws.py`) — 2026-11-23

**Role.** Trade-flow pressure: imbalance of aggressive buy vs sell volume over the last trades
(`order_flow_buy_pressure / moderate_buy / neutral / moderate_sell / sell_pressure`).

**Defect (P1, fixed in the feed; watcher code untouched).** It was never given trades (W0-3): every one
of its ~5,000 checks today ended "No Observation Generated". The monitoring loop already fetches BingX
public trades every 60 s for the E14 order-flow snapshot; `_feed_trades` now passes only trades newer
than the last fed one, oldest first, as `{price, quantity, side}` (BingX `isBuyerMaker=True` = aggressive
sell). No extra API calls. Test: imbalance (3 - 1)/4 = 0.5 after two trades; repeated trades not re-fed.

**Logic.** imbalance = (buy - sell) / (buy + sell) base volume over the last 100 trades; |x| < 0.1 neutral,
0.1-0.3 moderate, > 0.3 pressure. Standard volume-delta ratio; correct.

**Other findings.**
| # | Sev | Finding |
|---|---|---|
| W6-1 | P1 | No trade feed (fixed above). |
| W6-2 | P2 | Window is "last 100 trades": seconds on BTC, possibly hours on thin names — not time-consistent. A fixed time window (as in the E14 snapshot, 5 min) is standard. |
| W6-3 | P2 | Thresholds are not scaled to normal imbalance noise. E17: the CVD sign carries no information about the strategies' trade outcomes (no lift on 5/15/60 min windows). |
| W6-4 | note | It will now emit observations live; how the Engine routes `order_flow_*` is checked in G1. |

**Verdict: does its job after the feed fix** (deployed with the next runner restart).

---

## E15-W7 — HistoricalCandle watcher (`infrastructure/watchers/adapters/historical_candle.py`) — 2026-11-23

**Role.** Reversal candlestick patterns on closed 15m candles: `candle_reversal_bullish/bearish`, else
`candle_neutral`.

**Logic (live "tf" mode).** Closed 1m bars aggregated into closed 15m candles (UTC buckets, gaps
handled). Patterns on the last closed candle, only after a prior move of >= 1 ATR(14) over 10 candles:
hammer / shooting star (range >= ATR, long shadow >= 2x body, small opposite shadow) and bullish /
bearish engulfing (body >= 0.5 ATR). These are the textbook (Nison) definitions with a trend-context
requirement; correct, no lookahead.

**Live evidence.** neutral 12,794 / bearish reversal 376 / bullish reversal 178 (4 % of outputs);
5,780 "no observation" = warm-up (16 closed 15m candles) after the many restarts today.

**Findings.**
| # | Sev | Finding |
|---|---|---|
| W7-1 | P2 | The same closed-candle pattern is re-emitted on every cycle for 15 minutes (~30 identical observations); downstream de-duplication is checked in G1. |
| W7-2 | P2 | Confidence fixed (0.65 / 0.3). |
| W7-3 | P2 | ~450 lines of legacy-mode code (1m "any pattern anywhere") still loaded. Cleanup in E10. |

**Verdict: does its job.** No P1.
