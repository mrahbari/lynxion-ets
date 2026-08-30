# Edge Candidate Register v13 — C-14 Long-Horizon Time-Series Momentum

**Status:** PRE-REGISTERED — CONDITIONAL OUTCOMES UNOPENED

C-14 tests a low-turnover, long-horizon trend mechanism that is distinct from the rejected
short-horizon breakout, acceleration, reversal, cross-sectional ranking, and funding paths.
The protocol is frozen before evaluating any C-14 conditional outcomes.

## Hypothesis

A liquid perpetual contract's own trailing 180-day direction contains persistent information
about its following 28-day return large enough to survive a 0.30% round-trip cost.

## Data and Universe

- Native Binance USDT-margined futures 15m bars already integrity-checked by TASK-0094/0098.
- Primary temporal sample: 2023-01-01 through 2026-08-29.
- Independent reverse-time sample: 2020-01-01 through 2022-12-31.
- Frozen universe: BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- A symbol participates only after 180 complete UTC daily closes exist.

## Signal and Execution

- Construct UTC daily closes from closed 15m bars.
- On the final available closed UTC day of each calendar month, calculate the unannualized
  return from the close 180 calendar observations earlier to the current close.
- Positive return => LONG; negative return => SHORT; exact zero => no trade.
- Enter at the first exact 15m open after the decision timestamp.
- Exit at the first exact 15m open at least 28 days after entry.
- One position per symbol; monthly signals that occur before the prior exit are ignored.
- No volatility, regime, confidence, funding, or symbol-ranking filter.
- Charge 0.30% round trip; report 0.20% and 0.50% sensitivity.

## Frozen Reporting

- Funding is unavailable for the full combined price period and is an explicit limitation.
- Report gross/net expectancy, PF, win rate, payoff, drawdown, and sample count.
- Separate primary versus reverse-time sample, four chronological primary folds, symbol,
  direction, and cost sensitivity.
- Use a deterministic month-cluster bootstrap to preserve cross-symbol dependence.

## Frozen Gate

Every condition is required:

- Primary net expectancy > 0, PF > 1, and 95% month-cluster bootstrap lower bound > 0.
- At least 3/4 primary folds positive with >=30 trades each.
- Both LONG and SHORT positive with >=30 primary trades each.
- At least four of six symbols positive with >=20 primary trades each.
- No symbol contributes more than 40% of positive primary PnL.
- Reverse-time sample expectancy > 0 and PF > 1 with >=120 trades.
- Positive expectancy remains at 0.50% cost.

A pass is `KEEP_FOR_PATH_DEPENDENT_CONFIRMATION`, not production authorization. Otherwise the
candidate is `REJECT` with no parameter changes on opened outcomes.
