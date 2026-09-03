# Edge Candidate Register v26 — C-27 Concentrated Aggressor Exhaustion

**Status:** PREREGISTERED — OUTCOME UNOPENED

C-27 tests whether unusually concentrated, strongly one-sided aggregate-trade flow marks short-term
aggressor exhaustion and reverses after the completed 15-minute bucket. The large-trade
concentration moderator is unavailable in the previously rejected taker-flow candidates; this is
one reversal specification, not another continuation variant.

## Frozen Data and Boundaries

- TASK-0128 official BTCUSDT aggregate-trade features, aligned exactly to TASK-0094 native
  BTCUSDT USDT-perpetual 15-minute OHLC and the existing official BTC funding history.
- No fill, interpolation, nearest match, or resampling. Reject incomplete or non-contiguous paths.
- Primary: 2025-01-01 through 2026-08-29. Temporal reverse: 2024-01-01 through 2024-12-31.
- Four global chronological primary folds formed from eligible entry timestamps.
- The TASK-0128 panel hash is frozen as
  `3e5975b6e1369685877c57944375a330548515ce7eb064f240b3c81885ef9edf`.

## Frozen Signal

- At each completed 15-minute bucket, compute thresholds from the previous 2,880 exact panel rows,
  excluding the current row.
- Require `top_1pct_quote_share` strictly above its causal prior-window p99.
- Require absolute `signed_imbalance` strictly above both its causal prior-window p95 and 0.30.
- Positive imbalance indicates buyer aggression and negative imbalance indicates seller aggression.
- Trade the exhaustion reversal: SHORT after positive imbalance and LONG after negative imbalance.
- No price-return, volatility, trend, funding, regime, hour, weekday, or diagnostic filter is used.

## Frozen Execution and Economics

- Enter at the next exact native 15-minute open after the completed signal bucket.
- Exit at the exact open 16 native bars after entry (four hours).
- Reject missing/non-contiguous paths and overlapping BTC positions; retain the earliest signal.
- Include official funding settlements strictly after entry and at or before exit: LONG pays the
  funding rate and SHORT receives it.
- Charge 0.30% round trip. Report 0.20% and 0.50% sensitivities; the primary verdict uses 0.30%.
- Signal features use completed prior information only. Entry and exit opens cannot affect signal
  formation.

## Frozen Reporting and Gate

- Report alignment/lookback/signal/path/overlap census, sides, folds, calendar years, holding return,
  funding, cost sensitivities, threshold exceedance magnitudes, and monthly positive-PnL
  concentration.
- Cluster-bootstrap 10,000 samples by UTC entry day with seed 270027.
- KEEP requires every condition: primary N>=200; expectancy>0; PF>1; clustered 95% lower bound>0;
  >=3/4 positive folds with N>=30; both LONG and SHORT positive with N>=60; both primary calendar
  years positive with N>=50; positive-PnL monthly concentration<=25%; temporal reverse N>=100 with
  expectancy>0 and PF>1; and positive primary expectancy at 0.50% cost.
- Any failed condition is REJECT. A pass is only KEEP_FOR_PROSPECTIVE_VALIDATION.

## Frozen Prohibitions

No percentile, lookback, imbalance floor, direction, holding period, cost, funding rule, overlap
rule, period, fold, cluster, or gate may change after outcome opening. Diagnostics cannot alter the
verdict. No order, production strategy, risk, trailing, symbol-admission, or leverage change is
authorized.
