# E35 — MeanReversion rebuilt with a funding (crowding) condition, 4h (operator request, 2026-11-24)

Pre-registered and committed before the run (research/v2/experiments/e35_funding_mean_reversion.py).
Bollinger(20, 2) stretch on closed 4h bars; LONG only with funding <= 0, SHORT only with funding >= 0.02 %;
exit at SMA20, 72 h, or 2.5 ATR stop; 7 bp per side; real funding. CONTROL = no funding condition.

| arm | window | trades | net bp / trade | t | win | funding bp | long share | symbols + |
|---|---|---|---|---|---|---|---|---|
| FUNDING | DEV 2020-24 | 1,398 | **-61.7** | -2.91 | 0.523 | +18.3 | 0.50 | 3/10 |
| FUNDING | HOLDOUT 2025-26 | 562 | -25.8 | -1.16 | 0.548 | +0.6 | 1.00 | 1/10 |
| CONTROL | DEV | 4,768 | -54.8 | -5.59 | 0.525 | +5.0 | 0.48 | 1/10 |
| CONTROL | HOLDOUT | 1,937 | -13.7 | -1.20 | 0.550 | +0.9 | 0.52 | 2/10 |

**FAIL.** Fading 2-sigma moves at 4h loses in crypto: small frequent wins back to the mean, large losses when
the move continues (stop). Being on the side that receives funding (+18 bp per trade on DEV) does not offset
the price leg, and the funding condition selects WORSE trades than the control (crowding persists before it
unwinds). Together with E9, E21, E25, E28, E31 (daily, gross only), E33, E34: single-symbol mean reversion has
no edge on liquid perps from 15m to 4h. MeanReversion stays off the live allowlist.
