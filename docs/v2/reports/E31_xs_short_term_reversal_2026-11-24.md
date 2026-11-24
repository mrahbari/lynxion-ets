# E31 — cross-sectional 1-day reversal, daily, market-neutral (2026-11-24)

Pre-registered and committed before the run (research/v2/experiments/e31_xs_short_term_reversal.py).

| window | net Sharpe | gross Sharpe | net / yr | cost / yr | turnover / day |
|---|---|---|---|---|---|
| DEV 2020-24 | -1.86 | **+0.67** | -43.5 % | -57.6 % | 1.35 |
| HOLDOUT 2025-26 | -2.08 | **+0.39** | -61.2 % | -71.6 % | 1.50 |

**FAIL.** The reversal signal is real before costs in both windows (gross Sharpe 0.67 / 0.39, matching the
literature) but daily rebalancing turns over 135-150 % of the book per day and costs ~60-70 %/yr. Not tradable
as a standalone strategy. Possible non-standalone use (new idea, not tested): time XS-COMBO's weekly rebalance
trades with the reversal signal (buy names after a down day) — costs nothing extra in turnover.
