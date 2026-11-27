# E54 / E55 — XS-COMBO execution ideas from the repo study (2026-11-27)

Both were pre-registered in commit 0eb2ee3, before they were run. Frozen V1 machinery, 7 weekly phases.

## E54 — Smoothed targets (half new target, half last week's)

| Window | V1 Sharpe | Smoothed Sharpe | Phases better | Turnover cut | Cost/yr V1 → smoothed | Price leg V1 → smoothed |
|---|---|---|---|---|---|---|
| DEV 2020–24 | 1.79 | 1.81 | 4/7 | 35 % | 4.5 % → 2.7 % | +29.5 % → +25.9 % |
| TEST 2025–26 | 1.23 | 1.08 | 3/7 | 36 % | 6.6 % → 3.9 % | −3.7 % → −10.3 % |

**FAIL** (rule: Sharpe higher in both windows). The smoothing saves about 2–3 %/yr in costs. In 2025–26 the lagged book loses
more on price than it saves, because the signal decays within a week. V1 is unchanged.

## E55 — Seven staggered tranches (1/7 of the book rebalanced each day)

| Window | Tranche Sharpe | Single-phase Sharpe (min / median / max) | Cross-phase dispersion of rolling Sharpe | Order deltas < 6 USDT at a 3,200 book (count / notional) |
|---|---|---|---|---|
| DEV | **1.94** | 1.64 / 1.79 / 2.11 | 0.48 | 43 % / 12 % |
| TEST | **1.44** | **0.49** / 1.16 / 1.77 | 0.86 | 61 % / 32 % |

**Robustness: confirmed.** The tranche book beats the median single-phase book in both windows and removes the
phase lottery: TEST worst phase 0.49 against 1.44 for the tranches.

**Feasibility: FAIL at the VST book (3,200 USDT).** One seventh of the book is too small for BingX's 6 USDT minimum order,
so a third of the notional would be skipped.

Feasibility by book size (TEST period, order deltas below 6 USDT):

| Book | Share of orders (count) | Share of notional |
|---|---|---|
| 3,200 | 61 % | 32 % |
| 10,000 | 33 % | 2.4 % |
| 20,000 | 32 % | 2.2 % |
| 50,000 | 20 % | 0.9 % |

From about **10,000 USDT gross** the skipped orders are tiny re-weightings (2.4 % of notional). There, tranches are
feasible and remove a large source of outcome variance.

## Decision

- E54: no change.
- E55: no change on VST. **Recorded for the E12-3 real-capital package:** at ≥ 10k gross, run XS-COMBO as 7 daily
  tranches instead of one weekly rebalance. This needs an operator decision and a rebalancer schedule change.
- The live phase risk on VST remains. The R28 daily 7-phase shadow books already measure it.
