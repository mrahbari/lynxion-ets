# Edge Candidate Register v7 — C-08 Daily Relative-Strength Continuation

**Status:** PRE-REGISTERED — SHADOW RESEARCH ONLY

This longer-horizon hypothesis is frozen before C-08 output. It tests whether relative moves
large enough to overcome friction persist; it does not retune rejected intraday candidates.

## Hypothesis

When dispersion of 24-hour altcoin returns relative to BTC is historically elevated, the
strongest major should continue outperforming and the weakest should continue underperforming
over the next 24 hours. A paired LONG/SHORT position should reduce broad-market exposure.

## Frozen Features and Decision

- TASK-0094 aligned native futures 15m panel.
- BTCUSDT is the market benchmark. Tradable symbols are ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT,
  and ADAUSDT.
- Decide once per UTC day (`timestamp % 86400 == 0`) from completed bars.
- Relative strength is each alt's prior 96-bar return minus BTC's prior 96-bar return.
- Cross-sectional spread is maximum minus minimum relative strength.
- Trade only when current spread is strictly above the median of the prior 180 daily spreads;
  current spread is excluded. Otherwise emit NO TRADE.
- LONG the strongest relative symbol and SHORT the weakest; deterministic lexicographic tie
  breaking. Exactly one pair or NO TRADE.

## Frozen Execution and Gate

- Enter next 15m open and exit at the open 96 bars after entry (24 hours).
- Charge 0.30% round trip per leg; sensitivity at 0.20% and 0.50%.
- One position per selected symbol and two portfolio positions. The prior pair exits before a
  new pair enters at the same open. Pairs cannot cross fold boundaries.
- Four chronological folds after the 180-day threshold warmup.
- Report equal-weight pair and leg metrics, deterministic decision bootstrap CI, folds, sides,
  symbols, spread-ratio buckets, BTC regime, and cost sensitivity.
- KEEP requires positive pair expectancy, PF > 1, CI lower bound > 0, at least 3/4 positive
  folds with >=100 pairs, both legs non-negative with >=100 observations, at least three of
  five symbols non-negative, and maximum positive-PnL symbol concentration <=30%.
- Otherwise REJECT; no automatic production or shadow promotion.

## Limitations

Funding is unavailable and fixed costs proxy execution friction. The fixed horizon is a signal
diagnostic, not production exit logic.
