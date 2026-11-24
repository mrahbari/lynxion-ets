# E23 / E24 — funding-extreme and OI-flush reversal as standalone signals (2026-11-24)

Both pre-registered and committed before running (research/v2/experiments/e23_funding_extreme.py,
e24_oi_flush.py). Binance USDT-M 1h klines, funding and 5m OI; DEV to 2024-12-31, HOLDOUT 2025-01-01 on;
costs 5 bp + 2 bp per side, real funding during the hold, 2 x ATR protective stop.

| test | variant | DEV n / net bp / t | HOLDOUT n / net bp / t | verdict |
|---|---|---|---|---|
| E23 funding z >= 2 reversal | V1 24 h (primary) | 2384 / -11.4 / -0.97 | 767 / -8.1 / -0.61 | FAIL |
| | V2 8 h | 2811 / -15.5 / -2.18 | 836 / -21.5 / -2.52 | |
| | V3 z >= 3, 24 h | 1236 / -15.0 / -0.82 | 226 / +15.2 / +0.54 | |
| E24 OI flush (z dOI <= -2.5, abs z dP >= 2) | V1 12 h (primary) | 533 / -13.4 / -0.79 | 178 / -39.0 / -1.46 | FAIL |
| | V2 4 h | 548 / -10.5 / -0.90 | 183 / -31.2 / -1.83 | |
| | V3 z <= -3, 12 h | 384 / -9.2 / -0.46 | 111 / -49.3 / -1.32 | |

**Both FAIL.** Timing reversals on funding extremes or OI flushes lose after costs; the funding received on
the crowded side (+7 bp per trade on DEV for E23) does not offset the price move against it. In 2025-26
almost all funding extremes were negative (crowded shorts; 94 % LONG signals).
Funding works in this project only as diversified, market-neutral CARRY (XS-COMBO-V1), not as a
single-symbol timing signal.
