# Edge Candidate Register v3 — C-01/C-02/C-03 Frozen Evaluation

**Status:** PRE-REGISTERED — SHADOW RESEARCH ONLY

This protocol resolves mechanical ambiguities in v1 before C-01/C-02/C-03 results are
observed. It does not change the candidate hypotheses, production strategies, risk controls,
or capital allocation.

## Shared Frozen Protocol

- Data: existing processed 15m closed candles for BTCUSDT, ETHUSDT, and SOLUSDT.
- Costs: 0.30% round trip (0.10% fee plus 0.05% slippage per side).
- Entry: next 15m bar open after the signal bar; the signal bar cannot fill its own order.
- Exit: the setup's existing stop-loss or take-profit level, evaluated from subsequent candle
  high/low. If both are touched in one candle, SL has priority. An adverse gap through SL fills
  at the bar open; a favorable gap through TP receives no improvement beyond the TP level.
- Position state: at most one open trade per symbol; later signals are ignored until exit.
- Unresolved trades at the end of a fold are excluded and explicitly counted.
- Folds: four chronological, disjoint folds per symbol. Positions may not cross fold boundaries.
- Metrics: N, net expectancy, PF, win rate, average win/loss, payoff ratio, and drawdown.
- Eligibility: positive net expectancy in at least 3/4 adequately sampled folds, aggregate
  PF > 1, no single-symbol dependence, and no side pooling where side separation is required.

## Point-in-Time Trend Filter for C-01/C-02

- 15m EMA20 versus EMA50 must agree with direction.
- 1h EMA20 versus EMA50 must agree with direction.
- The 1h value is forward-filled to 15m and shifted by one completed 1h bar before alignment.
- Wilder ADX(14), calculated only from the current and earlier closed 15m bars, must be >= 25.
- C-01 evaluates BUY signals from the existing TrendFollow adapter on BTC/ETH/SOL.
- C-02 evaluates SELL signals from the same adapter on BTC/ETH only.

## Volatility Expansion Filter for C-03

- Use the existing VolatilityBreakout strategy signal on BTC/ETH/SOL.
- ATR(14) on the signal bar must exceed 1.10 times the rolling median ATR of the prior 100
  completed 15m bars (the current ATR is excluded from the median).
- BUY and SELL are evaluated separately and both must be reported.

## Decision

Each candidate receives `KEEP_FOR_FURTHER_VALIDATION` or `REJECT`. No result changes the
production path automatically.
