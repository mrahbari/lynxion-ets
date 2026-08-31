# Edge Candidate Register v19 — C-20 Symmetric Premium-Basis Convergence

**Status:** FROZEN — OUTCOMES UNOPENED

C-20 tests whether an extreme futures premium or discount relative to the index converges over the
next day. Unlike C-10/C-11's one-sided funding-settlement rule, this signal is symmetric, uses the
independent premium-index series, and applies no funding-level filter.

## Frozen Data and Samples

- BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- Official TASK-0112 premium-index 15m panel, native Binance Futures 15m prices, and actual funding.
- Primary: 2024-01-01 through the last common timestamp no later than 2026-08-29.
- Temporal reverse: 2023-01-01 through 2023-12-31.
- Condition-aligned C-20 price outcomes are unopened at this commit boundary.

## Frozen Signal and Alignment

- Exact four-hour UTC decisions.
- At decision `t`, use premium-index close at `t-15m`; require that exact completed candle and no
  fill across missing intervals.
- Threshold is the causal p95 of absolute premium close over the prior 180 valid four-hour
  observations for that symbol. Exclude the current value and require all 180 observations.
- Premium >= threshold => SHORT; premium <= -threshold => LONG.
- No price, funding-level, OI, book-depth, trend, volatility, volume, persistence, regime, ranking,
  symbol-specific, or one-sided filter.

## Frozen Execution and Gate

- Enter at exact next 15m open; exit at exact 24-hour prior-bar close.
- Reject overlapping positions per symbol.
- Apply actual funding strictly after entry through exit with correct side sign.
- Round-trip costs: 0.20%, 0.30% primary, and 0.50%.
- Report four chronological primary folds, both sides, all symbols, missing alignments, overlaps,
  funding contribution, deterministic day-cluster bootstrap, and positive-PnL concentration.
- KEEP requires every condition: primary N>=600, expectancy>0, PF>1, bootstrap lower bound>0;
  >=3/4 positive folds with N>=100; LONG and SHORT positive with N>=120 each; >=4/6 positive
  symbols with N>=80; concentration<=30%; reverse N>=200 with expectancy>0 and PF>1; primary
  expectancy positive at 0.50% cost.

A pass is historical KEEP only. Failure closes this exact hypothesis; post-result reversal,
one-sided promotion, threshold changes, and reslicing are prohibited.
