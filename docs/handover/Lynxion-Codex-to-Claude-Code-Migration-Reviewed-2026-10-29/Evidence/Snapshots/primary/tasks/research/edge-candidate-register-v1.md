# Edge Candidate Register v1

**Status:** PRE-REGISTERED — NOT IMPLEMENTED — SHADOW RESEARCH ONLY

This register was written before candidate evaluation. No candidate may be
amended after observing an OOS fold; an amendment creates a new version and
restarts evaluation.

## Shared Evaluation Protocol

- Market: BingX perpetual futures, liquid USDT contracts only.
- Costs: realized exchange fees and slippage; no zero-cost evaluation.
- Data: closed candles only, with all MTF series forward-filled then shifted by
  one completed higher-timeframe bar.
- Splits: four chronological, disjoint OOS folds; selection uses no OOS data.
- Candidate eligibility: positive net expectancy in at least 3/4 folds, PF > 1
  in aggregate and no OOS fold with a risk-control violation.

## C-01 — Trend Continuation, Long Only

**Hypothesis:** Trend-following long entries exhibit positive net expectancy
only when 15m and 1h EMA direction agree, ADX indicates a persistent trend,
and spread is within the existing execution-quality guard.

**Universe:** BTCUSDT, ETHUSDT, SOLUSDT only.  
**Direction:** BUY only.  
**Regime:** trending_up.  
**Entry/exit:** Existing TrendFollow signal and its existing protective SL/TP;
no new indicator or exit logic.  
**Primary metric:** net OOS expectancy per completed trade.  

## C-02 — Trend Continuation, Short Only

**Hypothesis:** Short-side trend continuation has different economics and must
be measured separately, not pooled with C-01.

**Universe:** BTCUSDT, ETHUSDT only; excludes restricted-short symbols.  
**Direction:** SELL only.  
**Regime:** trending_down.  
**Entry/exit:** Existing TrendFollow signal and existing protection.  
**Primary metric:** net OOS expectancy per completed trade.  

## C-03 — Volatility Breakout

**Hypothesis:** Breakout entries are viable only during volatility expansion,
not low-volatility consolidation.

**Universe:** BTCUSDT, ETHUSDT, SOLUSDT.  
**Direction:** evaluated separately for BUY and SELL.  
**Regime:** volatility expansion.  
**Entry/exit:** Existing volatility-breakout signal and existing protection.  
**Primary metric:** net OOS expectancy per completed trade.  

## Promotion Rule

No C-01/C-02/C-03 result authorizes live execution. A passing result becomes
eligible only for Task0081 shadow/paper validation.
