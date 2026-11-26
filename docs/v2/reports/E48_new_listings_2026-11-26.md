# E48 — Shorting new Binance perp listings (2026-11-26)

**Method.** Pre-registered: `research/v2/experiments/e48_new_listings.py`.
- Short at the close of listing day +1, hedged with a long 50/50 BTC/ETH position.
- Hold 30 days, with a hard stop at +30 %.
- Net of costs and funding.
- Day-1 volume ≥ $20M. Delisted contracts are included.

| Window | Listings | Primary mean | Primary median | t (week) | Win % | Stopped | No-stop mean | No-stop median | No-stop win % |
|---|---|---|---|---|---|---|---|---|---|
| 2021–24 | 259 | +6.1 % | +7.0 % | 3.0 | 55 % | 46 % | +9.9 % (t 3.9) | **+23 %** | **77 %** |
| 2025–26 | 266 | +2.5 % | −16 % | −0.1 | 46 % | 52 % | +0.9 % (t 0.75) | **+25 %** | **73 %** |

**FAIL** (TEST mean below 50 % of DEV, t < 2).

## Reading

- **New listings usually fall a lot.** Over 30 days the median listing lost about 23–25 % against BTC/ETH, and about three in four fell, in both eras. This is the same picture as the unlock study (E47): new supply weighs on price.
- **The tail is the problem.**
  - A minority of listings multiply, so the average short barely profits in 2025–26.
  - A 30 % stop is hit by ordinary volatility about half the time, before the fall, so it hurts.
- **Era decay again.** +9.9 % per event in 2021–24, +0.9 % in 2025–26. The trade has become crowded or the market changed. Funding also turned against the short in 2025–26 (−1.2 % per event).
- **Nothing adopted. No new shadow.** A second calendar shadow next to R31 would be fishing on the same "new supply" idea; R31 already tests it on future data.
