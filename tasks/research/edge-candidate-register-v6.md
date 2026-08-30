# Edge Candidate Register v6 — C-07 Volume-Confirmed Acceleration

**Status:** PRE-REGISTERED — SHADOW RESEARCH ONLY

This orthogonal hypothesis is frozen before C-07 output. It does not retune C-06 and uses
price/volume/context variables named in the supervisor directive.

## Hypothesis

An altcoin's directional acceleration should have positive next-four-hour expectancy only when
the move is confirmed by abnormal volume and agrees with BTC's completed 24-hour regime.
Otherwise the correct outcome is NO TRADE.

## Frozen Features and Universe

- TASK-0094 native futures 15m panel; BTCUSDT is context only.
- Tradable research universe: ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT.
- Decisions are hourly (`timestamp % 3600 == 0`) using completed bars.
- BTC regime: BTC 96-bar return; positive permits LONG and negative permits SHORT.
- Symbol momentum: prior 16-bar return.
- Acceleration: current 16-bar return minus the immediately preceding non-overlapping 16-bar
  return. It must have the same sign as the intended direction.
- Relative volume: current completed-bar volume divided by the median of the prior 96 completed
  volumes, excluding the current bar; require >= 2.0.
- LONG requires positive BTC regime, positive symbol momentum, and positive acceleration.
  SHORT requires all three negative. Rank eligible symbols by absolute acceleration and admit
  at most three. If none qualify, emit NO TRADE.

## Frozen Execution and Validation

- Enter next 15m open; exit at the open 16 bars after entry (four hours).
- 0.30% primary round-trip cost per trade; sensitivity at 0.20% and 0.50%.
- At most one position per symbol and three portfolio positions. Hourly candidates are ignored
  while a symbol remains open or capacity is full; exits at an entry open occur first.
- Four chronological folds; positions may not cross boundaries.
- Report N, expectancy, PF, win rate, payoff, drawdown, decision-cluster bootstrap 95% CI,
  folds, sides, symbols, BTC regimes, relative-volume buckets, and cost sensitivity.
- KEEP requires net expectancy/PF > 0/1, CI lower bound > 0, at least 3/4 positive folds with
  >=100 trades each, both sides non-negative with >=100 trades, at least three of five symbols
  non-negative, and maximum positive-PnL symbol concentration <=30%.
- Otherwise REJECT. No result directly authorizes production or shadow deployment.

## Limitations

Funding is unavailable. Fixed-horizon exits isolate entry/selection information and do not
represent production exit management.
