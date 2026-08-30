# Edge Candidate Register v4 — C-05 Cross-Sectional Momentum

**Status:** PRE-REGISTERED — SHADOW RESEARCH ONLY

This protocol is frozen before C-05 evaluation output is generated. It tests whether dynamic
symbol selection contains conditional information; it does not change production strategy,
universe, risk, sizing, or execution logic.

## Hypothesis

Among sufficiently liquid USDT perpetuals, the strongest four-hour relative-momentum symbols
should have positive next-four-hour net returns when the broad cross-section is rising, and the
weakest symbols should have positive short returns when the broad cross-section is falling.
LONG, SHORT, and NO TRADE are distinct outcomes.

## Point-in-Time Universe and Features

- Source: existing processed closed 15m `*-USDT.csv` candles only.
- A symbol is eligible at a rebalance only after 96 prior completed bars and a valid next-bar
  open plus 16-bar forward exit open exist.
- XMR-USDT is excluded because it is currently safety-restricted; stablecoin-like bases whose
  base contains `USD` are excluded.
- Liquidity is trailing median quote volume (`close * volume`) over the prior 96 completed
  bars, including the just-closed decision bar and no future bar.
- Retain the 50 highest-liquidity eligible symbols at each rebalance. Require at least 30;
  otherwise emit NO TRADE.
- Momentum is close-to-close return over the prior 16 completed 15m bars.
- Broad-market context is the median 16-bar momentum of the point-in-time liquid universe.
  This replaces BTC context because the stored BTC history overlaps the broad universe for
  only about one day; inventing unavailable BTC context is prohibited.

## Frozen Decision and Execution

- Rebalance every 16 bars on timestamps common to at least 30 eligible symbols.
- If broad median momentum is positive, select at most the top three momentum symbols LONG.
- If broad median momentum is negative, select at most the bottom three symbols SHORT.
- If the median is exactly zero or eligibility fails, take NO TRADE.
- Enter at the next 15m bar open and exit at the open 16 bars later (four-hour fixed horizon).
- Charge 0.30% round trip (0.10% fee plus 0.05% slippage per side).
- At most one concurrent trade per symbol and at most three concurrent portfolio positions.
  Rebalances while positions remain open cannot exceed those limits.
- Missing entry/exit bars reject that observation; prices are never forward-filled for fills.

## Validation and Decision Gate

- Split the common chronological decision timestamps into four disjoint folds. Positions may
  not cross fold boundaries; unresolved observations are excluded and counted.
- Report N, net expectancy, PF, win rate, average win/loss, payoff ratio, drawdown, bootstrap
  95% confidence interval, LONG/SHORT separation, fold stability, and symbol concentration.
- Evaluate cost sensitivity at 0.20%, 0.30% primary, and 0.50% round trip without retuning.
- `KEEP_FOR_FURTHER_VALIDATION` requires primary-cost expectancy > 0, PF > 1, a bootstrap
  confidence interval lower bound > 0, at least 3/4 positive folds with at least 30 trades
  each, both directions non-negative with at least 30 trades each, and no single symbol
  contributing more than 20% of total positive PnL.
- Any other result is `REJECT`. A KEEP result is not production authorization.

## Known Limitation

The files represent contracts retained in the current historical store rather than a complete
point-in-time exchange listing history. Survivorship/listing availability therefore remains a
deployment blocker even if the diagnostic passes.
