# Edge Candidate Register v28 — C-29 Top-Trader / Crowd Positioning Divergence

**Status:** PREREGISTERED — OUTCOMES UNOPENED

C-29 tests a previously unused derivatives-sentiment mechanism. When the broad account crowd is
extremely positioned in one direction but top-trader position size is on the opposite side, the
top-trader direction may contain information over the next day. This is not a new OI, taker-flow,
price-reversal, or momentum specification; the two positioning-ratio columns have not been used by
prior candidate outcomes.

## Sequential-Policy Admission

- Mechanism family: cross-cohort positioning divergence, not previously evaluated.
- Inputs are official point-in-time Binance Futures five-minute metrics already normalized under
  TASK-0106 and exact native futures price/funding files already frozen in prior registers.
- A 24-hour horizon is used because the hypothesis concerns slow crowd positioning rather than
  microstructure; gross movement is economically capable of clearing the frozen cost.
- This register freezes one primary specification before any conditional return is calculated.

## Frozen Data and Boundaries

- Symbols: BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, and SOLUSDT.
- Positioning inputs: `count_long_short_ratio` (global account crowd) and
  `sum_toptrader_long_short_ratio` (top-trader position size) from the normalized official metrics.
- Exact metrics SHA-256: BTC `1eb3cf846545e975f2be6ed32bc49a0333a6f7d07e4125c623bbc6fc12adbce6`,
  ETH `5eb10e69e01ad26f02cbf0164eaea6cc7348d80f698d3d285db25ff737cffc11`, BNB
  `910cbb0644779fda188c24eedb302b30a14c54a517208d9b226a8ac40dea582d`, XRP
  `64aaf6be57a3036687319c043f5a7da08e4ee385a07c2d72d0089cbba35996fe`, ADA
  `0c1c29430a77e04c96a4c35c99bbb0f6b4400787fee0641f26bc10739a031d53`, and SOL
  `8aec2bcdfcc72c23cd88d6cb0a54f886eead0d5f345e6549632ddf14938b1718`.
- Price and funding inputs and their exact hashes are unchanged from C-28's frozen six-symbol
  TASK-0094/TASK-0106 files; the evaluator must enforce every full hash before calculating outcomes.
- Primary: 2023-01-01 through 2026-08-29. Temporal reverse: 2021-12-01 through 2022-12-31.
- No interpolation, forward fill, nearest match, or synthetic observation is allowed.

## Frozen Signal

- Decisions occur at exact four-hour UTC boundaries.
- For each decision, use only the exact metrics observation five minutes earlier. A missing exact
  observation rejects the decision.
- Require both ratios to be finite and strictly positive. Transform them as
  `crowd = log(count_long_short_ratio)` and `top = log(sum_toptrader_long_short_ratio)`.
- From the prior 180 valid four-hour decisions for that symbol, excluding current, calculate the
  p90 of `abs(crowd)` and the p90 of `abs(top-crowd)`.
- Signal only when `crowd` and `top` have strictly opposite signs, `abs(crowd)` is strictly above
  its causal p90, and `abs(top-crowd)` is strictly above its causal p90.
- Trade with top-trader positioning: top above zero => LONG; top below zero => SHORT.
- No price, OI, taker, funding, regime, volume, symbol-ranking, hour, or diagnostic filter is used.

## Frozen Execution and Economics

- Enter at the exact native 15-minute open at the decision timestamp; exit at the exact open 96
  bars later (24 hours). Require all 97 timestamps to be contiguous.
- One position per symbol; retain the earliest signal and reject overlaps.
- Include official funding settlements strictly after entry and at or before exit: LONG pays and
  SHORT receives funding.
- Charge 0.30% round trip; report frozen 0.20% and 0.50% sensitivities.

## Frozen Reporting and Gate

- Report alignment, validity, warmup, threshold, signal, path, and overlap census; N, expectancy,
  PF, win rate, drawdown, funding, costs, folds, sides, symbols, years, and concentration.
- Form four global chronological primary folds and cluster-bootstrap 10,000 samples by UTC entry
  day with seed 290029.
- KEEP requires every condition: primary N>=300; expectancy>0; PF>1; clustered 95% lower bound>0;
  >=3/4 positive folds with N>=50; both sides positive with N>=75; >=4/6 symbols positive with
  N>=40; every primary calendar year positive with N>=50; maximum positive-PnL symbol
  concentration<=35%; temporal reverse N>=150 with expectancy>0 and PF>1; and positive primary
  expectancy at 0.50% cost.
- Any failed condition is REJECT. A pass is only `KEEP_FOR_PROSPECTIVE_VALIDATION`.

## Frozen Prohibitions

No ratio definition, threshold, lookback, alignment, direction, horizon, cost, funding rule,
overlap rule, period, symbol, fold, cluster, or gate may change after outcomes open. Diagnostics
cannot alter the verdict. No order or production strategy/risk/trailing/symbol/leverage change is
authorized.
