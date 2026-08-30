# Edge Candidate Register v14 — C-15 Independent Long-Only Trend Holdout

**Status:** PRE-REGISTERED — NEW UNIVERSE UNOPENED

C-14 exposed a positive LONG and strongly negative SHORT split in its primary period. C-15
tests the LONG-only clue once on a new symbol universe. It does not reslice or amend C-14.

## Frozen Data and Universe

- Native Binance USDT-margined futures 15m bars, 2023-01-01 through 2026-08-29.
- New frozen universe: DOGEUSDT, LINKUSDT, LTCUSDT, DOTUSDT, AVAXUSDT.
- These symbols' C-14/C-15 conditional outcomes are unopened at this boundary.
- Acquisition must record checksums, exact coverage, duplicates, gaps, OHLC integrity, and
  Binance Futures provenance before evaluation.

## Frozen Signal and Execution

- Reuse C-14 without parameter changes: 180 completed UTC daily closes, final closed day of
  each month, first exact next 15m open, and first exact open at least 28 days later.
- LONG only when trailing 180-day return is positive; negative or zero observations are no-trade.
- One position per symbol; ignore overlapping monthly signals.
- Primary round-trip cost 0.30%; sensitivity 0.20% and 0.50%.
- No symbol ranking, volatility, funding, regime, or confidence filter.

## Frozen Gate

Every condition is required:

- Net expectancy > 0, PF > 1, and month-cluster bootstrap 95% lower bound > 0.
- At least 3/4 chronological folds positive with >=20 trades each.
- At least four of five symbols positive with >=15 trades each.
- No symbol above 35% of positive PnL.
- Positive expectancy at 0.50% cost.

A pass is `KEEP_FOR_PATH_DEPENDENT_CONFIRMATION`; otherwise `REJECT`. No production or risk
mutation is authorized.
