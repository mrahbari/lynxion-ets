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

---

## E15-W8 — AnomalyML watcher (`infrastructure/watchers/adapters/anomaly_ml.py`) — 2026-11-23

**Role.** Flag an abnormal last 1m bar (outlier return, or outlier volume with a large return):
`anomaly_positive / anomaly_negative / anomaly_normal`.

**Logic (live "robust_z" mode).** Robust z-score of the last 1m log return against the median and
MAD x 1.4826 of the preceding window; volume z on log volume the same way; anomalous if |z_ret| is above
its threshold, or z_vol is high and |z_ret| above a lower threshold. MAD-based outlier detection is the
standard robust method; correct, no lookahead. Not machine learning despite the name.

**Live evidence.** normal 12,994 / negative 186 / positive 166 (2.6 %); 5,780 warm-up.

**Findings.**
| # | Sev | Finding |
|---|---|---|
| W8-1 | note | The Engine maps `anomaly_positive` to SELL and `anomaly_negative` to BUY (assumes 1m outliers revert); that is a trading hypothesis, not the watcher's job, and is untested -> G1. |
| W8-2 | P2 | ~250 lines of the former feature/score path remain after `return` (dead). Name "ML" is misleading. Cleanup in E10. |
| W8-3 | P2 | Confidence fixed (0.75 / 0.3). |

**Verdict: does its job.** No P1.

---

## E15-W9 — Watchers not running live — 2026-11-23

- **CMCScreener**: disabled since 2026-11-23 (`CMC_SCREENER_ENABLED=false`): duplicate trigger, not used in
  decisions. Keep disabled; retire in E10 unless a role is found.
- **TickWatcher** (`tick.py`): not instantiated by the live watcher set (8 watchers started per symbol).
  Retire candidate in E10.

**Watcher layer summary (W0-W9).** Feed mechanics correct; venue gap negligible (0.2-3.9 bp).
P1 defects found and fixed: TrendMTF spurious-regression trend statistic, FundingRate per-period vs
per-8h units, MarketPulse noise-level "strong" labels, OrderFlowWS never fed. Volatility, Liquidity,
HistoricalCandle and AnomalyML do their jobs. Phase-2 items listed per watcher. Next layer: Fusion (F1).

---

## E16 — Architect review of the watcher layer (2026-11-23)

**Design assessment.** The layer's architecture is sound: one interface (`update_data` / `analyze`), raw
observations only (no trading decisions), a base class with health tracking, closed-bar feed. What was
missing, and is now added without changing any label or interface:
1. **Declared contract** (`ROLE`, `HORIZON`, `CLAIM`, `VALIDATED` class attributes) stamped into every
   observation's `metadata['contract']`, plus `as_of_bar_close` (the bar the label was computed from).
   Downstream layers no longer need hard-coded guesses about what a watcher means.
2. **Base behaviour actually applied**: eight watchers overrode `analyze()` with a pass-through, so the
   base class's health tracking never ran; removed (behaviour otherwise identical).
3. **A validity harness** (`research/v2/experiments/e18_watcher_validity.py`): replays 13 months of closed
   1m bars (BTC, ETH, SOL, DOGE) through the live classes exactly as the feed does and tests each
   watcher's own claim on its own target, pre-registered, DEV then HOLDOUT.
4. **Calibrated confidence** where a claim is validated (confidence = DEV hit rate, checked on HOLDOUT).

**Pass grade** (roadmap E16): contract, correct and causal, null-calibrated, claim valid out of sample,
confidence calibrated. A = predictive claim validated; B = correct, honest descriptive claim.

| Watcher | Claim tested (E18) | DEV | HOLDOUT | Null (random walk) | Grade |
|---|---|---|---|---|---|
| Volatility | expansion/compression -> next-hour vol above/below baseline | 1.49x / 0.66x of normal, PASS | 1.52x / 0.66x, PASS | 0.2 % non-normal | **A** (confidence 0.85 / 0.92 = DEV hit rate; HOLDOUT 0.83 / 0.92) |
| AnomalyML | outlier bar -> abnormal next 15 min | 1.58x vs 0.96x, PASS | 1.50x vs 0.96x, PASS | 0 % | **A** (confidence 0.74; HOLDOUT 0.69) |
| TrendMTF | aligned trend continues 4 h | -2.4 bp, t -0.7, hit 43 %, FAIL | +25 bp, t 5.0, hit 51 %, FAIL | 5 % | **B** (descriptive; continuation not supported) |
| MarketPulse | strong 15m move continues | -4.7 bp, t -3.9 (reverses), FAIL | +0.3 bp, t 0.1, FAIL | ~5 % | **B** (descriptive) |
| HistoricalCandle | reversal pattern reverses 1 h | -3.0 bp, t -3.1, FAIL | +0.3 bp, t 0.3, FAIL | n/a | **B** (descriptive) |
| FundingRate | crowded side pays (definitional) | — | — | — | **B** (correct after W3 units fix; E12: crowded-side entries slightly worse) |
| Liquidity | book absorbs orders | not testable offline (no historical book) | | | **B** |
| OrderFlowWS | aggressor imbalance | E17: CVD sign carries no outcome information | | | **B** |

