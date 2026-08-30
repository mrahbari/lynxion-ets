# Edge Candidate Register v15 — C-16 OI-Confirmed Price Impulse

**Status:** PRE-REGISTERED — CONDITIONAL OUTCOMES UNOPENED

C-16 is the single primary candidate admitted after TASK-0106. It tests the intended open-interest
mechanism that the legacy `oi_footprint` implementation never consumed: whether a large price move
supported by expanding open interest persists over the next day.

## Frozen Universe and Samples

- Symbols: BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, ADAUSDT, SOLUSDT.
- Price: native Binance Futures 15m panels from TASK-0094/0098.
- OI: official Binance Data Vision five-minute metrics kept by TASK-0106.
- Funding: public Binance Futures settlement history, acquired after this register if missing.
- Primary period: 2023-01-01 through 2026-08-29.
- Reverse-time confirmation: common available interval beginning 2021-12-01 through 2022-12-31.

## Frozen Causal Features

- Decision timestamps are exact four-hour UTC boundaries.
- Price impulse uses the last completed 15m close before decision versus the completed close
  exactly four hours earlier.
- OI expansion uses the last OI observation strictly before decision versus the observation
  exactly four hours earlier; missing exact observations invalidate that decision.
- At each decision, calculate causal rolling p75 thresholds from the prior 180 valid four-hour
  decisions, excluding current, separately per symbol for absolute price return and OI return.
- Signal only when absolute price impulse >= its p75, OI return is positive and >= its p75.
- Positive price impulse => LONG; negative price impulse => SHORT; zero => no trade.

## Frozen Execution and Economics

- Enter at the exact 15m open at the decision timestamp.
- Exit at the exact 15m open 96 bars/24 hours later.
- One position per symbol; reject signals before the previous exit.
- Add actual intervening funding cashflows with correct LONG/SHORT sign.
- Charge 0.30% round trip; report 0.20% and 0.50% sensitivity.
- No ratio, regime, volume, symbol-ranking, severity, or post-result filter.

## Frozen Reporting and Gate

- Separate primary/reverse samples, four primary chronological folds, symbol, side, cost, price
  return, funding contribution, and OI/price impulse diagnostic buckets.
- Deterministic day-cluster bootstrap preserves cross-symbol dependence.
- KEEP requires every condition:
  - primary expectancy > 0, PF > 1, bootstrap 95% lower bound > 0;
  - at least 3/4 positive primary folds with >=100 trades each;
  - LONG and SHORT each positive with >=100 primary trades;
  - at least four of six symbols positive with >=80 primary trades;
  - no symbol above 35% of positive PnL;
  - reverse-time expectancy > 0 and PF > 1 with >=300 trades;
  - expectancy positive at 0.50% cost.

A pass is `KEEP_FOR_PATH_DEPENDENT_CONFIRMATION`; otherwise `REJECT`. Historical evidence cannot
modify production, risk controls, or orders.
