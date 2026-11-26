# E44 — Cross-sectional positioning factors from Binance metrics (2026-11-26)

**Data.** New information family: free Binance `metrics` archive.
- 619 liquid perpetuals, 2020-09..2026-11; 536,069 daily files reduced to hourly values.
- Stored in `data/lake/binance_um/metrics_1h`, 562 MB.

**Method.** Pre-registered in commit c65d789, before the data was read.
- Frozen V1 machinery on the names that have metrics (median 127 per day).
- All 7 weekly phases, paired.
- DEV 2020-09..2023-12; TEST 2024-01..2026-10, read once for this family.

## Factors (directions fixed in advance)

- **F_RETAIL:** against crowded retail accounts. −3-day mean of log(all-account long/short ratio).
- **F_TOP:** with the top traders. +3-day mean of log(top-trader position ratio).

## Results (phase means, annual)

| Signal | DEV net | DEV Sharpe | TEST net | TEST Sharpe | TEST funding |
|---|---|---|---|---|---|
| F_RETAIL | +6.1 % | 0.60 | +32.8 % | 1.29 | +20.3 % |
| F_TOP | −5.3 % | −0.80 | −13.0 % | −0.63 | −20.3 % |
| V1 (same universe) | +11.3 % | 1.25 | +24.9 % | 1.10 | +29.4 % |
| V1 + F_RETAIL | +10.4 % | 1.02 | +37.4 % | 1.57 | +31.8 % |
| V1 + F_TOP | +5.6 % | 0.63 | +11.8 % | 0.56 | +20.0 % |

**Pre-registered verdicts**

| Signal | Result | Why |
|---|---|---|
| F_RETAIL standalone | **FAIL** | DEV Sharpe 0.60, below 0.75 |
| F_TOP standalone | **FAIL** | Negative in both windows |
| V1 + F_RETAIL | **NOT A CANDIDATE** | DEV −0.9 %/yr (2/7 phases); TEST +12.4 %/yr (7/7 phases) |
| V1 + F_TOP | **NOT A CANDIDATE** | Worse in both windows, 0/7 phases |

## Reading

- **Following top traders loses money in both eras.** Its funding leg is −20 %/yr: top traders tend to be on the crowded, funding-paying side.
- **Fading crowded retail accounts is the strongest new signal in this project since XS-COMBO, but only in 2024–26.**
  - TEST Sharpe 1.29, 7/7 phases better than V1 when combined (+12.4 %/yr).
  - In 2020–23 it was weak: Sharpe 0.60, and slightly worse than V1 when combined.
  - About 60 % of its 2024–26 return is funding. It partly overlaps the carry factor: crowded retail longs pay funding.
- **By the pre-registered rule it is not adopted and goes to no shadow stage.** The rule required the improvement in both windows.
- **A prospective shadow test would need its own pre-registration.** It is cheap: F_RETAIL picks logged next to XS-COMBO, no trading. That is an operator decision, recorded as R28.

## Limits

- The metrics universe starts 2020-09 and covers only symbols that had metrics.
- V1 on this restricted universe differs from the headline V1 numbers.