Directional claims were not "fixed until they pass": a design iterated on DEV until it passes would be
fitted noise (MarketPulse's DEV reversal and TrendMTF's HOLDOUT continuation point in opposite
directions across periods). Their labels stay (descriptive, honest `CLAIM`, `VALIDATED=False`); their
confidence values are left unchanged for now because Engine/Fusion gate on them — how those layers should
consume an unvalidated directional label is decided in F1/G1, so no live behaviour is removed here.

**Use for the next layers.** The two validated watchers give real information: Volatility predicts the
next hour's volatility (useful for sizing, stop width and regime gating), AnomalyML predicts abnormal
activity (useful as an entry-caution / execution-risk input). Directional watchers should not be read as
predictions.

---

## E15-F1 + E16 — Fusion layer — 2026-11-23

**Role.** Combine what all watchers say about a symbol into one state: regime, directional bias,
execution context (design: DISCOVERY -> REGIME -> DIRECTION -> EXECUTION, hierarchical).

**Live behaviour before the fix (runner log).** 100 % of watcher observations were discarded before
fusion: `DISCARDED_INVALID_CLASSIFICATION` (liquidity, historical_candle) or `DISCARDED_BELOW_THRESHOLD`
(trend_mtf, funding_rate, anomaly_ml, market_pulse, volatility, orderflow_ws); every DIRECTION ANALYSIS
ended `no_direction_observations`; regime NEUTRAL 3,582 times vs RISK_ON twice.

**Defects (P1).**
| # | Defect |
|---|---|
| F1-1 | Called once per interpreted signal (`fuse_signals([signal])`) and stateless: two watchers are never fused together, so the hierarchical design could never run (E12). |
| F1-2 | Role table filed Liquidity as DIRECTION (it has no side) and anomaly as DISCOVERY; class names sent by the Engine were not recognised by the table at all. |
| F1-3 | Regime mapping read directional words (bullish -> RISK_ON, bearish -> OVERHEATED) and ignored the validated regime evidence (volatility, anomaly); `WEAK_RISK_ON` unreachable (`> 0.3` then `> 0.1`). |
| F1-4 | Hand-set confidence gates (0.45-0.70) discarded the validated volatility/anomaly evidence's neutral states and most others. |

**Fix (architecture kept, made executable).** `infrastructure/fusion/symbol_state_fusion.py`: per symbol,
the latest observation of every watcher is kept until stale (5 min; funding 20 min) and the whole state is
fused on every call; roles come from each watcher's declared contract (E16-WB), with a corrected fallback
table (liquidity = execution). Regime from validated evidence first: anomaly or volatility expansion ->
`volatile`; aligned TrendMTF -> `bullish_trending` / `bearish_trending` (descriptive); volatility
compression -> `ranging`; else `normal` — the vocabulary StrategyManager and the strategy adapters
already use. Direction = confidence-weighted vote of fresh direction watchers (neutral votes 0), marked
`validated_direction: False` (E18). One fused signal per incoming signal, as before (no change in how
often strategies are evaluated). Live container uses `mode='state'`; `FusionService()` without a mode
keeps the former hierarchical path, so frozen replays and research harnesses are unchanged
(`FUSION_MODE=hierarchical` restores it live).

**Effect on trading.** None on entries today: live strategy adapters do not gate on fused bias,
confidence or regime (E12); the fused regime feeds strategy ranking (0.7-1.2) and attribution only.
The gain is a correct, inspectable symbol state for the next layers (E16 strategy/risk use).

**Tests.** `tests/unit/test_symbol_state_fusion.py` (7): multi-watcher fusion, conflict cancelling, stale
expiry, liquidity never votes direction, contract role wins, regime from volatility/anomaly, symbol
isolation, class-name mapping, mode switch. Full suite 1,400 passed.

**Grade (E16).** Contract and correctness: pass. Validity of the fused direction: not supported (inputs
unvalidated, E18) -> recorded. Validity of the fused regime: inherits the validated volatility/anomaly
claims. Grade **B+** (A for regime, B for direction).

