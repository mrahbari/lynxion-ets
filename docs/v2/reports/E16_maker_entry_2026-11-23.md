# E16 — maker (post-only limit) entries vs market entries (roadmap E8-1, 2026-11-23)

Script `research/v2/experiments/e16_maker_entry.py` (pre-registered, committed before running: 44cb1e8).
E9 trades, Binance 1m candles (10 symbols, Oct 2025 - Oct 2026). Limit at the market-entry price P0, fill only
when price trades 1 bp through it (conservative queue), timeout W; missed = no trade (cancel) or market at
t + W (fallback). Metric: R per signal including missed trades.

| W | period | fill rate | market R | cancel R | fallback R | cancel gain | fallback gain | edge-neutral gain (cancel / fallback) |
|---|---|---|---|---|---|---|---|---|
| 5 min | DEV | 87.4 % | -0.101 | -0.058 | -0.065 | +0.043 | +0.037 | +0.030 / +0.031 |
| 5 min | HOLD | 88.1 % | -0.092 | -0.047 | -0.055 | +0.045 | +0.037 | +0.034 / +0.033 |
| 15 min | DEV | 90.4 % | -0.101 | -0.059 | -0.063 | +0.042 | +0.038 | +0.032 / +0.032 |
| 15 min | HOLD | 91.3 % | -0.092 | -0.050 | -0.053 | +0.042 | +0.039 | +0.034 / +0.035 |

**Verdict: PASS (all four variants).** About +0.04 R per signal, of which about +0.03 R is pure execution
cost (edge-neutral), stable DEV -> holdout. No meaningful adverse selection: missed trades win 38 % vs 39 %
for filled ones. Larger than the earlier +0.02-0.03 R estimate because the 2 bp entry slippage is also saved
and many stops are tight (small sl_pct makes fixed bp costs large in R).
Per strategy (holdout): biggest gain OIFootprint (+0.08 R edge-neutral, fill 75-78 %), VWAP +0.04,
MeanReversion +0.04; volatility_breakout slightly worse (-0.01 to -0.03).

Limits: fills are modelled on Binance 1m data; BingX (and VST's demo matching) has thinner books, so fill rate
must be measured live. It does not make any strategy profitable on its own (best holdout: mean_reversion
-0.014 -> +0.03 R) — it removes a fixed cost.

Decision: E8-2 unblocked. Implement post-only entry with fallback to market after 15 min (no missed signals),
behind a flag, then measure fill rate and realised cost on VST.
