# E11 — watcher logic review: each watcher fixed and re-tested against its own job (2026-11-23)

## Why this review
E8/E8b tested watchers mostly as-built and judged every one by direction. The operator asked for each
watcher to be read for what its name and role say it should do, its implementation fixed, then re-tested.
Result: **every watcher except FundingRate's thresholds had at least one implementation bug that changed
what it measured.**

## Bugs found and fixed (commits c502979, a27e119; TrendMTF in 729cd17)

| Watcher (role) | What it should do | What it actually did | Fix |
|---|---|---|---|
| TrendMTF (DIRECTION) | trend agreement across timeframes | regression over 5/15/30 samples of 1m bars (5–30 minutes); fired ~never | closed 15m/1h/4h bars, t-stat ≥ 2 on all three; history seeded at startup |
| HistoricalCandle (DIRECTION) | reversal candlestick on the latest candle | scanned all 150 one-minute candles for *any* pattern anywhere, so the output was the inverted sign of the 50-minute slope | last CLOSED 15m candle; hammer / shooting star / engulfing; ATR-sized; needs a prior trend of ≥ 1 ATR |
| AnomalyML (DISCOVERY) | flag unusual bars | weighted z-score passed through `tanh(1.5·z−1)` was > 0.1 for ordinary bars, so "anomaly" was the last 1m bar's sign | robust z (median/MAD, 240 bars): \|z_ret\| ≥ 4, or z_vol ≥ 4 with \|z_ret\| ≥ 2 |
| Volatility (REGIME) | volatility regime | stdev of raw price differences, last 20 min vs previous 20 min (noise); Engine read expansion as **BUY** | 1h realized vol / 24h baseline; Engine treats it as non-directional |
| MarketPulse (REGIME) | short-term momentum pulse | MACD threshold in absolute price units (BTC always "strong", DOGE never); volume added to the signed value; confidence could not reach the gate; Engine ignored the side in the type | relative MACD; volume unsigned; confidence = agreement of evidence; Engine reads bullish/bearish |
| FundingRate (REGIME) | crowding at extreme funding | confidence = \|rate\|·50, so extremes (0.05) were always gated out and "normal" (≈0.6) always passed | extremes 0.65/0.8, normal 0.3 |
| CMCScreener (REGIME) | macro/symbol context from CMC | keys are `BTC` but symbols are `BTCUSDT`, so every pair got the first CMC coin's data; volatility from minutes-apart polls was ~0, always "low" | base-asset mapping; 24h move as volatility |
| Liquidity (DIRECTION) | spread/depth state | never received an order book → never produced an observation | BingX top-20 depth every 60s |
| OrderFlowWS | — | not touched (operator decision) | — |

## Re-test (pre-registered in `research/v2/experiments/e11_watcher_role_retest.py`)
- **Windows:** FRESH = 2026-03..06, never used for any watcher test. DEV = 2026-07..08 and OLD-VAL = 2026-09..10
  were both seen before and are shown for continuity only.
- **Data:** 8 liquid perps, closed 1m bars, live payload shapes, and the live Engine rule.
- **Event-based scoring:** the first bar of each new side, non-overlapping, gross.
- **Stand-alone edge:** FRESH mean > 10 bp with t ≥ 2, at a horizon also positive on DEV.
- **Useful Fusion input:** FRESH gross > 0 with t ≥ 2 and DEV > 0.

| Watcher | Events / symbol / day | FRESH 15m / 1h / 4h, bp (t) | Verdict |
|---|---|---|---|
| TrendMTF | ~1 | −0.4 (−0.3) / −0.9 (−0.4) / −2.7 (−0.5) | no edge |
| HistoricalCandle | ~5 | −0.8 (−1.7) / −0.9 (−0.9) / +0.4 (0.2) | no edge |
| MarketPulse | ~37 | −0.4 (−1.9) / −1.0 (−1.7) / +0.7 (0.4) | no edge (slightly negative at short horizons) |
| AnomalyML (Engine reads as reversal) | ~13 | +0.6 (1.6) / −0.8 (−1.0) / −0.6 (−0.3) | no edge; 54% hit rate at 15m but ~0.6 bp |
| FundingRate | 0 | — | no ≥ 0.05% funding on these majors in 2026 (the extremes it targets did not occur) |

**Volatility** is judged on what it is for, forecasting volatility. It works in every window:

| Window | Next-hour vol ÷ 24h baseline: compression / normal / expansion | Spearman |
|---|---|---|
| FRESH | 0.70 / 0.99 / 1.39 | 0.59 |
| DEV | 0.69 / 0.98 / 1.50 | 0.59 |
| OLD-VAL | 0.66 / 1.00 / 1.47 | 0.65 |

## Conclusion (realistic)
1. The implementations were genuinely broken. Most watchers did not measure what their names say, and two
   produced inverted or random sides. The fixes are correct engineering and now run live.
2. **After the fixes, no directional watcher predicts 15m–4h returns on liquid perps, net or gross.** They now
   implement textbook signals faithfully: MTF trend alignment, candlestick reversals, a short-term pulse and 1m
   shocks. On liquid crypto perps those signals carry no edge, consistent with the literature.
   Fixing them did not create one.
3. **Volatility is the one watcher with demonstrated, stable value.** It forecasts next-hour realized volatility
   (state ratios 0.7 / 1.0 / 1.4–1.5, rank correlation about 0.6 in all three windows). Its production use is
   risk sizing and stop distance (volatility targeting), not entry direction.
4. Liquidity (spread/depth) and CMC are context and veto inputs, not testable offline. FundingRate only fires
   in crowded names, so its natural universe is the cross-sectional sleeve (XS-COMBO), where funding carry is
   the proven edge.
5. Fusion still needs two aligned DIRECTION observations. With no directional edge in any watcher, the
   platform's own entry path has no expected alpha. XS-COMBO remains the only evidence-backed strategy.