**Live verification (2026-11-23, after two deployment fixes).** (1) The live orchestrators resolve the
module-level `fusion_service` accessor, not the container builder, so the first deployment still ran the
hierarchical path; the accessor now uses `FUSION_MODE` (default `state`). (2) The second deployment raised
`'>' not supported between str and float` on ~1,800 signals in 10 minutes: a downstream consumer reads
`metadata['contributors']` as numeric weights; contributors are now `{watcher: confidence}` and the labels
moved to `contributor_labels`; the event system now logs the file:line of such errors. Third deployment:
480 fused signals in the first minutes, 0 errors; bias BUY 79 / NEUTRAL 125 / SELL 36; regime `normal` and
`ranging` (volatility compression) appear; execution intents continue as before (333).

---

## E15-G1 — EngineService (`infrastructure/engines/engine_service.py`) — first evaluation 2026-11-23

**Role.** Translate each raw watcher observation into an `InterpretedSignal` (type BUY / SELL / NEUTRAL /
HOLD, direction -1..1, strength) for Fusion.

**Mapping of every live label (probe).**
| label | -> type | direction | issue |
|---|---|---|---|
| volatility_normal / compression | HOLD | 0 / -0.5 | value rule `< 0.3` hits labels whose value is 0 or negative: normal volatility becomes HOLD |
| volatility_expansion | NEUTRAL | +0.5 | non-directional watcher gets a positive direction |
| liquidity_normal / high | HOLD / NEUTRAL | 0 / +0.9 | normal liquidity becomes HOLD; high liquidity gets a "bullish" direction |
| trend_positive, market_pulse_*_strong, candle_reversal_* | BUY / SELL | by side | consistent |
| anomaly_positive / negative | SELL / BUY | inverted | contrarian hypothesis embedded in a translation layer; tested on E18 data: next 15 min -1.5 / -1.2 bp (t -0.9), next 60 min +0.5 / +3.4 bp: **not supported** |
| funding_rate_positive / negative | SELL / BUY | 0 | contrarian, untested; direction field contradicts the type |
| order_flow_* | NEUTRAL | +/-value | side present in the label is never mapped to a type |

Live (current run): 606 NEUTRAL, 110 HOLD, 4 SELL interpreted signals.

**Findings.**
| # | Sev | Finding |
|---|---|---|
| G1-1 | P2 | Type and direction are inconsistent for non-directional watchers (HOLD for normal volatility/liquidity; positive direction for volatility expansion and high liquidity). |
| G1-2 | P2 | Two trading hypotheses (anomaly reversion, funding contrarian) live inside the translation layer; anomaly reversion is not supported by data (E18 probe). |
| G1-3 | P2 | Order-flow sides are not mapped; source watcher is guessed by substring when metadata lacks it (candle patterns -> None). |
| G1-4 | note | Since F1 the live fusion reads labels, roles and confidence, not the Engine's type/direction, so these defects do not change any decision today. |

**Grade (first evaluation): C** — works as a pass-through, but its own output (type/direction) is not
reliable. Upgrade task (E16-U7): role-aware translation from the watcher contract (direction only from
direction-role watchers; regime/positioning/execution -> NEUTRAL with direction 0 and the role attached);
hypotheses (anomaly/funding contrarian) moved out of the Engine until validated.

---

## E15-G2 — MarketStructureEngine (`infrastructure/market_structure/market_structure_engine.py`) — first evaluation 2026-11-23

**Role.** Levels the strategies trade from: volume profile POC / VAH / VAL, support / resistance, bias.
Used by all 9 strategy adapters (VWAPReversal enters on rejections at VAL/VAH and targets POC).

**Logic.** On the strategy's bar buffer (last 20 bars): support/resistance = min low / max high of the 20
bars (Donchian, including the current bar — not swing structure despite the name); volume profile = each
bar's whole volume assigned to the bin of its **close**, 10 bins; value area grown to 70 %; bias = price
vs POC +/- 0.1 %.

**Check against the standard definition.** Standard volume profile spreads each bar's volume over its
high-low range on a finer grid (here: 1m bars, 50 bins, same 20 hours). 600 random 20-hour windows (BTC,
ETH, SOL, DOGE): median difference POC 0.32, VAL 0.27, VAH 0.33 hourly ATRs; **POC more than 1 ATR away
in 23 %** of windows. Strategy entries and targets placed on these levels are therefore often placed on
noise-level levels.

**Findings.**
| # | Sev | Finding |
|---|---|---|
| G2-1 | P1-candidate | Volume profile from 20 closes in 10 bins is far from a standard profile (above). Directly affects VWAPReversal / NGMR entries and targets. |
| G2-2 | P2 | "Support/resistance" are 20-bar extremes including the current bar, not swing pivots. |
| G2-3 | P2 | Bias = price vs a noisy POC +/- 0.1 %, no volatility scaling. |

**Grade: C.** Upgrade task (E16-U8): standard volume profile (volume spread over each bar's range,
from 1m/5m bars, adaptive bin count, session or rolling 24 h window), swing-pivot S/R (fractals,
confirmed bars only), ATR-scaled bias; then re-run E9 for the strategies that use the levels.
