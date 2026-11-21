# Edge Candidate Register v8 — C-09 BTC-Regime Long Relative Strength

**Status:** PRE-REGISTERED — INDEPENDENT HISTORICAL HOLDOUT ONLY

C-09 is derived from C-08's post-result LONG/BTC-positive clue. It is frozen before acquiring
or evaluating the independent pre-2023 holdout and may not be tested by re-slicing C-08.

## Independent Dataset Boundary

- Binance USDT-margined futures native 15m bars from
  `https://fapi.binance.com/fapi/v1/klines`.
- Fixed symbols: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT.
- Requested opens: 2020-01-01 00:00 UTC through 2022-12-31 23:45 UTC.
- Exact intersection begins at the latest listing/availability time among the six; no fill.
- Store separately under `data/research/c09/binance_futures_15m/`; TASK-0094/C-08 files remain
  immutable. Manifest and integrity gates match TASK-0094.

## Frozen Hypothesis

When BTC's completed 24-hour return is positive and cross-sectional relative-strength spread
is elevated, the strongest alt major should continue upward over the next 24 hours after
realistic friction.

## Frozen Features and Execution

- Daily decisions at UTC midnight from completed bars.
- Relative strength: alt 96-bar return minus BTC 96-bar return.
- Spread: maximum minus minimum relative strength across ETH/SOL/BNB/XRP/ADA.
- Require spread above the median of the prior 180 daily spreads, excluding current.
- Require BTC 96-bar return > 0. LONG only the strongest relative alt; otherwise NO TRADE.
- Enter next 15m open; exit at the open 96 bars after entry; 0.30% round-trip cost with 0.20%
  and 0.50% sensitivity. One open position; prior exit occurs before next entry.

## Gate

- Four chronological folds on the untouched holdout; trades cannot cross folds.
- Report N, expectancy, PF, win rate, payoff, drawdown, bootstrap CI, folds, symbols, spread
  buckets, BTC-return buckets, and costs.
- KEEP_FOR_PROSPECTIVE_VST requires expectancy > 0, PF > 1, bootstrap lower bound > 0,
  at least 3/4 positive folds with >=50 trades each, at least three of five symbols
  non-negative, and maximum positive-PnL symbol concentration <=30%.
- Otherwise REJECT. Even KEEP is reverse-time external confirmation, not production evidence;
  a fresh prospective VST cohort remains mandatory.

## Limitations

The holdout predates the discovery sample, so it is independent but reverse-time rather than a
forward chronological OOS period. Funding remains unavailable and unmodeled.
