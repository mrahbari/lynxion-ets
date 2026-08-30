# Edge Candidate Register v18 — C-19 Liquidity-Withdrawal Differential

**Status:** FROZEN — OUTCOMES UNOPENED

C-19 tests a dynamic liquidity-provision mechanism distinct from C-18's static imbalance. A larger
four-hour withdrawal of ask depth than bid depth signals LONG; the symmetric bid withdrawal signals
SHORT.

## Frozen Data, Universe, and Samples

- BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- TASK-0109 official book panel, using only `notional_m1` and `notional_p1`.
- Native Binance Futures 15m prices and actual funding from the already integrity-gated panels.
- Primary: 2024-01-01 through the last common timestamp no later than 2026-08-29.
- Temporal reverse: 2023-01-01 through 2023-12-31.
- C-19 condition-aligned outcomes are unopened at this commit boundary.

## Frozen Signal

- Exact four-hour UTC decisions.
- At each decision anchor and at the anchor exactly four hours earlier, use the latest complete book
  snapshot strictly before that anchor; each snapshot must be no more than five minutes old.
- Require all four near-book notionals to be finite and strictly positive.
- Compute `bid_change = log(current_bid / lagged_bid)` and
  `ask_change = log(current_ask / lagged_ask)`.
- Define withdrawal differential `score = bid_change - ask_change`. A positive score means ask-side
  liquidity fell relative to bid-side liquidity; a negative score is symmetric bid-side withdrawal.
- Threshold: causal p90 of `abs(score)` over the prior 180 valid decisions for that symbol, excluding
  the current observation and requiring all 180.
- `score >= threshold` => LONG; `score <= -threshold` => SHORT.
- No static-imbalance, price, OI, funding-level, trend, volatility, volume, regime, ranking,
  persistence, deeper-level, or symbol-specific filter.

## Frozen Execution and Gate

- Exact next 15m open entry, exact 24-hour prior-bar close exit, and per-symbol overlap rejection.
- Actual funding strictly after entry through exit with correct side sign.
- Round-trip costs 0.20%, 0.30% primary, and 0.50%.
- Four chronological primary folds; side, symbol, staleness, missing alignment, overlap, funding,
  day-cluster bootstrap, and positive-PnL concentration reports.
- KEEP requires all C-18 numeric gates unchanged: primary N>=600, expectancy>0, PF>1, bootstrap
  lower bound>0; >=3/4 positive folds with N>=120; both sides positive with N>=150; >=4/6 positive
  symbols with N>=80; concentration<=30%; reverse N>=250 with expectancy>0 and PF>1; primary
  expectancy positive at 0.50% cost.

A pass is historical KEEP only and authorizes no production or risk mutation. Failure closes this
exact dynamic mechanism; reversing or reslicing the opened outcomes is prohibited.
