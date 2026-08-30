# Edge Candidate Register v16 — C-17 OI-Flush Exhaustion Reversal

**Status:** PRE-REGISTERED — NEW CONDITIONAL UNIVERSE UNOPENED

C-17 tests a causally distinct OI mechanism from C-16. C-16 asked whether expanding OI confirms
continuation; C-17 asks whether a large price move accompanied by contracting OI indicates
position closure/exhaustion and reverses over the next day.

## Frozen Universe and Samples

- Symbols: DOGEUSDT, LINKUSDT, LTCUSDT, DOTUSDT, AVAXUSDT.
- Primary: 2023-01-01 through 2026-08-29.
- Reverse-time: 2021-12-01 through 2022-12-31, subject to exact common data availability.
- Native Binance Futures 15m price, official Data Vision five-minute OI, and actual Binance
  funding settlements are acquired/checksummed before evaluation.
- C-16 symbols are excluded; C-17 OI-conditioned outcomes are unopened at this boundary.

## Frozen Signal

- Exact four-hour UTC decisions and strict pre-decision alignment identical to C-16.
- Absolute completed-price return threshold: causal p75 of prior 180 valid decisions.
- OI contraction magnitude `-oi_return` threshold: causal p75 of prior 180 valid decisions.
- Signal only when absolute price return >= threshold, OI return is negative, and contraction
  magnitude >= threshold.
- Trade opposite the price impulse: positive impulse => SHORT; negative impulse => LONG.
- No ratio, funding-level, regime, volume, symbol-ranking, or diagnostic filter.

## Frozen Execution and Gate

- Exact next 15m open, exact 24h exit, per-symbol overlap rejection.
- Actual funding with correct side sign; costs 0.20%, 0.30% primary, and 0.50%.
- Day-cluster bootstrap and separate primary/reverse, fold, side, symbol, and funding reports.
- KEEP requires every condition:
  - primary expectancy > 0, PF > 1, bootstrap lower bound > 0;
  - at least 3/4 positive folds with >=80 trades each;
  - both sides positive with >=80 trades each;
  - at least four of five symbols positive with >=60 trades each;
  - maximum positive-PnL symbol concentration <=35%;
  - reverse-time expectancy > 0, PF > 1, N>=200;
  - expectancy positive at 0.50% cost.

A pass is historical KEEP only. No production or risk mutation is authorized.
