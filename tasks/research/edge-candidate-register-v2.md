# Edge Candidate Register v2

**Status:** PRE-REGISTERED — SHADOW RESEARCH ONLY

This version preserves C-01 through C-03 from v1 without amendment and adds C-04 after TASK
001/002 identified VWAPReversal as the only adequately sampled positive residual strategy.
No result authorizes production or capital changes.

## Frozen Evaluation Protocol

- Data: existing closed-candle history only.
- Universe: BTCUSDT, ETHUSDT, and SOLUSDT; XMR and all post-hoc winning-symbol selection are
  excluded from candidate definition.
- Costs: existing 0.10% fee and 0.05% slippage per side, 0.30% round trip.
- Regime values use only the current and earlier closed bars. Higher-timeframe values, if used,
  must be forward-filled, shifted one completed HTF bar, and aligned to the decision bar.
- Four chronological, disjoint OOS folds; no parameter or universe amendment after results.
- BUY and SELL are reported separately before any aggregate conclusion.
- Eligibility: positive cost-adjusted expectancy in at least 3/4 adequately sampled folds,
  aggregate PF > 1, no single-symbol dependence, and no risk-control violation.
- Fixed-horizon signal returns are diagnostic evidence only. Production eligibility additionally
  requires path-dependent SL/TP simulation using candle high/low, SL-before-TP priority when
  both occur in one candle, and realistic execution prices.

## C-01 — Trend Continuation, Long Only

Unchanged from v1.

## C-02 — Trend Continuation, Short Only

Unchanged from v1.

## C-03 — Volatility Breakout

Unchanged from v1.

## C-04 — VWAP Reversal in Ranging Regimes

**Falsifiable hypothesis:** Existing VWAPReversal signals on liquid BTC/ETH/SOL contracts have
positive cost-adjusted expectancy in ranging regimes across at least three of four chronological
OOS folds. The relationship must survive side separation and may not depend on one symbol.

**Universe:** BTCUSDT, ETHUSDT, SOLUSDT only.
**Direction:** BUY and SELL evaluated separately.
**Regime:** ranging, reconstructed point-in-time.
**Entry:** existing VWAPReversal adapter with existing production configuration.
**Exit diagnostic:** predeclared design-timeframe fixed horizon, net of 0.30% round-trip cost.
**Path-dependent confirmation:** existing protective SL/TP semantics; candle high/low and
SL-priority required.
**Primary metric:** cost-adjusted OOS expectancy per signal/trade.
**Secondary metrics:** N, PF, win rate, payoff, drawdown, symbol/side/fold stability.

## Rejection Rules

Reject C-04 if fewer than three adequately sampled folds are positive, aggregate PF is not above
one, performance depends on one symbol/side, costs erase the edge, or path-dependent confirmation
contradicts the fixed-horizon diagnostic.
