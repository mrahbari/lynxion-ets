# E8 — Each watcher in isolation (2026-11-22)

Script `research/v2/experiments/e8_watcher_isolation.py`; data `E8_watcher_isolation.csv`.
10 liquid Binance USDT-M perps, 21 days of 1m bars (live watchers refresh every ~30s), each watcher fed exactly
the payload its `update_data()` reads, scored by the live Engine rule and by the live Fusion keyword rule.
Forward returns 15m / 1h / 4h, non-overlapping samples, gross (round-trip taker cost ~10 bp).

## Plumbing findings (live)
- Fusion produced **no direction** in 297 live attempts: it needs >=2 aligned DIRECTION watchers
  (trend_mtf, liquidity, historical_candle) but historical_candle and liquidity never receive data live.
  Live trades therefore come only from each strategy's own candle logic.
- Live payloads are flat close/high/low/volume: market_pulse and historical_candle need `candle`,
  funding_rate needs `funding_rate`, liquidity needs `bids/asks`, orderflow_ws needs `trades` -> always silent.
- Engine has no rule for `funding_*` or `candle_reversal_*` observations -> always NEUTRAL there.
- anomaly_ml: Engine treats "positive" as SELL (contrarian), Fusion treats it as BUY -> the two layers disagree.
- volatility: Engine maps high volatility to BUY -> a pure long bias whenever volatility is high.

## Predictive power (one watcher alone)
| Watcher | Best result | Verdict |
|---|---|---|
| historical_candle (Fusion rule) | 4h: +22.9 bp, t=4.8, 9/10 symbols, both halves +; +20 bp after removing drift | **Only candidate.** Short sample, one falling regime -> needs long test |
| anomaly_ml (Engine rule) | 4h: +12.6 bp, t=2.2; 15m/1h below cost | weak; Fusion rule is the exact mirror (negative) |
| volatility (Engine rule) | always long; 1h +9.6 bp t=1.7 | a long bias, not a signal |
| market_pulse | |t| <= 3.4 with the wrong sign under the Fusion rule | no edge |
| trend_mtf | signals on 0.4% of bars, negative | no edge |
| funding_rate | produces no direction | untestable as wired |
Not testable offline: liquidity, cmc_screener; orderflow_ws left untouched by operator decision.
