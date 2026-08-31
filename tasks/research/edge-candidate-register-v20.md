# Edge Candidate Register v20 — C-21 Aggressive Taker-Flow Continuation

**Status:** FROZEN — OUTCOMES UNOPENED

C-21 tests whether extreme net aggressive taker flow over a fully completed four-hour window
continues over the next day. It uses executed taker flow rather than resting book depth, OI, basis,
funding severity, or price momentum.

## Frozen Data and Samples

- BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- Official TASK-0114 native 15m total/taker-buy quote flow, integrity-gated futures prices, and
  actual funding settlements.
- Primary: 2024-01-01 through the last common timestamp no later than 2026-08-29.
- Temporal reverse: 2023-01-01 through 2023-12-31.
- C-21 condition-aligned outcomes are unopened at this commit boundary.

## Frozen Signal

- Exact four-hour UTC decisions.
- Use exactly the 16 native bars from `t-4h` through `t-15m`; reject the decision if any bar is
  missing or total quote volume is non-finite/non-positive.
- For the window, define `score = (2 * sum(taker_buy_quote) - sum(total_quote)) /
  sum(total_quote)`.
- Threshold: causal p90 of `abs(score)` over the prior 180 valid decisions per symbol, excluding
  current and requiring all 180.
- Score >= threshold => LONG; score <= -threshold => SHORT.
- No price, funding-level, OI, book, basis, volatility, trend, regime, persistence, ranking, or
  symbol-specific filter.

## Frozen Execution and Gate

- Exact next 15m open entry; exact 24-hour prior-bar close exit; per-symbol overlap rejection.
- Actual funding strictly after entry through exit, correct side sign.
- Round-trip costs 0.20%, 0.30% primary, and 0.50%.
- Four primary folds plus side, symbol, missing-window, overlap, funding, day-cluster bootstrap, and
  positive-PnL concentration reports.
- KEEP requires all: primary N>=600, expectancy>0, PF>1, bootstrap lower bound>0; >=3/4 positive
  folds with N>=120; both sides positive with N>=150; >=4/6 positive symbols with N>=80;
  concentration<=30%; reverse N>=250 with expectancy>0 and PF>1; primary positive at 0.50% cost.

A pass is historical KEEP only. Failure closes this exact mechanism; reversal, horizon/threshold
changes, and post-result subgroup promotion are prohibited.
